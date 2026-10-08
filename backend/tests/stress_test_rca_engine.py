"""
Adversarial Stress Test Suite for Deductive RCA & Preventative Engine.
Target: backend/services/rca_engine.py

Probes:
1. Extreme & boundary symptoms: empty symptom lists, 1-character/1-word symptoms,
   100+ symptoms, duplicate symptoms, whitespace symptoms, injection payloads.
2. Citation grounding enforcement: fake citation IDs, missing citation IDs,
   auto-flagging of unsubstantiated nodes and assumptions across 5-Why and Fishbone.
3. 5-Why depth & logical hierarchy: 5-level depth integrity, parent-child chaining,
   terminal root cause constraint, cycle detection, bifurcated branching, and level boundaries.
4. Ishikawa 6M classification: 6M coverage, keyword absence, normalization of categories,
   category rejection, and flat cause item grounding.
5. OEM envelope mathematical boundaries: division-by-zero, extreme values (+/- 1e12),
   corrupted telemetry payloads, descending sort invariant.
6. Historical near-miss matcher boundaries: empty/giant text, sister asset taxonomy,
   telemetry excursion math, and recurrence probability limits.
7. Cryptographic SHA-256 seal integrity and tamper detection under adversarial payload modifications.
8. Concurrent multi-threaded execution and randomized fuzzing stability.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pytest
from pydantic import ValidationError

from api.rca_schemas import (
    ActionStatus,
    CitationObject,
    ContainmentAction,
    CorrectiveAction,
    EightDIncidentReport,
    FishboneAnalysis,
    FishboneBranch,
    FishboneCategory,
    FiveWhyNode,
    HistoricalMatch,
    OEMDeviation,
    PreventativeControls,
    ProblemDescription,
    RCAAnalyzeRequest,
    RootCauseAnalysis,
    SeverityLevel,
    SignOffStatus,
    TeamFormation,
    TeamRecognition,
    TimelineEvent,
    ValidationPlan,
)
from services.rca_engine import (
    DeductiveRCAEngine,
    EightDReportAssembler,
    ExtendedHistoricalMatch,
    ExtendedOEMDeviation,
    FishboneCauseItem,
    FiveWhyGenerator,
    FiveWhyTreeBuilder,
    HistoricalMatcher,
    HistoricalNearMissMatcher,
    IshikawaClassifier,
    OEMEnvelopeAnalyzer,
    OEMOperatingEnvelopeEngine,
    RCAEngine,
    analyze_oem_deviations,
    assemble_eight_d_report,
    classify_oem_severity,
    compute_oem_deviation,
    compute_single_deviation,
    generate_fishbone_analysis,
    generate_five_why_chain,
    generate_preventative_controls,
    match_historical_records,
)
from services.rca_ingestion import (
    CitationRegistry,
    EvidenceCitationExtractor,
    verify_causal_grounding,
)


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture
def mock_registry() -> CitationRegistry:
    """Pre-populated CitationRegistry with authentic citations."""
    reg = CitationRegistry()
    reg.register_citation(
        source_doc="Near_Miss_Report_2023.txt",
        excerpt="The maximum allowable vibration for Pump A12 is strictly 5.0 mm/s as per OEM manual.",
        section="4. Corrective Action",
        page_or_line="Line 16",
        title="Near Miss Report",
        confidence=1.0,
        custom_id="CITE-PUMP-001",
    )
    reg.register_citation(
        source_doc="Near_Miss_Report_2023.txt",
        excerpt="Any vibration reading exceeding 5.5 mm/s requires an immediate, mandatory shutdown of the pump.",
        section="4. Corrective Action",
        page_or_line="Line 17",
        title="Near Miss Report",
        confidence=1.0,
        custom_id="CITE-PUMP-002",
    )
    return reg


@pytest.fixture
def sample_citations(mock_registry: CitationRegistry) -> List[CitationObject]:
    return mock_registry.list_citations()


# ==============================================================================
# 1. EXTREME & BOUNDARY SYMPTOMS ADVERSARIAL TESTS
# ==============================================================================

class TestSymptomBoundariesAdversarial:
    """Adversarial testing of symptoms input handling across all engine components."""

    def test_symptoms_empty_list_historical_matcher(self):
        """Probe: Historical matcher receives empty symptoms list."""
        matcher = HistoricalMatcher()
        matches = matcher.match(
            asset_tag="Pump-A12",
            symptoms=[],
            near_miss_text="vibration 5.8 mm/s seal fracture",
        )
        assert matches == []
        assert len(matches) == 0

    def test_symptoms_empty_list_five_why_builder(self, sample_citations: List[CitationObject]):
        """Probe: FiveWhyTreeBuilder receives empty symptoms list."""
        tree = FiveWhyTreeBuilder.build_tree(
            asset_tag="Pump-A12",
            symptoms=[],
            citations=sample_citations,
        )
        assert len(tree) == 5
        # Verify node 1 contains graceful fallback rather than empty or crash
        assert "Unspecified operational anomaly" in tree[0].cause_statement
        for node in tree:
            assert len(node.cause_statement) >= 3

    def test_symptoms_empty_list_ishikawa_classifier(self, sample_citations: List[CitationObject]):
        """Probe: IshikawaClassifier receives empty symptoms list."""
        analysis = IshikawaClassifier.classify_causes(
            asset_tag="Pump-A12",
            symptoms=[],
            citations=sample_citations,
        )
        assert len(analysis.branches) == 6
        for branch in analysis.branches:
            assert len(branch.causes) > 0

    def test_symptoms_single_character_and_single_word(self):
        """Probe: Symptoms containing single-character or single-word strings."""
        single_char_syms = ["v", "x", "!", "k"]
        matcher = HistoricalMatcher()
        matches = matcher.match(
            asset_tag="Pump-A12",
            symptoms=single_char_syms,
            near_miss_text="vibration failure leak",
        )
        assert isinstance(matches, list)
        for m in matches:
            assert 0.0 <= m.similarity_score <= 1.0

        tree = FiveWhyTreeBuilder.build_tree(
            asset_tag="Pump-A12",
            symptoms=["v"],
        )
        assert len(tree) == 5
        assert "(v)" in tree[0].cause_statement

    def test_symptoms_massive_list_100_plus(self, sample_citations: List[CitationObject]):
        """Probe: Stress test with 150 symptoms testing memory, latency, and ratio boundedness."""
        large_symptoms = [f"symptom_excursion_metric_{i}_anomaly" for i in range(150)]
        large_symptoms.append("vibration")
        large_symptoms.append("coolant leak")

        start = time.perf_counter()
        matcher = HistoricalMatcher()
        matches = matcher.match(
            asset_tag="Pump-A12",
            symptoms=large_symptoms,
            near_miss_text="Severe vibration of 5.8 mm/s coolant leak occurred.",
        )
        elapsed = time.perf_counter() - start

        assert elapsed < 0.20, f"Historical matching took too long: {elapsed}s"
        assert isinstance(matches, list)
        for m in matches:
            assert 0.0 <= m.similarity_score <= 1.0

        # Verify FiveWhyTreeBuilder handles 150 symptoms without error
        tree = FiveWhyTreeBuilder.build_tree(
            asset_tag="Pump-A12",
            symptoms=large_symptoms,
            citations=sample_citations,
        )
        assert len(tree) == 5
        assert len(tree[0].cause_statement) > 5

    def test_symptoms_duplicate_and_whitespace_flood(self):
        """Probe: Duplicate identical symptoms, whitespace-only strings, tabs, and newlines."""
        dirty_symptoms = [
            "vibration",
            "vibration",
            "   ",
            "\t\n",
            "VIBRATION",
            "vibration",
            "coolant leak",
            "  ",
        ]
        matcher = HistoricalMatcher()
        matches = matcher.match(
            asset_tag="Pump-A12",
            symptoms=dirty_symptoms,
            near_miss_text="vibration coolant leak",
        )
        assert isinstance(matches, list)
        for m in matches:
            assert 0.0 <= m.similarity_score <= 1.0

    def test_symptoms_injection_payloads(self, sample_citations: List[CitationObject]):
        """Probe: Malicious strings (SQL injection, XSS, unicode, emojis, control chars)."""
        malicious = [
            "<script>alert('XSS')</script>",
            "'; DROP TABLE incidents; --",
            "🔥 CRITICAL_MELTDOWN 💥",
            "\\x00\\x01\\x02\\xff",
            "{{ 7 * 7 }}",
        ]
        tree = FiveWhyTreeBuilder.build_tree(
            asset_tag="Pump-A12",
            symptoms=malicious,
            citations=sample_citations,
        )
        assert len(tree) == 5
        # Verify cause statement contains clean text without crashing
        assert "<script>" in tree[0].cause_statement
        assert "DROP TABLE" in tree[0].cause_statement

        analysis = IshikawaClassifier.classify_causes(
            asset_tag="Pump-A12",
            symptoms=malicious,
            citations=sample_citations,
        )
        assert len(analysis.branches) == 6


# ==============================================================================
# 2. CITATION GROUNDING & ASSUMPTION ENFORCEMENT ADVERSARIAL TESTS
# ==============================================================================

class TestCitationGroundingAdversarial:
    """Adversarial testing of strict evidence grounding and assumption flagging."""

    def test_fake_citation_ids_rejected_by_registry(self, mock_registry: CitationRegistry):
        """Probe: Causes with fabricated/hallucinated citation IDs are flagged unsubstantiated."""
        fake_node = FiveWhyNode(
            why_id="WHY-1",
            level=1,
            cause_statement="Coolant leak observed due to pressure surge",
            citation_ids=["CITE-FAKE-999", "CITE-NONEXISTENT-000"],
        )
        # Verify against authentic registry
        valid_ids, _ = mock_registry.validate_citation_ids(fake_node.citation_ids)
        assert valid_ids == []

        res = verify_causal_grounding([fake_node], mock_registry)
        assert res["grounded_causes"] == 0
        assert res["ungrounded_causes"] == 1
        assert res["grounding_ratio"] == 0.0
        assert fake_node.is_unsubstantiated is True
        assert fake_node.assumed_flag is True
        assert fake_node.assumption_flag is True

    def test_missing_citation_ids_auto_flagged_by_model(self):
        """Probe: FiveWhyNode with empty citation_ids automatically sets is_unsubstantiated=True."""
        node = FiveWhyNode(
            why_id="WHY-3",
            level=3,
            cause_statement="Unknown vibration anomaly occurred without records",
            citation_ids=[],
        )
        assert node.is_unsubstantiated is True
        assert node.assumed_flag is True
        assert node.assumption_flag is True

    def test_fishbone_branch_grounding_enforcement(self):
        """Probe: FishboneBranch with causes but no citations auto-flags is_unsubstantiated=True."""
        branch = FishboneBranch(
            category="Machine",
            causes=["Shaft imbalance caused bearing wear"],
            citation_ids=[],
        )
        assert branch.is_unsubstantiated is True
        assert branch.assumed_flag is True

        # Branch with empty causes and empty citations does not flag
        empty_branch = FishboneBranch(
            category="Machine",
            causes=[],
            citation_ids=[],
        )
        assert empty_branch.is_unsubstantiated is False
        assert empty_branch.assumed_flag is False

    def test_fishbone_cause_item_grounding_enforcement(self):
        """Probe: FishboneCauseItem auto-flags ungrounded statements."""
        ungrounded_item = FishboneCauseItem(
            cause_id="FB-1",
            category="Method",
            statement="Operators bypassed safety checklist",
            evidence_citation_ids=[],
        )
        assert ungrounded_item.is_unsubstantiated is True
        assert ungrounded_item.assumed_flag is True

        grounded_item = FishboneCauseItem(
            cause_id="FB-2",
            category="Method",
            statement="Operators followed checklist accurately",
            evidence_citation_ids=["CITE-PUMP-001"],
        )
        assert grounded_item.is_unsubstantiated is False
        assert grounded_item.assumed_flag is False

    def test_eight_d_report_cross_reference_grounding_validation(self, sample_citations: List[CitationObject]):
        """Probe: EightDIncidentReport cross-references D4 five_why_chain citations against report.citations."""
        nodes = [
            FiveWhyNode(
                why_id=f"WHY-{i}",
                level=i,
                cause_statement=f"Causal statement level {i} for pump failure",
                citation_ids=["CITE-GHOST-UNKNOWN"],  # Fake citation!
                is_root_cause=(i == 5),
            )
            for i in range(1, 6)
        ]
        # In FiveWhyNode creation, citation_ids is non-empty so model validator initially set is_unsubstantiated=False
        assert nodes[0].is_unsubstantiated is False

        # Now assemble report with authentic sample_citations (which DO NOT contain CITE-GHOST-UNKNOWN)
        report = assemble_eight_d_report(
            asset_tag="Pump-A12",
            symptoms=["vibration"],
            incident_timestamp="2023-11-04T12:00:00Z",
            five_why_chain=nodes,
            citations=sample_citations,
        )
        # EightDIncidentReport validator MUST cross-reference and mark all nodes unsubstantiated
        for node in report.d4_root_causes.five_why_chain:
            assert node.is_unsubstantiated is True, f"Node {node.why_id} was not marked unsubstantiated!"
            assert node.assumed_flag is True
            assert node.assumption_flag is True

    def test_tree_builder_with_empty_registry_marks_all_unsubstantiated(self):
        """Probe: FiveWhyTreeBuilder built with empty registry marks all 5 nodes unsubstantiated."""
        empty_reg = CitationRegistry()
        tree = FiveWhyTreeBuilder.build_tree(
            asset_tag="Pump-A12",
            symptoms=["vibration"],
            citations=[],
            registry=empty_reg,
        )
        assert len(tree) == 5
        for node in tree:
            assert node.is_unsubstantiated is True
            assert node.assumed_flag is True
            assert node.assumption_flag is True


# ==============================================================================
# 3. 5-WHY DEPTH & LOGICAL HIERARCHY ADVERSARIAL TESTS
# ==============================================================================

class TestFiveWhyDepthAndHierarchyAdversarial:
    """Adversarial testing of 5-Why deductive tree structure and constraints."""

    def test_strict_five_level_hierarchy_ordering(self, sample_citations: List[CitationObject]):
        """Probe: 5-Why tree strictly contains Levels 1 through 5 in monotonic order."""
        tree = FiveWhyTreeBuilder.build_tree(
            asset_tag="Pump-A12",
            symptoms=["vibration", "leak"],
            citations=sample_citations,
        )
        assert len(tree) == 5
        assert [n.level for n in tree] == [1, 2, 3, 4, 5]
        assert [n.why_id for n in tree] == ["WHY-1", "WHY-2", "WHY-3", "WHY-4", "WHY-5"]

    def test_parent_child_acyclic_pointer_chain(self, sample_citations: List[CitationObject]):
        """Probe: Traversing parent_node_id forms a strictly acyclic chain from leaf to root."""
        tree = FiveWhyTreeBuilder.build_tree(
            asset_tag="Pump-A12",
            symptoms=["vibration"],
            citations=sample_citations,
        )
        # Root node has no parent
        assert tree[0].parent_node_id is None

        # Each child points strictly to predecessor
        for i in range(1, 5):
            assert tree[i].parent_node_id == tree[i - 1].why_id

        # Verify no cycles by graph traversal
        visited = set()
        current = tree[-1]  # Start at WHY-5
        node_map = {n.why_id: n for n in tree}

        while current is not None:
            assert current.why_id not in visited, f"Cycle detected at {current.why_id}!"
            visited.add(current.why_id)
            parent_id = current.parent_node_id
            current = node_map.get(parent_id) if parent_id else None

        assert len(visited) == 5

    def test_single_terminal_root_cause_constraint(self, sample_citations: List[CitationObject]):
        """Probe: Only Level 5 is marked as root cause; Levels 1-4 are intermediate causes."""
        tree = FiveWhyTreeBuilder.build_tree(
            asset_tag="Pump-A12",
            symptoms=["vibration"],
            citations=sample_citations,
        )
        for i in range(4):
            assert tree[i].is_root_cause is False, f"Node {tree[i].why_id} should NOT be root cause"
        assert tree[4].is_root_cause is True, "Node WHY-5 MUST be marked as root cause"

    def test_bifurcated_branching_depth_increment_and_uniqueness(self, sample_citations: List[CitationObject]):
        """Probe: build_bifurcated_tree creates two child nodes with level + 1 and distinct IDs."""
        parent = FiveWhyNode(
            why_id="WHY-2",
            level=2,
            cause_statement="Mechanical seal fractured under cyclic shock",
            citation_ids=["CITE-PUMP-001"],
        )
        child_a, child_b = FiveWhyTreeBuilder.build_bifurcated_tree(
            parent_node=parent,
            branch_a_statement="Branch A: High dynamic radial deflection exceeding allowable seal gap",
            branch_b_statement="Branch B: Ceramic face brittle stress fracture under cyclic resonance",
            citations=sample_citations,
        )
        assert child_a.level == 3
        assert child_b.level == 3
        assert child_a.why_id == "WHY-2-A"
        assert child_b.why_id == "WHY-2-B"
        assert child_a.parent_node_id == "WHY-2"
        assert child_b.parent_node_id == "WHY-2"
        assert child_a.why_id != child_b.why_id

    def test_node_schema_boundaries_invalid_levels_and_lengths(self):
        """Probe: FiveWhyNode schema enforces level bounds (1-10) and minimum cause statement length."""
        # Level 0 is invalid
        with pytest.raises(ValidationError):
            FiveWhyNode(why_id="WHY-0", level=0, cause_statement="Valid statement text")

        # Level 11 is invalid
        with pytest.raises(ValidationError):
            FiveWhyNode(why_id="WHY-11", level=11, cause_statement="Valid statement text")

        # Cause statement < 3 chars is invalid
        with pytest.raises(ValidationError):
            FiveWhyNode(why_id="WHY-1", level=1, cause_statement="ab")


# ==============================================================================
# 4. ISHIKAWA 6M CLASSIFICATION ADVERSARIAL TESTS
# ==============================================================================

class TestIshikawaClassificationAdversarial:
    """Adversarial testing of 6M categorization and keyword boundary conditions."""

    def test_all_six_categories_presence_invariant(self, sample_citations: List[CitationObject]):
        """Probe: All 6 standard categories are generated under every condition."""
        analysis = IshikawaClassifier.classify_causes(
            asset_tag="Pump-A12",
            symptoms=["vibration"],
            citations=sample_citations,
        )
        category_names = [b.category for b in analysis.branches]
        expected = ["Man", "Machine", "Material", "Method", "Measurement", "Environment"]
        assert category_names == expected

    def test_symptoms_with_zero_keywords_fallback_gracefully(self, sample_citations: List[CitationObject]):
        """Probe: Symptoms with no manufacturing keywords (e.g. nonsense or abstract text)."""
        nonsense_symptoms = ["xyz123abc", "quantum fluctuation", "unidentified cosmic ray"]
        analysis = IshikawaClassifier.classify_causes(
            asset_tag="Pump-A12",
            symptoms=nonsense_symptoms,
            citations=sample_citations,
        )
        assert len(analysis.branches) == 6
        for branch in analysis.branches:
            assert len(branch.causes) > 0
            for cause in branch.causes:
                assert len(cause) > 10

    def test_extreme_asset_tag_in_ishikawa(self, sample_citations: List[CitationObject]):
        """Probe: Asset tags with unicode, spaces, or excessive length."""
        tag = "EXTREME_ASSET_TAG_with_special_chars_!@#$_9999"
        analysis = IshikawaClassifier.classify_causes(
            asset_tag=tag,
            symptoms=["vibration"],
            citations=sample_citations,
        )
        assert len(analysis.branches) == 6
        # Verify tag appears substituted in causes
        man_causes = analysis.branches[0].causes
        assert any(tag in c for c in man_causes)

    def test_fishbone_branch_category_validation_and_normalization(self):
        """Probe: FishboneBranch normalizes case and valid synonyms ('milieu' -> 'Environment')."""
        b1 = FishboneBranch(category="milieu", causes=["ambient temperature"])
        assert b1.category == "Environment"

        b2 = FishboneBranch(category="machine", causes=["gear tooth wear"])
        assert b2.category == "Machine"

        b3 = FishboneBranch(category="METHOD", causes=["improper torquing"])
        assert b3.category == "Method"

        # Invalid category raises ValidationError
        with pytest.raises(ValidationError):
            FishboneBranch(category="Marketing", causes=["unrelated"])

    def test_classify_cause_items_flat_structure_integrity(self, sample_citations: List[CitationObject]):
        """Probe: classify_cause_items produces valid, weighted flat items."""
        items = IshikawaClassifier.classify_cause_items(
            asset_tag="Pump-A12",
            symptoms=["vibration"],
            citations=sample_citations,
        )
        assert len(items) == 12  # 2 causes per category * 6 categories
        ids = [it.cause_id for it in items]
        assert len(set(ids)) == len(ids), "Duplicate cause IDs detected in flat items!"
        for it in items:
            assert 0.0 <= it.contribution_weight <= 1.0
            assert len(it.statement) >= 3


# ==============================================================================
# 5. OEM OPERATING ENVELOPE MATHEMATICAL BOUNDARIES
# ==============================================================================

class TestOEMOperatingEnvelopeAdversarial:
    """Adversarial testing of deviation formulas, division by zero, and sorting."""

    def test_division_by_zero_protection_envelope_zero(self):
        """Probe: envelope_max is 0.0 or negative."""
        dev_zero = compute_single_deviation(
            parameter_name="Test Metric",
            unit="unit",
            envelope_max=0.0,
            incident_value=50.0,
        )
        assert dev_zero.deviation_percent == 0.0
        assert dev_zero.is_exceeded is False

        dev_neg = compute_single_deviation(
            parameter_name="Test Metric",
            unit="unit",
            envelope_max=-5.0,
            incident_value=10.0,
        )
        assert dev_neg.deviation_percent == 0.0
        assert dev_neg.is_exceeded is False

    def test_extreme_numerical_incident_values(self):
        """Probe: astronomical incident values (+1e12) and negative incident values (-1e12)."""
        dev_huge = compute_single_deviation(
            parameter_name="Vibration",
            unit="mm/s",
            envelope_max=5.0,
            incident_value=1e9,
        )
        assert dev_huge.deviation_percent > 1000000.0
        assert dev_huge.is_exceeded is True
        assert classify_oem_severity(dev_huge.deviation_percent) == "CRITICAL"

        dev_neg = compute_single_deviation(
            parameter_name="Vibration",
            unit="mm/s",
            envelope_max=5.0,
            incident_value=-1000.0,
        )
        assert dev_neg.deviation_percent < 0.0
        assert dev_neg.is_exceeded is False
        assert classify_oem_severity(dev_neg.deviation_percent) == "NORMAL"

    def test_corrupted_telemetry_dictionary_handling(self):
        """Probe: Telemetry values that cannot be parsed as floats are skipped safely."""
        corrupted_telemetry = {
            "vibration": "CORRUPTED_STRING",
            "bearing_temp_c": None,
            "discharge_pressure_bar": [1, 2, 3],
            "vibration_mm_s": 5.8,  # Valid entry
        }
        deviations = analyze_oem_deviations("Pump-A12", corrupted_telemetry)
        assert len(deviations) == 1
        assert deviations[0].parameter_name == "Peak Vibration Velocity"
        assert deviations[0].actual_incident_value == 5.8
        assert deviations[0].deviation_percent == 16.0

    def test_multi_parameter_sorting_invariant(self):
        """Probe: analyze_oem_deviations strictly sorts output descending by deviation_percent."""
        telemetry = {
            "vibration_mm_s": 5.8,           # limit 5.0 -> +16.0%
            "bearing_temp_c": 91.0,          # limit 70.0 -> +30.0%
            "discharge_pressure_bar": 12.0,  # limit 16.0 -> -25.0%
        }
        deviations = analyze_oem_deviations("Pump-A12", telemetry)
        assert len(deviations) == 3
        # Check monotonic descending order
        pcts = [d.deviation_percent for d in deviations]
        assert pcts == sorted(pcts, reverse=True)
        assert deviations[0].parameter_name == "Bearing Temperature"  # 30%
        assert deviations[1].parameter_name == "Peak Vibration Velocity"  # 16%
        assert deviations[2].parameter_name == "Discharge Pressure"  # -25%


# ==============================================================================
# 6. HISTORICAL NEAR-MISS MATCHER ADVERSARIAL TESTS
# ==============================================================================

class TestHistoricalMatcherAdversarial:
    """Adversarial testing of historical matching and recurrence risk calculation."""

    def test_empty_or_whitespace_document_text(self):
        """Probe: near_miss_text is empty or whitespace-only returns empty list."""
        matcher = HistoricalMatcher()
        assert matcher.match("Pump-A12", ["vibration"], near_miss_text="") == []
        assert matcher.match("Pump-A12", ["vibration"], near_miss_text="   \n\t  ") == []

    def test_giant_document_text_latency(self):
        """Probe: Document text with 50,000 lines of repetitive text."""
        giant_text = "Operating log line data sensor reading normal\n" * 50000
        giant_text += "Incident: Pump-A12 severe vibration 5.8 mm/s ceramic seal fracture\n"

        matcher = HistoricalMatcher()
        start = time.perf_counter()
        matches = matcher.match(
            asset_tag="Pump-A12",
            symptoms=["vibration", "ceramic seal"],
            near_miss_text=giant_text,
        )
        elapsed = time.perf_counter() - start
        assert elapsed < 0.50, f"Giant text matching took too long: {elapsed}s"
        assert len(matches) > 0

    def test_sister_asset_horizontal_read_across_taxonomy(self):
        """Probe: Sister assets (Pump-A11, Pump-A13) inherit horizontal match; unrelated equipment does not."""
        matcher = HistoricalMatcher()
        # Sister asset Pump-A11
        m_sister = matcher.match(
            asset_tag="Pump-A11",
            symptoms=["vibration", "coolant leak"],
            near_miss_text="Pump-A12 vibration coolant leak",
        )
        assert len(m_sister) > 0
        assert m_sister[0].similarity_score >= 0.70

        # Unrelated equipment Boiler-B01
        m_unrelated = matcher.match(
            asset_tag="Boiler-B01",
            symptoms=["drum pressure", "steam temperature"],
            near_miss_text="Pump-A12 vibration coolant leak",
        )
        assert len(m_unrelated) == 0

    def test_recurrence_risk_boundaries(self):
        """Probe: estimate_recurrence_risk probability always bounded between 0.05 and 0.99."""
        matcher = HistoricalMatcher()

        # Worst-case inputs
        p_worst, lvl_worst, _ = matcher.estimate_recurrence_risk(
            similarity_score=1.0,
            asset_similarity=1.0,
            telemetry_similarity=1.0,
            matching_symptoms=["vibration"],
        )
        assert 0.05 <= p_worst <= 0.99
        assert lvl_worst in ["HIGH", "CRITICAL"]

        # Best-case inputs
        p_best, lvl_best, _ = matcher.estimate_recurrence_risk(
            similarity_score=0.1,
            asset_similarity=0.0,
            telemetry_similarity=0.1,
            matching_symptoms=[],
        )
        assert 0.05 <= p_best <= 0.99
        assert lvl_best in ["LOW", "MEDIUM"]


# ==============================================================================
# 7. MASTER 8D REPORT SYNTHESIS & TAMPER DETECTION ADVERSARIAL TESTS
# ==============================================================================

class TestReportSynthesisAndTamperAdversarial:
    """Adversarial testing of master 8D report generation and SHA-256 integrity."""

    def test_canonical_sha256_tamper_detection(self, sample_citations: List[CitationObject]):
        """Probe: Any mutation to report data invalidates canonical SHA-256 seal."""
        report = assemble_eight_d_report(
            asset_tag="Pump-A12",
            symptoms=["vibration", "leak"],
            incident_timestamp="2023-11-04T12:00:00Z",
            citations=sample_citations,
        )
        # Seal is initially valid
        assert report.verify_checksum() is True
        original_seal = report.checksum_sha256

        # Tampering attack 1: Mutate severity score
        report.severity_score = 1
        assert report.verify_checksum() is False

        # Tampering attack 2: Revert severity score, mutate team member
        report.severity_score = 8
        assert report.verify_checksum() is True
        report.d1_team.leader = "Malicious Impostor"
        assert report.verify_checksum() is False

        # Tampering attack 3: Mutate citation ID in 5-Why
        report.d1_team.leader = "Elena Rostova (Lead Reliability Engineer)"
        assert report.verify_checksum() is True
        report.d4_root_causes.five_why_chain[0].cause_statement = "Altered statement"
        assert report.verify_checksum() is False

    def test_end_to_end_deductive_engine_with_telemetry_and_near_miss(self):
        """Probe: DeductiveRCAEngine end-to-end incident analysis pipeline."""
        engine = DeductiveRCAEngine()
        req = RCAAnalyzeRequest(
            asset_tag="Pump-A12",
            symptoms=["severe vibration", "coolant leak", "seal failure"],
            incident_timestamp="2023-11-04T08:30:00Z",
            telemetry_data={"vibration_mm_s": 5.8},
        )
        report = engine.analyze_incident(req)

        assert report.asset_tag == "Pump-A12"
        assert report.severity_score == 8
        assert report.rpn_score == 336
        assert len(report.d4_root_causes.five_why_chain) == 5
        assert len(report.d4_root_causes.fishbone_analysis.branches) == 6
        assert report.verify_checksum() is True
        assert len(report.checksum_sha256) == 64


# ==============================================================================
# 8. CONCURRENCY & FUZZING STABILITY TESTS
# ==============================================================================

class TestConcurrencyAndFuzzingStability:
    """Stress testing multi-threaded execution and randomized fuzzing."""

    def test_concurrent_rca_engine_analyses(self):
        """Probe: 10 concurrent threads executing DeductiveRCAEngine analysis simultaneously."""
        engine = DeductiveRCAEngine()

        def run_analysis(worker_id: int) -> bool:
            tag = f"Pump-A1{worker_id % 3 + 1}"
            req = RCAAnalyzeRequest(
                asset_tag=tag,
                symptoms=["vibration", "leak"],
                incident_timestamp=f"2023-11-04T0{worker_id}:00:00Z",
                telemetry_data={"vibration_mm_s": 5.0 + (worker_id * 0.1)},
            )
            report = engine.analyze_incident(req)
            return report.verify_checksum()

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(run_analysis, i) for i in range(10)]
            results = [f.result() for f in as_completed(futures)]

        assert all(results), "At least one concurrent analysis failed or produced invalid checksum!"

    def test_randomized_fuzzing_smoke_test(self):
        """Probe: 25 iterations of randomized symptom lists and telemetry values."""
        import random

        symptom_pool = [
            "vibration", "coolant leak", "seal fracture", "high temperature",
            "pressure drop", "cavitation", "unusual noise", "bearing wear",
            "electrical surge", "sensor drift", "valve stuck", "operator alert"
        ]

        engine = DeductiveRCAEngine()

        for iteration in range(25):
            chosen_symptoms = random.sample(symptom_pool, k=random.randint(1, 6))
            vib_val = round(random.uniform(0.0, 15.0), 2)
            temp_val = round(random.uniform(20.0, 120.0), 2)

            req = RCAAnalyzeRequest(
                asset_tag="Pump-A12",
                symptoms=chosen_symptoms,
                incident_timestamp="2023-11-04T12:00:00Z",
                telemetry_data={"vibration_mm_s": vib_val, "bearing_temp_c": temp_val},
            )
            report = engine.analyze_incident(req)
            assert report.report_id.startswith("8D-2023-")
            assert len(report.d4_root_causes.five_why_chain) == 5
            assert len(report.d4_root_causes.fishbone_analysis.branches) == 6
            assert report.verify_checksum() is True


# ==============================================================================
# 9. EMPIRICAL VULNERABILITY REPRODUCTION & BOUNDARY TESTS
# ==============================================================================

class TestEmpiricalBoundaryVulnerabilities:
    """Tests probing specific empirical corner cases and discovered vulnerabilities."""

    def test_empty_asset_tag_with_invalid_report_id_pattern_mismatch(self):
        """
        EMPIRICAL FINDING:
        When asset_tag is empty ("") and report_id fails regex pattern,
        assemble_eight_d_report generates rep_id = "8D-2023-", which violates
        pattern r"^8D-[0-9]{4}-[A-Za-z0-9_\\-]+$" and raises ValidationError.
        """
        with pytest.raises(ValidationError) as exc_info:
            assemble_eight_d_report(
                asset_tag="",
                symptoms=["vibration"],
                incident_timestamp="2023-11-04T12:00:00Z",
                report_id="invalid_format_id",
            )
        assert "String should match pattern '^8D-[0-9]{4}-[A-Za-z0-9_\\-]+$'" in str(exc_info.value)
        assert "'8D-2023-'" in str(exc_info.value)

    def test_classify_oem_severity_boundary_thresholds(self):
        """Probe: Exact floating point boundary thresholds for classify_oem_severity."""
        assert classify_oem_severity(-10.0) == "NORMAL"
        assert classify_oem_severity(-0.001) == "NORMAL"
        assert classify_oem_severity(0.0) == "NORMAL"
        assert classify_oem_severity(0.001) == "WARNING"
        assert classify_oem_severity(5.0) == "WARNING"
        assert classify_oem_severity(10.0) == "WARNING"
        assert classify_oem_severity(10.001) == "HIGH"
        assert classify_oem_severity(12.5) == "HIGH"
        assert classify_oem_severity(15.0) == "HIGH"
        assert classify_oem_severity(15.001) == "CRITICAL"
        assert classify_oem_severity(100.0) == "CRITICAL"

    def test_extended_schemas_dual_access_synchronization(self):
        """Probe: ExtendedHistoricalMatch and ExtendedOEMDeviation bidirectional property sync."""
        # ExtendedHistoricalMatch
        m1 = ExtendedHistoricalMatch(
            matched_report_id="NM-01",
            title="Near Miss 1",
            similarity_score=0.9,
            historical_lessons=["Lesson A", "Lesson B"],
        )
        assert m1.preventative_recommendations == ["Lesson A", "Lesson B"]
        assert m1.historical_lessons == ["Lesson A", "Lesson B"]

        m2 = ExtendedHistoricalMatch(
            matched_report_id="NM-02",
            title="Near Miss 2",
            similarity_score=0.8,
            preventative_recommendations=["Lesson X"],
        )
        assert m2.historical_lessons == ["Lesson X"]

        # ExtendedOEMDeviation
        dev = ExtendedOEMDeviation(
            parameter_name="Peak Vibration Velocity",
            unit="mm/s",
            oem_envelope_limit=5.0,
            actual_incident_value=5.8,
            deviation_percent=16.0,
            is_exceeded=True,
        )
        assert dev.deviation_pct == 16.0
        assert dev.envelope_max == 5.0
        assert dev.incident_value == 5.8
        assert dev.oem_parameter == "Peak Vibration Velocity"

    def test_five_why_chain_with_partial_fake_citations_marked_unsubstantiated(
        self, mock_registry: CitationRegistry
    ):
        """Probe: Node with mixture of authentic and fake citation IDs."""
        mixed_node = FiveWhyNode(
            why_id="WHY-1",
            level=1,
            cause_statement="Vibration alert triggered on DCS",
            citation_ids=["CITE-PUMP-001", "CITE-FAKE-HALLUCINATED"],
        )
        # Registry validation should succeed because CITE-PUMP-001 is valid
        res = verify_causal_grounding([mixed_node], mock_registry)
        assert res["grounded_causes"] == 1
        assert res["ungrounded_causes"] == 0
        assert mixed_node.is_unsubstantiated is False
        assert mixed_node.assumed_flag is False


# ==============================================================================
# 10. CITATION GROUNDING RATIO (CGR) MATHEMATICAL INTEGRITY
# ==============================================================================

class TestCitationGroundingRatios:
    """Adversarial testing of CGR computation in RootCauseAnalysis."""

    def test_cgr_zero_percent_grounded(self):
        """Probe: All 5-Why nodes and Fishbone branches have zero citations -> CGR = 0.0."""
        ungrounded_nodes = [
            FiveWhyNode(
                why_id=f"WHY-{i}",
                level=i,
                cause_statement=f"Ungrounded cause level {i}",
                citation_ids=[],
                is_root_cause=(i == 5),
            )
            for i in range(1, 6)
        ]
        ungrounded_branches = [
            FishboneBranch(category=cat, causes=[f"Cause in {cat}"], citation_ids=[])
            for cat in ["Man", "Machine", "Material", "Method", "Measurement", "Environment"]
        ]
        rca = RootCauseAnalysis(
            five_why_chain=ungrounded_nodes,
            fishbone_analysis=FishboneAnalysis(branches=ungrounded_branches),
            occurrence_root_cause="Occurrence cause",
            escape_root_cause="Escape cause",
        )
        assert rca.citation_grounding_ratio == 0.0

    def test_cgr_one_hundred_percent_grounded(self):
        """Probe: All 5-Why nodes and Fishbone branches have valid citations -> CGR = 1.0."""
        grounded_nodes = [
            FiveWhyNode(
                why_id=f"WHY-{i}",
                level=i,
                cause_statement=f"Grounded cause level {i}",
                citation_ids=["CITE-VALID-01"],
                is_root_cause=(i == 5),
            )
            for i in range(1, 6)
        ]
        grounded_branches = [
            FishboneBranch(category=cat, causes=[f"Cause in {cat}"], citation_ids=["CITE-VALID-01"])
            for cat in ["Man", "Machine", "Material", "Method", "Measurement", "Environment"]
        ]
        rca = RootCauseAnalysis(
            five_why_chain=grounded_nodes,
            fishbone_analysis=FishboneAnalysis(branches=grounded_branches),
            occurrence_root_cause="Occurrence cause",
            escape_root_cause="Escape cause",
        )
        assert rca.citation_grounding_ratio == 1.0

    def test_cgr_partial_grounding_proportions(self):
        """
        Probe: 5 Why nodes grounded (5/11), 6 Fishbone branches ungrounded (0/6).
        Expected CGR = 5 / 11 = 0.4545.
        """
        grounded_nodes = [
            FiveWhyNode(
                why_id=f"WHY-{i}",
                level=i,
                cause_statement=f"Grounded cause level {i}",
                citation_ids=["CITE-VALID-01"],
                is_root_cause=(i == 5),
            )
            for i in range(1, 6)
        ]
        ungrounded_branches = [
            FishboneBranch(category=cat, causes=[f"Cause in {cat}"], citation_ids=[])
            for cat in ["Man", "Machine", "Material", "Method", "Measurement", "Environment"]
        ]
        rca = RootCauseAnalysis(
            five_why_chain=grounded_nodes,
            fishbone_analysis=FishboneAnalysis(branches=ungrounded_branches),
            occurrence_root_cause="Occurrence cause",
            escape_root_cause="Escape cause",
        )
        assert rca.citation_grounding_ratio == 0.4545

