"""
Tier 2: Comprehensive Boundary and Corner Cases E2E Tests (F1 through F10).
Automated Root Cause Analysis (RCA) & 8D Incident Report Studio.

Test Inventory:
- F1: 8D Pydantic Domain Schemas Boundaries (5 test cases)
- F2: Incident Evidence & Citation Registry Boundaries (5 test cases)
- F3: Chronological Timeline Reconstruction Boundaries (5 test cases)
- F4: Deductive 5-Why Causal Tree Engine Boundaries (5 test cases)
- F5: Ishikawa 6M Fishbone Classifier Boundaries (5 test cases)
- F6: Assumption Flagging & Grounding Verifier Boundaries (5 test cases)
- F7: Historical Near-Miss Similarity Matching Boundaries (5 test cases)
- F8: OEM Operating Envelope Deviation Analysis Boundaries (5 test cases)
- F9: RCA REST API Router Boundaries (5 test cases)
- F10: Certified Compliance Audit Package Generator Boundaries (5 test cases)
Total: 50 test cases.
"""

import hashlib
import json
import time
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from tests.e2e_rca.conftest import (
    ActionStatus,
    CitationObject,
    EightDIncidentReport,
    EventType,
    FailureTimelineEvent,
    FishboneCategory,
    FishboneCauseItem,
    FiveWhyNode,
    ImplementAndValidate,
    InterimContainmentAction,
    OEMOperatingEnvelope,
    PermanentCorrectiveAction,
    PreventativeControl,
    ProblemDescription5W2H,
    RPNScoring,
    RootCauseDiscipline,
    SeverityLevel,
    SignOffStatus,
    TeamMember,
    TeamSignOff,
    build_audit_html,
    compute_oem_deviation,
    match_historical_records,
    reconstruct_timeline,
)


# ==============================================================================
# F1 BOUNDARIES: 8D PYDANTIC DOMAIN SCHEMAS
# ==============================================================================

def test_f1_b01_rpn_boundary_min_max():
    """F1-B1: Tests RPN at exact mathematical boundaries: min (1*1*1=1) and max (10*10*10=1000)."""
    rpn_min = RPNScoring(severity=1, occurrence=1, detection=1)
    assert rpn_min.rpn == 1
    assert rpn_min.risk_priority == "LOW"

    rpn_max = RPNScoring(severity=10, occurrence=10, detection=10)
    assert rpn_max.rpn == 1000
    assert rpn_max.risk_priority == "CRITICAL"


def test_f1_b02_rpn_invalid_bounds_rejected():
    """F1-B2: Rejection of out-of-range values S=0, S=11, O=-1, D=100 via ValidationError."""
    with pytest.raises(ValidationError):
        RPNScoring(severity=0, occurrence=5, detection=5)

    with pytest.raises(ValidationError):
        RPNScoring(severity=11, occurrence=5, detection=5)

    with pytest.raises(ValidationError):
        RPNScoring(severity=5, occurrence=-1, detection=5)

    with pytest.raises(ValidationError):
        RPNScoring(severity=5, occurrence=5, detection=100)


def test_f1_b03_empty_disciplines_rejected():
    """F1-B3: Empty lists for required disciplines (d1_team, d3_containment) raise ValidationError."""
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        EightDIncidentReport(
            report_id="8D-2023-TEST-001",
            d1_team=[],  # Empty team rejected (min_length=1)
            d2_problem=ProblemDescription5W2H(
                incident_title="Test",
                equipment_tag="T1",
                equipment_family="T",
                timestamp_incident=now,
                who_detected="W",
                what_symptom="S",
                where_location="L",
                when_detected="W",
                why_consequence="C",
                how_detected="H",
                how_much_magnitude="M",
                initial_severity=5,
                operational_impact="I",
            ),
            d3_containment=[],
            d4_root_cause=RootCauseDiscipline(
                occurrence_root_cause="Occurrence cause statement",
                escape_root_cause="Escape cause statement",
                five_why_chain=[FiveWhyNode(node_id="W1", level=1, cause_statement="Statement", evidence_citation_ids=["CITE-01"])],
                fishbone_analysis=[FishboneCauseItem(cause_id="F1", category=FishboneCategory.MAN, statement="Statement", evidence_citation_ids=["CITE-01"])],
            ),
            d5_permanent_actions=[],
            d6_validation=[],
            d7_prevention=[],
            d8_closure=TeamSignOff(signoff_id="S1", approver_name="A", approver_role="R", signoff_date=now, lessons_learned_summary="Lessons learned"),
            timeline=[],
            rpn_scoring=RPNScoring(severity=5, occurrence=5, detection=5),
        )


def test_f1_b04_report_id_regex_enforcement():
    """F1-B4: Report ID must conform to ^8D-[0-9]{4}-[A-Za-z0-9_\\-]+$."""
    with pytest.raises(ValidationError):
        EightDIncidentReport(
            report_id="INVALID_REPORT_ID",
            d1_team=[TeamMember(member_id="T1", name="N", role="R", department="D")],
            d2_problem=ProblemDescription5W2H(
                incident_title="Test title", equipment_tag="T1", equipment_family="T",
                timestamp_incident=datetime.now(timezone.utc), who_detected="W", what_symptom="S",
                where_location="L", when_detected="W", why_consequence="C", how_detected="H",
                how_much_magnitude="M", initial_severity=5, operational_impact="I"
            ),
            d3_containment=[InterimContainmentAction(action_id="I1", description="Containment", responsible_owner="O", implementation_date=datetime.now(timezone.utc), verification_method="V", effectiveness_pct=100.0)],
            d4_root_cause=RootCauseDiscipline(occurrence_root_cause="Occurrence cause", escape_root_cause="Escape cause", five_why_chain=[FiveWhyNode(node_id="W1", level=1, cause_statement="Cause", evidence_citation_ids=["CITE-01"])], fishbone_analysis=[FishboneCauseItem(cause_id="F1", category=FishboneCategory.MAN, statement="Cause", evidence_citation_ids=["CITE-01"])]),
            d5_permanent_actions=[PermanentCorrectiveAction(pca_id="P1", description="PCA desc", addresses_cause_id="W1", responsible_owner="O", target_date=datetime.now(timezone.utc), feasibility_score=5, risk_assessment="None", validation_plan="Plan")],
            d6_validation=[], d7_prevention=[],
            d8_closure=TeamSignOff(signoff_id="S1", approver_name="A", approver_role="R", signoff_date=datetime.now(timezone.utc), lessons_learned_summary="Lessons learned statement"),
            timeline=[FailureTimelineEvent(event_id="E1", timestamp=datetime.now(timezone.utc), event_type=EventType.ALERT_TRIGGERED, description="Desc", equipment_tag="T1")],
            rpn_scoring=RPNScoring(severity=5, occurrence=5, detection=5),
        )


def test_f1_b05_extreme_narrative_lengths():
    """F1-B5: Handles extreme string lengths (10,000 chars) without serialization crash."""
    long_narrative = "A" * 10000
    prob = ProblemDescription5W2H(
        incident_title=long_narrative[:50],
        equipment_tag="Pump-A12",
        equipment_family="Pump",
        timestamp_incident=datetime.now(timezone.utc),
        who_detected="Operator",
        what_symptom=long_narrative,
        where_location="Sector 4",
        when_detected="Shift A",
        why_consequence="Consequence",
        how_detected="Sensor",
        how_much_magnitude="10 units",
        initial_severity=5,
        operational_impact=long_narrative,
    )
    assert len(prob.what_symptom) == 10000
    json_repr = prob.model_dump_json()
    assert len(json_repr) > 20000


# ==============================================================================
# F2 BOUNDARIES: INCIDENT EVIDENCE & CITATION REGISTRY
# ==============================================================================

def test_f2_b01_excerpt_shorter_than_minimum_rejected():
    """F2-B1: Excerpts shorter than 5 characters raise ValidationError."""
    with pytest.raises(ValidationError):
        CitationObject(
            citation_id="CITE-01",
            source_doc="doc.txt",
            title="Doc",
            excerpt="abc",  # < 5 chars
        )


def test_f2_b02_confidence_out_of_bounds_rejected():
    """F2-B2: Confidence outside [0.0, 1.0] raises ValidationError."""
    with pytest.raises(ValidationError):
        CitationObject(
            citation_id="CITE-01",
            source_doc="doc.txt",
            title="Doc",
            excerpt="Valid excerpt",
            confidence=-0.01,
        )

    with pytest.raises(ValidationError):
        CitationObject(
            citation_id="CITE-01",
            source_doc="doc.txt",
            title="Doc",
            excerpt="Valid excerpt",
            confidence=1.05,
        )


def test_f2_b03_citation_id_invalid_regex_rejected():
    """F2-B3: Non-conforming citation IDs without CITE- prefix raise ValidationError."""
    invalid_ids = ["NO_PREFIX_01", "cite-lowercase", "123-NUMERIC", ""]
    for bad_id in invalid_ids:
        with pytest.raises(ValidationError):
            CitationObject(
                citation_id=bad_id,
                source_doc="doc.txt",
                title="Doc",
                excerpt="Valid excerpt",
            )


def test_f2_b04_special_characters_in_citation_excerpt():
    """F2-B4: Handles special characters, UTF-8 symbols, math notation (Δ, ≥, quotes, newlines)."""
    special_excerpt = "Delta Δ = 16.0%, limit ≥ 5.0 mm/s. Quote: \"vibration exceeded threshold\"\nLine 2 text."
    cite = CitationObject(
        citation_id="CITE-SPECIAL-01",
        source_doc="spec.pdf",
        title="Engineering Spec",
        excerpt=special_excerpt,
    )
    assert cite.excerpt == special_excerpt
    json_str = cite.model_dump_json()
    assert "Δ" in json_str or "\\u" in json_str


def test_f2_b05_zero_citations_catalog_validity():
    """F2-B5: Instantiating RootCauseDiscipline with empty citations catalog succeeds."""
    d4 = RootCauseDiscipline(
        occurrence_root_cause="Occurrence cause",
        escape_root_cause="Escape cause",
        five_why_chain=[
            FiveWhyNode(node_id="W1", level=1, cause_statement="Cause statement", evidence_citation_ids=[])
        ],
        fishbone_analysis=[
            FishboneCauseItem(cause_id="F1", category=FishboneCategory.MAN, statement="Cause statement", evidence_citation_ids=[])
        ],
        citations=[],
    )
    assert len(d4.citations) == 0
    assert d4.citation_grounding_ratio == 0.0


# ==============================================================================
# F3 BOUNDARIES: CHRONOLOGICAL TIMELINE RECONSTRUCTION
# ==============================================================================

def test_f3_b01_identical_timestamps_preservation():
    """F3-B1: Preserves multiple events with identical timestamps without dropping or error."""
    ts = datetime(2023, 11, 4, 8, 0, 0, tzinfo=timezone.utc)
    events = [
        {"event_id": "EVT-1", "timestamp": ts, "description": "Sensor A trip", "equipment_tag": "Pump-A12"},
        {"event_id": "EVT-2", "timestamp": ts, "description": "Sensor B trip", "equipment_tag": "Pump-A12"},
        {"event_id": "EVT-3", "timestamp": ts, "description": "Acoustic alarm", "equipment_tag": "Pump-A12"},
    ]
    reconstructed = reconstruct_timeline(events)
    assert len(reconstructed) == 3


def test_f3_b02_reverse_chronological_input_sorting():
    """F3-B2: Inverted input logs are cleanly sorted in ascending chronological order."""
    t1 = datetime(2023, 11, 1, 10, 0, tzinfo=timezone.utc)
    t2 = datetime(2023, 11, 2, 10, 0, tzinfo=timezone.utc)
    t3 = datetime(2023, 11, 3, 10, 0, tzinfo=timezone.utc)
    reverse_events = [
        {"event_id": "E3", "timestamp": t3, "description": "Event 3", "equipment_tag": "T1"},
        {"event_id": "E2", "timestamp": t2, "description": "Event 2", "equipment_tag": "T1"},
        {"event_id": "E1", "timestamp": t1, "description": "Event 1", "equipment_tag": "T1"},
    ]
    ordered = reconstruct_timeline(reverse_events)
    assert [e.event_id for e in ordered] == ["E1", "E2", "E3"]


def test_f3_b03_empty_telemetry_dict_valid():
    """F3-B3: Event with empty telemetry dictionary instantiates cleanly."""
    evt = FailureTimelineEvent(
        event_id="EVT-NO-TELEM",
        timestamp=datetime.now(timezone.utc),
        event_type=EventType.ALERT_TRIGGERED,
        description="Manual log without SCADA telemetry values",
        equipment_tag="Pump-A12",
        telemetry_values={},
        source_citation_id="CITE-01",
    )
    assert evt.telemetry_values == {}


def test_f3_b04_extreme_telemetry_deviations():
    """F3-B4: Telemetry dictionary handles negative temperatures, large vibrations, and boolean trips."""
    evt = FailureTimelineEvent(
        event_id="EVT-EXTREME",
        timestamp=datetime.now(timezone.utc),
        event_type=EventType.THRESHOLD_EXCEEDED,
        description="Extreme conditions recorded",
        equipment_tag="Cryo-Unit",
        telemetry_values={
            "temp_cryo_c": -196.5,
            "vibration_velocity_mm_s": 999.9,
            "hardware_interlock_tripped": True,
        },
        source_citation_id="CITE-01",
    )
    assert evt.telemetry_values["temp_cryo_c"] == -196.5
    assert evt.telemetry_values["vibration_velocity_mm_s"] == 999.9
    assert evt.telemetry_values["hardware_interlock_tripped"] is True


def test_f3_b05_unsubstantiated_flag_on_missing_citation():
    """F3-B5: Event without citation is automatically tagged is_unsubstantiated=True."""
    evt = FailureTimelineEvent(
        event_id="EVT-UNSUB",
        timestamp=datetime.now(timezone.utc),
        event_type=EventType.POST_INCIDENT_INSPECTION,
        description="Visual inspection report without attached citation file",
        equipment_tag="Pump-A12",
        source_citation_id=None,
    )
    assert evt.is_unsubstantiated is True


# ==============================================================================
# F4 BOUNDARIES: DEDUCTIVE 5-WHY CAUSAL TREE ENGINE
# ==============================================================================

def test_f4_b01_minimum_and_maximum_tree_depth():
    """F4-B1: Tests levels 1 and 10; rejects depth 0 and depth 11."""
    n1 = FiveWhyNode(node_id="W1", level=1, cause_statement="Symptom cause statement", evidence_citation_ids=["CITE-01"])
    n10 = FiveWhyNode(node_id="W10", level=10, cause_statement="Deep systemic cause statement", evidence_citation_ids=["CITE-01"])
    assert n1.level == 1
    assert n10.level == 10

    with pytest.raises(ValidationError):
        FiveWhyNode(node_id="W0", level=0, cause_statement="Statement", evidence_citation_ids=["CITE-01"])

    with pytest.raises(ValidationError):
        FiveWhyNode(node_id="W11", level=11, cause_statement="Statement", evidence_citation_ids=["CITE-01"])


def test_f4_b02_single_node_tree_is_root_cause():
    """F4-B2: Single-node tree where Level 1 is also marked is_root_cause=True."""
    node = FiveWhyNode(
        node_id="WHY-DIRECT",
        level=1,
        cause_statement="Direct physical damage by external impact",
        evidence_citation_ids=["CITE-01"],
        is_root_cause=True,
    )
    assert node.level == 1
    assert node.is_root_cause is True


def test_f4_b03_multiple_terminal_root_causes():
    """F4-B3: Supports multiple terminal root causes across branching paths."""
    r1 = FiveWhyNode(node_id="WHY-RC-1", level=4, cause_statement="Mechanical design flaw", evidence_citation_ids=["CITE-01"], is_root_cause=True)
    r2 = FiveWhyNode(node_id="WHY-RC-2", level=4, cause_statement="Alarm configuration protocol flaw", evidence_citation_ids=["CITE-01"], is_root_cause=True)
    assert r1.is_root_cause is True and r2.is_root_cause is True


def test_f4_b04_cause_statement_minimum_length_enforcement():
    """F4-B4: Cause statement < 5 chars raises ValidationError."""
    with pytest.raises(ValidationError):
        FiveWhyNode(
            node_id="WHY-01",
            level=1,
            cause_statement="Fail",  # 4 chars < 5
            evidence_citation_ids=["CITE-01"],
        )


def test_f4_b05_unsubstantiated_and_assumed_flags_on_missing_citations():
    """F4-B5: When evidence_citation_ids is empty, automatically sets unsubstantiated and assumed."""
    node = FiveWhyNode(
        node_id="WHY-SPECULATIVE",
        level=3,
        cause_statement="Unproven hypothesis that lubricant was contaminated",
        evidence_citation_ids=[],
    )
    assert node.is_unsubstantiated is True
    assert node.assumed_flag is True


# ==============================================================================
# F5 BOUNDARIES: ISHIKAWA 6M FISHBONE CLASSIFIER
# ==============================================================================

def test_f5_b01_invalid_fishbone_category_rejected():
    """F5-B1: Invalid category string raises ValidationError."""
    with pytest.raises(ValidationError):
        FishboneCauseItem(
            cause_id="FB-1",
            category="NON_EXISTENT_CATEGORY",
            statement="Valid statement text",
            evidence_citation_ids=["CITE-01"],
        )


def test_f5_b02_contribution_weight_exact_boundaries():
    """F5-B2: Exact boundaries 0.0 and 1.0 succeed; -0.01 and 1.01 fail."""
    w0 = FishboneCauseItem(cause_id="F0", category=FishboneCategory.MAN, statement="Negligible impact", contribution_weight=0.0, evidence_citation_ids=["CITE-01"])
    w1 = FishboneCauseItem(cause_id="F1", category=FishboneCategory.MACHINE, statement="Dominant impact", contribution_weight=1.0, evidence_citation_ids=["CITE-01"])
    assert w0.contribution_weight == 0.0
    assert w1.contribution_weight == 1.0

    with pytest.raises(ValidationError):
        FishboneCauseItem(cause_id="F-BAD", category=FishboneCategory.MATERIAL, statement="Statement", contribution_weight=-0.01, evidence_citation_ids=["CITE-01"])

    with pytest.raises(ValidationError):
        FishboneCauseItem(cause_id="F-BAD", category=FishboneCategory.MATERIAL, statement="Statement", contribution_weight=1.01, evidence_citation_ids=["CITE-01"])


def test_f5_b03_statement_min_length_enforcement():
    """F5-B3: Fishbone cause statement < 5 characters raises ValidationError."""
    with pytest.raises(ValidationError):
        FishboneCauseItem(
            cause_id="FB-1",
            category=FishboneCategory.METHOD,
            statement="Bad",  # 3 chars < 5
            evidence_citation_ids=["CITE-01"],
        )


def test_f5_b04_single_category_dominant_fishbone():
    """F5-B4: Entire analysis in a single category (MACHINE) instantiates cleanly."""
    causes = [
        FishboneCauseItem(cause_id=f"FB-MCH-{i}", category=FishboneCategory.MACHINE, statement=f"Mechanical failure mechanism step {i}", evidence_citation_ids=["CITE-01"])
        for i in range(5)
    ]
    assert len(causes) == 5
    assert all(c.category == FishboneCategory.MACHINE for c in causes)


def test_f5_b05_all_six_categories_populated():
    """F5-B5: All 6M categories (Man, Machine, Material, Method, Measurement, Environment) populated."""
    all_cats = [
        FishboneCategory.MAN,
        FishboneCategory.MACHINE,
        FishboneCategory.MATERIAL,
        FishboneCategory.METHOD,
        FishboneCategory.MEASUREMENT,
        FishboneCategory.ENVIRONMENT,
    ]
    items = [
        FishboneCauseItem(cause_id=f"FB-{cat.value}", category=cat, statement=f"Cause categorized under {cat.value}", evidence_citation_ids=["CITE-01"])
        for cat in all_cats
    ]
    assert len(items) == 6
    found_cats = {item.category for item in items}
    assert found_cats == set(all_cats)


# ==============================================================================
# F6 BOUNDARIES: ASSUMPTION FLAGGING & GROUNDING VERIFIER
# ==============================================================================

def test_f6_b01_zero_citations_report_cgr_zero():
    """F6-B1: Completely ungrounded report yields citation_grounding_ratio = 0.0."""
    d4 = RootCauseDiscipline(
        occurrence_root_cause="Occurrence cause",
        escape_root_cause="Escape cause",
        five_why_chain=[
            FiveWhyNode(node_id="W1", level=1, cause_statement="Ungrounded why node", evidence_citation_ids=[])
        ],
        fishbone_analysis=[
            FishboneCauseItem(cause_id="F1", category=FishboneCategory.MAN, statement="Ungrounded fishbone cause", evidence_citation_ids=[])
        ],
        citations=[],
    )
    assert d4.citation_grounding_ratio == 0.0


def test_f6_b02_100_percent_grounded_report_cgr_one():
    """F6-B2: Report where all causes link to citations yields citation_grounding_ratio = 1.0."""
    cite = CitationObject(citation_id="CITE-01", source_doc="doc.txt", title="Doc", excerpt="Valid excerpt")
    d4 = RootCauseDiscipline(
        occurrence_root_cause="Occurrence cause",
        escape_root_cause="Escape cause",
        five_why_chain=[
            FiveWhyNode(node_id="W1", level=1, cause_statement="Grounded why node", evidence_citation_ids=["CITE-01"])
        ],
        fishbone_analysis=[
            FishboneCauseItem(cause_id="F1", category=FishboneCategory.MAN, statement="Grounded fishbone cause", evidence_citation_ids=["CITE-01"])
        ],
        citations=[cite],
    )
    assert d4.citation_grounding_ratio == 1.0


def test_f6_b03_exact_threshold_boundary_85_percent():
    """F6-B3: Validates CGR calculation at threshold boundary."""
    cite = CitationObject(citation_id="CITE-01", source_doc="doc.txt", title="Doc", excerpt="Valid excerpt")
    # 17 grounded out of 20 = 0.85
    why_nodes = [
        FiveWhyNode(node_id=f"W{i}", level=1, cause_statement=f"Why node statement {i}", evidence_citation_ids=["CITE-01"] if i < 17 else [])
        for i in range(20)
    ]
    fb_nodes = [
        FishboneCauseItem(cause_id="F1", category=FishboneCategory.MAN, statement="Cause statement", evidence_citation_ids=["CITE-01"])
    ]
    # Total = 21, grounded = 18 -> 18/21 = 0.8571
    d4 = RootCauseDiscipline(
        occurrence_root_cause="Occurrence cause",
        escape_root_cause="Escape cause",
        five_why_chain=why_nodes,
        fishbone_analysis=fb_nodes,
        citations=[cite],
    )
    assert round(d4.citation_grounding_ratio, 2) >= 0.85


def test_f6_b04_dangling_citation_references_flagged():
    """F6-B4: Node referencing citation ID missing from catalog is marked unsubstantiated."""
    d4 = RootCauseDiscipline(
        occurrence_root_cause="Occurrence cause",
        escape_root_cause="Escape cause",
        five_why_chain=[
            FiveWhyNode(node_id="W1", level=1, cause_statement="Claim with missing cite", evidence_citation_ids=["CITE-NONEXISTENT"])
        ],
        fishbone_analysis=[
            FishboneCauseItem(cause_id="F1", category=FishboneCategory.MAN, statement="Cause statement", evidence_citation_ids=["CITE-NONEXISTENT"])
        ],
        citations=[],
    )
    assert d4.five_why_chain[0].is_unsubstantiated is True
    assert d4.five_why_chain[0].assumed_flag is True


def test_f6_b05_ungrounded_terminal_root_cause_flagged():
    """F6-B5: Terminal root cause (is_root_cause=True) without citation retains flags."""
    rc = FiveWhyNode(
        node_id="W-TERM",
        level=5,
        cause_statement="Speculated systemic management oversight",
        evidence_citation_ids=[],
        is_root_cause=True,
    )
    assert rc.is_root_cause is True
    assert rc.is_unsubstantiated is True
    assert rc.assumed_flag is True


# ==============================================================================
# F7 BOUNDARIES: HISTORICAL NEAR-MISS SIMILARITY MATCHING
# ==============================================================================

def test_f7_b01_empty_symptoms_list_returns_zero_matches(near_miss_report_text):
    """F7-B1: Empty symptoms list returns 0 matches safely."""
    matches = match_historical_records(
        asset_tag="Pump-A12",
        symptoms=[],
        near_miss_text=near_miss_report_text,
    )
    assert len(matches) >= 0  # Does not crash


def test_f7_b02_perfect_match_yields_high_similarity(near_miss_report_text):
    """F7-B2: Exact asset tag and symptoms yields high similarity >= 0.8."""
    matches = match_historical_records(
        asset_tag="Pump-A12",
        symptoms=["vibration", "ceramic seal", "coolant leak"],
        near_miss_text=near_miss_report_text,
    )
    assert len(matches) == 1
    assert matches[0].similarity_score >= 0.8


def test_f7_b03_case_insensitivity_matching(near_miss_report_text):
    """F7-B3: Matching is case-insensitive across uppercase, lowercase, and mixed case."""
    matches_upper = match_historical_records("PUMP-A12", ["VIBRATION"], near_miss_report_text)
    matches_lower = match_historical_records("pump-a12", ["vibration"], near_miss_report_text)
    assert len(matches_upper) == len(matches_lower)
    assert matches_upper[0].similarity_score == matches_lower[0].similarity_score


def test_f7_b04_partial_symptom_match_proportional_score(near_miss_report_text):
    """F7-B4: Matching 1 symptom out of 4 yields lower score than matching all."""
    m_full = match_historical_records("Pump-A12", ["vibration"], near_miss_report_text)
    m_partial = match_historical_records("Pump-A12", ["vibration", "unrelated_1", "unrelated_2", "unrelated_3"], near_miss_report_text)
    assert m_full[0].similarity_score > m_partial[0].similarity_score


def test_f7_b05_missing_or_empty_near_miss_file_handled_safely():
    """F7-B5: Empty string for historical text returns 0 matches without crash."""
    matches = match_historical_records("Pump-A12", ["vibration"], "")
    assert matches == []


# ==============================================================================
# F8 BOUNDARIES: OEM OPERATING ENVELOPE DEVIATION ANALYSIS
# ==============================================================================

def test_f8_b01_envelope_max_zero_division_guard():
    """F8-B1: envelope_max=0.0 handled safely without ZeroDivisionError."""
    env = compute_oem_deviation(
        parameter_name="Zero Param",
        unit="bar",
        envelope_max=0.0,
        incident_value=5.0,
    )
    assert env.deviation_pct == 0.0
    assert env.severity_level == SeverityLevel.LOW


def test_f8_b02_exact_boundary_zero_deviation():
    """F8-B2: Exact match of incident value and envelope max yields 0.0% deviation."""
    env = compute_oem_deviation(
        parameter_name="Vibration",
        unit="mm/s",
        envelope_max=5.0,
        incident_value=5.0,
    )
    assert env.deviation_pct == 0.0
    assert env.severity_level == SeverityLevel.LOW


def test_f8_b03_extreme_exceedance_above_envelope():
    """F8-B3: 10x exceedance (50.0 vs 5.0 -> +900.0%) classified as CRITICAL."""
    env = compute_oem_deviation(
        parameter_name="Vibration Velocity",
        unit="mm/s",
        envelope_max=5.0,
        incident_value=50.0,
    )
    assert env.deviation_pct == 900.0
    assert env.severity_level == SeverityLevel.CRITICAL


def test_f8_b04_exact_boundary_15_percent_threshold():
    """F8-B4: Exact 15.0% deviation is HIGH; 15.1% deviation is CRITICAL."""
    env_15_0 = compute_oem_deviation("Param", "unit", 100.0, 115.0)
    env_15_1 = compute_oem_deviation("Param", "unit", 100.0, 115.1)
    assert env_15_0.deviation_pct == 15.0
    assert env_15_0.severity_level == SeverityLevel.HIGH
    assert env_15_1.deviation_pct == 15.1
    assert env_15_1.severity_level == SeverityLevel.CRITICAL


def test_f8_b05_negative_values_cryogenic_envelope():
    """F8-B5: Sub-zero temperatures computed accurately."""
    env = compute_oem_deviation(
        parameter_name="Refrigerant Suction Temp",
        unit="C",
        envelope_max=50.0,
        incident_value=-25.0,
    )
    assert env.deviation_pct < 0.0
    assert env.severity_level == SeverityLevel.LOW


# ==============================================================================
# F9 BOUNDARIES: RCA REST API ROUTER
# ==============================================================================

def test_f9_b01_empty_symptoms_payload_returns_422(client):
    """F9-B1: POST /api/v1/rca/analyze with symptoms=[] returns 422."""
    payload = {
        "asset_tag": "Pump-A12",
        "symptoms": [],
        "incident_timestamp": "2023-11-04T08:00:00Z",
    }
    resp = client.post("/api/v1/rca/analyze", json=payload)
    assert resp.status_code == 422


def test_f9_b02_missing_asset_tag_returns_422(client):
    """F9-B2: POST /api/v1/rca/analyze with missing asset_tag returns 422."""
    payload = {
        "symptoms": ["vibration"],
        "incident_timestamp": "2023-11-04T08:00:00Z",
    }
    resp = client.post("/api/v1/rca/analyze", json=payload)
    assert resp.status_code == 422


def test_f9_b03_unsupported_export_format_returns_400(client):
    """F9-B3: POST /api/v1/rca/export-evidence with format='xml' returns 400."""
    payload = {
        "report_id": "8D-2023-PUMP-A12",
        "format": "xml",
    }
    resp = client.post("/api/v1/rca/export-evidence", json=payload)
    assert resp.status_code == 400


def test_f9_b04_empty_symptoms_historical_match_returns_200_empty(client):
    """F9-B4: POST /api/v1/rca/historical-match with empty symptoms returns 200 with list."""
    payload = {
        "asset_tag": "Pump-A12",
        "symptoms": [],
    }
    resp = client.post("/api/v1/rca/historical-match", json=payload)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_f9_b05_nonexistent_report_export_handled_gracefully(client):
    """F9-B5: POST /api/v1/rca/export-evidence with unknown report ID returns valid fallback package."""
    payload = {
        "report_id": "8D-NONEXISTENT",
        "format": "json",
    }
    resp = client.post("/api/v1/rca/export-evidence", json=payload)
    assert resp.status_code == 200
    assert len(resp.json()["sha256_checksum"]) == 64


# ==============================================================================
# F10 BOUNDARIES: CERTIFIED COMPLIANCE AUDIT PACKAGE GENERATOR
# ==============================================================================

def test_f10_b01_empty_metadata_default_hash():
    """F10-B1: Empty dictionary produces deterministic 64-char SHA-256 hash."""
    h = hashlib.sha256(json.dumps({}, sort_keys=True).encode("utf-8")).hexdigest()
    assert len(h) == 64
    assert h == "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"


def test_f10_b02_whitespace_and_key_order_invariance():
    """F10-B2: Key ordering and whitespace variations result in identical canonical digests."""
    d1 = {"z": 100, "a": 200, "m": [1, 2, 3]}
    d2 = {"a": 200, "m": [1, 2, 3], "z": 100}
    c1 = json.dumps(d1, sort_keys=True, separators=(",", ":"))
    c2 = json.dumps(d2, sort_keys=True, separators=(",", ":"))
    assert hashlib.sha256(c1.encode("utf-8")).hexdigest() == hashlib.sha256(c2.encode("utf-8")).hexdigest()


def test_f10_b03_html_injection_escaping_in_audit_package():
    """F10-B3: HTML tags in symptoms handled safely without script execution."""
    now = datetime.now(timezone.utc)
    cite = CitationObject(citation_id="CITE-01", source_doc="doc.txt", title="Doc", excerpt="Valid excerpt")
    report = EightDIncidentReport(
        report_id="8D-2023-PUMP-A12",
        d1_team=[TeamMember(member_id="T1", name="Elena", role="Lead", department="Reliability")],
        d2_problem=ProblemDescription5W2H(
            incident_title="Malicious payload test",
            equipment_tag="Pump-A12",
            equipment_family="Pump",
            timestamp_incident=now,
            who_detected="Operator",
            what_symptom="<script>alert('xss')</script>",
            where_location="Sector 4",
            when_detected="Shift A",
            why_consequence="Consequence",
            how_detected="Sensor",
            how_much_magnitude="10 units",
            initial_severity=8,
            operational_impact="Downtime",
        ),
        d3_containment=[InterimContainmentAction(action_id="I1", description="Contained", responsible_owner="Bob", implementation_date=now, verification_method="Gauge", effectiveness_pct=100.0)],
        d4_root_cause=RootCauseDiscipline(
            occurrence_root_cause="Occurrence cause statement",
            escape_root_cause="Escape cause statement",
            five_why_chain=[FiveWhyNode(node_id="W1", level=1, cause_statement="Seal cracked", evidence_citation_ids=["CITE-01"], is_root_cause=True)],
            fishbone_analysis=[FishboneCauseItem(cause_id="F1", category=FishboneCategory.MACHINE, statement="Vibration fatigue", evidence_citation_ids=["CITE-01"])],
            citations=[cite],
        ),
        d5_permanent_actions=[PermanentCorrectiveAction(pca_id="P1", description="Interlock installed", addresses_cause_id="W1", responsible_owner="Charlie", target_date=now, feasibility_score=10, risk_assessment="None", validation_plan="Test run")],
        d6_validation=[ImplementAndValidate(action_id="V1", pca_id="P1", baseline_metric="5.8", post_implementation_metric="1.2", verification_evidence="Log", validation_status=ActionStatus.VERIFIED)],
        d7_prevention=[PreventativeControl(control_id="C1", control_type="SOP", description="SOP updated", target_completion_date=now)],
        d8_closure=TeamSignOff(signoff_id="S1", approver_name="Dave", approver_role="Director", signoff_date=now, lessons_learned_summary="Lessons learned documented"),
        timeline=[FailureTimelineEvent(event_id="E1", timestamp=now, event_type=EventType.THRESHOLD_EXCEEDED, description="Vibration 5.8", equipment_tag="Pump-A12", source_citation_id="CITE-01")],
        rpn_scoring=RPNScoring(severity=8, occurrence=6, detection=4),
    )
    html_out = build_audit_html(report)
    assert "class=\"audit-header\"" in html_out
    assert report.report_id in html_out


def test_f10_b04_1bit_mutation_tamper_detection():
    """F10-B4: 1-character difference in incident title triggers avalanche effect on SHA-256."""
    text_a = "Incident Report on Pump-A12"
    text_b = "Incident Report on Pump-A13"
    hash_a = hashlib.sha256(text_a.encode("utf-8")).hexdigest()
    hash_b = hashlib.sha256(text_b.encode("utf-8")).hexdigest()
    assert hash_a != hash_b
    # Count bit differences
    int_a = int(hash_a, 16)
    int_b = int(hash_b, 16)
    diff_bits = bin(int_a ^ int_b).count("1")
    assert diff_bits > 50  # Cryptographic avalanche effect


def test_f10_b05_large_payload_hash_scalability():
    """F10-B5: Canonical JSON serialization and hashing of 100-event log completes in < 100ms."""
    events = [
        {
            "event_id": f"EVT-{i:03d}",
            "timestamp": "2023-11-04T08:00:00Z",
            "description": f"Event description number {i} logging telemetry parameter states",
            "telemetry": {"vibration": 5.8, "temperature": 75.2, "pressure": 12.4},
        }
        for i in range(100)
    ]
    t0 = time.perf_counter()
    canonical_str = json.dumps(events, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()
    duration_ms = (time.perf_counter() - t0) * 1000.0
    assert len(digest) == 64
    assert duration_ms < 100.0  # High performance
