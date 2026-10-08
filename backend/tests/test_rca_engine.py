"""
Industrial Mind OS - Deductive Root Cause Analysis (RCA) Engine Test Suite
Location: backend/tests/test_rca_engine.py

Comprehensive unit test suite for Milestone 2:
1. 5-Why Recursive Causal Tree Engine (Hierarchy, Parent-Child, Root Cause, Grounding, Assumption Flagging)
2. Ishikawa 6M Fishbone Classifier (6M Categories, Keyword Matching, Citation Linking, Cause Items)
3. Historical Near-Miss Matching Engine (Pump-A12 Baseline, Sister Assets, Similarity Scoring, Risk Assessment)
4. OEM Operating Envelope Deviation Engine (Division-by-Zero, 4-Tier Severity, Multi-Param Sorting, Sister Assets)
5. Preventative Controls Generator (4 Pillars: SOP, PM, FMEA RPN 336->16, Horizontal Deployment)
6. Master Deductive RCA Engine & 8D Report Assembler (D1-D8 Synthesis, RPN Scoring, Canonical SHA-256 Seal)
"""

from __future__ import annotations

import os
import pytest
from datetime import datetime, timezone
from typing import Any, Dict, List

from api.rca_schemas import (
    ActionStatus,
    CitationObject,
    EightDIncidentReport,
    FishboneAnalysis,
    FishboneCategory,
    FiveWhyNode,
    HistoricalMatch,
    OEMDeviation,
    PreventativeControls,
    RCAAnalyzeRequest,
    RootCauseAnalysis,
    SeverityLevel,
    SignOffStatus,
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
    detect_asset_family,
    generate_fishbone_analysis,
    generate_five_why_chain,
    generate_preventative_controls,
    match_historical_records,
    match_semantic_citations,
    resolve_sister_assets,
)
from services.rca_ingestion import CitationRegistry, EvidenceCitationExtractor


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture
def near_miss_text() -> str:
    """Loads Near_Miss_Report_2023.txt from repository."""
    candidates = [
        "Near_Miss_Report_2023.txt",
        os.path.join("..", "Near_Miss_Report_2023.txt"),
        os.path.join(os.path.dirname(__file__), "..", "..", "Near_Miss_Report_2023.txt"),
    ]
    for c in candidates:
        if os.path.exists(c):
            with open(c, "r", encoding="utf-8") as f:
                return f.read()
    return """# INCIDENT REPORT & NEAR-MISS RECORD (2023-11-04)
## Equipment Tag: Pump-A12
Severe vibration level of 5.8 mm/s sustained for 48 hours shattered inboard ceramic seals.
Maximum allowable vibration strictly 5.0 mm/s as per OEM manual.
Mandatory shutdown protocol at 5.5 mm/s."""


@pytest.fixture
def sample_registry() -> CitationRegistry:
    """Pre-populated CitationRegistry with near-miss citations."""
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
    reg.register_citation(
        source_doc="Near_Miss_Report_2023.txt",
        excerpt="The sustained vibration at 5.8 mm/s shattered the inboard ceramic seals.",
        section="3. Root Cause Analysis (Historical)",
        page_or_line="Line 13",
        title="Near Miss Report",
        confidence=1.0,
        custom_id="CITE-PUMP-003",
    )
    reg.register_citation(
        source_doc="Near_Miss_Report_2023.txt",
        excerpt="Pump A12 experienced a catastrophic mechanical seal failure. This resulted in a minor leak of coolant fluid onto the factory floor.",
        section="2. Event Description",
        page_or_line="Line 10",
        title="Near Miss Report",
        confidence=1.0,
        custom_id="CITE-PUMP-004",
    )
    reg.register_citation(
        source_doc="Near_Miss_Report_2023.txt",
        excerpt="Operations personnel ignored the vibration alerts because they mistakenly believed the threshold was 6.5 mm/s.",
        section="3. Root Cause Analysis (Historical)",
        page_or_line="Line 13",
        title="Near Miss Report",
        confidence=1.0,
        custom_id="CITE-PUMP-005",
    )
    return reg


# ==============================================================================
# 1. FIVE-WHY DEDUCTIVE CAUSAL TREE TESTS
# ==============================================================================

class TestFiveWhyCausalTree:
    """Unit tests for FiveWhyTreeBuilder and FiveWhyGenerator."""

    def test_01_five_level_hierarchy_completeness(self, sample_registry: CitationRegistry):
        cites = sample_registry.list_citations()
        tree = FiveWhyTreeBuilder.build_tree(
            asset_tag="Pump-A12",
            symptoms=["vibration", "coolant leak"],
            telemetry={"vibration_mm_s": 5.8},
            citations=cites,
            registry=sample_registry,
        )
        assert len(tree) == 5
        for idx, node in enumerate(tree, start=1):
            assert node.level == idx
            assert node.why_id == f"WHY-{idx}"
            assert len(node.cause_statement) > 5

    def test_02_recursive_parent_child_linking(self, sample_registry: CitationRegistry):
        cites = sample_registry.list_citations()
        tree = FiveWhyTreeBuilder.build_tree(
            asset_tag="Pump-A12",
            symptoms=["vibration"],
            citations=cites,
            registry=sample_registry,
        )
        assert tree[0].parent_node_id is None
        for i in range(1, len(tree)):
            assert tree[i].parent_node_id == tree[i - 1].why_id

    def test_03_terminal_root_cause_flag(self, sample_registry: CitationRegistry):
        cites = sample_registry.list_citations()
        tree = FiveWhyTreeBuilder.build_tree(
            asset_tag="Pump-A12",
            symptoms=["vibration"],
            citations=cites,
            registry=sample_registry,
        )
        # Levels 1-4 should not be marked as root cause
        for node in tree[:-1]:
            assert node.is_root_cause is False
        # Terminal Level 5 must be marked as root cause
        assert tree[-1].is_root_cause is True

    def test_04_bifurcated_branching(self, sample_registry: CitationRegistry):
        cites = sample_registry.list_citations()
        parent = FiveWhyNode(
            why_id="WHY-1",
            level=1,
            cause_statement="Coolant leak observed on floor",
            citation_ids=[cites[0].citation_id],
        )
        branch_a, branch_b = FiveWhyTreeBuilder.build_bifurcated_tree(
            parent_node=parent,
            branch_a_statement="Ceramic mechanical seal brittle face fracture",
            branch_b_statement="Dynamic shaft deflection exceeding seal tolerance",
            citations=cites,
        )
        assert branch_a.why_id == "WHY-1-A"
        assert branch_a.level == 2
        assert branch_a.parent_node_id == "WHY-1"
        assert branch_b.why_id == "WHY-1-B"
        assert branch_b.level == 2
        assert branch_b.parent_node_id == "WHY-1"

    def test_05_grounded_citations_validation(self, sample_registry: CitationRegistry):
        cites = sample_registry.list_citations()
        tree = FiveWhyTreeBuilder.build_tree(
            asset_tag="Pump-A12",
            symptoms=["vibration"],
            citations=cites,
            registry=sample_registry,
        )
        for node in tree:
            assert node.is_unsubstantiated is False
            assert node.assumed_flag is False
            assert node.assumption_flag is False

    def test_06_unsubstantiated_auto_flagging_empty_citations(self):
        node = FiveWhyNode(
            why_id="WHY-X",
            level=1,
            cause_statement="Hypothesized ungrounded mechanical flaw",
            citation_ids=[],
        )
        assert node.is_unsubstantiated is True
        assert node.assumed_flag is True
        assert node.assumption_flag is True

    def test_07_dangling_citation_handling_against_registry(self, sample_registry: CitationRegistry):
        # Pass a citation ID that does not exist in the registry
        tree = FiveWhyTreeBuilder.build_tree(
            asset_tag="Pump-A12",
            symptoms=["vibration"],
            citations=[],
            registry=sample_registry,
        )
        for node in tree:
            assert node.is_unsubstantiated is True
            assert node.assumed_flag is True

    def test_08_alias_generator_and_module_function(self, sample_registry: CitationRegistry):
        cites = sample_registry.list_citations()
        tree1 = FiveWhyGenerator.build_tree("Pump-A12", ["vibration"], {}, cites, sample_registry)
        tree2 = generate_five_why_chain("Pump-A12", ["vibration"], {}, cites, sample_registry)
        assert len(tree1) == 5
        assert len(tree2) == 5
        assert tree1[-1].is_root_cause is True


# ==============================================================================
# 2. ISHIKAWA 6M FISHBONE CLASSIFIER TESTS
# ==============================================================================

class TestIshikawaClassifier:
    """Unit tests for IshikawaClassifier and FishboneAnalysis."""

    def test_09_all_six_categories_generated(self, sample_registry: CitationRegistry):
        cites = sample_registry.list_citations()
        fb = IshikawaClassifier.classify_causes("Pump-A12", ["vibration"], {}, cites)
        assert isinstance(fb, FishboneAnalysis)
        assert len(fb.branches) == 6
        cat_names = [b.category for b in fb.branches]
        expected = ["Man", "Machine", "Material", "Method", "Measurement", "Environment"]
        assert cat_names == expected

    def test_10_man_category_classification(self, sample_registry: CitationRegistry):
        cites = sample_registry.list_citations()
        fb = IshikawaClassifier.classify_causes("Pump-A12", ["vibration"], {}, cites)
        branch = fb.get_branch("Man")
        assert branch is not None
        assert len(branch.causes) >= 2
        joined = " ".join(branch.causes).lower()
        assert "operator" in joined or "personnel" in joined
        assert "training" in joined or "ignored" in joined

    def test_11_machine_and_material_classification(self, sample_registry: CitationRegistry):
        cites = sample_registry.list_citations()
        fb = IshikawaClassifier.classify_causes("Pump-A12", ["vibration"], {}, cites)
        mch = fb.get_branch("Machine")
        mat = fb.get_branch("Material")
        assert mch is not None and mat is not None
        mch_text = " ".join(mch.causes).lower()
        mat_text = " ".join(mat.causes).lower()
        assert "seal" in mch_text and "vibration" in mch_text
        assert "ceramic" in mat_text

    def test_12_method_and_measurement_classification(self, sample_registry: CitationRegistry):
        cites = sample_registry.list_citations()
        fb = IshikawaClassifier.classify_causes("Pump-A12", ["vibration"], {}, cites)
        meth = fb.get_branch("Method")
        meas = fb.get_branch("Measurement")
        assert meth is not None and meas is not None
        meth_text = " ".join(meth.causes).lower()
        meas_text = " ".join(meas.causes).lower()
        assert "sop" in meth_text or "procedure" in meth_text
        assert "dcs" in meas_text or "threshold" in meas_text or "6.5 mm/s" in meas_text

    def test_13_environment_classification(self, sample_registry: CitationRegistry):
        cites = sample_registry.list_citations()
        fb = IshikawaClassifier.classify_causes("Pump-A12", ["vibration"], {}, cites)
        env = fb.get_branch("Environment")
        assert env is not None
        env_text = " ".join(env.causes).lower()
        assert "resonance" in env_text or "sector 4" in env_text

    def test_14_citation_linking_on_branches(self, sample_registry: CitationRegistry):
        cites = sample_registry.list_citations()
        fb = IshikawaClassifier.classify_causes("Pump-A12", ["vibration"], {}, cites)
        for b in fb.branches:
            if b.causes:
                assert len(b.citation_ids) >= 1
                assert b.is_unsubstantiated is False
                assert b.assumed_flag is False

    def test_15_cause_items_flat_representation(self, sample_registry: CitationRegistry):
        cites = sample_registry.list_citations()
        items = IshikawaClassifier.classify_cause_items("Pump-A12", ["vibration"], cites)
        assert len(items) >= 6
        for it in items:
            assert isinstance(it, FishboneCauseItem)
            assert 0.0 <= it.contribution_weight <= 1.0
            assert len(it.statement) > 5

    def test_16_generate_fishbone_analysis_module_helper(self, sample_registry: CitationRegistry):
        cites = sample_registry.list_citations()
        fb = generate_fishbone_analysis("Pump-A12", ["vibration"], cites)
        assert len(fb.branches) == 6


# ==============================================================================
# 3. HISTORICAL NEAR-MISS SIMILARITY MATCHER TESTS
# ==============================================================================

class TestHistoricalMatcher:
    """Unit tests for HistoricalMatcher and HistoricalNearMissMatcher."""

    def test_17_pump_a12_exact_match(self, near_miss_text: str):
        matches = match_historical_records(
            asset_tag="Pump-A12",
            symptoms=["vibration", "ceramic seal", "coolant leak"],
            near_miss_text=near_miss_text,
        )
        assert len(matches) == 1
        m = matches[0]
        assert m.matched_report_id == "NM-2023-PUMP-A12"
        assert m.similarity_score >= 0.80
        assert "ceramic seal" in [s.lower() for s in m.matching_symptoms]
        assert m.equipment_family == "A-Series Centrifugal Pump"

    def test_18_sister_asset_pump_a11_read_across(self, near_miss_text: str):
        matches = match_historical_records(
            asset_tag="Pump-A11",
            symptoms=["vibration", "ceramic seal"],
            near_miss_text=near_miss_text,
        )
        assert len(matches) == 1
        m = matches[0]
        assert m.matched_report_id == "NM-2023-PUMP-A12"
        assert m.similarity_score >= 0.70
        assert m.equipment_family == "A-Series Centrifugal Pump"

    def test_19_sister_asset_pump_a13_horizontal(self, near_miss_text: str):
        matches = match_historical_records(
            asset_tag="Pump-A13",
            symptoms=["severe vibration", "coolant leak"],
            near_miss_text=near_miss_text,
        )
        assert len(matches) == 1
        assert matches[0].matched_report_id == "NM-2023-PUMP-A12"

    def test_20_unrelated_equipment_zero_matches(self, near_miss_text: str):
        matches = match_historical_records(
            asset_tag="Conveyor-C99",
            symptoms=["roller belt tear", "spillway blockage"],
            near_miss_text=near_miss_text,
        )
        assert len(matches) == 0

    def test_21_case_insensitivity(self, near_miss_text: str):
        m_upper = match_historical_records("PUMP-A12", ["VIBRATION", "COOLANT LEAK"], near_miss_text)
        m_lower = match_historical_records("pump-a12", ["vibration", "coolant leak"], near_miss_text)
        assert len(m_upper) == len(m_lower) == 1
        assert m_upper[0].similarity_score == m_lower[0].similarity_score

    def test_22_symptom_proportionality(self, near_miss_text: str):
        m_full = match_historical_records("Pump-A12", ["vibration"], near_miss_text)
        m_partial = match_historical_records(
            "Pump-A12", ["vibration", "unrelated_1", "unrelated_2", "unrelated_3"], near_miss_text
        )
        assert m_full[0].similarity_score > m_partial[0].similarity_score

    def test_23_empty_symptoms_returns_empty_list(self, near_miss_text: str):
        matches = match_historical_records("Pump-A12", [], near_miss_text)
        assert matches == []

    def test_24_empty_text_returns_empty_list(self):
        matches = match_historical_records("Pump-A12", ["vibration"], "")
        assert matches == []

    def test_25_historical_lessons_retrieval(self, near_miss_text: str):
        matches = match_historical_records("Pump-A12", ["vibration"], near_miss_text)
        assert len(matches) == 1
        lessons = " ".join(matches[0].historical_lessons)
        assert "5.0 mm/s" in lessons
        assert "shutdown" in lessons.lower()
        assert "retraining" in lessons.lower() or "re-training" in lessons.lower()

    def test_26_telemetry_excursion_scoring(self, near_miss_text: str):
        m_without_tel = match_historical_records(
            asset_tag="Pump-A12",
            symptoms=["vibration"],
            near_miss_text=near_miss_text,
        )
        m_with_tel = match_historical_records(
            asset_tag="Pump-A12",
            symptoms=["vibration"],
            near_miss_text=near_miss_text,
            telemetry_features={"vibration_mm_s": 5.8},
        )
        assert m_with_tel[0].similarity_score >= m_without_tel[0].similarity_score

    def test_27_recurring_risk_assessment_narrative(self, near_miss_text: str):
        matches = match_historical_records("Pump-A12", ["vibration", "ceramic seal"], near_miss_text)
        assert len(matches) == 1
        narrative = matches[0].recurring_risk_assessment
        assert "High risk of repeat ceramic seal fracture" in narrative
        assert "5.0 mm/s" in narrative

    def test_28_dual_schema_property_access(self, near_miss_text: str):
        matches = match_historical_records("Pump-A12", ["vibration"], near_miss_text)
        m = matches[0]
        assert isinstance(m, HistoricalMatch)
        assert len(m.preventative_recommendations) >= 3
        assert len(m.historical_lessons) >= 3
        assert m.historical_lessons == m.preventative_recommendations
        assert m.source_doc_citation_id == "CITE-NM-2023-01"

    def test_29_historical_near_miss_matcher_classmethod(self, near_miss_text: str):
        matches = HistoricalNearMissMatcher.match("Pump-A12", ["vibration"], near_miss_text)
        assert len(matches) >= 1
        assert matches[0].matched_report_id == "NM-2023-PUMP-A12"


# ==============================================================================
# 4. OEM OPERATING ENVELOPE DEVIATION ENGINE TESTS
# ==============================================================================

class TestOEMOperatingEnvelopeEngine:
    """Unit tests for OEM Operating Envelope Engine and Severity Stratification."""

    def test_30_pump_a12_critical_exceedance(self):
        dev = compute_single_deviation(
            parameter_name="Peak Vibration Velocity",
            unit="mm/s",
            envelope_max=5.0,
            incident_value=5.8,
        )
        assert dev.deviation_percent == 16.0
        assert dev.severity_level == SeverityLevel.CRITICAL
        assert dev.is_exceeded is True
        assert "CRITICAL" in dev.recommended_action

    def test_31_nominal_safe_operation(self):
        dev = compute_single_deviation(
            parameter_name="Peak Vibration Velocity",
            unit="mm/s",
            envelope_max=5.0,
            incident_value=4.2,
        )
        assert dev.deviation_percent == -16.0
        assert dev.severity_level == SeverityLevel.LOW
        assert dev.is_exceeded is False
        assert "NORMAL" in dev.recommended_action

    def test_32_exact_boundary_operation(self):
        dev = compute_single_deviation(
            parameter_name="Peak Vibration Velocity",
            unit="mm/s",
            envelope_max=5.0,
            incident_value=5.0,
        )
        assert dev.deviation_percent == 0.0
        assert dev.severity_level == SeverityLevel.LOW
        assert dev.is_exceeded is False
        assert "NORMAL" in dev.recommended_action

    def test_33_warning_tier_operation(self):
        dev = compute_single_deviation(
            parameter_name="Peak Vibration Velocity",
            unit="mm/s",
            envelope_max=5.0,
            incident_value=5.3,
        )
        assert dev.deviation_percent == 6.0
        assert dev.severity_level == SeverityLevel.HIGH
        assert dev.is_exceeded is True
        assert "WARNING" in dev.recommended_action

    def test_34_high_tier_operation(self):
        dev = compute_single_deviation(
            parameter_name="Peak Vibration Velocity",
            unit="mm/s",
            envelope_max=5.0,
            incident_value=5.6,
        )
        assert dev.deviation_percent == 12.0
        assert dev.severity_level == SeverityLevel.HIGH
        assert dev.is_exceeded is True
        assert "HIGH" in dev.recommended_action

    def test_35_division_by_zero_protection(self):
        dev = compute_single_deviation(
            parameter_name="Test Parameter",
            unit="bar",
            envelope_max=0.0,
            incident_value=10.0,
        )
        assert dev.deviation_percent == 0.0
        assert dev.is_exceeded is False
        assert dev.severity_level == SeverityLevel.LOW

    def test_36_steam_turbine_overspeed_deviation(self):
        dev = compute_oem_deviation(
            parameter_name="Rotor Speed",
            unit="RPM",
            envelope_max=3300.0,
            incident_value=3450.0,
        )
        assert dev.deviation_pct == 4.55
        assert dev.severity_level == SeverityLevel.HIGH

    def test_37_boiler_temperature_critical(self):
        dev = compute_single_deviation(
            parameter_name="Superheater Steam Temperature",
            unit="°C",
            envelope_max=540.0,
            incident_value=575.0,
        )
        assert dev.deviation_percent == 6.48
        assert dev.severity_level == SeverityLevel.HIGH

    def test_38_multi_parameter_evaluation_and_descending_sort(self):
        telemetry = {
            "vibration_mm_s": 5.8,       # 5.0 limit -> +16.0% (CRITICAL)
            "bearing_temp_c": 78.0,      # 70.0 limit -> +11.43% (HIGH)
            "discharge_pressure_bar": 14.0, # 16.0 limit -> -12.5% (LOW)
        }
        deviations = analyze_oem_deviations("Pump-A12", telemetry)
        assert len(deviations) == 3
        # Must be sorted descending by deviation_percent
        assert deviations[0].deviation_percent >= deviations[1].deviation_percent
        assert deviations[1].deviation_percent >= deviations[2].deviation_percent
        assert deviations[0].parameter_name == "Peak Vibration Velocity"
        assert deviations[0].deviation_percent == 16.0

    def test_39_sister_asset_parameter_inheritance(self):
        # Pump-A11 should inherit Pump-A12 specs
        telemetry = {"vibration_mm_s": 5.8}
        devs_a11 = analyze_oem_deviations("Pump-A11", telemetry)
        devs_a12 = analyze_oem_deviations("Pump-A12", telemetry)
        assert len(devs_a11) == 1 and len(devs_a12) == 1
        assert devs_a11[0].oem_envelope_limit == devs_a12[0].oem_envelope_limit
        assert devs_a11[0].deviation_percent == devs_a12[0].deviation_percent

    def test_40_unknown_asset_fallback_to_default(self):
        telemetry = {"vibration_mm_s": 5.4}  # default limit 4.5 -> +20.0%
        devs = analyze_oem_deviations("UNKNOWN-MACHINE-99", telemetry)
        assert len(devs) == 1
        assert devs[0].oem_envelope_limit == 4.5
        assert devs[0].deviation_percent == 20.0
        assert devs[0].severity_level == SeverityLevel.CRITICAL

    def test_41_dual_access_alias_attributes(self):
        dev = compute_single_deviation("Peak Vibration Velocity", "mm/s", 5.0, 5.8)
        assert dev.deviation_pct == dev.deviation_percent == 16.0
        assert dev.envelope_max == dev.oem_envelope_limit == 5.0
        assert dev.incident_value == dev.actual_incident_value == 5.8
        assert dev.oem_parameter == dev.parameter_name == "Peak Vibration Velocity"


# ==============================================================================
# 5. PREVENTATIVE MAINTENANCE & CONTROLS GENERATOR TESTS
# ==============================================================================

class TestPreventativeControlsGenerator:
    """Unit tests for generate_preventative_controls and D7 4-pillar integration."""

    def test_42_four_pillars_presence(self):
        devs = [compute_single_deviation("Peak Vibration Velocity", "mm/s", 5.0, 5.8)]
        controls = generate_preventative_controls("Pump-A12", devs, initial_rpn=336)
        assert isinstance(controls, PreventativeControls)
        # Pillar 1: SOP updates
        assert len(controls.sop_updates) >= 3
        # Pillar 2: PM schedule updates
        assert len(controls.pm_updates) >= 3
        # Pillar 3: FMEA risk matrix reduction in description
        assert "336" in controls.description and "16" in controls.description
        assert "risk reduction" in controls.description
        # Pillar 4: Horizontal deployment assets
        assert "Pump-A11" in controls.horizontal_assets
        assert "Pump-A13" in controls.horizontal_assets

    def test_43_fmea_rpn_mitigation_exceeds_90_percent(self):
        devs = [compute_single_deviation("Peak Vibration Velocity", "mm/s", 5.0, 5.8)]
        controls = generate_preventative_controls("Pump-A12", devs, initial_rpn=336)
        # 336 down to 16 = 95.24% reduction
        assert "95.24%" in controls.description or "95.2%" in controls.description
        assert controls.status == ActionStatus.OPEN

    def test_44_sister_assets_mapping(self):
        devs = [compute_single_deviation("Peak Vibration Velocity", "mm/s", 5.0, 5.8)]
        ctrl_a12 = generate_preventative_controls("Pump-A12", devs)
        assert set(ctrl_a12.horizontal_assets) == {"Pump-A11", "Pump-A13"}
        ctrl_a11 = generate_preventative_controls("Pump-A11", devs)
        assert set(ctrl_a11.horizontal_assets) == {"Pump-A12", "Pump-A13"}


# ==============================================================================
# 6. MASTER DEDUCTIVE RCA ENGINE & 8D REPORT ASSEMBLER TESTS
# ==============================================================================

class TestDeductiveRCAEngineAndReportAssembler:
    """Unit tests for DeductiveRCAEngine, EightDReportAssembler, and SHA-256 sealing."""

    def test_45_master_engine_full_report_generation(self, sample_registry: CitationRegistry):
        engine = DeductiveRCAEngine(registry=sample_registry)
        req = RCAAnalyzeRequest(
            asset_tag="Pump-A12",
            symptoms=["mechanical seal failure", "coolant leak", "high vibration"],
            incident_timestamp="2023-11-04T08:00:00Z",
            telemetry_data={"vibration_mm_s": 5.8},
        )
        report = engine.analyze_incident(req)

        assert isinstance(report, EightDIncidentReport)
        assert report.report_id.startswith("8D-2023-")
        assert report.asset_tag == "Pump-A12"
        assert report.severity_score == 8
        assert report.rpn_score == 336  # 8 * 7 * 6

        # Check D1 through D8
        assert report.d1_team.leader != ""
        assert report.d2_problem.what != ""
        assert len(report.d3_containment) >= 1
        assert len(report.d4_root_causes.five_why_chain) == 5
        assert len(report.d4_root_causes.fishbone_analysis.branches) == 6
        assert len(report.d5_permanent_actions) >= 2
        assert report.d6_validation.metrics != ""
        assert len(report.d7_preventative_controls.sop_updates) >= 3
        assert report.d8_recognition.signoff_status == SignOffStatus.APPROVED

    def test_46_dual_vector_root_causes(self, sample_registry: CitationRegistry):
        engine = DeductiveRCAEngine(registry=sample_registry)
        req = RCAAnalyzeRequest(
            asset_tag="Pump-A12",
            symptoms=["vibration", "coolant leak"],
            incident_timestamp="2023-11-04T08:00:00Z",
        )
        report = engine.analyze_incident(req)
        rc = report.d4_root_causes
        assert "fatigue" in rc.occurrence_root_cause.lower() or "fracture" in rc.occurrence_root_cause.lower()
        assert "alarm" in rc.escape_root_cause.lower() or "interlock" in rc.escape_root_cause.lower()

    def test_47_canonical_sha256_checksum_and_tamper_proofing(self, sample_registry: CitationRegistry):
        engine = DeductiveRCAEngine(registry=sample_registry)
        req = RCAAnalyzeRequest(
            asset_tag="Pump-A12",
            symptoms=["vibration"],
            incident_timestamp="2023-11-04T08:00:00Z",
            telemetry_data={"vibration_mm_s": 5.8},
        )
        report = engine.analyze_incident(req)

        digest = report.checksum_sha256
        assert len(digest) == 64
        assert report.verify_checksum() is True
        assert report.verify_sha256() is True

        # Tampering with a field must invalidate checksum
        report.severity_score = 10
        assert report.verify_checksum() is False

    def test_48_citation_grounding_ratio(self, sample_registry: CitationRegistry):
        engine = DeductiveRCAEngine(registry=sample_registry)
        req = RCAAnalyzeRequest(
            asset_tag="Pump-A12",
            symptoms=["vibration"],
            incident_timestamp="2023-11-04T08:00:00Z",
            telemetry_data={"vibration_mm_s": 5.8},
        )
        report = engine.analyze_incident(req)
        cgr = report.d4_root_causes.citation_grounding_ratio
        assert cgr > 0.0
        assert 0.0 <= cgr <= 1.0

    def test_49_assemble_eight_d_report_standalone(self, sample_registry: CitationRegistry):
        cites = sample_registry.list_citations()
        report = assemble_eight_d_report(
            asset_tag="Pump-A12",
            symptoms=["ceramic seal fracture", "vibration"],
            incident_timestamp="2023-11-04T08:00:00Z",
            telemetry_data={"vibration_mm_s": 5.8},
            citations=cites,
        )
        assert isinstance(report, EightDIncidentReport)
        assert report.verify_checksum() is True
        assert len(report.d4_root_causes.five_why_chain) == 5

    def test_50_rca_engine_and_assembler_aliases(self, sample_registry: CitationRegistry):
        engine = RCAEngine(registry=sample_registry)
        report = engine.analyze(
            asset_tag="Pump-A12",
            symptoms=["vibration"],
            incident_timestamp="2023-11-04T08:00:00Z",
            telemetry_data={"vibration_mm_s": 5.8},
        )
        assert isinstance(report, EightDIncidentReport)
        assert report.verify_checksum() is True


# ==============================================================================
# 7. MILESTONE 2 REMEDIATIONS & CROSS-ASSET ADVERSARIAL VERIFICATION
# ==============================================================================

class TestMilestone2Remediations:
    """
    Independent verification suite for Reviewer 1 & Challenger 2 Remediations:
    1. Cross-Asset 5-Why synthesis (Steam Turbine, Boiler, Pump, General).
    2. Dynamic keyword-based Ishikawa 6M classification without static pump narratives.
    3. Dynamic sister asset resolution and bounded FMEA RPN mitigation.
    4. OEM operating envelope lower-bound detection and negative math safety.
    5. Semantic citation grounding and ungrounded claim flagging.
    """

    def test_51_steam_turbine_cross_asset_rca(self, sample_registry: CitationRegistry):
        """Reviewer 1 Core Challenge: TURB-ST-04 must NOT produce ceramic pump narratives."""
        cites = sample_registry.list_citations()
        report = assemble_eight_d_report(
            asset_tag="TURB-ST-04",
            symptoms=["bearing vibration", "low lube oil pressure"],
            incident_timestamp="2024-04-12T10:00:00Z",
            telemetry_data={"rpm": 3450, "lube_oil_pressure_bar": 0.8},
            citations=cites,
        )
        assert isinstance(report, EightDIncidentReport)
        assert report.verify_checksum() is True

        # Assert no pump/ceramic references leaked into turbine generated disciplines
        d2_text = report.d2_problem.model_dump_json().lower()
        d4_text = report.d4_root_causes.model_dump_json().lower()
        d7_text = report.d7_preventative_controls.model_dump_json().lower()
        assert "ceramic" not in d2_text
        assert "ceramic" not in d4_text
        assert "ceramic" not in d7_text
        assert "a-series pump" not in d2_text
        assert "a-series pump" not in d4_text

        # Dynamic 5-Why turbine verification
        chain = report.d4_root_causes.five_why_chain
        assert len(chain) == 5
        assert "TURB-ST-04" in chain[0].cause_statement
        assert any("bearing" in node.cause_statement.lower() or "lube" in node.cause_statement.lower() or "oil" in node.cause_statement.lower() for node in chain)
        assert chain[-1].is_root_cause is True

        # Sister assets must be turbine-derived
        sisters = report.d7_preventative_controls.sister_assets
        assert "TURB-ST-01" in sisters or "TURB-ST-02" in sisters
        assert "Pump-A11" not in sisters

    def test_52_boiler_cross_asset_rca(self, sample_registry: CitationRegistry):
        """Reviewer 1 Cross-Asset: High-pressure boiler must produce boiler-specific RCA."""
        cites = sample_registry.list_citations()
        report = assemble_eight_d_report(
            asset_tag="BLR-HP-101",
            symptoms=["steam temperature excursion", "pressure spike"],
            incident_timestamp="2024-04-12T10:00:00Z",
            telemetry_data={"temperature_c": 575.0, "pressure_bar": 128.0},
            citations=cites,
        )
        assert isinstance(report, EightDIncidentReport)
        d2_text = report.d2_problem.model_dump_json().lower()
        d4_text = report.d4_root_causes.model_dump_json().lower()
        d7_text = report.d7_preventative_controls.model_dump_json().lower()
        assert "ceramic" not in d2_text
        assert "ceramic" not in d4_text
        assert "ceramic" not in d7_text

        # Boiler sister assets
        sisters = report.d7_preventative_controls.sister_assets
        assert "BLR-HP-102" in sisters or "BLR-HP-103" in sisters

        # 5-Why chain checks
        chain = report.d4_root_causes.five_why_chain
        assert len(chain) == 5
        assert "BLR-HP-101" in chain[0].cause_statement
        assert any("boiler" in node.cause_statement.lower() or "superheater" in node.cause_statement.lower() or "steam" in node.cause_statement.lower() for node in chain)

    def test_53_lower_bound_lube_pressure_deviation(self):
        """Reviewer 1 Lower-Bound: Lube oil pressure below nominal_min must trigger CRITICAL deviation."""
        # Incident value 0.8 bar is below nominal_min (1.5 bar) and trip limit (1.0 bar)
        devs = analyze_oem_deviations(
            asset_tag="TURB-ST-04",
            telemetry_data={"lube_oil_pressure_bar": 0.8},
        )
        assert len(devs) >= 1
        lube_dev = next((d for d in devs if "lube" in d.parameter_name.lower()), None)
        assert lube_dev is not None
        assert lube_dev.is_exceeded is True
        assert lube_dev.deviation_percent > 40.0
        assert lube_dev.severity_level == SeverityLevel.CRITICAL
        assert lube_dev.is_lower_bound is True

        # Safe value: 1.8 bar is above nominal_min (1.5 bar)
        safe_devs = analyze_oem_deviations(
            asset_tag="TURB-ST-04",
            telemetry_data={"lube_oil_pressure_bar": 1.8},
        )
        safe_lube = next((d for d in safe_devs if "lube" in d.parameter_name.lower()), None)
        assert safe_lube is not None
        assert safe_lube.is_exceeded is False
        assert safe_lube.severity_level == SeverityLevel.LOW

    def test_54_dynamic_ishikawa_6m_classifier_turbine(self, sample_registry: CitationRegistry):
        """Challenger 2: Ishikawa classifier dynamically synthesizes 6M categories for non-pumps."""
        cites = sample_registry.list_citations()
        fb = IshikawaClassifier.classify_causes(
            asset_tag="TURB-ST-04",
            symptoms=["bearing vibration", "lube oil pressure drop"],
            telemetry={"rpm": 3450, "lube_oil_pressure_bar": 0.8},
            citations=cites,
        )
        assert len(fb.branches) == 6
        machine_branch = fb.get_branch("Machine")
        assert machine_branch is not None
        joined = " ".join(machine_branch.causes).lower()
        assert "bearing" in joined or "governor" in joined or "turbine" in joined
        assert "ceramic mechanical seal" not in joined

        env_branch = fb.get_branch("Environment")
        assert env_branch is not None
        assert len(env_branch.causes) >= 1

    def test_55_dynamic_sister_asset_resolution(self):
        """Sister asset resolution derives siblings from tag prefix and numbering."""
        assert resolve_sister_assets("TURB-ST-04") == ["TURB-ST-01", "TURB-ST-02"]
        assert resolve_sister_assets("BLR-HP-101") == ["BLR-HP-102", "BLR-HP-103"]
        assert resolve_sister_assets("Pump-A12") == ["Pump-A11", "Pump-A13"]
        assert resolve_sister_assets("GEN-1") == ["GEN-2", "GEN-3"]

    def test_56_semantic_citation_grounding_flags_unsubstantiated(self):
        """Semantic citation matching marks causes without evidentiary backing as unsubstantiated."""
        # Unrelated citation registry
        unrelated_reg = CitationRegistry()
        unrelated_reg.register_citation(
            source_doc="Chemical_Reactor_Guide.txt",
            excerpt="Reactor vessel jacket temperature must not exceed 95 Celsius.",
            section="Operations",
            page_or_line="Page 4",
            title="Reactor Guide",
            confidence=1.0,
            custom_id="CITE-CHEM-999",
        )
        cites = unrelated_reg.list_citations()
        tree = FiveWhyTreeBuilder.build_tree(
            asset_tag="TURB-ST-04",
            symptoms=["lube oil pressure drop"],
            telemetry={"lube_oil_pressure_bar": 0.8},
            citations=cites,
            registry=unrelated_reg,
        )
        # All turbine nodes should be flagged as unsubstantiated because citation has zero overlap
        for node in tree:
            assert node.is_unsubstantiated is True
            assert node.assumed_flag is True

        # Now add a substantiated turbine citation
        unrelated_reg.register_citation(
            source_doc="Turbine_Manual.txt",
            excerpt="Steam turbine journal bearings require minimum 1.5 bar lube oil pressure to prevent hydrodynamic collapse.",
            section="Lubrication",
            page_or_line="Section 3.1",
            title="Turbine OEM Manual",
            confidence=1.0,
            custom_id="CITE-TURB-001",
        )
        cites2 = unrelated_reg.list_citations()
        tree2 = FiveWhyTreeBuilder.build_tree(
            asset_tag="TURB-ST-04",
            symptoms=["lube oil pressure drop"],
            telemetry={"lube_oil_pressure_bar": 0.8},
            citations=cites2,
            registry=unrelated_reg,
        )
        # At least one node in tree2 should now be grounded
        grounded_nodes = [n for n in tree2 if not n.is_unsubstantiated]
        assert len(grounded_nodes) >= 1

    def test_57_fmea_rpn_mitigation_when_initial_below_16(self):
        """Mitigated RPN must never exceed initial RPN even when initial RPN < 16."""
        ctrl_small = generate_preventative_controls("PUMP-01", initial_rpn=10)
        assert ctrl_small.mitigated_rpn <= 10
        assert ctrl_small.mitigated_rpn <= ctrl_small.initial_rpn

        ctrl_zero = generate_preventative_controls("PUMP-01", initial_rpn=0)
        assert ctrl_zero.mitigated_rpn == 0

        ctrl_normal = generate_preventative_controls("PUMP-01", initial_rpn=336)
        assert ctrl_normal.mitigated_rpn == 16
        assert ctrl_normal.rpn_reduction_percent > 90.0

    def test_58_json_roundtrip_lower_bound_persistence(self):
        """Lower-bound telemetry excursion (TURB-ST-04 lube oil pressure 0.8 bar)
        survives model_validate_json(rep.model_dump_json()), preserving positive deviation,
        CRITICAL severity, and SHA-256 seal invariance.
        """
        rep = assemble_eight_d_report(
            asset_tag="TURB-ST-04",
            symptoms=["low lube oil pressure excursion"],
            incident_timestamp="2024-04-12T10:00:00Z",
            telemetry_data={"lube_oil_pressure_bar": 0.8},
        )
        assert rep.verify_checksum() is True

        json_str = rep.model_dump_json()
        reloaded = EightDIncidentReport.model_validate_json(json_str)

        # 1. SHA-256 digital seal invariance
        assert reloaded.verify_checksum() is True

        # 2. Lower-bound deviation math preservation (> 40%, CRITICAL severity)
        oem_devs = reloaded.d7_preventative_controls.oem_deviations
        assert len(oem_devs) >= 1
        lube_dev = next((d for d in oem_devs if "lube" in d.parameter_name.lower()), None)
        assert lube_dev is not None
        assert lube_dev.deviation_percent > 40.0
        assert lube_dev.severity_level == SeverityLevel.CRITICAL
        assert lube_dev.is_exceeded is True

    def test_59_general_rotating_asset_narrative_isolation(self):
        """Uncataloged assets (GEN-1, COMP-01) must generate generic rotating machinery
        narratives and strictly isolate against centrifugal pump ceramic seal text.
        """
        # Test GEN-1 (General Rotating Asset fallback)
        rep_gen = assemble_eight_d_report(
            asset_tag="GEN-1",
            symptoms=["bearing vibration", "dynamic unbalance"],
            incident_timestamp="2024-04-12T10:00:00Z",
        )
        assert rep_gen.verify_checksum() is True
        gen_d2_what = rep_gen.d2_problem.what.lower()
        gen_d5_actions = " ".join(a.action.lower() for a in rep_gen.d5_permanent_actions)
        gen_d3_actions = " ".join(a.action.lower() for a in rep_gen.d3_containment)
        gen_d8_notes = rep_gen.d8_recognition.recognition_notes.lower()

        assert "ceramic" not in gen_d2_what
        assert "ceramic" not in gen_d5_actions
        assert "ceramic" not in gen_d3_actions
        assert "ceramic" not in gen_d8_notes
        assert "coolant fluid leak" not in gen_d2_what
        assert "silicon carbide" not in gen_d5_actions
        assert "bearing" in gen_d2_what or "unbalance" in gen_d2_what or "rotating" in gen_d2_what

        # Test COMP-01 (Centrifugal Compressor)
        rep_comp = assemble_eight_d_report(
            asset_tag="COMP-01",
            symptoms=["bearing vibration", "shaft misalignment"],
            incident_timestamp="2024-04-12T10:00:00Z",
        )
        assert rep_comp.verify_checksum() is True
        comp_d2_what = rep_comp.d2_problem.what.lower()
        comp_d5_actions = " ".join(a.action.lower() for a in rep_comp.d5_permanent_actions)

        assert "ceramic" not in comp_d2_what
        assert "ceramic" not in comp_d5_actions
        assert "coolant fluid leak" not in comp_d2_what

        # Ishikawa 6M classification isolation for GEN-1
        fb_gen = IshikawaClassifier.classify_causes("GEN-1", ["bearing vibration"])
        fb_machine = " ".join(fb_gen.get_branch("Machine").causes).lower()
        fb_material = " ".join(fb_gen.get_branch("Material").causes).lower()
        assert "ceramic" not in fb_machine
        assert "ceramic" not in fb_material
        assert "unbalance" in fb_machine or "bearing" in fb_machine or "misalignment" in fb_machine

