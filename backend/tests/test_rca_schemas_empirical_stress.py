"""
Industrial Mind OS - Empirical Adversarial Stress Test Suite
Target: backend/api/rca_schemas.py
Author: Challenger 1 (Gen 3) - Milestone 1

Comprehensive empirical challenge suite probing:
1. Extreme and boundary values for RPN components (S, O, D: 0, 1, 10, 11, types, booleans, recalculation).
2. Division-by-zero, negative, subnormal, and infinite scenarios for OEM envelope calculations.
3. SHA-256 canonical hash invariance under field-order permutations, timeline auto-sorting invariance,
   and single-field tamper detection across all 8D disciplines.
4. Malformed ISO timestamps, empty string IDs, unconstrained enum fields, and regex boundaries.
5. Payload serialization round-trips (model_dump_json -> model_validate_json) and cryptographic persistence.
"""

import copy
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from api.rca_schemas import (
    ActionStatus,
    CitationObject,
    ContainmentAction,
    CorrectiveAction,
    EightDIncidentReport,
    EightDIncidentReportSummary,
    EventType,
    ExportEvidenceRequest,
    ExportEvidenceResponse,
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


# ==============================================================================
# AUTHORITATIVE FIXTURE
# ==============================================================================

@pytest.fixture
def valid_report_dict():
    """Returns a fully-populated valid 8D report dictionary matching Pump-A12 baseline."""
    return {
        "report_id": "8D-2023-PUMP-A12-001",
        "created_at": "2023-11-04T12:00:00Z",
        "asset_tag": "Pump-A12",
        "severity_score": 8,
        "occurrence_score": 5,
        "detection_score": 4,
        "rpn_score": 160,
        "d1_team": {
            "leader": "Sarah Jenkins",
            "champion": "Robert Vance",
            "members": ["Dave Miller", "Elena Rostova"],
            "facilitator": "Marcus Vance",
        },
        "d2_problem": {
            "what": "Inboard ceramic seal shattered causing coolant leak",
            "where": "Sector 4 Cooling Loop, Pump-A12",
            "when": "2023-11-04T08:30:00Z",
            "who": "Shift B Control Room Operator",
            "why": "Unplanned equipment shutdown and hazardous containment loss",
            "how": "SCADA vibration alarm tripped at 5.8 mm/s",
            "how_many": "15 liters coolant spilled, 2.5 hours downtime",
            "incident_title": "Pump-A12 Ceramic Seal Fracture",
            "equipment_tag": "Pump-A12",
            "initial_severity": 8,
        },
        "d3_containment": [
            {
                "action_id": "ICA-01",
                "action": "Isolate suction/discharge block valves and deploy absorbent spill kits",
                "verified_effective": True,
                "effectiveness_pct": 100.0,
                "owner": "Dave Miller",
                "status": "IMPLEMENTED",
            }
        ],
        "d4_root_causes": {
            "five_why_chain": [
                {
                    "why_id": "WHY-1",
                    "level": 1,
                    "cause_statement": "Ceramic mechanical seal shattered under vibration fatigue",
                    "citation_ids": ["CITE-PUMP-001"],
                    "is_root_cause": False,
                },
                {
                    "why_id": "WHY-2",
                    "level": 2,
                    "cause_statement": "Sustained shaft deflection under 5.8 mm/s vibration",
                    "citation_ids": ["CITE-PUMP-001"],
                    "is_root_cause": False,
                },
                {
                    "why_id": "WHY-3",
                    "level": 3,
                    "cause_statement": "Operations personnel mistakenly believed threshold was 6.5 mm/s",
                    "citation_ids": ["CITE-PUMP-001"],
                    "is_root_cause": True,
                },
            ],
            "fishbone_analysis": {
                "branches": [
                    {
                        "category": "Machine",
                        "causes": ["Sustained 5.8 mm/s vibration exceeded OEM envelope"],
                        "citation_ids": ["CITE-PUMP-001"],
                    },
                    {
                        "category": "Method",
                        "causes": ["DCS alert logic failed to force mandatory shutdown"],
                        "citation_ids": ["CITE-PUMP-001"],
                    },
                ]
            },
            "occurrence_root_cause": "Sustained operation at 5.8 mm/s for 48 hours exceeded OEM 5.0 mm/s limit",
            "escape_root_cause": "DCS alarm logic allowed operation up to 6.5 mm/s without mandatory interlock",
        },
        "d5_permanent_actions": [
            {
                "pca_id": "PCA-01",
                "action": "Reprogram DCS interlock to trigger mandatory shutdown at 5.5 mm/s",
                "target_cause_id": "WHY-3",
                "owner": "Elena Rostova",
                "feasibility_score": 9,
                "status": "OPEN",
            }
        ],
        "d6_validation": {
            "validation_id": "VAL-01",
            "metrics": "Continuous vibration <= 1.8 mm/s across 30 days full load",
            "status": "IN_PROGRESS",
        },
        "d7_preventative_controls": {
            "control_id": "PRV-01",
            "sop_updates": ["SOP-ROTATING-04 Rev 3: Mandatory OEM envelope verification"],
            "pm_updates": ["PM-PUMP-WEEKLY: Laser vibration spectrum audit"],
            "oem_deviations": [
                {
                    "parameter_name": "Peak Vibration Velocity",
                    "oem_envelope_limit": 5.0,
                    "actual_incident_value": 5.8,
                    "unit": "mm/s",
                }
            ],
            "historical_matches": [
                {
                    "matched_report_id": "HIST-2023-PUMP-001",
                    "title": "Near Miss Report Nov 2023",
                    "similarity_score": 0.96,
                    "matching_symptoms": ["vibration 5.8 mm/s", "ignored alerts"],
                    "preventative_recommendations": ["Audit OEM limits across all loops"],
                }
            ],
            "horizontal_assets": ["Pump-A11", "Pump-A13"],
        },
        "d8_recognition": {
            "recognition_notes": "Commendation to operations shift team for rapid containment",
            "approver_name": "Dr. Marcus Vance",
            "approver_role": "VP Reliability Engineering",
            "signoff_status": "APPROVED",
            "financial_impact_total_usd": 14200.0,
            "downtime_hours_total": 2.5,
        },
        "timeline": [
            {
                "event_id": "EVT-001",
                "timestamp": "2023-11-02T08:00:00Z",
                "event_type": "TELEMETRY_ALARM",
                "description": "Vibration reached 5.8 mm/s, alert acknowledged without shutdown",
                "equipment_tag": "Pump-A12",
                "citation_ids": ["CITE-PUMP-001"],
                "parameters": {"vibration_mm_s": 5.8},
            },
            {
                "event_id": "EVT-002",
                "timestamp": "2023-11-04T08:00:00Z",
                "event_type": "SYSTEM_FAILURE",
                "description": "Catastrophic seal fracture and coolant release detected",
                "equipment_tag": "Pump-A12",
                "citation_ids": ["CITE-PUMP-001"],
                "parameters": {"vibration_mm_s": 5.9, "leak_volume_l": 15.0},
            },
        ],
        "citations": [
            {
                "citation_id": "CITE-PUMP-001",
                "source_doc": "Near_Miss_Report_2023.txt",
                "excerpt": "The maximum allowable vibration for Pump A12 is strictly 5.0 mm/s as per the OEM manual.",
                "section": "OEM Envelope & Thresholds",
                "page_or_line": "Lines 16-17",
                "confidence": 1.0,
            }
        ],
    }


# ==============================================================================
# 1. RPN COMPONENTS & BOUNDARY TESTING
# ==============================================================================

class TestRPNBoundariesAdversarial:
    """Stress tests Severity, Occurrence, Detection, and RPN score."""

    @pytest.mark.parametrize("s", [0, -1, -100, 11, 12, 100])
    def test_severity_boundary_rejection(self, valid_report_dict, s):
        data = copy.deepcopy(valid_report_dict)
        data["severity_score"] = s
        with pytest.raises(ValidationError) as exc:
            EightDIncidentReport.model_validate(data)
        assert any("severity_score" in str(e["loc"]) for e in exc.value.errors())

    @pytest.mark.parametrize("o", [0, -1, -50, 11, 12, 500])
    def test_occurrence_boundary_rejection(self, valid_report_dict, o):
        data = copy.deepcopy(valid_report_dict)
        data["occurrence_score"] = o
        with pytest.raises(ValidationError) as exc:
            EightDIncidentReport.model_validate(data)
        assert any("occurrence_score" in str(e["loc"]) for e in exc.value.errors())

    @pytest.mark.parametrize("d", [0, -1, -99, 11, 12, 1000])
    def test_detection_boundary_rejection(self, valid_report_dict, d):
        data = copy.deepcopy(valid_report_dict)
        data["detection_score"] = d
        with pytest.raises(ValidationError) as exc:
            EightDIncidentReport.model_validate(data)
        assert any("detection_score" in str(e["loc"]) for e in exc.value.errors())

    @pytest.mark.parametrize(
        "s, o, d, expected_rpn",
        [
            (1, 1, 1, 1),        # Absolute theoretical lower bound
            (10, 10, 10, 1000),  # Absolute theoretical upper bound
            (10, 1, 1, 10),
            (1, 10, 1, 10),
            (1, 1, 10, 10),
            (8, 5, 4, 160),      # Standard Pump-A12 incident baseline
            (9, 7, 3, 189),
            (10, 10, 5, 500),
        ],
    )
    def test_rpn_exact_bounds_and_auto_computation(self, valid_report_dict, s, o, d, expected_rpn):
        data = copy.deepcopy(valid_report_dict)
        data["severity_score"] = s
        data["occurrence_score"] = o
        data["detection_score"] = d
        data["rpn_score"] = 0  # Request auto-computation
        report = EightDIncidentReport.model_validate(data)
        assert report.rpn_score == expected_rpn

    def test_rpn_overrides_malicious_forged_underreporting(self, valid_report_dict):
        """Attacker passes forged low RPN score to hide risk."""
        data = copy.deepcopy(valid_report_dict)
        data["severity_score"] = 10
        data["occurrence_score"] = 10
        data["detection_score"] = 10
        data["rpn_score"] = 5  # Maliciously low score passed in
        report = EightDIncidentReport.model_validate(data)
        assert report.rpn_score == 1000, "Validator failed to overwrite forged RPN score!"

    def test_rpn_components_reject_invalid_non_numeric_types(self, valid_report_dict):
        data = copy.deepcopy(valid_report_dict)
        data["severity_score"] = "HIGH"
        with pytest.raises(ValidationError):
            EightDIncidentReport.model_validate(data)

        data["severity_score"] = None
        with pytest.raises(ValidationError):
            EightDIncidentReport.model_validate(data)

        data["severity_score"] = [8]
        with pytest.raises(ValidationError):
            EightDIncidentReport.model_validate(data)

        data["severity_score"] = {"val": 8}
        with pytest.raises(ValidationError):
            EightDIncidentReport.model_validate(data)

    def test_boolean_coercion_empirical_behavior(self, valid_report_dict):
        """
        EMPIRICAL OBSERVATION:
        Python bool is an int subclass. Without strict=True on Field,
        Pydantic v2 coerces True to 1.
        False (0) violates ge=1 and is rejected.
        True (1) satisfies ge=1, le=10 and is coerced to 1.
        """
        data = copy.deepcopy(valid_report_dict)
        data["severity_score"] = False
        with pytest.raises(ValidationError):
            EightDIncidentReport.model_validate(data)

        data["severity_score"] = True
        report = EightDIncidentReport.model_validate(data)
        assert report.severity_score == 1
        assert report.rpn_score == 1 * report.occurrence_score * report.detection_score


# ==============================================================================
# 2. OEM ENVELOPE DEVIATION DIVISION-BY-ZERO & NUMERICAL STRESS TESTS
# ==============================================================================

class TestOEMDeviationSafetyAndBoundaries:
    """Probes OEM deviation calculations for division by zero and edge cases."""

    def test_division_by_zero_zero_limit_guarded(self):
        """oem_envelope_limit = 0.0 must not raise ZeroDivisionError."""
        dev = OEMDeviation(
            parameter_name="Gas Leak ppm",
            oem_envelope_limit=0.0,
            actual_incident_value=25.0,
            unit="ppm",
        )
        assert dev.deviation_percent == 0.0
        assert dev.is_exceeded is False
        assert dev.severity_level == SeverityLevel.LOW

    def test_negative_oem_envelope_limit(self):
        """Negative limits (e.g. cryogenic temperatures) do not divide by zero."""
        dev = OEMDeviation(
            parameter_name="Cryogenic Storage",
            oem_envelope_limit=-40.0,
            actual_incident_value=-30.0,
            unit="°C",
        )
        assert dev.deviation_percent == 0.0
        assert dev.is_exceeded is False
        assert dev.severity_level == SeverityLevel.LOW

    def test_exact_limit_boundary(self):
        """When actual == limit, deviation is exactly 0.0% and is_exceeded is False."""
        dev = OEMDeviation(
            parameter_name="Vibration",
            oem_envelope_limit=5.0,
            actual_incident_value=5.0,
            unit="mm/s",
        )
        assert dev.deviation_percent == 0.0
        assert dev.is_exceeded is False
        assert dev.severity_level == SeverityLevel.LOW

    def test_infinitesimal_positive_exceedance(self):
        """Actual slightly above limit triggers exceedance."""
        dev = OEMDeviation(
            parameter_name="Vibration",
            oem_envelope_limit=5.0,
            actual_incident_value=5.001,
            unit="mm/s",
        )
        assert dev.is_exceeded is True
        assert dev.deviation_percent == 0.02
        assert dev.severity_level == SeverityLevel.HIGH

    def test_exact_fifteen_percent_threshold(self):
        """Threshold rule: > 15.0% is CRITICAL, <= 15.0% is HIGH."""
        dev_15_exact = OEMDeviation(
            parameter_name="Vibration",
            oem_envelope_limit=100.0,
            actual_incident_value=115.0,
            unit="mm/s",
        )
        assert dev_15_exact.deviation_percent == 15.0
        assert dev_15_exact.severity_level == SeverityLevel.HIGH

        dev_15_point_01 = OEMDeviation(
            parameter_name="Vibration",
            oem_envelope_limit=100.0,
            actual_incident_value=115.01,
            unit="mm/s",
        )
        assert dev_15_point_01.deviation_percent == 15.01
        assert dev_15_point_01.severity_level == SeverityLevel.CRITICAL

    def test_pump_a12_baseline_calculation(self):
        """Near-Miss report baseline: limit 5.0, actual 5.8 -> +16.0% CRITICAL."""
        dev = OEMDeviation(
            parameter_name="Peak Vibration Velocity",
            oem_envelope_limit=5.0,
            actual_incident_value=5.8,
            unit="mm/s",
        )
        assert dev.deviation_percent == 16.0
        assert dev.is_exceeded is True
        assert dev.severity_level == SeverityLevel.CRITICAL

    def test_subnormal_floating_point_limit(self):
        """Tests floating-point stability with very small numbers."""
        dev = OEMDeviation(
            parameter_name="Particulate",
            oem_envelope_limit=1e-5,
            actual_incident_value=2e-5,
            unit="ppm",
        )
        assert dev.is_exceeded is True
        assert dev.deviation_percent == 100.0
        assert dev.severity_level == SeverityLevel.CRITICAL

    def test_infinite_envelope_limit_empirical_behavior(self):
        """
        EMPIRICAL OBSERVATION:
        oem_envelope_limit = float('inf') produces deviation_percent = nan.
        Pydantic's model_dump_json() outputs null for nan/inf, which causes
        subsequent model_validate_json() to fail validation.
        """
        dev = OEMDeviation(
            parameter_name="Overpressure",
            oem_envelope_limit=float("inf"),
            actual_incident_value=10.0,
            unit="bar",
        )
        assert math.isnan(dev.deviation_percent)
        # Verify serialization round-trip failure on nan
        json_repr = dev.model_dump_json()
        assert '"deviation_percent":null' in json_repr
        with pytest.raises(ValidationError):
            OEMDeviation.model_validate_json(json_repr)


# ==============================================================================
# 3. SHA-256 CANONICAL HASH INVARIANCE & TAMPER DETECTION
# ==============================================================================

class TestSHA256CanonicalHashingAndTamperingAdversarial:
    """Verifies cryptographic tamper detection and canonical formatting invariance."""

    def test_canonical_hash_invariance_under_field_order_perturbation(self, valid_report_dict):
        """Payload dictionaries with different key orders must produce identical canonical SHA-256."""
        payload1 = copy.deepcopy(valid_report_dict)
        # Invert top-level keys
        payload2 = {k: payload1[k] for k in reversed(list(payload1.keys()))}
        # Invert nested keys in d1_team and d2_problem
        payload2["d1_team"] = {k: payload1["d1_team"][k] for k in reversed(list(payload1["d1_team"].keys()))}
        payload2["d2_problem"] = {k: payload1["d2_problem"][k] for k in reversed(list(payload1["d2_problem"].keys()))}

        r1 = EightDIncidentReport.model_validate(payload1)
        r2 = EightDIncidentReport.model_validate(payload2)

        h1 = r1.compute_canonical_sha256()
        h2 = r2.compute_canonical_sha256()

        assert h1 == h2, "Canonical SHA-256 differed when field ordering was perturbed!"
        assert len(h1) == 64
        assert r1.verify_checksum() is True
        assert r2.verify_checksum() is True

    def test_canonical_hash_invariance_nested_parameter_keys(self, valid_report_dict):
        """Parameters dict inside TimelineEvent must have canonical sorting in SHA-256."""
        p1 = copy.deepcopy(valid_report_dict)
        p1["timeline"][0]["parameters"] = {"alpha": 1, "beta": 2, "gamma": 3}

        p2 = copy.deepcopy(valid_report_dict)
        p2["timeline"][0]["parameters"] = {"gamma": 3, "alpha": 1, "beta": 2}

        r1 = EightDIncidentReport.model_validate(p1)
        r2 = EightDIncidentReport.model_validate(p2)

        assert r1.compute_canonical_sha256() == r2.compute_canonical_sha256()

    def test_timeline_auto_sort_invariance_in_canonical_hash(self, valid_report_dict):
        """Input timeline provided in reverse order must be auto-sorted and yield the same hash."""
        p1 = copy.deepcopy(valid_report_dict)  # Already chronologically sorted: EVT-001 (Nov 2), EVT-002 (Nov 4)

        p2 = copy.deepcopy(valid_report_dict)
        p2["timeline"] = [p1["timeline"][1], p1["timeline"][0]]  # Reversed order

        r1 = EightDIncidentReport.model_validate(p1)
        r2 = EightDIncidentReport.model_validate(p2)

        assert r2.timeline[0].event_id == "EVT-001"
        assert r2.timeline[1].event_id == "EVT-002"
        assert r1.compute_canonical_sha256() == r2.compute_canonical_sha256()

    def test_uncomputed_checksum_verification_fails(self, valid_report_dict):
        report = EightDIncidentReport.model_validate(valid_report_dict)
        report.checksum_sha256 = ""
        assert report.verify_checksum() is False
        assert report.verify_sha256() is False

    @pytest.mark.parametrize(
        "field_path, mutated_value",
        [
            ("severity_score", 9),
            ("occurrence_score", 6),
            ("detection_score", 3),
            ("asset_tag", "Pump-A99"),
            ("report_id", "8D-2023-PUMP-A12-999"),
            ("created_at", "2023-11-04T12:00:01Z"),
            ("d1_team.leader", "Forged Leader"),
            ("d1_team.champion", "Forged Champion"),
            ("d2_problem.what", "Forged problem statement"),
            ("d2_problem.how_many", "1000 liters spilled"),
            ("d3_containment.0.action", "Forged containment action"),
            ("d3_containment.0.effectiveness_pct", 50.0),
            ("d4_root_causes.occurrence_root_cause", "Forged occurrence root cause"),
            ("d4_root_causes.five_why_chain.0.cause_statement", "Tampered 5-Why statement"),
            ("d5_permanent_actions.0.feasibility_score", 2),
            ("d5_permanent_actions.0.action", "Tampered permanent corrective action"),
            ("d6_validation.metrics", "Tampered validation metrics description"),
            ("d7_preventative_controls.horizontal_assets", ["Pump-A11", "Pump-A99"]),
            ("d8_recognition.approver_name", "Tampered Approver Name"),
            ("timeline.0.description", "Tampered timeline narrative"),
            ("timeline.0.timestamp", "2023-11-02T09:00:00Z"),
            ("citations.0.excerpt", "Tampered document excerpt text"),
        ],
    )
    def test_single_field_tamper_detection_across_all_disciplines(self, valid_report_dict, field_path, mutated_value):
        """Mutating any field after computing hash MUST fail verify_checksum()."""
        report = EightDIncidentReport.model_validate(valid_report_dict)
        original_hash = report.compute_canonical_sha256()
        assert report.verify_checksum() is True

        # Apply mutation
        target = report
        parts = field_path.split(".")
        for part in parts[:-1]:
            if part.isdigit():
                target = target[int(part)]
            else:
                target = getattr(target, part)

        final_key = parts[-1]
        if final_key.isdigit():
            target[int(final_key)] = mutated_value
        else:
            setattr(target, final_key, mutated_value)

        assert report.verify_checksum() is False, f"Tamper undetected on path: {field_path}"
        assert report.compute_canonical_sha256() != original_hash


# ==============================================================================
# 4. TIMESTAMPS, FORMATS, EMPTY STRINGS & ENUMS
# ==============================================================================

class TestTimestampsStringsAndEnumsAdversarial:
    """Probes ISO 8601 parsing, empty IDs, enum boundaries, and regex patterns."""

    @pytest.mark.parametrize(
        "valid_iso",
        [
            "2023-11-04T08:00:00Z",
            "2023-11-04T08:00:00+00:00",
            "2023-11-04T08:00:00-05:00",
            "2023-11-04T08:00:00.123456+00:00",
            "2023-11-04T08:00:00.999Z",
        ],
    )
    def test_valid_iso_timestamp_variants(self, valid_iso):
        evt = TimelineEvent(
            event_id="EVT-01",
            timestamp=valid_iso,
            event_type="TELEMETRY_ALARM",
            description="Valid event description",
            equipment_tag="Pump-A12",
        )
        assert evt.timestamp is not None

    @pytest.mark.parametrize(
        "malformed_iso",
        [
            "",
            "   ",
            "2023-02-30T00:00:00Z",   # Invalid calendar date
            "2023-13-01T00:00:00Z",   # Month out of range
            "2023-11-04T25:00:00Z",   # Hour out of range
            "2023/11/04 08:00:00",    # Slashes instead of dashes
            "November 4, 2023 8:00 AM",
            "1699084800",             # Epoch timestamp string
            "undefined",
            "null",
        ],
    )
    def test_malformed_iso_timestamps_rejected(self, malformed_iso):
        with pytest.raises(ValidationError):
            TimelineEvent(
                event_id="EVT-01",
                timestamp=malformed_iso,
                event_type="TELEMETRY_ALARM",
                description="Valid event description",
                equipment_tag="Pump-A12",
            )

    @pytest.mark.parametrize(
        "invalid_cite_id",
        [
            "",
            "   ",
            "CITE",
            "CITE-",
            "cite-pump-001",     # Lowercase prefix
            "CITE PUMP 001",     # Spaces
            "CITE@PUMP@001",     # Symbols
            "CITE#001",
            "INVALID-PUMP-001",
        ],
    )
    def test_citation_id_strict_regex(self, invalid_cite_id):
        with pytest.raises(ValidationError):
            CitationObject(
                citation_id=invalid_cite_id,
                source_doc="doc.txt",
                excerpt="Valid text excerpt",
            )

    @pytest.mark.parametrize(
        "invalid_report_id",
        [
            "",
            "   ",
            "8D-23-PUMP",       # 2 digit year
            "8D-2023-",         # Missing slug
            "8D_2023_PUMP_001", # Underscore prefix
            "INCIDENT-001",
        ],
    )
    def test_report_id_strict_regex(self, valid_report_dict, invalid_report_id):
        data = copy.deepcopy(valid_report_dict)
        data["report_id"] = invalid_report_id
        with pytest.raises(ValidationError):
            EightDIncidentReport.model_validate(data)

    def test_empty_string_ids_empirical_behavior(self):
        """
        EMPIRICAL OBSERVATION:
        While CitationObject.citation_id and EightDIncidentReport.report_id enforce regex,
        other ID fields (event_id, why_id, action_id, pca_id, validation_id, control_id, matched_report_id)
        are typed as unconstrained `str` and permit empty strings `\"\"`.
        """
        evt = TimelineEvent(event_id="", timestamp="2023-11-04T08:00:00Z", event_type="ALARM", description="desc", equipment_tag="Pump-A12")
        assert evt.event_id == ""

        why = FiveWhyNode(why_id="", level=1, cause_statement="statement")
        assert why.why_id == ""

        act = ContainmentAction(action_id="", action="action", owner="owner")
        assert act.action_id == ""

    def test_timeline_event_type_unconstrained_str_behavior(self):
        """
        EMPIRICAL OBSERVATION:
        TimelineEvent.event_type is typed as `str` rather than `EventType` enum.
        Arbitrary string values like 'CUSTOM_LOG_ENTRY' are accepted.
        """
        evt = TimelineEvent(
            event_id="EVT-01",
            timestamp="2023-11-04T08:00:00Z",
            event_type="ARBITRARY_UNLISTED_TYPE",
            description="desc",
            equipment_tag="Pump-A12",
        )
        assert evt.event_type == "ARBITRARY_UNLISTED_TYPE"

    @pytest.mark.parametrize(
        "cat_input, expected_normalized",
        [
            ("man", "Man"),
            ("MAN", "Man"),
            ("machine", "Machine"),
            ("MACHINE", "Machine"),
            ("material", "Material"),
            ("method", "Method"),
            ("measurement", "Measurement"),
            ("environment", "Environment"),
            ("milieu", "Environment"),
            ("  machine  ", "Machine"),
        ],
    )
    def test_fishbone_category_normalization(self, cat_input, expected_normalized):
        branch = FishboneBranch(category=cat_input, causes=["Causal factor"], citation_ids=["CITE-01"])
        assert branch.category == expected_normalized

    @pytest.mark.parametrize("invalid_cat", ["Software", "Quality", "Management", ""])
    def test_fishbone_category_invalid_rejected(self, invalid_cat):
        with pytest.raises(ValidationError):
            FishboneBranch(category=invalid_cat, causes=["Causal factor"])

    @pytest.mark.parametrize("invalid_status", ["DONE", "FINISHED", "CANCELLED", "COMPLETE"])
    def test_action_status_rejects_invalid_enums(self, invalid_status):
        with pytest.raises(ValidationError):
            ContainmentAction(action="Test action", owner="Owner", status=invalid_status)

    @pytest.mark.parametrize("invalid_fmt", ["pdf", "xml", "csv", "xlsx", "", "markdown"])
    def test_export_evidence_request_rejects_unsupported_formats(self, invalid_fmt):
        with pytest.raises(ValidationError):
            ExportEvidenceRequest(report_id="8D-2023-PUMP-001", format=invalid_fmt)

    @pytest.mark.parametrize("valid_fmt", ["html", "HTML", "json", "JSON", "Json"])
    def test_export_evidence_request_case_insensitive_supported_formats(self, valid_fmt):
        req = ExportEvidenceRequest(report_id="8D-2023-PUMP-001", format=valid_fmt)
        assert req.format == valid_fmt.lower()


# ==============================================================================
# 5. ROUND-TRIP SERIALIZATION & EXTRA FIELDS ISOLATION
# ==============================================================================

class TestSerializationAndIsolationAdversarial:
    """Tests model_dump_json -> model_validate_json and extra fields isolation."""

    def test_model_dump_json_roundtrip_preserves_checksum_and_state(self, valid_report_dict):
        """Serializing to JSON and deserializing back must retain identical state and pass hash verification."""
        report = EightDIncidentReport.model_validate(valid_report_dict)
        original_digest = report.compute_canonical_sha256()
        assert report.verify_checksum() is True

        json_serialized = report.model_dump_json()
        assert isinstance(json_serialized, str)
        assert original_digest in json_serialized

        restored_report = EightDIncidentReport.model_validate_json(json_serialized)
        assert restored_report.report_id == report.report_id
        assert restored_report.checksum_sha256 == original_digest
        assert restored_report.verify_checksum() is True
        assert restored_report.compute_canonical_sha256() == original_digest

    def test_extra_field_injection_ignored_safely(self, valid_report_dict):
        """Injecting arbitrary extra fields must be safely ignored without polluting hash or state."""
        injected_dict = copy.deepcopy(valid_report_dict)
        injected_dict["__malicious_injected_root__"] = "SELECT * FROM secrets;"
        injected_dict["d1_team"]["__backdoor__"] = "unauthorized_data"
        injected_dict["timeline"][0]["__extra__"] = 9999

        clean_report = EightDIncidentReport.model_validate(valid_report_dict)
        injected_report = EightDIncidentReport.model_validate(injected_dict)

        assert clean_report.compute_canonical_sha256() == injected_report.compute_canonical_sha256()
        assert "__malicious_injected_root__" not in injected_report.model_dump()
        assert "__backdoor__" not in injected_report.d1_team.model_dump()


# ==============================================================================
# 6. CITATION GROUNDING & ASSUMPTION FLAGGING
# ==============================================================================

class TestCitationGroundingIntegrityAdversarial:
    """Verifies causal grounding verification in 5-Why and Fishbone structures."""

    def test_orphaned_citation_id_marks_node_unsubstantiated(self, valid_report_dict):
        """If 5-Why node cites an ID that does NOT exist in report.citations, it must be flagged."""
        data = copy.deepcopy(valid_report_dict)
        data["d4_root_causes"]["five_why_chain"][0]["citation_ids"] = ["CITE-NON-EXISTENT"]
        report = EightDIncidentReport.model_validate(data)

        node = report.d4_root_causes.five_why_chain[0]
        assert node.is_unsubstantiated is True
        assert node.assumed_flag is True
        assert node.assumption_flag is True

    def test_empty_citations_flags_entire_causal_chain(self, valid_report_dict):
        """If report has empty citations list, all causal nodes must be marked unsubstantiated."""
        data = copy.deepcopy(valid_report_dict)
        data["citations"] = []
        report = EightDIncidentReport.model_validate(data)

        for node in report.d4_root_causes.five_why_chain:
            assert node.is_unsubstantiated is True
            assert node.assumed_flag is True
            assert node.assumption_flag is True

    def test_citation_grounding_ratio_calculation(self):
        """Tests exact grounding ratio computation across 5-Why nodes and Fishbone branches."""
        node1 = FiveWhyNode(why_id="W1", level=1, cause_statement="Statement 1", citation_ids=["C1"])
        node2 = FiveWhyNode(why_id="W2", level=2, cause_statement="Statement 2", citation_ids=[])  # ungrounded
        fb = FishboneAnalysis(
            branches=[
                FishboneBranch(category="Machine", causes=["Cause FB1"], citation_ids=["C1"]),  # grounded
                FishboneBranch(category="Method", causes=["Cause FB2"], citation_ids=[]),        # ungrounded
            ]
        )
        rca = RootCauseAnalysis(
            five_why_chain=[node1, node2],
            fishbone_analysis=fb,
            occurrence_root_cause="Occurrence cause",
            escape_root_cause="Escape cause",
        )
        # Total items = 2 why nodes + 2 branches with causes = 4. Grounded = 2. Ratio = 2/4 = 0.5
        assert rca.citation_grounding_ratio == 0.5


# ==============================================================================
# MAIN RUNNER
# ==============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("RUNNING MILENSTONE 1 ADVERSARIAL STRESS TEST HARNESS")
    print("=" * 80)
    sys.exit(pytest.main(["-v", __file__]))
