"""
Industrial Mind OS - Milestone 2 Adversarial Stress Test Suite
Location: backend/tests/test_adversarial_m2_stress.py

Adversarial stress testing targeting:
1. Historical matching under missing/corrupted historical corpora, unknown asset tags,
   zero-similarity symptoms, whitespace symptoms, and malformed telemetry features.
2. OEM envelope deviation calculations with zero limit (0.0), negative limit (-10.0),
   actual = 0.0, extreme values (1e12, -1e12, inf, nan), and JSON deserialization integrity.
3. FMEA RPN mitigation calculations: bounds [1, 1000], mitigated vs initial RPN,
   and division-by-zero guards.
4. Master 8D report assembly under partial or missing telemetry data:
   strict schema validity, canonical SHA-256 seal determinism and tamper invariance.
"""

from __future__ import annotations

import math
import os
import re
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
    SeverityLevel,
    SignOffStatus,
)
from services.rca_engine import (
    DeductiveRCAEngine,
    EightDReportAssembler,
    ExtendedHistoricalMatch,
    ExtendedOEMDeviation,
    HistoricalMatcher,
    HistoricalNearMissMatcher,
    OEMOperatingEnvelopeEngine,
    analyze_oem_deviations,
    assemble_eight_d_report,
    classify_oem_severity,
    compute_oem_deviation,
    compute_single_deviation,
    generate_preventative_controls,
    match_historical_records,
)
from services.rca_ingestion import CitationRegistry


# ==============================================================================
# 1. HISTORICAL MATCHING ADVERSARIAL STRESS TESTS
# ==============================================================================

class TestHistoricalMatchingAdversarial:
    """Stress tests probing historical matcher robustness under hostile inputs."""

    def test_missing_or_empty_corpus(self):
        """Matcher should safely return empty results when corpus is missing or empty."""
        matcher = HistoricalMatcher()

        # Explicitly empty string corpus
        res_empty = matcher.match(
            asset_tag="Pump-A12",
            symptoms=["vibration", "leak"],
            near_miss_text="",
        )
        assert res_empty == [], "Empty near_miss_text must return empty list safely"

        # Whitespace-only corpus
        res_whitespace = matcher.match(
            asset_tag="Pump-A12",
            symptoms=["vibration", "leak"],
            near_miss_text="   \n\t   ",
        )
        assert res_whitespace == [], "Whitespace-only corpus must return empty list safely"

        # Non-existent file path fallback
        res_nofile = matcher.load_near_miss_text(filepath="non_existent_fake_path_12345.txt")
        assert isinstance(res_nofile, str)

    def test_corrupted_or_gibberish_corpus(self):
        """Matcher should handle random noise or corrupted binary-like text without exception."""
        matcher = HistoricalMatcher()
        corrupted_text = "### CORRUPTED BINARY ### \x00\x01\x02\x03\x7f\x80\xff \u2603 \U0001f4a9" * 200

        res = matcher.match(
            asset_tag="Pump-A12",
            symptoms=["vibration", "leak"],
            near_miss_text=corrupted_text,
        )
        assert isinstance(res, list)
        for m in res:
            assert 0.0 <= m.similarity_score <= 1.0

    def test_unknown_asset_tags_isolation(self):
        """Probes asset tag isolation: unknown asset tags should get 0 asset similarity."""
        matcher = HistoricalMatcher()
        test_tags = [
            "UNKNOWN-ASSET-999",
            "TURBINE-DELTA-01",
            "REACTOR-CORE-B",
            "CONVEYOR-CV-88",
            "???$$$###",
            "X",
        ]
        near_miss_text = (
            "Equipment Tag: Pump-A12. Severe vibration 5.8 mm/s. Ceramic mechanical seal shattered. "
            "OEM manual limit is 5.0 mm/s. Coolant leak occurred."
        )

        for tag in test_tags:
            res = matcher.match(
                asset_tag=tag,
                symptoms=["vibration", "coolant leak"],
                near_miss_text=near_miss_text,
            )
            # Tag similarity should be 0.0, so score = 0.50 * 0.0 + 0.50 * 1.0 = 0.50
            if res:
                for m in res:
                    assert m.similarity_score <= 0.60, f"Unknown asset {tag} should not receive sister/exact boost"

    def test_zero_similarity_symptoms_on_unknown_asset(self):
        """Completely unrelated symptoms on unknown asset must yield zero score and be rejected."""
        matcher = HistoricalMatcher()
        unrelated_symptoms = [
            "baking chocolate chip cookies",
            "quantum tunneling in vacuum",
            "paint color discoloration on office wall",
            "payroll database transaction timeout",
        ]
        near_miss_text = (
            "Equipment Tag: Pump-A12. Severe vibration 5.8 mm/s. Ceramic mechanical seal shattered. "
            "OEM manual limit is 5.0 mm/s. Coolant leak occurred."
        )

        res = matcher.match(
            asset_tag="UNKNOWN-ASSET-999",
            symptoms=unrelated_symptoms,
            near_miss_text=near_miss_text,
        )
        assert res == [], "Zero asset similarity + zero symptom similarity must yield 0.0 score and empty results"

    @pytest.mark.xfail(
        reason="Vulnerability: Asset tag bias causes false positive match and populates unrelated symptoms as matching_symptoms",
        strict=False,
    )
    def test_zero_similarity_symptoms_on_known_asset_leakage(self):
        """
        Adversarial probe: Unrelated symptoms for Pump-A12 still match at score 0.50
        and attribute unrelated symptoms as matching_symptoms because s_asset alone exceeds 0.30 cutoff.
        """
        matcher = HistoricalMatcher()
        unrelated_symptoms = [
            "baking chocolate chip cookies",
            "taking a long walk in park",
        ]
        near_miss_text = (
            "Equipment Tag: Pump-A12. Severe vibration 5.8 mm/s. Ceramic mechanical seal shattered. "
            "OEM manual limit is 5.0 mm/s. Coolant leak occurred."
        )
        matches = matcher.match(
            asset_tag="Pump-A12",
            symptoms=unrelated_symptoms,
            near_miss_text=near_miss_text,
        )
        # Ideal behavior: Should NOT match near-miss when symptoms have 0% overlap
        assert matches == [], "Zero symptom overlap should not trigger historical near-miss match"

    @pytest.mark.xfail(
        reason="Vulnerability: Whitespace-only symptoms list is not sanitized at entry, causing false match with empty strings",
        strict=False,
    )
    def test_empty_or_whitespace_symptoms_sanitization(self):
        """
        Adversarial probe: Symptoms list containing only whitespace/empty strings.
        Ideal behavior: Should be sanitized and return [] safely.
        """
        matcher = HistoricalMatcher()
        assert matcher.match("Pump-A12", []) == []
        res = matcher.match("Pump-A12", ["", "   ", "\t"])
        assert res == [], "Whitespace-only symptoms list should return empty list"

    def test_adversarial_telemetry_features_in_matcher(self):
        """Telemetry similarity calculation with non-numeric, extreme, inf, and nan values."""
        matcher = HistoricalMatcher()
        baseline = {"nominal_limit": 5.0, "trip_limit": 5.5, "excursion_value": 5.8}

        # Non-numeric vibration
        assert matcher.calculate_telemetry_similarity({"vibration": "malformed_str"}, baseline) is None
        assert matcher.calculate_telemetry_similarity({"vibration": None}, baseline) is None
        assert matcher.calculate_telemetry_similarity({}, baseline) is None

        # Extreme positive vibration
        sim_huge = matcher.calculate_telemetry_similarity({"vibration": 1e9}, baseline)
        assert sim_huge is not None
        assert 0.0 <= sim_huge <= 1.0

        # Zero and negative vibration
        assert matcher.calculate_telemetry_similarity({"vibration": 0.0}, baseline) == 0.20
        assert matcher.calculate_telemetry_similarity({"vibration": -10.0}, baseline) == 0.20

        # Float inf
        sim_inf = matcher.calculate_telemetry_similarity({"vibration": float("inf")}, baseline)
        assert sim_inf is not None
        assert 0.0 <= sim_inf <= 1.0

    def test_recurrence_risk_clamping_invariance(self):
        """Recurrence risk probability must strictly remain bounded in [0.05, 0.99]."""
        matcher = HistoricalMatcher()

        # Maximum possible scores
        p_max, lvl_max, _ = matcher.estimate_recurrence_risk(
            similarity_score=1.0,
            asset_similarity=1.0,
            telemetry_similarity=1.0,
            matching_symptoms=["vibration", "leak"],
        )
        assert 0.05 <= p_max <= 0.99
        assert lvl_max == "CRITICAL"

        # Minimum possible scores
        p_min, lvl_min, _ = matcher.estimate_recurrence_risk(
            similarity_score=0.0,
            asset_similarity=0.0,
            telemetry_similarity=0.0,
            matching_symptoms=[],
        )
        assert 0.05 <= p_min <= 0.99
        assert lvl_min in ["LOW", "MEDIUM"]


# ==============================================================================
# 2. OEM OPERATING ENVELOPE ADVERSARIAL STRESS TESTS
# ==============================================================================

class TestOEMEnvelopeAdversarial:
    """Stress tests probing OEM deviation calculations under extreme numerical boundaries."""

    def test_zero_envelope_limit(self):
        """Division by zero guard: envelope_max = 0.0 must yield 0.0% deviation without crash."""
        dev = compute_single_deviation(
            parameter_name="Pressure",
            unit="bar",
            envelope_max=0.0,
            incident_value=15.0,
        )
        assert dev.deviation_percent == 0.0
        assert dev.deviation_pct == 0.0
        assert not dev.is_exceeded
        assert dev.severity_level == SeverityLevel.LOW

    def test_negative_envelope_limit(self):
        """Negative limit should be guarded (envelope_max <= 0 returns 0.0% deviation)."""
        dev = compute_single_deviation(
            parameter_name="Cryo Temperature",
            unit="°C",
            envelope_max=-10.0,
            incident_value=-5.0,
        )
        assert dev.deviation_percent == 0.0
        assert not dev.is_exceeded
        assert dev.severity_level == SeverityLevel.LOW

    def test_zero_actual_value(self):
        """actual = 0.0 with positive limit: should compute -100.0% deviation safely."""
        dev = compute_single_deviation(
            parameter_name="Flow Rate",
            unit="m3/h",
            envelope_max=50.0,
            incident_value=0.0,
        )
        assert dev.deviation_percent == -100.0
        assert not dev.is_exceeded
        assert dev.severity_level == SeverityLevel.LOW

    def test_negative_actual_value(self):
        """Negative actual value with positive limit computes valid negative deviation."""
        dev = compute_single_deviation(
            parameter_name="Temperature",
            unit="°C",
            envelope_max=100.0,
            incident_value=-20.0,
        )
        assert dev.deviation_percent == -120.0
        assert not dev.is_exceeded
        assert dev.severity_level == SeverityLevel.LOW

    def test_extreme_actual_values(self):
        """Very large actual values (e.g. 1e12, -1e12) compute extreme deviation without overflow."""
        dev = compute_single_deviation(
            parameter_name="Vibration",
            unit="mm/s",
            envelope_max=5.0,
            incident_value=1e12,
        )
        assert dev.deviation_percent > 1e10
        assert dev.is_exceeded
        assert dev.severity_level == SeverityLevel.CRITICAL

        dev_neg = compute_single_deviation(
            parameter_name="Vibration",
            unit="mm/s",
            envelope_max=5.0,
            incident_value=-1e12,
        )
        assert dev_neg.deviation_percent < -1e10
        assert not dev_neg.is_exceeded
        assert dev_neg.severity_level == SeverityLevel.LOW

    def test_oem_deviation_direct_pydantic_model(self):
        """Tests OEMDeviation model validator directly with zero and negative limits."""
        m_zero = OEMDeviation(
            parameter_name="Test",
            oem_envelope_limit=0.0,
            actual_incident_value=50.0,
            unit="psi",
        )
        assert m_zero.deviation_percent == 0.0
        assert not m_zero.is_exceeded

        m_neg = OEMDeviation(
            parameter_name="Test",
            oem_envelope_limit=-5.0,
            actual_incident_value=10.0,
            unit="psi",
        )
        assert m_neg.deviation_percent == 0.0
        assert not m_neg.is_exceeded

    def test_analyze_oem_deviations_with_malformed_telemetry(self):
        """Probes analyze_oem_deviations against non-numeric, None, or unexpected telemetry types."""
        malformed_telemetry = {
            "vibration": "not-a-number",
            "temperature": None,
            "pressure": [1, 2, 3],
            "rpm": {"val": 3000},
            "unknown_sensor_xyz": 999.9,
            "bearing_temp_c": "88.5",  # numeric string should parse
        }

        deviations = analyze_oem_deviations("Pump-A12", malformed_telemetry)
        assert len(deviations) == 1
        assert deviations[0].parameter_name == "Bearing Temperature"
        assert deviations[0].actual_incident_value == 88.5
        assert deviations[0].is_exceeded

    def test_analyze_oem_deviations_sorting_invariance(self):
        """Deviations must always be sorted descending by deviation_percent."""
        telemetry = {
            "vibration_mm_s": 6.5,          # +30.0%
            "bearing_temp_c": 70.0,         # 0.0%
            "discharge_pressure_bar": 18.0, # +12.5%
        }
        deviations = analyze_oem_deviations("Pump-A12", telemetry)
        assert len(deviations) == 3
        dev_percentages = [d.deviation_percent for d in deviations]
        assert dev_percentages == sorted(dev_percentages, reverse=True)

    @pytest.mark.xfail(
        reason="Vulnerability: NaN or Inf actual_incident_value dumps to null in JSON, breaking Pydantic deserialization",
        strict=False,
    )
    def test_nan_and_inf_json_roundtrip_integrity(self):
        """
        Adversarial probe: passing NaN or Inf into telemetry produces deviations that
        fail Pydantic deserialization upon JSON reload because floats serialize as null.
        """
        dev_nan = compute_single_deviation("Vib", "mm/s", 5.0, float("nan"))
        report = assemble_eight_d_report(
            asset_tag="Pump-A12",
            symptoms=["vibration"],
            incident_timestamp="2023-11-04T08:00:00Z",
            oem_deviations=[dev_nan],
        )
        json_str = report.model_dump_json()
        # Should be cleanly re-loadable by schema
        reloaded = EightDIncidentReport.model_validate_json(json_str)
        assert reloaded.verify_checksum() is True


# ==============================================================================
# 3. FMEA RPN MITIGATION ADVERSARIAL STRESS TESTS
# ==============================================================================

class TestFMEARPNMitigationAdversarial:
    """Stress tests probing FMEA RPN calculations and boundaries."""

    def test_nominal_rpn_mitigation(self):
        """Nominal case: initial RPN 336 mitigated to 16 yields 95.24% reduction."""
        controls = generate_preventative_controls("Pump-A12", [], initial_rpn=336)
        assert "336" in controls.description
        assert "16" in controls.description
        assert "95.24%" in controls.description

    def test_zero_initial_rpn_guard(self):
        """Division by zero guard: initial_rpn = 0 must not raise ZeroDivisionError."""
        controls = generate_preventative_controls("Pump-A12", [], initial_rpn=0)
        assert "0% risk reduction" in controls.description or "0.0% risk reduction" in controls.description

    def test_negative_initial_rpn_guard(self):
        """Negative initial_rpn must not crash."""
        controls = generate_preventative_controls("Pump-A12", [], initial_rpn=-50)
        assert "0.0% risk reduction" in controls.description or "0% risk reduction" in controls.description

    def test_boundary_max_initial_rpn(self):
        """Maximum possible FMEA RPN is 1000 (S:10, O:10, D:10)."""
        controls = generate_preventative_controls("Pump-A12", [], initial_rpn=1000)
        assert "98.4%" in controls.description

    @pytest.mark.xfail(
        reason="Vulnerability: Mitigated RPN is hardcoded to 16, so when initial_rpn < 16, mitigated RPN exceeds initial RPN and produces negative risk reduction",
        strict=False,
    )
    def test_mitigated_rpn_never_exceeds_initial_rpn(self):
        """
        Adversarial probe: Verify that mitigated RPN never exceeds initial RPN.
        When initial_rpn = 10, mitigated RPN should be <= 10, not 16.
        """
        controls = generate_preventative_controls("Pump-A12", [], initial_rpn=10)
        # Check description does not claim negative risk reduction
        assert "-60" not in controls.description, "Mitigated RPN must not exceed initial RPN, producing negative reduction"

    def test_eight_d_report_rpn_bounds_invariance(self):
        """Verify EightDIncidentReport enforces valid RPN = S * O * D in [1, 1000]."""
        # Minimum valid RPN: S=1, O=1, D=1 -> RPN=1
        r_min = assemble_eight_d_report(
            asset_tag="Pump-A12",
            symptoms=["leak"],
            incident_timestamp=datetime.now(timezone.utc).isoformat(),
        )
        r_min.severity_score = 1
        r_min.occurrence_score = 1
        r_min.detection_score = 1
        r_min.rpn_score = 0  # Trigger auto-compute
        r_min.calculate_rpn_and_sort_timeline()
        assert r_min.rpn_score == 1
        assert 1 <= r_min.rpn_score <= 1000

        # Maximum valid RPN: S=10, O=10, D=10 -> RPN=1000
        r_max = assemble_eight_d_report(
            asset_tag="Pump-A12",
            symptoms=["leak"],
            incident_timestamp=datetime.now(timezone.utc).isoformat(),
        )
        r_max.severity_score = 10
        r_max.occurrence_score = 10
        r_max.detection_score = 10
        r_max.rpn_score = 0  # Trigger auto-compute
        r_max.calculate_rpn_and_sort_timeline()
        assert r_max.rpn_score == 1000
        assert 1 <= r_max.rpn_score <= 1000


# ==============================================================================
# 4. MASTER 8D REPORT ASSEMBLY & SHA-256 SEAL INVARIANCE
# ==============================================================================

class TestMaster8DAssemblyAndSealInvariance:
    """Stress tests probing report assembly under missing data and cryptographic seal invariance."""

    def test_assembly_with_none_telemetry(self):
        """Report assembly must succeed when telemetry_data is None."""
        report = assemble_eight_d_report(
            asset_tag="Pump-A12",
            symptoms=["seal leak", "vibration"],
            incident_timestamp="2023-11-04T08:00:00Z",
            telemetry_data=None,
        )
        assert report is not None
        assert report.verify_checksum() is True
        assert report.d7_preventative_controls.oem_deviations == []

    def test_assembly_with_empty_telemetry(self):
        """Report assembly must succeed when telemetry_data is empty dict."""
        report = assemble_eight_d_report(
            asset_tag="Pump-A12",
            symptoms=["coolant spill"],
            incident_timestamp="2023-11-04T08:00:00Z",
            telemetry_data={},
        )
        assert report is not None
        assert report.verify_checksum() is True
        assert report.d7_preventative_controls.oem_deviations == []

    def test_assembly_with_unknown_asset_and_special_chars(self):
        """Report assembly must sanitize special characters in report_id and succeed."""
        weird_tag = "PUMP#@!99-SPECIAL"
        report = assemble_eight_d_report(
            asset_tag=weird_tag,
            symptoms=["abnormal acoustic noise"],
            incident_timestamp="2023-11-04T12:00:00Z",
        )
        assert report is not None
        assert report.verify_checksum() is True
        assert re.match(r"^8D-[0-9]{4}-[A-Za-z0-9_\-]+$", report.report_id)

    def test_canonical_sha256_determinism(self):
        """Two independently assembled reports with identical input must produce identical SHA-256."""
        now_ts = "2023-11-04T10:00:00Z"
        report_1 = assemble_eight_d_report(
            asset_tag="Pump-A12",
            symptoms=["vibration 5.8 mm/s", "coolant leak"],
            incident_timestamp=now_ts,
            telemetry_data={"vibration_mm_s": 5.8},
            report_id="8D-2023-PUMP-A12-DETERMINISTIC",
        )
        report_2 = assemble_eight_d_report(
            asset_tag="Pump-A12",
            symptoms=["vibration 5.8 mm/s", "coolant leak"],
            incident_timestamp=now_ts,
            telemetry_data={"vibration_mm_s": 5.8},
            report_id="8D-2023-PUMP-A12-DETERMINISTIC",
        )

        assert report_1.checksum_sha256 == report_2.checksum_sha256
        assert len(report_1.checksum_sha256) == 64

    def test_sha256_tamper_detection_on_every_discipline(self):
        """Tampering with ANY section (D1-D8, metadata, citations) must break the seal."""
        report = assemble_eight_d_report(
            asset_tag="Pump-A12",
            symptoms=["ceramic seal shattered"],
            incident_timestamp="2023-11-04T10:00:00Z",
            telemetry_data={"vibration_mm_s": 5.8},
        )
        assert report.verify_checksum() is True

        # Tamper 1: D1 Team Leader
        orig_leader = report.d1_team.leader
        report.d1_team.leader = "Malicious Imposter"
        assert report.verify_checksum() is False
        report.d1_team.leader = orig_leader
        assert report.verify_checksum() is True

        # Tamper 2: D2 Problem Description
        orig_what = report.d2_problem.what
        report.d2_problem.what = "Altered incident description"
        assert report.verify_checksum() is False
        report.d2_problem.what = orig_what
        assert report.verify_checksum() is True

        # Tamper 3: D3 Containment Action
        orig_action = report.d3_containment[0].action
        report.d3_containment[0].action = "Fabricated containment step"
        assert report.verify_checksum() is False
        report.d3_containment[0].action = orig_action
        assert report.verify_checksum() is True

        # Tamper 4: D4 Root Cause Statement
        orig_cause = report.d4_root_causes.five_why_chain[0].cause_statement
        report.d4_root_causes.five_why_chain[0].cause_statement = "Falsified cause statement"
        assert report.verify_checksum() is False
        report.d4_root_causes.five_why_chain[0].cause_statement = orig_cause
        assert report.verify_checksum() is True

        # Tamper 5: D5 Corrective Action
        orig_pca = report.d5_permanent_actions[0].action
        report.d5_permanent_actions[0].action = "Cancelled corrective action"
        assert report.verify_checksum() is False
        report.d5_permanent_actions[0].action = orig_pca
        assert report.verify_checksum() is True

        # Tamper 6: D6 Validation Metrics
        orig_metrics = report.d6_validation.metrics
        report.d6_validation.metrics = "Manipulated test metrics"
        assert report.verify_checksum() is False
        report.d6_validation.metrics = orig_metrics
        assert report.verify_checksum() is True

        # Tamper 7: D7 Preventative Controls
        orig_desc = report.d7_preventative_controls.description
        report.d7_preventative_controls.description = "Deleted preventative controls"
        assert report.verify_checksum() is False
        report.d7_preventative_controls.description = orig_desc
        assert report.verify_checksum() is True

        # Tamper 8: D8 Recognition Approver
        orig_approver = report.d8_recognition.approver_name
        report.d8_recognition.approver_name = "Forged Signature"
        assert report.verify_checksum() is False
        report.d8_recognition.approver_name = orig_approver
        assert report.verify_checksum() is True

        # Tamper 9: Severity Score
        orig_sev = report.severity_score
        report.severity_score = 1
        assert report.verify_checksum() is False
        report.severity_score = orig_sev
        assert report.verify_checksum() is True

    def test_json_serialization_roundtrip_preserves_seal(self):
        """JSON dump and re-parse must preserve valid checksum verification."""
        report = assemble_eight_d_report(
            asset_tag="Pump-A12",
            symptoms=["ceramic seal fracture"],
            incident_timestamp="2023-11-04T10:00:00Z",
            telemetry_data={"vibration_mm_s": 5.8},
        )
        assert report.verify_checksum() is True

        raw_json = report.model_dump_json()
        restored_report = EightDIncidentReport.model_validate_json(raw_json)

        assert restored_report.checksum_sha256 == report.checksum_sha256
        assert restored_report.verify_checksum() is True

    def test_end_to_end_deductive_engine_with_minimal_request(self):
        """DeductiveRCAEngine.analyze_incident must succeed with minimal request without errors."""
        engine = DeductiveRCAEngine()
        req = RCAAnalyzeRequest(
            asset_tag="Pump-A12",
            symptoms=["coolant leak"],
            incident_timestamp="2023-11-04T08:00:00Z",
            telemetry_data={},
        )
        report = engine.analyze_incident(req)
        assert isinstance(report, EightDIncidentReport)
        assert report.verify_checksum() is True
        assert report.d4_root_causes.citation_grounding_ratio >= 0.0
