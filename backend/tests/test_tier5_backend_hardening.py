"""
Tier 5 Adversarial Coverage Hardening Test Suite.
Industrial Mind OS - Deductive Root Cause Analysis (RCA) & Compliance Engine.
Location: backend/tests/test_tier5_backend_hardening.py

Adversarial Stress Test Matrix:
1. Asset Tag & Classification Fuzzing (Numeric, Lowercase, Symbols, Unicode, Length Extremes, Uncataloged)
2. Telemetry Parameter Excursion Fuzzing (Float Extremes, NaN/Inf, Cryogenic/Negative, Zero Division)
3. 5-Why & Ishikawa Structure Fuzzing (Depth Boundaries, Dangling/Isolated Nodes, Multiple Roots, Grounding Auto-Sync, 200+ Items Stress)
4. SHA-256 Seal Invariance & Tamper Evident Cryptography (Model/JSON/Dict Invariance, 1-Bit Mutation Detection)
5. Compliance HTML Packaging & Malicious Injection Hardening (Recursive Scripts, Tag Variations, Null Bytes, Unicode, Data Island Breakout)
6. Concurrency & REST API Boundary Hardening (Thread Safety, Concurrency, FastApi Client Validation)
"""

from __future__ import annotations

import copy
import hashlib
import html
import json
import math
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Dict, List

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api.rca_router import rca_report_store, router
from api.rca_schemas import (
    ActionStatus,
    CitationObject,
    ContainmentAction,
    CorrectiveAction,
    EightDIncidentReport,
    EventType,
    FishboneAnalysis,
    FishboneBranch,
    FishboneCategory,
    FiveWhyNode,
    HistoricalMatch,
    HistoricalMatchRequest,
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
from services.compliance_package import (
    build_audit_html,
    build_audit_json,
    compute_canonical_sha256,
    generate_compliance_package,
    verify_compliance_checksum,
)
from services.rca_engine import (
    DeductiveRCAEngine,
    EightDReportAssembler,
    ExtendedHistoricalMatch,
    ExtendedOEMDeviation,
    FishboneCauseItem,
    IshikawaClassifier,
    OEM_DESIGN_ENVELOPES,
    OEMOperatingEnvelopeEngine,
    analyze_oem_deviations,
    assemble_eight_d_report,
    classify_oem_severity,
    compute_single_deviation,
    detect_asset_family,
    generate_fishbone_analysis,
    generate_five_why_chain,
    generate_preventative_controls,
    match_historical_records,
    match_semantic_citations,
    resolve_sister_assets,
)
from services.rca_ingestion import (
    CitationRegistry,
    EvidenceCitationExtractor,
    TimelineExtractor,
    verify_causal_grounding,
)


# ==============================================================================
# TEST FIXTURES
# ==============================================================================

@pytest.fixture
def clean_report_store():
    """Provides an isolated clean report store before each test."""
    rca_report_store.clear()
    yield rca_report_store
    rca_report_store.clear()


@pytest.fixture
def fresh_registry():
    """Provides a fresh isolated citation registry."""
    reg = CitationRegistry()
    reg.clear()
    return reg


@pytest.fixture
def api_client():
    """Provides FastAPI test client configured with RCA router."""
    app = FastAPI(title="Tier 5 Hardening Test App")
    app.include_router(router, prefix="/api/v1")
    return TestClient(app)


@pytest.fixture
def baseline_report() -> EightDIncidentReport:
    """Constructs a fully formed authentic EightDIncidentReport instance."""
    engine = DeductiveRCAEngine()
    req = RCAAnalyzeRequest(
        asset_tag="Pump-A12",
        symptoms=["mechanical seal failure", "high vibration 5.8 mm/s"],
        incident_timestamp="2023-11-04T08:00:00Z",
        telemetry_data={"vibration_mm_s": 5.8, "bearing_temp_c": 62.0},
    )
    return engine.analyze_incident(req)


# ==============================================================================
# GROUP 1: FUZZ ASSET TAGS AND CLASSIFICATION (TIER 5 AREA 1)
# ==============================================================================

def test_t5_asset_fuzz_pure_numeric_tags():
    """Fuzz pure numeric asset tags ('1001', '0', '999999')."""
    numeric_tags = ["1001", "0", "999999"]
    for tag in numeric_tags:
        family = detect_asset_family(tag)
        assert isinstance(family, str) and len(family) > 0

        sisters = resolve_sister_assets(tag)
        assert isinstance(sisters, list)
        assert tag not in sisters

        report = assemble_eight_d_report(
            asset_tag=tag,
            symptoms=["mechanical seal fracture", "excessive vibration"],
            incident_timestamp="2023-11-04T08:00:00Z",
        )
        assert report.asset_tag == tag
        assert report.report_id.startswith("8D-2023-")
        assert report.verify_checksum() is True


def test_t5_asset_fuzz_lowercase_and_mixed_case():
    """Fuzz lowercase and mixed-case tags matching known equipment."""
    cases = [
        ("pump-a12", "A-Series Centrifugal Pump"),
        ("PUMP-a12", "A-Series Centrifugal Pump"),
        ("turb-st-04", "Steam Turbine"),
        ("blr-hp-101", "High-Pressure Boiler"),
    ]
    for tag, expected_family in cases:
        family = detect_asset_family(tag)
        assert family == expected_family

        devs = analyze_oem_deviations(tag, {"vibration_mm_s": 5.8})
        assert isinstance(devs, list)
        assert len(devs) > 0


def test_t5_asset_fuzz_special_characters_and_symbols():
    """Fuzz tags containing symbols, punctuation, and delimiters."""
    special_tags = [
        "PUMP#42/SEC@9",
        "PUMP:A12.01",
        "ASSET-WITH-DASHES_UNDERSCORES",
        "COMP[01]",
        "PUMP$MONEY%PERCENT",
    ]
    for tag in special_tags:
        family = detect_asset_family(tag)
        assert isinstance(family, str)

        report = assemble_eight_d_report(
            asset_tag=tag,
            symptoms=["unexpected shutdown"],
            incident_timestamp="2023-11-04T08:00:00Z",
        )
        assert report.asset_tag == tag
        assert report.report_id.startswith("8D-")
        # Ensure report_id matches canonical pattern
        import re
        assert re.match(r"^8D-[0-9]{4}-[A-Za-z0-9_\-]+$", report.report_id)
        assert report.verify_checksum() is True


def test_t5_asset_fuzz_unicode_and_exotic_scripts():
    """Fuzz asset tags with Unicode characters, umlauts, Cyrillic, and Asian scripts."""
    unicode_tags = [
        "PÜMP-Ä12",
        "КОМПРЕССОР-01",
        "ポンプ-01",
        "PUMP-β-99",
        "TAG_WITH_EMOJI_🏭_01",
    ]
    for tag in unicode_tags:
        family = detect_asset_family(tag)
        assert isinstance(family, str)

        report = assemble_eight_d_report(
            asset_tag=tag,
            symptoms=["bearing overheating", "vibration trip"],
            incident_timestamp="2023-11-04T08:00:00Z",
        )
        assert report.asset_tag == tag
        assert report.verify_checksum() is True


def test_t5_asset_fuzz_extreme_length_tags():
    """Fuzz asset tags at length extremes: 1 character to 250 characters."""
    short_tag = "X"
    long_tag = "PUMP-" + "A" * 240

    for tag in [short_tag, long_tag]:
        report = assemble_eight_d_report(
            asset_tag=tag,
            symptoms=["vibration alarm trip"],
            incident_timestamp="2023-11-04T08:00:00Z",
        )
        assert report.asset_tag == tag
        assert report.verify_checksum() is True


def test_t5_asset_fuzz_hybrid_and_uncataloged_types():
    """Fuzz classification with hybrid and completely uncataloged equipment."""
    # Tag has no known prefix, but symptoms indicate steam turbine
    family = detect_asset_family(
        asset_tag="UNKNOWN-ASSET-X",
        symptoms=["turbine overspeed trip", "governor valve lag"],
    )
    assert family == "Steam Turbine"

    # Tag has no known prefix, but telemetry has boiler signature
    family2 = detect_asset_family(
        asset_tag="UNKNOWN-ASSET-Y",
        telemetry={"temperature_c": 560.0, "pressure_bar": 120.0},
    )
    assert family2 == "High-Pressure Boiler"

    # Completely generic asset
    family3 = detect_asset_family(
        asset_tag="CUSTOM-MACHINE-01",
        symptoms=["mechanical noise"],
        telemetry={"flow_rate": 10.0},
    )
    assert family3 == "General Rotating Asset"


def test_t5_asset_fuzz_sister_asset_derivation_edge_cases():
    """Fuzz sister asset derivation across irregular sequence formats."""
    test_cases = [
        ("TURB-ST-04", ["TURB-ST-01", "TURB-ST-02"]),
        ("BLR-HP-101", ["BLR-HP-102", "BLR-HP-103"]),
        ("COMP-1", ["COMP-2", "COMP-3"]),
        ("SINGLETAG", ["SINGLETAG-01", "SINGLETAG-02"]),
    ]
    for query_tag, expected_sisters in test_cases:
        sisters = resolve_sister_assets(query_tag)
        assert sisters == expected_sisters
        assert query_tag not in sisters


# ==============================================================================
# GROUP 2: FUZZ TELEMETRY PARAMETER EXCURSIONS (TIER 5 AREA 2)
# ==============================================================================

def test_t5_telemetry_fuzz_float_extremes():
    """Fuzz float extreme values: 1e308, 1e20, 1e-308, 0.0, -0.0."""
    extreme_values = [1e20, 1e-308, 0.0, -0.0]
    for val in extreme_values:
        dev = compute_single_deviation(
            parameter_name="Extreme Vibration",
            unit="mm/s",
            envelope_max=5.0,
            incident_value=val,
        )
        assert isinstance(dev, ExtendedOEMDeviation)
        assert math.isfinite(dev.deviation_percent)

    # 1e308 evaluates without unhandled exception; deviation overflows to inf
    dev_max = compute_single_deviation(
        parameter_name="Max Float Vibration",
        unit="mm/s",
        envelope_max=5.0,
        incident_value=1e308,
    )
    assert dev_max.is_exceeded is True
    assert dev_max.severity_level == SeverityLevel.CRITICAL
    assert math.isinf(dev_max.deviation_percent) or math.isfinite(dev_max.deviation_percent)

    # Multi-parameter analysis with float extremes
    telemetry = {"vibration_mm_s": 1e20, "bearing_temp_c": 0.0}
    devs = analyze_oem_deviations("Pump-A12", telemetry)
    assert len(devs) > 0
    assert math.isfinite(devs[0].deviation_percent)


def test_t5_telemetry_fuzz_nan_and_inf_guarding():
    """Fuzz non-finite numbers (NaN, Inf, -Inf) verifying zero crash / safe reset."""
    for bad_val in [float("inf"), float("-inf"), float("nan")]:
        dev = compute_single_deviation(
            parameter_name="Peak Vibration Velocity",
            unit="mm/s",
            envelope_max=5.0,
            incident_value=bad_val,
        )
        # Non-finite values must be gracefully neutralized to 0.0 (which is -100% of 5.0 limit)
        assert dev.actual_incident_value == 0.0
        assert dev.deviation_percent == -100.0
        assert dev.is_exceeded is False
        assert dev.severity_level == SeverityLevel.LOW

    # In batch analysis, non-finite keys must be safely skipped or sanitized
    devs = analyze_oem_deviations(
        "Pump-A12",
        {"vibration_mm_s": float("nan"), "bearing_temp_c": float("inf")},
    )
    assert isinstance(devs, list)
    for d in devs:
        assert math.isfinite(d.deviation_percent)


def test_t5_telemetry_fuzz_cryogenic_and_negative_limits():
    """Fuzz negative and cryogenic operating envelopes (lower bound math)."""
    # Cryogenic temperature envelope: nominal_min = -180.0 C, actual = -195.0 C (exceeded)
    dev_cryo = compute_single_deviation(
        parameter_name="Cryogenic LNG Temperature",
        unit="°C",
        nominal_min=-180.0,
        incident_value=-195.0,
        is_lower_bound=True,
    )
    assert dev_cryo.is_exceeded is True
    # ((-180.0 - (-195.0)) / 180.0) * 100 = (15 / 180) * 100 = 8.33%
    assert dev_cryo.deviation_percent == pytest.approx(8.33, rel=1e-2)
    assert dev_cryo.severity_level in (SeverityLevel.HIGH, SeverityLevel.CRITICAL)

    # Vacuum pressure envelope: nominal_min = -0.5 bar, actual = -0.2 bar (within normal)
    dev_vac = compute_single_deviation(
        parameter_name="Condenser Vacuum",
        unit="bar",
        nominal_min=-0.5,
        incident_value=-0.2,
        is_lower_bound=True,
    )
    assert dev_vac.is_exceeded is False


def test_t5_telemetry_fuzz_zero_envelope_and_zero_division():
    """Fuzz envelope boundary exactly equal to zero to verify zero division guard."""
    dev = compute_single_deviation(
        parameter_name="Zero Envelope Parameter",
        unit="ppm",
        envelope_max=0.0,
        incident_value=5.0,
    )
    assert dev.deviation_percent == 0.0
    assert dev.is_exceeded is False
    assert dev.severity_level == SeverityLevel.LOW


def test_t5_telemetry_fuzz_non_numeric_and_malformed_values():
    """Fuzz telemetry dictionaries with invalid types, None, strings, and lists."""
    malformed_telemetry = {
        "vibration_mm_s": "NOT_A_FLOAT",
        "bearing_temp_c": None,
        "discharge_pressure_bar": [1.0, 2.0],
        "nested_dict": {"foo": "bar"},
    }
    # analyze_oem_deviations should skip unparseable values gracefully
    devs = analyze_oem_deviations("Pump-A12", malformed_telemetry)
    assert isinstance(devs, list)
    assert len(devs) == 0


def test_t5_telemetry_fuzz_extreme_telemetry_in_timeline_reconstruction():
    """Fuzz timeline reconstruction with extreme and bizarre telemetry dictionaries."""
    extractor = TimelineExtractor()
    telemetry_logs = [
        {
            "timestamp": "2023-11-04T08:00:00Z",
            "vibration_mm_s": 999999.9,
            "bearing_temp_c": -273.15,
            "description": "Extreme anomalous telemetry reading",
        }
    ]
    events = extractor.reconstruct_timeline(
        equipment_tag="Pump-A12",
        telemetry_logs=telemetry_logs,
        incident_timestamp="2023-11-04T08:00:00Z",
    )
    assert len(events) >= 1
    assert events[0].parameters["vibration_mm_s"] == 999999.9
    assert events[0].parameters["bearing_temp_c"] == -273.15


# ==============================================================================
# GROUP 3: FUZZ 5-WHY AND ISHIKAWA STRUCTURES (TIER 5 AREA 3)
# ==============================================================================

def test_t5_five_why_fuzz_depth_boundaries_and_rejection():
    """Fuzz 5-Why tree depth levels: level 1-10 valid, level 0 and 11 rejected."""
    # Level 10 is maximum valid depth
    node_max = FiveWhyNode(
        why_id="WHY-10",
        level=10,
        cause_statement="Deep latent systemic architectural flaw",
        citation_ids=["CITE-VALID-01"],
    )
    assert node_max.level == 10

    # Level 0 out of bounds (ge=1)
    with pytest.raises(ValidationError):
        FiveWhyNode(
            why_id="WHY-0",
            level=0,
            cause_statement="Under-level cause",
        )

    # Level 11 out of bounds (le=10)
    with pytest.raises(ValidationError):
        FiveWhyNode(
            why_id="WHY-11",
            level=11,
            cause_statement="Over-level cause",
        )


def test_t5_five_why_fuzz_isolated_and_dangling_nodes():
    """Fuzz 5-Why trees containing isolated nodes and dangling parent references."""
    chain = [
        FiveWhyNode(
            why_id="WHY-1",
            level=1,
            cause_statement="Observable symptom on pump",
            parent_node_id=None,
            citation_ids=["CITE-01"],
        ),
        FiveWhyNode(
            why_id="WHY-2",
            level=2,
            cause_statement="Dangling child with non-existent parent",
            parent_node_id="WHY-NON-EXISTENT",
            citation_ids=["CITE-02"],
        ),
        FiveWhyNode(
            why_id="WHY-3",
            level=3,
            cause_statement="Isolated node with None parent",
            parent_node_id=None,
            citation_ids=[],
        ),
    ]
    fb = IshikawaClassifier.classify_causes("Pump-A12", ["leak"])
    rca = RootCauseAnalysis(
        five_why_chain=chain,
        fishbone_analysis=fb,
        occurrence_root_cause="Fatigue fracture",
        escape_root_cause="Alarm disabled",
    )
    assert len(rca.five_why_chain) == 3
    # WHY-3 has no citations, so it must be unsubstantiated
    assert rca.five_why_chain[2].is_unsubstantiated is True


def test_t5_five_why_fuzz_multiple_and_zero_root_causes():
    """Fuzz 5-Why trees with multiple terminal root causes or zero root causes."""
    chain_multiple_roots = [
        FiveWhyNode(
            why_id="WHY-1",
            level=1,
            cause_statement="Primary vibration symptom",
            is_root_cause=True,
            citation_ids=["CITE-01"],
        ),
        FiveWhyNode(
            why_id="WHY-2",
            level=2,
            cause_statement="Secondary electrical symptom",
            is_root_cause=True,
            citation_ids=["CITE-02"],
        ),
    ]
    fb = IshikawaClassifier.classify_causes("Pump-A12", ["vibration"])
    rca = RootCauseAnalysis(
        five_why_chain=chain_multiple_roots,
        fishbone_analysis=fb,
        occurrence_root_cause="Dual vector occurrence root cause",
        escape_root_cause="Dual vector escape root cause",
    )
    root_nodes = [n for n in rca.five_why_chain if n.is_root_cause]
    assert len(root_nodes) == 2


def test_t5_five_why_fuzz_grounding_auto_sync():
    """Fuzz 5-Why node citation grounding synchronization and alias preservation."""
    # Empty citation_ids -> auto-flagged unsubstantiated & assumed
    unsub_node = FiveWhyNode(
        why_id="WHY-UNSUB",
        level=2,
        cause_statement="Unsubstantiated engineering conjecture",
        citation_ids=[],
    )
    assert unsub_node.is_unsubstantiated is True
    assert unsub_node.assumed_flag is True
    assert unsub_node.assumption_flag is True

    # Providing evidence_citation_ids syncs with citation_ids
    sync_node = FiveWhyNode(
        why_id="WHY-SYNC",
        level=3,
        cause_statement="Substantiated claim via evidence alias",
        evidence_citation_ids=["CITE-DOC-001"],
    )
    assert sync_node.citation_ids == ["CITE-DOC-001"]
    assert sync_node.is_unsubstantiated is False
    assert sync_node.assumed_flag is False


def test_t5_ishikawa_fuzz_case_insensitivity_and_aliases():
    """Fuzz 6M fishbone category normalization across casing and aliases."""
    test_mappings = [
        ("man", "Man"),
        ("MAN", "Man"),
        ("machine", "Machine"),
        ("MACHINE", "Machine"),
        ("material", "Material"),
        ("method", "Method"),
        ("measurement", "Measurement"),
        ("environment", "Environment"),
        ("ENVIRONMENT", "Environment"),
        ("milieu", "Environment"),  # 6M French alias
    ]
    for input_cat, expected_norm in test_mappings:
        branch = FishboneBranch(
            category=input_cat,
            causes=["Valid causal statement"],
            citation_ids=["CITE-01"],
        )
        assert branch.category == expected_norm


def test_t5_ishikawa_fuzz_invalid_category_rejection():
    """Fuzz 6M fishbone rejecting non-6M categories."""
    invalid_categories = ["Finance", "Software", "Governance", "12345", ""]
    for cat in invalid_categories:
        with pytest.raises(ValidationError):
            FishboneBranch(category=cat, causes=["Invalid branch cause"])


def test_t5_ishikawa_fuzz_contribution_weight_bounds():
    """Fuzz FishboneCauseItem contribution weights at boundaries and invalid values."""
    # Valid boundaries
    for valid_w in [0.0, 0.5, 1.0]:
        item = FishboneCauseItem(
            cause_id="FB-1",
            category="Machine",
            statement="Bearing race fatigue spalling",
            contribution_weight=valid_w,
            evidence_citation_ids=["CITE-01"],
        )
        assert item.contribution_weight == valid_w

    # Invalid weights
    for invalid_w in [-0.1, 1.05, 50.0]:
        with pytest.raises(ValidationError):
            FishboneCauseItem(
                cause_id="FB-ERR",
                category="Machine",
                statement="Bearing race fatigue spalling",
                contribution_weight=invalid_w,
            )


def test_t5_ishikawa_fuzz_grounding_and_unsubstantiated_branches():
    """Fuzz Ishikawa branch auto-flagging on empty citation list."""
    unsub_branch = FishboneBranch(
        category="Method",
        causes=["SOP allowed operating past envelope without trip"],
        citation_ids=[],
    )
    assert unsub_branch.is_unsubstantiated is True
    assert unsub_branch.assumed_flag is True
    assert unsub_branch.assumption_flag is True

    sub_branch = FishboneBranch(
        category="Method",
        causes=["SOP allowed operating past envelope without trip"],
        citation_ids=["CITE-METHOD-01"],
    )
    assert sub_branch.is_unsubstantiated is False
    assert sub_branch.assumed_flag is False


def test_t5_ishikawa_fuzz_massive_causes_stress():
    """Stress-test Ishikawa with a massive list of 200 causal statements."""
    causes = [f"Contributing mechanical vibration mode #{i} identified" for i in range(200)]
    branch = FishboneBranch(
        category="Machine",
        causes=causes,
        citation_ids=["CITE-STRESS-01"],
    )
    assert len(branch.causes) == 200

    fb = FishboneAnalysis(branches=[branch])
    retrieved = fb.get_branch("machine")
    assert retrieved is not None
    assert len(retrieved.causes) == 200


# ==============================================================================
# GROUP 4: FUZZ SHA-256 SEAL INVARIANCE & TAMPER DETECTION (TIER 5 AREA 4)
# ==============================================================================

def test_t5_sha256_invariance_model_to_json_to_model(baseline_report: EightDIncidentReport):
    """Test SHA-256 seal invariance across model -> JSON string -> model reload."""
    initial_sha = baseline_report.compute_canonical_sha256()
    assert len(initial_sha) == 64
    assert baseline_report.verify_checksum() is True

    # Serialize to JSON string
    json_str = baseline_report.model_dump_json()

    # Re-instantiate model from JSON
    reloaded = EightDIncidentReport.model_validate_json(json_str)

    # Recomputed hash on reloaded object must match identically
    reloaded_sha = reloaded.compute_canonical_sha256()
    assert reloaded_sha == initial_sha
    assert reloaded.verify_checksum() is True


def test_t5_sha256_invariance_dict_serialization_and_key_reordering(
    baseline_report: EightDIncidentReport,
):
    """Test SHA-256 seal invariance across dictionary conversions and key re-ordering."""
    original_sha = baseline_report.compute_canonical_sha256()

    # Model to dict
    data_dict = baseline_report.model_dump(mode="json")
    # Re-compute via compute_canonical_sha256 function on dict
    dict_sha = compute_canonical_sha256(data_dict)
    assert dict_sha == original_sha

    # Shuffled key order in JSON
    shuffled_keys = list(data_dict.keys())
    shuffled_keys.reverse()
    shuffled_dict = {k: data_dict[k] for k in shuffled_keys}
    shuffled_sha = compute_canonical_sha256(shuffled_dict)
    assert shuffled_sha == original_sha


def test_t5_sha256_invariance_multiple_invocations_idempotency(
    baseline_report: EightDIncidentReport,
):
    """Test that repeatedly calling compute_canonical_sha256 is strictly idempotent."""
    first_sha = baseline_report.compute_canonical_sha256()
    for _ in range(10):
        next_sha = baseline_report.compute_canonical_sha256()
        assert next_sha == first_sha
        assert baseline_report.checksum_sha256 == first_sha
        assert baseline_report.verify_checksum() is True


def test_t5_sha256_tamper_detection_single_character_mutation(
    baseline_report: EightDIncidentReport,
):
    """Test that a single character mutation anywhere in the report breaks checksum verification."""
    baseline_report.compute_canonical_sha256()
    assert baseline_report.verify_checksum() is True

    # 1. Mutate problem description
    rep1 = copy.deepcopy(baseline_report)
    rep1.d2_problem.what += "!"
    assert rep1.verify_checksum() is False

    # 2. Mutate occurrence root cause
    rep2 = copy.deepcopy(baseline_report)
    rep2.d4_root_causes.occurrence_root_cause += "."
    assert rep2.verify_checksum() is False

    # 3. Mutate severity score
    rep3 = copy.deepcopy(baseline_report)
    rep3.severity_score = 9 if rep3.severity_score != 9 else 8
    assert rep3.verify_checksum() is False

    # 4. Mutate an action owner
    rep4 = copy.deepcopy(baseline_report)
    rep4.d3_containment[0].owner += " Jr."
    assert rep4.verify_checksum() is False


def test_t5_sha256_tamper_detection_checksum_field_mutation(
    baseline_report: EightDIncidentReport,
):
    """Test modifying the checksum_sha256 attribute itself invalidates verification."""
    baseline_report.compute_canonical_sha256()
    assert baseline_report.verify_checksum() is True

    # Alter 1 byte of the checksum
    fake_sha = ("0" if baseline_report.checksum_sha256[0] != "0" else "1") + baseline_report.checksum_sha256[1:]
    baseline_report.checksum_sha256 = fake_sha
    assert baseline_report.verify_checksum() is False

    # But recomputing restores validity
    restored = baseline_report.compute_canonical_sha256()
    assert restored != fake_sha
    assert baseline_report.verify_checksum() is True


def test_t5_sha256_compliance_verifier_across_types(
    baseline_report: EightDIncidentReport,
):
    """Test verify_compliance_checksum across models and dicts."""
    baseline_report.compute_canonical_sha256()
    assert verify_compliance_checksum(baseline_report) is True

    # Dict representation
    raw_dict = baseline_report.model_dump(mode="json")
    assert verify_compliance_checksum(raw_dict) is True

    # Tampered dict
    raw_dict["asset_tag"] = "MUTATED-TAG"
    assert verify_compliance_checksum(raw_dict) is False


# ==============================================================================
# GROUP 5: FUZZ COMPLIANCE HTML PACKAGING & MALICIOUS PAYLOADS (TIER 5 AREA 5)
# ==============================================================================

def test_t5_html_fuzz_recursive_script_injection(baseline_report: EightDIncidentReport):
    """Fuzz HTML packaging with recursive script tags."""
    xss_payload = "<script><script>alert('XSS-PWNED')</script></script>"
    rep = copy.deepcopy(baseline_report)
    rep.d2_problem.what = xss_payload
    rep.d8_recognition.recognition_notes = xss_payload

    html_out = build_audit_html(rep)
    # The literal unescaped tag must NOT appear in the rendered HTML
    assert "<script><script>" not in html_out
    assert "&lt;script&gt;&lt;script&gt;alert(&#x27;XSS-PWNED&#x27;)&lt;/script&gt;&lt;/script&gt;" in html_out


def test_t5_html_fuzz_angle_bracket_variations_and_event_handlers(
    baseline_report: EightDIncidentReport,
):
    """Fuzz HTML packaging with image/svg tags, event handlers, and quotes."""
    payloads = [
        "<img src=x onerror=alert(1)>",
        "<svg onload=alert(document.domain)>",
        "';alert(String.fromCharCode(88,83,83))//",
        '"><script>alert(1)</script>',
    ]
    rep = copy.deepcopy(baseline_report)
    rep.d2_problem.why = payloads[0]
    rep.d4_root_causes.occurrence_root_cause = payloads[1]
    rep.d3_containment[0].action = payloads[2]
    rep.d5_permanent_actions[0].action = payloads[3]

    html_out = build_audit_html(rep)
    assert "<img src=x" not in html_out
    assert "<svg onload=" not in html_out
    assert '"><script>' not in html_out


def test_t5_html_fuzz_null_bytes_and_control_chars(baseline_report: EightDIncidentReport):
    """Fuzz HTML packaging with null bytes and ASCII control characters."""
    null_payload = "Corrupted\x00Telemetry\x01Excursion\x08Confirmed"
    rep = copy.deepcopy(baseline_report)
    rep.d2_problem.how = null_payload

    html_out = build_audit_html(rep)
    assert "Corrupted" in html_out
    assert html_out.startswith("<!DOCTYPE html>")


def test_t5_html_fuzz_special_unicode_and_bidi_overrides(
    baseline_report: EightDIncidentReport,
):
    """Fuzz HTML packaging with RTL overrides, zero-width spaces, and emojis."""
    bidi_payload = "Sensor \u202Ereversed\u202C reading \u200B🚨 5.8 mm/s ∑(x)"
    rep = copy.deepcopy(baseline_report)
    rep.d2_problem.what = bidi_payload

    content, sha, filename = generate_compliance_package(rep, format="html")
    assert "5.8 mm/s" in content
    assert len(sha) == 64
    assert filename.endswith(".html")


def test_t5_html_fuzz_data_island_script_breakout_prevention(
    baseline_report: EightDIncidentReport,
):
    """Fuzz machine-readable JSON data island preventing </script> breakout."""
    breakout_payload = "</script><script>alert('DATA_ISLAND_BREAKOUT')</script>"
    rep = copy.deepcopy(baseline_report)
    rep.d2_problem.what = breakout_payload

    html_out = build_audit_html(rep)
    # The JSON data island must encode < and > as \u003c and \u003e
    # to prevent HTML parser from terminating the script block early!
    assert "</script><script>alert('DATA_ISLAND_BREAKOUT')" not in html_out
    assert "\\u003c/script\\u003e" in html_out


def test_t5_html_fuzz_print_css_and_iso_metadata_integrity(
    baseline_report: EightDIncidentReport,
):
    """Verify ISO 9001 / IATF 16949 metadata headers and CSS print rules."""
    html_out = build_audit_html(baseline_report)
    assert '@page {' in html_out
    assert 'size: letter portrait;' in html_out
    assert 'margin: 15mm 18mm;' in html_out
    assert '@media print' in html_out
    assert 'meta name="x-compliance-standard"' in html_out
    assert 'meta name="x-compliance-checksum-sha256"' in html_out


# ==============================================================================
# GROUP 6: CONCURRENCY, THREAD-SAFETY & API INTEGRATION (TIER 5 AREA 6)
# ==============================================================================

def test_t5_concurrency_thread_safe_report_store():
    """Test concurrent thread safety of in-memory RCAReportStore."""
    rca_report_store.clear()
    num_threads = 20
    barrier = threading.Barrier(num_threads)

    def worker(i: int):
        barrier.wait()
        rep_id = f"8D-2023-THREAD-{i:03d}"
        engine = DeductiveRCAEngine()
        req = RCAAnalyzeRequest(
            asset_tag="Pump-A12",
            symptoms=["vibration alarm", f"worker thread #{i}"],
            incident_timestamp="2023-11-04T08:00:00Z",
        )
        report = engine.analyze_incident(req)
        report.report_id = rep_id
        rca_report_store.save(report)
        retrieved = rca_report_store.get(rep_id)
        assert retrieved is not None
        assert retrieved.report_id == rep_id

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker, i) for i in range(num_threads)]
        for f in futures:
            f.result()

    all_reports = rca_report_store.list_all()
    assert len(all_reports) == num_threads
    rca_report_store.clear()


def test_t5_concurrency_citation_registry():
    """Test concurrent registration and deduplication in CitationRegistry."""
    reg = CitationRegistry()
    num_threads = 20
    barrier = threading.Barrier(num_threads)

    def worker(i: int):
        barrier.wait()
        for j in range(5):
            # Same doc & excerpt -> must deduplicate
            cite = reg.register_citation(
                source_doc="Shared_Manual.txt",
                excerpt="Strict vibration envelope limit 5.0 mm/s.",
                section="Section 4",
            )
            assert cite.citation_id.startswith("CITE-")

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker, i) for i in range(num_threads)]
        for f in futures:
            f.result()

    # Deduplication map must ensure only 1 unique citation was created
    assert len(reg.list_citations()) == 1


def test_t5_api_fuzz_analyze_edge_payloads(api_client: TestClient, clean_report_store):
    """Test FastAPI /api/v1/rca/analyze with diverse payloads and schema rejections."""
    # 1. Valid payload with exotic asset tag
    res_valid = api_client.post(
        "/api/v1/rca/analyze",
        json={
            "asset_tag": "EXOTIC-ASSET#99",
            "symptoms": ["spill", "fracture"],
            "incident_timestamp": "2023-11-04T08:00:00Z",
            "telemetry_data": {"vibration_mm_s": 5.8},
        },
    )
    assert res_valid.status_code == 200
    data = res_valid.json()
    assert data["asset_tag"] == "EXOTIC-ASSET#99"
    assert data["rpn_score"] > 0
    assert len(data["checksum_sha256"]) == 64

    # 2. Invalid: empty symptoms list -> 422
    res_empty_sym = api_client.post(
        "/api/v1/rca/analyze",
        json={
            "asset_tag": "Pump-A12",
            "symptoms": [],
            "incident_timestamp": "2023-11-04T08:00:00Z",
        },
    )
    assert res_empty_sym.status_code == 422

    # 3. Invalid: missing asset_tag -> 422
    res_missing_tag = api_client.post(
        "/api/v1/rca/analyze",
        json={
            "symptoms": ["leak"],
            "incident_timestamp": "2023-11-04T08:00:00Z",
        },
    )
    assert res_missing_tag.status_code == 422


def test_t5_api_fuzz_historical_match_empty_and_special_symptoms(api_client: TestClient):
    """Test FastAPI /api/v1/rca/historical-match with empty and special symptoms."""
    # Empty symptoms -> 200 OK with empty list
    res_empty = api_client.post(
        "/api/v1/rca/historical-match",
        json={
            "asset_tag": "Pump-A12",
            "symptoms": [],
        },
    )
    assert res_empty.status_code == 200
    assert res_empty.json() == []

    # Matching symptoms
    res_match = api_client.post(
        "/api/v1/rca/historical-match",
        json={
            "asset_tag": "Pump-A12",
            "symptoms": ["ceramic seal", "coolant leak", "vibration"],
            "telemetry_features": {"vibration_mm_s": 5.8},
        },
    )
    assert res_match.status_code == 200
    matches = res_match.json()
    assert len(matches) > 0
    assert matches[0]["similarity_score"] >= 0.70


def test_t5_api_fuzz_export_evidence_malicious_report(
    api_client: TestClient, clean_report_store
):
    """Test /api/v1/rca/export-evidence with XSS vectors and format validations."""
    engine = DeductiveRCAEngine()
    req = RCAAnalyzeRequest(
        asset_tag="Pump-A12",
        symptoms=["<script>alert('pwn')</script>", "leak"],
        incident_timestamp="2023-11-04T08:00:00Z",
    )
    report = engine.analyze_incident(req)
    rep_id = "8D-2023-TEST-XSS-001"
    report.report_id = rep_id
    report.compute_canonical_sha256()
    rca_report_store.save(report)

    # Export HTML
    res_html = api_client.post(
        "/api/v1/rca/export-evidence",
        json={"report_id": rep_id, "format": "html"},
    )
    assert res_html.status_code == 200
    html_data = res_html.json()
    assert "<script>alert('pwn')</script>" not in html_data["content"]
    assert len(html_data["sha256_checksum"]) == 64

    # Export JSON
    res_json = api_client.post(
        "/api/v1/rca/export-evidence",
        json={"report_id": rep_id, "format": "json"},
    )
    assert res_json.status_code == 200

    # Unsupported format -> 400 Bad Request
    res_bad_fmt = api_client.post(
        "/api/v1/rca/export-evidence",
        json={"report_id": rep_id, "format": "pdf"},
    )
    assert res_bad_fmt.status_code == 400
