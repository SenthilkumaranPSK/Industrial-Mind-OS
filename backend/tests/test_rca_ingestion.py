"""
Unit test suite for RCA Ingestion, Timeline Extraction & Evidence Citation Engine.
Location: backend/tests/test_rca_ingestion.py

Covers chronological sorting, out-of-order telemetry logs, deviation calculations,
Near_Miss_Report_2023.txt ingestion, citation indexing, excerpt retrieval, and assumption flagging.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import os
import pytest

from api.rca_schemas import CitationObject, FishboneBranch, FiveWhyNode, TimelineEvent
from services.rca_ingestion import (
    CitationRegistry,
    EvidenceCitationExtractor,
    TimelineExtractor,
    verify_causal_grounding,
)


# ==============================================================================
# 1. CITATION REGISTRY TESTS
# ==============================================================================

def test_citation_registry_registration_and_lookup():
    reg = CitationRegistry()
    cite = reg.register_citation(
        source_doc="Near_Miss_Report_2023.txt",
        excerpt="The maximum allowable vibration for Pump A12 is strictly 5.0 mm/s.",
        section="4. Corrective Action",
        page_or_line="Line 16",
        title="Near Miss Report",
        confidence=0.98,
    )
    assert cite.citation_id.startswith("CITE-NEARMISS-")
    found = reg.get(cite.citation_id)
    assert found is not None
    assert found.excerpt == cite.excerpt
    assert found.confidence == 0.98


def test_citation_registry_deterministic_id_slug():
    reg = CitationRegistry()
    c1 = reg.register_citation(source_doc="Pump-A12_Manual.pdf", excerpt="Manual excerpt 1")
    c2 = reg.register_citation(source_doc="Pump-A12_Manual.pdf", excerpt="Manual excerpt 2")
    assert c1.citation_id == "CITE-PUMPA12M-001"
    assert c2.citation_id == "CITE-PUMPA12M-002"


def test_citation_registry_deduplication_exact():
    reg = CitationRegistry()
    c1 = reg.register_citation(source_doc="Report.txt", excerpt="Identical excerpt")
    c2 = reg.register_citation(source_doc="Report.txt", excerpt="Identical excerpt")
    assert c1.citation_id == c2.citation_id
    assert len(reg.list_citations()) == 1


def test_citation_registry_validate_citation_ids():
    reg = CitationRegistry()
    c1 = reg.register_citation(source_doc="doc1.txt", excerpt="Excerpt one")
    valid_ids, invalid_ids = reg.validate_citation_ids([c1.citation_id, "CITE-GHOST-999"])
    assert valid_ids == [c1.citation_id]
    assert invalid_ids == ["CITE-GHOST-999"]
    # Test alias
    v2, inv2 = reg.validate_ids([c1.citation_id])
    assert v2 == [c1.citation_id]
    assert inv2 == []


def test_citation_registry_clear():
    reg = CitationRegistry()
    reg.register_citation(source_doc="doc.txt", excerpt="Excerpt here")
    assert len(reg.list_citations()) == 1
    reg.clear()
    assert len(reg.list_citations()) == 0


def test_citation_registry_register_existing_object():
    reg = CitationRegistry()
    c = CitationObject(
        citation_id="CITE-CUSTOM-001",
        source_doc="doc.txt",
        excerpt="Valid excerpt text",
    )
    cid = reg.register(c)
    assert cid == "CITE-CUSTOM-001"
    assert reg.get("CITE-CUSTOM-001") is not None


def test_citation_registry_thread_safety():
    reg = CitationRegistry()

    def worker(i: int):
        reg.register_citation(source_doc="ThreadDoc.txt", excerpt=f"Unique excerpt from worker {i}")

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(worker, range(40)))

    assert len(reg.list_citations()) == 40


def test_citation_registry_short_excerpt_rejection():
    reg = CitationRegistry()
    with pytest.raises(ValueError):
        reg.register_citation(source_doc="doc.txt", excerpt="ab")


# ==============================================================================
# 2. EVIDENCE CITATION EXTRACTOR TESTS
# ==============================================================================

def test_evidence_extractor_parse_markdown_headings():
    extractor = EvidenceCitationExtractor()
    content = """# Title
## Section One
First paragraph of section one with meaningful content.
## Section Two
Second paragraph with another detail."""
    cites = extractor.parse_markdown_document(content, "test.md")
    assert len(cites) >= 2
    assert any("Section One" in c.section for c in cites)
    assert any("Section Two" in c.section for c in cites)


def test_evidence_extractor_ingest_near_miss_file():
    extractor = EvidenceCitationExtractor()
    cites = extractor.ingest_near_miss_file()
    assert len(cites) >= 4
    # Verify key facts are present in citations
    excerpts_combined = " ".join([c.excerpt for c in cites])
    assert "5.8 mm/s" in excerpts_combined
    assert "5.0 mm/s" in excerpts_combined
    assert "5.5 mm/s" in excerpts_combined
    assert "ceramic seal" in excerpts_combined.lower()


def test_evidence_extractor_spaced_text_cleaned():
    extractor = EvidenceCitationExtractor()
    content = "## Section 1\nNotice that the C o n t a i n e r i z a t i o n of c e r a m i c elements failed."
    cites = extractor.parse_markdown_document(content, "spaced.md")
    assert len(cites) == 1
    assert "Containerization" in cites[0].excerpt
    assert "ceramic" in cites[0].excerpt


def test_evidence_extractor_confidence_exact_match():
    extractor = EvidenceCitationExtractor()
    excerpt = "Operating with a severe vibration level of 5.8 mm/s for 48 hours prior to failure."
    score = extractor.compute_retrieval_confidence(
        excerpt=excerpt,
        symptoms=["severe vibration", "failure"],
        telemetry_values={"vibration_mm_s": 5.8},
        source_authority=1.0,
    )
    assert score >= 0.90


def test_evidence_extractor_confidence_partial_match():
    extractor = EvidenceCitationExtractor()
    excerpt = "Minor fluid leak onto factory floor during operation."
    score = extractor.compute_retrieval_confidence(
        excerpt=excerpt,
        symptoms=["severe vibration", "shattered seal"],
        telemetry_values={"vibration_mm_s": 5.8},
        source_authority=1.0,
    )
    assert 0.1 <= score <= 0.6


def test_evidence_extractor_confidence_no_overlap():
    extractor = EvidenceCitationExtractor()
    excerpt = "The cafeteria menu was updated yesterday."
    score = extractor.compute_retrieval_confidence(
        excerpt=excerpt,
        symptoms=["pump vibration", "seal blowout"],
        telemetry_values={"pressure_bar": 12.0},
        source_authority=1.0,
    )
    assert score <= 0.4


def test_evidence_extractor_traverse_documents_empty():
    extractor = EvidenceCitationExtractor()
    assert extractor.traverse_documents([]) == []
    assert extractor.traverse_documents(None) == []


def test_evidence_extractor_traverse_documents_batch():
    extractor = EvidenceCitationExtractor()
    docs = [
        {"filename": "doc1.txt", "content": "## S1\nImportant info about bearings."},
        {"filename": "doc2.txt", "content": "## S2\nInspection checklist for motors."},
    ]
    results = extractor.traverse_documents(docs)
    assert len(results) >= 2


# ==============================================================================
# 3. TIMELINE EXTRACTOR TESTS
# ==============================================================================

def test_timeline_extractor_reconstruct_near_miss_ordering():
    extractor = TimelineExtractor()
    text = (
        "During routine operations, Pump A12 experienced a catastrophic mechanical seal failure. "
        "The pump had been operating with a severe vibration level of 5.8 mm/s for 48 hours prior to the failure. "
        "Operations personnel ignored the vibration alerts because they mistakenly believed the threshold was 6.5 mm/s. "
        "The spill was contained within 15 minutes by the emergency response team. "
        "Post-incident analysis revealed that sustained vibration at 5.8 mm/s shattered the inboard ceramic seals."
    )
    events = extractor.reconstruct_timeline(
        equipment_tag="Pump-A12",
        raw_text=text,
        incident_timestamp="2023-11-04T08:00:00Z",
    )
    assert len(events) >= 4
    # Confirm strictly chronological timestamps
    for i in range(len(events) - 1):
        t1 = datetime.fromisoformat(events[i].timestamp)
        t2 = datetime.fromisoformat(events[i + 1].timestamp)
        assert t1 <= t2


def test_timeline_extractor_out_of_order_telemetry_sorting():
    extractor = TimelineExtractor()
    logs = [
        {"timestamp": "2023-11-04T09:00:00Z", "description": "Post-event inspection", "event_id": "EVT-03"},
        {"timestamp": "2023-11-04T07:00:00Z", "description": "Pre-onset normal", "event_id": "EVT-01"},
        {"timestamp": "2023-11-04T08:00:00Z", "description": "Alarm excursion", "event_id": "EVT-02"},
    ]
    events = extractor.reconstruct_timeline(
        equipment_tag="Pump-A12",
        telemetry_logs=logs,
    )
    assert len(events) == 3
    assert events[0].event_id == "EVT-01"
    assert events[1].event_id == "EVT-02"
    assert events[2].event_id == "EVT-03"


def test_timeline_extractor_telemetry_deviation_critical():
    extractor = TimelineExtractor()
    logs = [
        {"timestamp": "2023-11-04T08:00:00Z", "vibration_mm_s": 5.8, "description": "Vibration excursion"}
    ]
    events = extractor.reconstruct_timeline(
        equipment_tag="Pump-A12",
        telemetry_logs=logs,
    )
    assert len(events) == 1
    evt = events[0]
    assert evt.parameters["deviation_pct"] == 16.0
    assert evt.parameters["is_exceeded"] is True
    assert evt.parameters["is_trip_exceeded"] is True


def test_timeline_extractor_telemetry_deviation_warning():
    extractor = TimelineExtractor()
    logs = [
        {"timestamp": "2023-11-04T08:00:00Z", "vibration_mm_s": 5.2, "description": "Vibration slight rise"}
    ]
    events = extractor.reconstruct_timeline(
        equipment_tag="Pump-A12",
        telemetry_logs=logs,
    )
    assert len(events) == 1
    evt = events[0]
    assert evt.parameters["deviation_pct"] == 4.0
    assert evt.parameters["is_exceeded"] is True
    assert evt.parameters["is_trip_exceeded"] is False


def test_timeline_extractor_telemetry_deviation_nominal():
    extractor = TimelineExtractor()
    logs = [
        {"timestamp": "2023-11-04T08:00:00Z", "vibration_mm_s": 4.0, "description": "Nominal vibration"}
    ]
    events = extractor.reconstruct_timeline(
        equipment_tag="Pump-A12",
        telemetry_logs=logs,
    )
    assert len(events) == 1
    evt = events[0]
    assert evt.parameters["deviation_pct"] == -20.0
    assert evt.parameters["is_exceeded"] is False
    assert evt.parameters["is_trip_exceeded"] is False


def test_timeline_extractor_telemetry_division_by_zero_guard():
    extractor = TimelineExtractor()
    extractor.OEM_ENVELOPES["ZeroAsset"] = {
        "vibration_mm_s": {"nominal_max": 0.0, "trip_limit": 0.0}
    }
    logs = [
        {"timestamp": "2023-11-04T08:00:00Z", "vibration_mm_s": 5.0}
    ]
    events = extractor.reconstruct_timeline(
        equipment_tag="ZeroAsset",
        telemetry_logs=logs,
    )
    assert len(events) == 1
    assert events[0].parameters["deviation_pct"] == 0.0


def test_timeline_extractor_relative_time_hours_prior():
    extractor = TimelineExtractor()
    anchor = datetime(2023, 11, 4, 8, 0, 0, tzinfo=timezone.utc)
    ts = extractor._extract_sentence_timestamp("Operating with high vibration for 48 hours prior to failure.", anchor)
    expected = anchor - datetime.resolution * 0
    from datetime import timedelta
    assert ts == anchor - timedelta(hours=48)


def test_timeline_extractor_relative_time_days_prior():
    extractor = TimelineExtractor()
    anchor = datetime(2023, 11, 4, 8, 0, 0, tzinfo=timezone.utc)
    ts = extractor._extract_sentence_timestamp("Discoloration noticed 3 days prior to failure.", anchor)
    from datetime import timedelta
    assert ts == anchor - timedelta(days=3)


def test_timeline_extractor_relative_time_within_minutes():
    extractor = TimelineExtractor()
    anchor = datetime(2023, 11, 4, 8, 0, 0, tzinfo=timezone.utc)
    ts = extractor._extract_sentence_timestamp("Spill contained within 15 minutes by response crew.", anchor)
    from datetime import timedelta
    assert ts == anchor + timedelta(minutes=15)


def test_timeline_extractor_relative_time_post_incident():
    extractor = TimelineExtractor()
    anchor = datetime(2023, 11, 4, 8, 0, 0, tzinfo=timezone.utc)
    ts = extractor._extract_sentence_timestamp("Post-incident teardown confirmed shattered ceramic seal.", anchor)
    from datetime import timedelta
    assert ts == anchor + timedelta(hours=4)


def test_timeline_extractor_event_classification_types():
    extractor = TimelineExtractor()
    assert extractor._classify_sentence("Catastrophic mechanical seal fracture and fluid spill") == "SYSTEM_FAILURE"
    assert extractor._classify_sentence("Operator ignored high vibration alarm") == "OPERATOR_ACTION"
    assert extractor._classify_sentence("Vibration alert reading 5.8 mm/s on DCS sensor") == "TELEMETRY_ALARM"
    assert extractor._classify_sentence("Routine maintenance inspection and lubrication round") == "MAINTENANCE_LOG"


def test_timeline_extractor_parameter_extraction_regex():
    extractor = TimelineExtractor()
    sentence = "Operating at 5.8 mm/s vibration, 82.5 °C temp, 14.2 bar pressure, and 3550 RPM with 15 liters leak."
    params = extractor._extract_parameters(sentence, "Pump-A12")
    assert params["vibration_mm_s"] == 5.8
    assert params["temperature_c"] == 82.5
    assert params["pressure_bar"] == 14.2
    assert params["rpm"] == 3550.0
    assert params["leak_volume_l"] == 15.0


def test_timeline_extractor_empty_inputs():
    extractor = TimelineExtractor()
    assert extractor.reconstruct_timeline(equipment_tag="Pump-A12", raw_text="", telemetry_logs=[]) == []


def test_timeline_extractor_missing_timestamp_fallback():
    extractor = TimelineExtractor()
    logs = [{"description": "Missing timestamp entry"}]
    events = extractor.reconstruct_timeline(equipment_tag="Pump-A12", telemetry_logs=logs)
    assert len(events) == 1
    assert "2023-11-04T08:00:00" in events[0].timestamp


def test_timeline_extractor_malformed_timestamp_string_fallback():
    extractor = TimelineExtractor()
    logs = [{"timestamp": "not-a-valid-date", "description": "Malformed timestamp"}]
    events = extractor.reconstruct_timeline(equipment_tag="Pump-A12", telemetry_logs=logs)
    assert len(events) == 1
    assert "2023-11-04T08:00:00" in events[0].timestamp


def test_timeline_extractor_citation_linking():
    extractor = TimelineExtractor()
    cites = [
        CitationObject(
            citation_id="CITE-VIB-01",
            source_doc="doc.txt",
            excerpt="High vibration 5.8 mm/s detected.",
        )
    ]
    logs = [
        {"timestamp": "2023-11-04T08:00:00Z", "description": "Severe vibration at 5.8 mm/s observed"}
    ]
    events = extractor.reconstruct_timeline(
        equipment_tag="Pump-A12",
        telemetry_logs=logs,
        citations=cites,
    )
    assert len(events) == 1
    assert "CITE-VIB-01" in events[0].citation_ids
    assert events[0].is_unsubstantiated is False


# ==============================================================================
# 4. VERIFY CAUSAL GROUNDING TESTS
# ==============================================================================

def test_verify_causal_grounding_all_grounded():
    reg = CitationRegistry()
    c1 = reg.register_citation(source_doc="doc1.txt", excerpt="Evidence 1")
    c2 = reg.register_citation(source_doc="doc2.txt", excerpt="Evidence 2")

    n1 = FiveWhyNode(why_id="W1", level=1, cause_statement="Statement 1", citation_ids=[c1.citation_id])
    n2 = FiveWhyNode(why_id="W2", level=2, cause_statement="Statement 2", citation_ids=[c2.citation_id])

    res = verify_causal_grounding([n1, n2], reg)
    assert res["grounding_ratio"] == 1.0
    assert res["compliance_status"] == "AUDIT_GROUNDED"
    assert n1.is_unsubstantiated is False
    assert n1.assumed_flag is False


def test_verify_causal_grounding_partial():
    reg = CitationRegistry()
    c1 = reg.register_citation(source_doc="doc1.txt", excerpt="Evidence 1")
    c2 = reg.register_citation(source_doc="doc2.txt", excerpt="Evidence 2")
    c3 = reg.register_citation(source_doc="doc3.txt", excerpt="Evidence 3")

    n1 = FiveWhyNode(why_id="W1", level=1, cause_statement="Statement 1", citation_ids=[c1.citation_id])
    n2 = FiveWhyNode(why_id="W2", level=2, cause_statement="Statement 2", citation_ids=[c2.citation_id])
    n3 = FiveWhyNode(why_id="W3", level=3, cause_statement="Statement 3", citation_ids=[c3.citation_id])
    n4 = FiveWhyNode(why_id="W4", level=4, cause_statement="Statement 4", citation_ids=[])

    res = verify_causal_grounding([n1, n2, n3, n4], reg)
    assert res["grounding_ratio"] == 0.75
    assert res["compliance_status"] == "PROVISIONAL_ACCEPTANCE"
    assert n4.is_unsubstantiated is True
    assert n4.assumed_flag is True
    assert n4.assumption_flag is True


def test_verify_causal_grounding_low():
    reg = CitationRegistry()
    c1 = reg.register_citation(source_doc="doc1.txt", excerpt="Evidence 1")

    n1 = FiveWhyNode(why_id="W1", level=1, cause_statement="Statement 1", citation_ids=[c1.citation_id])
    n2 = FiveWhyNode(why_id="W2", level=2, cause_statement="Statement 2", citation_ids=[])
    n3 = FiveWhyNode(why_id="W3", level=3, cause_statement="Statement 3", citation_ids=[])
    n4 = FiveWhyNode(why_id="W4", level=4, cause_statement="Statement 4", citation_ids=[])

    res = verify_causal_grounding([n1, n2, n3, n4], reg)
    assert res["grounding_ratio"] == 0.25
    assert res["compliance_status"] == "GROUNDING_DEFICIENT"


def test_verify_causal_grounding_empty_causes():
    reg = CitationRegistry()
    res = verify_causal_grounding([], reg)
    assert res["grounding_ratio"] == 0.0
    assert res["compliance_status"] == "GROUNDING_DEFICIENT"


def test_verify_causal_grounding_flags_unsubstantiated_and_assumptions():
    reg = CitationRegistry()
    node = FiveWhyNode(why_id="W1", level=1, cause_statement="Cause", citation_ids=["CITE-NONEXISTENT"])
    res = verify_causal_grounding([node], reg)
    assert res["grounded_causes"] == 0
    assert node.is_unsubstantiated is True
    assert node.assumed_flag is True
    assert node.assumption_flag is True


def test_timeline_extractor_zero_telemetry_reading_preservation():
    """Verify that a reading of 0.0 (e.g. vibration: 0.0 mm/s) is preserved and processed for deviations."""
    extractor = TimelineExtractor()
    log_zero = {
        "timestamp": "2023-11-04T08:00:00Z",
        "description": "Standstill baseline reading",
        "vibration_mm_s": 0.0,
    }
    events = extractor.reconstruct_timeline(equipment_tag="Pump-A12", telemetry_logs=[log_zero])
    assert len(events) == 1
    evt = events[0]
    assert evt.parameters["vibration_mm_s"] == 0.0
    assert "deviation_pct" in evt.parameters
    assert evt.parameters["deviation_pct"] == -100.0
    assert evt.parameters["is_exceeded"] is False
    assert evt.parameters["is_trip_exceeded"] is False

    # Also verify temperature 0.0 is preserved
    log_temp_zero = {
        "timestamp": "2023-11-04T08:05:00Z",
        "description": "Chill test reading",
        "temperature_c": 0.0,
    }
    events_temp = extractor.reconstruct_timeline(equipment_tag="Pump-A12", telemetry_logs=[log_temp_zero])
    assert len(events_temp) == 1
    assert events_temp[0].parameters["temperature_c"] == 0.0


def test_timeline_extractor_none_description_handling():
    """Verify that telemetry entries with description: None do not crash and generate valid TimelineEvents."""
    extractor = TimelineExtractor()
    log_none_desc = {"timestamp": "2023-11-04T08:00:00Z", "description": None}
    events = extractor.reconstruct_timeline(equipment_tag="Pump-A12", telemetry_logs=[log_none_desc])
    assert len(events) == 1
    assert events[0].description is not None
    assert len(events[0].description) >= 3
    assert "Pump-A12" in events[0].description

    # Also verify _classify_sentence handles None input without AttributeError
    assert extractor._classify_sentence(None) == "MAINTENANCE_LOG"
    assert extractor._classify_sentence("") == "MAINTENANCE_LOG"


def test_timeline_extractor_preserves_preexisting_citations():
    """Verify that _link_citations preserves pre-existing citation_ids on events and does not wipe them."""
    extractor = TimelineExtractor()
    c_existing = CitationObject(
        citation_id="CITE-PREEXISTING-01",
        source_doc="manual.pdf",
        excerpt="Pump manual technical specs",
    )
    c_unrelated = CitationObject(
        citation_id="CITE-UNRELATED-02",
        source_doc="cafeteria.pdf",
        excerpt="Cafeteria menu details",
    )

    log_with_cite = {
        "timestamp": "2023-11-04T08:00:00Z",
        "description": "Custom bearing vibration monitoring",
        "citation_ids": [c_existing.citation_id],
    }

    # Reconstruct timeline passing an unrelated external citation
    events = extractor.reconstruct_timeline(
        equipment_tag="Pump-A12",
        telemetry_logs=[log_with_cite],
        citations=[c_unrelated],
    )
    assert len(events) == 1
    # Pre-existing citation must be preserved!
    assert c_existing.citation_id in events[0].citation_ids
    # Event must NOT be marked unsubstantiated because it has a valid existing citation
    assert events[0].is_unsubstantiated is False


def test_verify_causal_grounding_supports_fishbone_branch():
    """Verify that verify_causal_grounding safely handles FishboneBranch objects without raising ValueError."""
    reg = CitationRegistry()
    c1 = reg.register_citation(source_doc="doc1.txt", excerpt="Shaft misalignment causes vibration")

    # Grounded branch
    branch_grounded = FishboneBranch(
        category="Machine",
        causes=["Misaligned impeller shaft"],
        citation_ids=[c1.citation_id],
    )
    # Ungrounded branch
    branch_ungrounded = FishboneBranch(
        category="Man",
        causes=["Operator error during startup"],
        citation_ids=["CITE-NONEXISTENT"],
    )

    res = verify_causal_grounding([branch_grounded, branch_ungrounded], reg)
    assert res["total_causes"] == 2
    assert res["grounded_causes"] == 1
    assert res["ungrounded_causes"] == 1
    assert res["grounding_ratio"] == 0.5
    assert res["compliance_status"] == "GROUNDING_DEFICIENT"

    # Branch flags updated correctly
    assert branch_grounded.is_unsubstantiated is False
    assert branch_grounded.assumed_flag is False
    assert branch_grounded.assumption_flag is False

    assert branch_ungrounded.is_unsubstantiated is True
    assert branch_ungrounded.assumed_flag is True
    assert branch_ungrounded.assumption_flag is True


def test_verify_causal_grounding_supports_dict_causes():
    """Verify that verify_causal_grounding safely handles dictionary causes without raising AttributeError."""
    reg = CitationRegistry()
    c1 = reg.register_citation(source_doc="doc1.txt", excerpt="Evidence statement")

    dict_grounded = {"citation_ids": [c1.citation_id], "cause": "Bearing failure"}
    dict_ungrounded = {"citation_ids": [], "cause": "Unknown electrical fault"}

    res = verify_causal_grounding([dict_grounded, dict_ungrounded], reg)
    assert res["total_causes"] == 2
    assert res["grounded_causes"] == 1
    assert res["ungrounded_causes"] == 1

    assert dict_grounded["is_unsubstantiated"] is False
    assert dict_grounded["assumed_flag"] is False
    assert dict_grounded["assumption_flag"] is False

    assert dict_ungrounded["is_unsubstantiated"] is True
    assert dict_ungrounded["assumed_flag"] is True
    assert dict_ungrounded["assumption_flag"] is True

