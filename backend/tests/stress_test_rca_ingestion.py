"""
Adversarial Stress Test Suite for RCA Ingestion, Timeline Extraction & Evidence Citation Engine.
Target: backend/services/rca_ingestion.py

Probes:
1. Out-of-order, duplicate, and completely missing timestamps in telemetry/alarm streams.
2. High-concurrency or multiple parallel calls to CitationRegistry to test deduplication and thread-safety.
3. Text extraction edge cases: spaced-out characters, unicode symbols, empty documents, giant log files, ReDoS patterns.
4. Causal grounding verification under extreme graphs: circular dependencies, empty causal nodes, invalid/nonexistent citation IDs, 100% ungrounded nodes.
"""

from __future__ import annotations

import copy
import hashlib
import math
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import pytest
from pydantic import ValidationError

from api.rca_schemas import (
    CitationObject,
    EventType,
    FishboneAnalysis,
    FishboneBranch,
    FiveWhyNode,
    SeverityLevel,
    TimelineEvent,
)
from core.text_utils import clean_spaced_text
from services.rca_ingestion import (
    CitationRegistry,
    EvidenceCitationExtractor,
    TimelineExtractor,
    cleaned_content_filter,
    verify_causal_grounding,
)


# ==============================================================================
# SECTION 1: TELEMETRY & ALARM STREAMS (TIMESTAMPS, SORTING, SENSOR EXTREMES)
# ==============================================================================

class TestTelemetryStreamAdversarial:
    """Stress testing TimelineExtractor against extreme, corrupted, and large-scale streams."""

    def test_out_of_order_telemetry_across_centuries_and_offsets(self):
        """Probe: Shuffled timestamps spanning past centuries, leap years, and extreme offsets."""
        extractor = TimelineExtractor()
        raw_timestamps = [
            "2099-12-31T23:59:59Z",
            "1970-01-01T00:00:00Z",
            "2023-11-04T08:00:00+00:00",
            "2023-11-04T07:59:59Z",
            "2024-02-29T12:00:00Z",  # Leap year day
            "2020-01-01T00:00:00Z",
            "2023-11-04T08:00:01Z",
        ]
        shuffled = list(reversed(raw_timestamps))
        logs = [{"timestamp": ts, "description": f"Log at {ts}", "event_id": f"EVT-{i}"} for i, ts in enumerate(shuffled)]

        events = extractor.reconstruct_timeline(equipment_tag="Pump-A12", telemetry_logs=logs)
        assert len(events) == len(raw_timestamps)

        # Verify strict monotonicity
        parsed_dts = [extractor._parse_iso_or_default(e.timestamp) for e in events]
        for i in range(len(parsed_dts) - 1):
            assert parsed_dts[i] <= parsed_dts[i + 1], f"Event {i} not <= Event {i+1}: {parsed_dts[i]} > {parsed_dts[i+1]}"

        # Oldest must be 1970 and newest 2099
        assert events[0].timestamp.startswith("1970")
        assert events[-1].timestamp.startswith("2099")

    def test_duplicate_timestamps_deterministic_tie_breaker(self):
        """Probe: 50 entries with identical timestamps to check stable tie-breaking by event_id."""
        extractor = TimelineExtractor()
        fixed_ts = "2023-11-04T08:00:00Z"
        logs = [
            {"timestamp": fixed_ts, "description": f"Identical ts event {i}", "event_id": f"EVT-{50 - i:03d}"}
            for i in range(50)
        ]

        events = extractor.reconstruct_timeline(equipment_tag="Pump-A12", telemetry_logs=logs)
        assert len(events) == 50
        # Verification: tie-break by event_id should sort event_ids ascendingly
        event_ids = [e.event_id for e in events]
        assert event_ids == sorted(event_ids)

    def test_missing_and_corrupted_timestamps_fallback(self):
        """Probe: Missing timestamp keys, None, empty string, and corrupted date formats."""
        extractor = TimelineExtractor()
        anchor = datetime(2023, 11, 4, 10, 0, 0, tzinfo=timezone.utc)
        logs = [
            {"description": "No timestamp key provided", "event_id": "EVT-NO-KEY"},
            {"timestamp": None, "description": "Timestamp is explicit None", "event_id": "EVT-NONE"},
            {"timestamp": "", "description": "Timestamp is empty string", "event_id": "EVT-EMPTY"},
            {"timestamp": "INVALID_DATE_FORMAT", "description": "Corrupted date string", "event_id": "EVT-BAD"},
            {"timestamp": "2023-99-99T99:99:99", "description": "Nonsense numbers", "event_id": "EVT-NONSENSE"},
            {"timestamp": 1699084800, "description": "Numeric epoch timestamp", "event_id": "EVT-NUMERIC"},
        ]

        events = extractor.reconstruct_timeline(
            equipment_tag="Pump-A12",
            telemetry_logs=logs,
            incident_timestamp=anchor,
        )
        assert len(events) == len(logs)
        for e in events:
            assert isinstance(e.timestamp, str)
            dt = datetime.fromisoformat(e.timestamp)
            assert dt is not None

    def test_mixed_timezones_normalized_chronology(self):
        """Probe: Timestamps with disparate timezone offsets (+05:30, -08:00, Z) must compare correctly."""
        extractor = TimelineExtractor()
        # All of these represent 2023-11-04 12:00:00 UTC, except last which is 13:00:00 UTC
        logs = [
            {"timestamp": "2023-11-04T17:30:00+05:30", "event_id": "EVT-INDIA", "description": "Event in IST (12:00 UTC)"},
            {"timestamp": "2023-11-04T04:00:00-08:00", "event_id": "EVT-PACIFIC", "description": "Event in PST (12:00 UTC)"},
            {"timestamp": "2023-11-04T12:00:00Z", "event_id": "EVT-UTC", "description": "Event in UTC (12:00 UTC)"},
            {"timestamp": "2023-11-04T13:00:00Z", "event_id": "EVT-LATER", "description": "Event 1 hr later"},
        ]
        events = extractor.reconstruct_timeline(equipment_tag="Pump-A12", telemetry_logs=logs)
        assert len(events) == 4
        # EVT-LATER must be the last element
        assert events[-1].event_id == "EVT-LATER"

    def test_large_scale_telemetry_stream_performance(self):
        """Probe: 5,000 out-of-order telemetry events processed within tight execution envelope."""
        extractor = TimelineExtractor()
        base_dt = datetime(2023, 11, 4, 0, 0, 0, tzinfo=timezone.utc)
        count = 5000
        logs = []
        for i in range(count):
            dt = base_dt + timedelta(seconds=(count - i))
            logs.append({
                "timestamp": dt.isoformat(),
                "event_id": f"EVT-BIG-{i:05d}",
                "vibration_mm_s": 5.0 + (i % 10) * 0.1,
                "description": f"Telemetry scan entry index {i}",
            })

        t0 = time.perf_counter()
        events = extractor.reconstruct_timeline(equipment_tag="Pump-A12", telemetry_logs=logs)
        t_elapsed = time.perf_counter() - t0

        assert len(events) == count
        assert t_elapsed < 3.0, f"Timeline reconstruction for {count} events took {t_elapsed:.2f}s (> 3.0s threshold)"
        assert events[0].timestamp <= events[-1].timestamp

    def test_telemetry_extreme_sensor_values_and_truthiness_vulnerability(self):
        """
        Adversarial probe:
        Identifies truthiness bug on zero vibration reading:
        `vib = params.get('vibration_mm_s') or params.get('vibration')`
        When vibration_mm_s == 0.0, 0.0 evaluates to falsy, and 0.0 or None evaluates to None!
        """
        extractor = TimelineExtractor()

        # Non-zero extreme values work correctly
        log_pos = {"timestamp": "2023-11-04T08:00:00Z", "description": "High vibration", "vibration_mm_s": 1000.0}
        events_pos = extractor.reconstruct_timeline(equipment_tag="Pump-A12", telemetry_logs=[log_pos])
        assert events_pos[0].parameters["vibration_mm_s"] == 1000.0
        assert events_pos[0].parameters["deviation_pct"] == 19900.0
        assert events_pos[0].parameters["is_exceeded"] is True

        # EMPIRICAL VULNERABILITY CONFIRMATION:
        # When vibration_mm_s == 0.0, the truthiness bug causes it to be skipped completely!
        log_zero = {"timestamp": "2023-11-04T08:00:00Z", "description": "Zero vibration test", "vibration_mm_s": 0.0}
        events_zero = extractor.reconstruct_timeline(equipment_tag="Pump-A12", telemetry_logs=[log_zero])
        # Vibration reading 0.0 is dropped from deviation analysis!
        assert "deviation_pct" not in events_zero[0].parameters, (
            "Vulnerability confirmed: vibration_mm_s = 0.0 evaluates to falsy in `a or b` and is ignored!"
        )

    def test_telemetry_none_description_unhandled_crash_vulnerability(self):
        """
        Adversarial probe:
        When a telemetry log has `description: None`, `_classify_sentence` crashes with
        `AttributeError: 'NoneType' object has no attribute 'lower'`.
        """
        extractor = TimelineExtractor()
        log_none_desc = {"timestamp": "2023-11-04T08:00:00Z", "description": None}
        with pytest.raises(AttributeError, match="'NoneType' object has no attribute 'lower'"):
            extractor.reconstruct_timeline(equipment_tag="Pump-A12", telemetry_logs=[log_none_desc])

    def test_citation_linking_overwrites_existing_event_citations_vulnerability(self):
        """
        Adversarial probe:
        When `reconstruct_timeline` is given `citations`, `_link_citations` overwrites
        any pre-existing `citation_ids` on the event and marks it `is_unsubstantiated=True`
        if the extra citations don't match the description text.
        """
        extractor = TimelineExtractor()
        old_cite = CitationObject(citation_id="CITE-PREEXISTING-01", source_doc="manual.pdf", excerpt="Pump manual details")
        unrelated_cite = CitationObject(citation_id="CITE-UNRELATED-02", source_doc="other.pdf", excerpt="Irrelevant cafeteria info")

        log_with_cite = {
            "timestamp": "2023-11-04T08:00:00Z",
            "description": "Custom bearing vibration",
            "citation_ids": [old_cite.citation_id],
        }

        # Reconstruct with unrelated citations passed
        events = extractor.reconstruct_timeline(
            equipment_tag="Pump-A12",
            telemetry_logs=[log_with_cite],
            citations=[unrelated_cite],
        )

        # EMPIRICAL VULNERABILITY CONFIRMATION:
        # Event already had CITE-PREEXISTING-01, but is now flagged as unsubstantiated!
        assert events[0].is_unsubstantiated is True, (
            "Vulnerability confirmed: _link_citations flags event as unsubstantiated despite having valid existing citations!"
        )


# ==============================================================================
# SECTION 2: HIGH CONCURRENCY & CITATION REGISTRY THREAD SAFETY
# ==============================================================================

class TestCitationRegistryConcurrency:
    """Stress testing CitationRegistry against race conditions, deadlock, and deduplication under heavy concurrency."""

    def test_high_concurrency_massive_duplicate_deduplication(self):
        """Probe: 50 worker threads attempting to register the exact same citation simultaneously (1,000 calls)."""
        reg = CitationRegistry()
        workers = 50
        iterations_per_worker = 20
        results: List[CitationObject] = []
        lock = threading.Lock()

        def worker_task(worker_id: int):
            local_results = []
            for _ in range(iterations_per_worker):
                cite = reg.register_citation(
                    source_doc="Pump-A12_Manual.pdf",
                    excerpt="Operating vibration threshold is strictly 5.0 mm/s.",
                    section="Envelope Specifications",
                )
                local_results.append(cite)
            with lock:
                results.extend(local_results)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(worker_task, i) for i in range(workers)]
            for f in as_completed(futures):
                f.result()

        total_registered_calls = workers * iterations_per_worker
        assert len(results) == total_registered_calls

        # Exact deduplication check
        all_ids = {c.citation_id for c in results}
        assert len(all_ids) == 1, f"Expected exactly 1 unique citation ID, found {len(all_ids)}: {all_ids}"
        registered_citations = reg.list_citations()
        assert len(registered_citations) == 1
        assert registered_citations[0].citation_id == list(all_ids)[0]

    def test_high_concurrency_unique_citations_registration(self):
        """Probe: 20 worker threads concurrently registering 1,000 unique citations."""
        reg = CitationRegistry()
        total_items = 1000
        workers = 20

        def worker_task(idx: int):
            return reg.register_citation(
                source_doc=f"Doc_{idx % 10}.txt",
                excerpt=f"Unique citation excerpt payload with sequence number {idx:05d}",
                section=f"Section {idx}",
            )

        with ThreadPoolExecutor(max_workers=workers) as executor:
            created = list(executor.map(worker_task, range(total_items)))

        assert len(created) == total_items
        unique_ids = {c.citation_id for c in created}
        assert len(unique_ids) == total_items

        all_stored = reg.list_citations()
        assert len(all_stored) == total_items

    def test_concurrent_read_write_validate_safety(self):
        """Probe: Concurrent readers and writers ensuring no dictionary mutation race conditions."""
        reg = CitationRegistry()
        stop_event = threading.Event()
        errors: List[Exception] = []

        for i in range(50):
            reg.register_citation(source_doc="InitDoc.txt", excerpt=f"Initial excerpt {i}")

        def writer():
            idx = 100
            while not stop_event.is_set():
                try:
                    reg.register_citation(
                        source_doc="DynamicDoc.txt",
                        excerpt=f"Dynamic continuous excerpt registration {idx}",
                    )
                    idx += 1
                    time.sleep(0.001)
                except Exception as ex:
                    errors.append(ex)

        def reader():
            while not stop_event.is_set():
                try:
                    cites = reg.list_citations()
                    assert isinstance(cites, list)
                    valid, invalid = reg.validate_citation_ids(["CITE-INITDOC-001", "NON-EXISTENT"])
                    assert isinstance(valid, list)
                    time.sleep(0.001)
                except Exception as ex:
                    errors.append(ex)

        threads = [threading.Thread(target=writer) for _ in range(4)] + [
            threading.Thread(target=reader) for _ in range(6)
        ]

        for t in threads:
            t.start()

        time.sleep(0.4)
        stop_event.set()

        for t in threads:
            t.join(timeout=2.0)

        assert len(errors) == 0, f"Thread errors encountered during concurrent R/W: {errors}"
        assert len(reg.list_citations()) >= 50

    def test_custom_id_collision_silent_overwrite_vulnerability(self):
        """
        Adversarial probe:
        When multiple callers register different documents/excerpts using the SAME custom_id,
        the second registration quietly overwrites the first in _citations,
        causing earlier lookups to return the wrong excerpt!
        """
        reg = CitationRegistry()
        c1 = reg.register_citation(source_doc="DocA.txt", excerpt="Original excerpt content A", custom_id="CITE-CUSTOM-01")
        c2 = reg.register_citation(source_doc="DocB.txt", excerpt="Conflicting excerpt content B", custom_id="CITE-CUSTOM-01")

        # EMPIRICAL VULNERABILITY CONFIRMATION:
        # c1 was overwritten by c2 under the same ID
        lookup = reg.get("CITE-CUSTOM-01")
        assert lookup.excerpt == "Conflicting excerpt content B"
        # Total citation count is 1, DocA citation was silently destroyed!
        assert len(reg.list_citations()) == 1


# ==============================================================================
# SECTION 3: TEXT EXTRACTION EDGE CASES (SPACED TEXT, UNICODE, REDOS, SCALE)
# ==============================================================================

class TestTextExtractionEdgeCases:
    """Stress testing text extraction against bizarre unicode, spaced artifacts, huge inputs, and ReDoS."""

    def test_spaced_text_cleaning_limitations(self):
        """
        Probe: clean_spaced_text works on single ASCII spaces with >=5 characters,
        but fails on double spaces, non-ASCII characters, and words with numbers.
        """
        # 1. Standard single-space ASCII >= 5 chars succeeds
        assert clean_spaced_text("C o n t a i n e r i z a t i o n") == "Containerization"

        # 2. Double spaces between letters fail to collapse
        double_spaced = "C  e  r  a  m  i  c"
        assert clean_spaced_text(double_spaced) == double_spaced  # Untouched!

        # 3. Words with digits fail to collapse
        pump_tag = "P u m p - A 1 2"
        assert clean_spaced_text(pump_tag) == pump_tag  # Untouched!

        # 4. Words < 5 characters fail to collapse
        short_word = "P u m p"
        assert clean_spaced_text(short_word) == short_word  # Untouched!

    def test_unicode_and_industrial_symbols_extraction(self):
        """Probe: Multilingual strings, emojis, mathematical/engineering symbols, RTL."""
        extractor = EvidenceCitationExtractor()
        content = """# Industrial Symbols Test
## Section 1: Mechanical Stress
Parameters: Temperature = 125.5 °C, Pressure = 14.8 bar, ΔP = 2.3 bar, Vibration = 5.8 mm/s.
Tolerance: ±0.05 mm, Roughness: 0.8 µm, Shaft: Ø 50 mm.
## Section 2: Multilingual & Emoji Logs
🚨 Critical failure alert! ⚠️ Operator ignored sound.
German: Überhitzung der Dichtungsringe festgestellt.
Arabic: فشل في مانع التسرب الميكانيكي تحت ضغط عالي.
Chinese: 机械密封在5.8毫米/秒振动下碎裂。
Russian: Разрушение керамического уплотнения насоса.
"""
        citations = extractor.parse_markdown_document(content, "multilingual_report.md")
        assert len(citations) >= 2
        all_text = " ".join(c.excerpt for c in citations)
        assert "125.5 °C" in all_text
        assert "ΔP" in all_text
        assert "±0.05 mm" in all_text
        assert "🚨" in all_text
        assert "Überhitzung" in all_text
        assert "فشل" in all_text
        assert "机械密封" in all_text

    def test_empty_and_whitespace_only_documents(self):
        """Probe: Empty strings, only whitespace, markdown headings with no body."""
        extractor = EvidenceCitationExtractor()
        assert extractor.parse_markdown_document("", "empty.md") == []
        assert extractor.parse_markdown_document("   \n\t\n   ", "whitespace.md") == []
        empty_headings = "# Heading 1\n## Heading 2\n### Heading 3\n"
        assert extractor.parse_markdown_document(empty_headings, "headings_only.md") == []

    def test_short_text_filtering_true_boundary(self):
        """Probe: Single-line blocks shorter than 5 chars are skipped."""
        extractor = EvidenceCitationExtractor()
        # "Hi" is 2 chars (< 5)
        short_content = "# Section\nHi\n"
        citations = extractor.parse_markdown_document(short_content, "short.md")
        assert len(citations) == 0

    def test_giant_document_parsing_performance(self):
        """Probe: 10,000 lines of markdown document parsed without OOM or slowdown."""
        extractor = EvidenceCitationExtractor()
        lines = []
        for i in range(50):
            lines.append(f"## Section {i}")
            for j in range(100):
                lines.append(f"Telemetry log row {j} for section {i}: sensor reading nominal at 4.2 mm/s.")
        giant_md = "\n".join(lines)

        t0 = time.perf_counter()
        cites = extractor.parse_markdown_document(giant_md, "giant_log.md")
        t_elapsed = time.perf_counter() - t0

        assert len(cites) == 50
        assert t_elapsed < 2.0, f"Parsing giant document took {t_elapsed:.2f}s (> 2.0s limit)"

    def test_redos_pattern_resilience(self):
        """Probe: Pathological inputs against regexes (vibration, time offset, spaced text)."""
        extractor = TimelineExtractor()

        pathological_vib = "vibration " * 500 + "5.8 mm/s"
        t0 = time.perf_counter()
        params = extractor._extract_parameters(pathological_vib, "Pump-A12")
        t_elapsed = time.perf_counter() - t0
        assert t_elapsed < 0.2
        assert params.get("vibration_mm_s") == 5.8

        pathological_hours = "48 " + "hours " * 300 + "prior"
        t0 = time.perf_counter()
        anchor = datetime(2023, 11, 4, 8, 0, 0, tzinfo=timezone.utc)
        extractor._extract_sentence_timestamp(pathological_hours, anchor)
        t_elapsed = time.perf_counter() - t0
        assert t_elapsed < 0.2

        pathological_spaced = ("A " * 2000)
        t0 = time.perf_counter()
        cleaned = clean_spaced_text(pathological_spaced)
        t_elapsed = time.perf_counter() - t0
        assert t_elapsed < 0.5


# ==============================================================================
# SECTION 4: CAUSAL GROUNDING UNDER EXTREME GRAPHS
# ==============================================================================

class TestCausalGroundingExtremeGraphs:
    """Stress testing verify_causal_grounding with cyclic, empty, invalid, and boundary graphs."""

    def test_circular_dependency_graph_termination(self):
        """
        Probe: Causal nodes forming a cyclic reference loop (Node 1 -> Node 2 -> Node 3 -> Node 1).
        Must terminate safely without infinite recursion or stack overflow.
        """
        reg = CitationRegistry()
        cite = reg.register_citation(source_doc="doc.txt", excerpt="Valid ground truth evidence")

        # Cyclic causal graph
        n1 = FiveWhyNode(why_id="WHY-1", level=1, cause_statement="Loop cause 1", parent_node_id="WHY-3", citation_ids=[cite.citation_id])
        n2 = FiveWhyNode(why_id="WHY-2", level=2, cause_statement="Loop cause 2", parent_node_id="WHY-1", citation_ids=[])
        n3 = FiveWhyNode(why_id="WHY-3", level=3, cause_statement="Loop cause 3", parent_node_id="WHY-2", citation_ids=[cite.citation_id])

        t0 = time.perf_counter()
        result = verify_causal_grounding([n1, n2, n3], reg)
        t_elapsed = time.perf_counter() - t0

        assert t_elapsed < 0.1
        assert result["total_causes"] == 3
        assert result["grounded_causes"] == 2
        assert result["ungrounded_causes"] == 1
        assert result["grounding_ratio"] == round(2 / 3, 4)
        assert result["compliance_status"] == "GROUNDING_DEFICIENT"  # 0.6667 < 0.70

    def test_100_percent_ungrounded_causes(self):
        """Probe: All causal claims ungrounded (0 citations registered)."""
        reg = CitationRegistry()
        nodes = [
            FiveWhyNode(why_id=f"WHY-{i}", level=i, cause_statement=f"Unverified cause level {i}", citation_ids=[])
            for i in range(1, 6)
        ]

        result = verify_causal_grounding(nodes, reg)
        assert result["total_causes"] == 5
        assert result["grounded_causes"] == 0
        assert result["ungrounded_causes"] == 5
        assert result["grounding_ratio"] == 0.0
        assert result["cgr"] == 0.0
        assert result["compliance_status"] == "GROUNDING_DEFICIENT"

        for n in nodes:
            assert n.is_unsubstantiated is True
            assert n.assumed_flag is True
            assert n.assumption_flag is True

    def test_invalid_and_nonexistent_citation_ids(self):
        """Probe: Nodes referencing malformed, empty, or ghost citation IDs."""
        reg = CitationRegistry()
        reg.register_citation(source_doc="doc.txt", excerpt="Only valid citation in registry")

        node_ghost = FiveWhyNode(
            why_id="WHY-GHOST",
            level=1,
            cause_statement="Claim backed by ghost citation",
            citation_ids=["CITE-NONEXISTENT-999"],
        )
        node_empty_id = FiveWhyNode(
            why_id="WHY-EMPTY",
            level=2,
            cause_statement="Claim backed by empty citation ID list",
            citation_ids=[],
        )

        result = verify_causal_grounding([node_ghost, node_empty_id], reg)
        assert result["grounded_causes"] == 0
        assert result["ungrounded_causes"] == 2
        assert result["compliance_status"] == "GROUNDING_DEFICIENT"
        assert node_ghost.is_unsubstantiated is True
        assert node_empty_id.is_unsubstantiated is True

    def test_cgr_boundary_threshold_transitions(self):
        """
        Probe exact boundary conditions:
        < 0.70 -> GROUNDING_DEFICIENT
        >= 0.70 and < 0.85 -> PROVISIONAL_ACCEPTANCE
        >= 0.85 -> AUDIT_GROUNDED
        """
        reg = CitationRegistry()
        c = reg.register_citation(source_doc="doc.txt", excerpt="Grounding evidence for test")

        def make_nodes(total: int, grounded: int) -> List[FiveWhyNode]:
            nodes = []
            for i in range(grounded):
                nodes.append(FiveWhyNode(why_id=f"WG-{i}", level=1, cause_statement=f"Grounded node {i}", citation_ids=[c.citation_id]))
            for i in range(total - grounded):
                nodes.append(FiveWhyNode(why_id=f"WU-{i}", level=1, cause_statement=f"Ungrounded node {i}", citation_ids=[]))
            return nodes

        # 1. Ratio = 0.60 (6/10) -> GROUNDING_DEFICIENT
        r1 = verify_causal_grounding(make_nodes(10, 6), reg)
        assert r1["grounding_ratio"] == 0.60
        assert r1["compliance_status"] == "GROUNDING_DEFICIENT"

        # 2. Ratio = 0.70 (7/10) -> PROVISIONAL_ACCEPTANCE
        r2 = verify_causal_grounding(make_nodes(10, 7), reg)
        assert r2["grounding_ratio"] == 0.70
        assert r2["compliance_status"] == "PROVISIONAL_ACCEPTANCE"

        # 3. Ratio = 0.80 (8/10) -> PROVISIONAL_ACCEPTANCE
        r3 = verify_causal_grounding(make_nodes(10, 8), reg)
        assert r3["grounding_ratio"] == 0.80
        assert r3["compliance_status"] == "PROVISIONAL_ACCEPTANCE"

        # 4. Ratio = 0.85 (17/20) -> AUDIT_GROUNDED
        r4 = verify_causal_grounding(make_nodes(20, 17), reg)
        assert r4["grounding_ratio"] == 0.85
        assert r4["compliance_status"] == "AUDIT_GROUNDED"

        # 5. Ratio = 1.00 (10/10) -> AUDIT_GROUNDED
        r5 = verify_causal_grounding(make_nodes(10, 10), reg)
        assert r5["grounding_ratio"] == 1.00
        assert r5["compliance_status"] == "AUDIT_GROUNDED"

    def test_fishbone_branch_grounding_crash_vulnerability(self):
        """
        Adversarial probe:
        CRITICAL VULNERABILITY:
        FishboneBranch (from rca_schemas.py) does not have `assumed_flag` field.
        Calling `verify_causal_grounding` on a list containing FishboneBranch raises:
        `ValueError: "FishboneBranch" object has no field "assumed_flag"`
        """
        reg = CitationRegistry()
        c = reg.register_citation(source_doc="doc.txt", excerpt="Common evidence citation")
        branch = FishboneBranch(category="Machine", causes=["Misaligned impeller shaft"], citation_ids=[c.citation_id])

        with pytest.raises(ValueError, match='"FishboneBranch" object has no field "assumed_flag"'):
            verify_causal_grounding([branch], reg)

    def test_dict_cause_object_crash_vulnerability(self):
        """
        Adversarial probe:
        Passing dictionary representations of causes to verify_causal_grounding crashes with
        `AttributeError: 'dict' object has no attribute 'is_unsubstantiated'`.
        """
        reg = CitationRegistry()
        with pytest.raises(AttributeError, match="'dict' object has no attribute 'is_unsubstantiated'"):
            verify_causal_grounding([{"citation_ids": []}], reg)


# ==============================================================================
# MAIN RUNNER
# ==============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
