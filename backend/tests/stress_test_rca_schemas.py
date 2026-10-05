"""
Adversarial Stress Test Suite for RCA Pydantic v2 Schemas
Target: backend/api/rca_schemas.py

Probes:
1. Extreme and boundary values for RPN components (Severity, Occurrence, Detection [0, 1, 10, 11, extremes]).
2. Division-by-zero, subnormal, and zero-limit guards for OEM deviation calculations.
3. SHA-256 canonical hash invariance under field order perturbations, and tamper detection on all core disciplines.
4. Malformed ISO timestamps, empty/whitespace strings, invalid enum values, regex boundary breaks.
5. Payload serialization round-trips (model_dump_json -> model_validate_json) and checksum persistence.
6. Extra field injection resistance and schema isolation.
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
# FIXTURES
# ==============================================================================

@pytest.fixture
def base_valid_report_dict():
    """Generates a complete, structurally sound dictionary representation of an 8D report."""
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
        },
        "d2_problem": {
            "what": "Inboard ceramic seal shattered resulting in glycol coolant release",
            "where": "Sector 4 Primary Cooling Loop, Pump-A12",
            "when": "2023-11-04T08:30:00Z",
            "who": "Shift B Control Room Operator",
            "why": "Unplanned equipment stoppage and environmental containment breach",
            "how": "SCADA vibration velocity high-high trip alarm (5.8 mm/s)",
            "how_many": "15 liters spilled, 2.5 hours total train downtime",
            "initial_severity": 8,
        },
        "d3_containment": [
            {
                "action_id": "ICA-01",
                "action": "Isolate suction/discharge block valves and deploy absorbent booms",
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
                    "cause_statement": "Mechanical ceramic seal shattered",
                    "citation_ids": ["CITE-PUMP-001"],
                    "is_root_cause": False,
                },
                {
                    "why_id": "WHY-2",
                    "level": 2,
                    "cause_statement": "Extreme dynamic shaft deflection under 5.8 mm/s vibration",
                    "citation_ids": ["CITE-PUMP-001"],
                    "is_root_cause": False,
                },
                {
                    "why_id": "WHY-3",
                    "level": 3,
                    "cause_statement": "Vibration warning alert ignored for 48 hours",
                    "citation_ids": ["CITE-PUMP-001"],
                    "is_root_cause": True,
                },
            ],
            "fishbone_analysis": {
                "branches": [
                    {
                        "category": "Machine",
                        "causes": ["Sustained 5.8 mm/s vibration beyond 5.0 mm/s envelope"],
                        "citation_ids": ["CITE-PUMP-001"],
                    },
                    {
                        "category": "Method",
                        "causes": ["DCS alarm threshold set to 6.5 mm/s instead of OEM 5.0 mm/s"],
                        "citation_ids": ["CITE-PUMP-001"],
                    },
                ]
            },
            "occurrence_root_cause": "Sustained operation at 5.8 mm/s exceeded OEM design envelope of 5.0 mm/s",
            "escape_root_cause": "DCS alarm logic allowed operation up to 6.5 mm/s without triggering mandatory trip",
        },
        "d5_permanent_actions": [
            {
                "pca_id": "PCA-01",
                "action": "Reprogram DCS interlock logic to force mandatory trip at 5.5 mm/s",
                "target_cause_id": "WHY-3",
                "owner": "Elena Rostova",
                "feasibility_score": 9,
                "status": "OPEN",
            }
        ],
        "d6_validation": {
            "validation_id": "VAL-01",
            "metrics": "Continuous vibration monitoring demonstrating <= 1.8 mm/s over 30 days",
            "status": "IN_PROGRESS",
        },
        "d7_preventative_controls": {
            "control_id": "PRV-01",
            "sop_updates": ["SOP-ROTATING-04 Rev 3: Mandatory OEM envelope verification"],
            "pm_updates": ["PM-PUMP-WEEKLY: Laser vibration spectrum audit"],
            "horizontal_assets": ["Pump-A11", "Pump-A13"],
        },
        "d8_recognition": {
            "recognition_notes": "Commendation to shift team for immediate isolation preventing water table contamination",
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
                "description": "Vibration levels reached 5.8 mm/s; operator acknowledged without trip",
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


@pytest.fixture
def sample_report_instance(base_valid_report_dict):
    """Returns an instantiated and validated EightDIncidentReport."""
    return EightDIncidentReport.model_validate(base_valid_report_dict)


# ==============================================================================
# SECTION 1: RPN BOUNDARY & EXTREME VALUE ADVERSARIAL TESTS
# ==============================================================================

class TestRPNBoundariesAndCalculations:
    """Adversarially stresses Severity, Occurrence, Detection, and RPN score bounds."""

    @pytest.mark.parametrize("invalid_severity", [0, -1, -999, 11, 12, 100, 99999])
    def test_severity_out_of_bounds_rejected(self, base_valid_report_dict, invalid_severity):
        payload = copy.deepcopy(base_valid_report_dict)
        payload["severity_score"] = invalid_severity
        with pytest.raises(ValidationError) as exc_info:
            EightDIncidentReport.model_validate(payload)
        errors = exc_info.value.errors()
        assert any("severity_score" in str(err["loc"]) for err in errors)

    @pytest.mark.parametrize("invalid_occurrence", [0, -1, -50, 11, 12, 1000])
    def test_occurrence_out_of_bounds_rejected(self, base_valid_report_dict, invalid_occurrence):
        payload = copy.deepcopy(base_valid_report_dict)
        payload["occurrence_score"] = invalid_occurrence
        with pytest.raises(ValidationError) as exc_info:
            EightDIncidentReport.model_validate(payload)
        errors = exc_info.value.errors()
        assert any("occurrence_score" in str(err["loc"]) for err in errors)

    @pytest.mark.parametrize("invalid_detection", [0, -1, -500, 11, 15, 99])
    def test_detection_out_of_bounds_rejected(self, base_valid_report_dict, invalid_detection):
        payload = copy.deepcopy(base_valid_report_dict)
        payload["detection_score"] = invalid_detection
        with pytest.raises(ValidationError) as exc_info:
            EightDIncidentReport.model_validate(payload)
        errors = exc_info.value.errors()
        assert any("detection_score" in str(err["loc"]) for err in errors)

    @pytest.mark.parametrize(
        "s, o, d, expected_rpn",
        [
            (1, 1, 1, 1),        # Absolute theoretical minimum
            (10, 10, 10, 1000),  # Absolute theoretical maximum
            (1, 10, 10, 100),
            (10, 1, 1, 10),
            (5, 5, 5, 125),
            (8, 5, 4, 160),
            (9, 3, 7, 189),
            (10, 10, 1, 100),
        ],
    )
    def test_rpn_exact_multiplication_invariants(self, base_valid_report_dict, s, o, d, expected_rpn):
        payload = copy.deepcopy(base_valid_report_dict)
        payload["severity_score"] = s
        payload["occurrence_score"] = o
        payload["detection_score"] = d
        # Pass a bogus initial rpn_score to test auto-recalculation
        payload["rpn_score"] = 0
        report = EightDIncidentReport.model_validate(payload)
        assert report.rpn_score == expected_rpn

    def test_rpn_overrides_malicious_forged_rpn(self, base_valid_report_dict):
        """If an attacker attempts to supply a forged lower RPN (e.g. 50 instead of 8*5*4=160), model must enforce 160."""
        payload = copy.deepcopy(base_valid_report_dict)
        payload["severity_score"] = 8
        payload["occurrence_score"] = 5
        payload["detection_score"] = 4
        payload["rpn_score"] = 10  # Forged under-reporting of risk
        report = EightDIncidentReport.model_validate(payload)
        assert report.rpn_score == 160

    @pytest.mark.parametrize("invalid_type", ["8", 8.5, None, [], {}, True])
    def test_rpn_components_reject_invalid_types(self, base_valid_report_dict, invalid_type):
        if invalid_type == "8":
            # Pydantic v2 in loose mode might coerce str "8" to int 8. Test true invalid non-numeric strings
            invalid_type = "CRITICAL_EIGHT"
        payload = copy.deepcopy(base_valid_report_dict)
        payload["severity_score"] = invalid_type
        with pytest.raises(ValidationError):
            EightDIncidentReport.model_validate(payload)


# ==============================================================================
# SECTION 2: OEM ENVELOPE DEVIATION DIVISION-BY-ZERO & NUMERICAL STRESS TESTS
# ==============================================================================

class TestOEMDeviationNumericalSafety:
    """Stress tests OEM envelope deviation calculations against zero, negative, and extreme inputs."""

    def test_zero_limit_avoids_division_by_zero(self):
        """Crucial safety test: envelope limit = 0.0 must never raise ZeroDivisionError."""
        dev = OEMDeviation(
            parameter_name="Gas Leak ppm",
            oem_envelope_limit=0.0,
            actual_incident_value=50.0,
            unit="ppm",
        )
        assert dev.deviation_percent == 0.0
        assert dev.is_exceeded is False
        assert dev.severity_level == SeverityLevel.LOW

    def test_negative_limit_safe_fallback(self):
        """Negative OEM limit (e.g. cryogenic threshold) must not trigger divide-by-zero or crashes."""
        dev = OEMDeviation(
            parameter_name="Sub-zero Storage Temp",
            oem_envelope_limit=-20.0,
            actual_incident_value=-15.0,
            unit="°C",
        )
        assert dev.deviation_percent == 0.0
        assert dev.is_exceeded is False

    def test_exact_limit_boundary_not_exceeded(self):
        """When actual == limit, deviation is 0.0% and is_exceeded is False."""
        dev = OEMDeviation(
            parameter_name="Peak Vibration Velocity",
            oem_envelope_limit=5.0,
            actual_incident_value=5.0,
            unit="mm/s",
        )
        assert dev.deviation_percent == 0.0
        assert dev.is_exceeded is False
        assert dev.severity_level == SeverityLevel.LOW

    def test_infinitesimal_positive_delta(self):
        """Smallest positive exceedance must trigger is_exceeded = True and SeverityLevel.HIGH."""
        dev = OEMDeviation(
            parameter_name="Peak Vibration Velocity",
            oem_envelope_limit=5.0,
            actual_incident_value=5.001,
            unit="mm/s",
        )
        assert dev.is_exceeded is True
        assert dev.deviation_percent > 0.0
        assert dev.severity_level == SeverityLevel.HIGH

    def test_subnormal_positive_limit(self):
        """Near-zero positive limit (e.g. 1e-6) tests floating-point stability."""
        dev = OEMDeviation(
            parameter_name="Micro-particulate count",
            oem_envelope_limit=1e-4,
            actual_incident_value=2e-4,
            unit="particles/ml",
        )
        assert dev.is_exceeded is True
        assert dev.deviation_percent == 100.0
        assert dev.severity_level == SeverityLevel.CRITICAL

    def test_astronomical_telemetry_values(self):
        """Extreme magnitude numbers should not cause overflow."""
        dev = OEMDeviation(
            parameter_name="High Voltage Spike",
            oem_envelope_limit=1000.0,
            actual_incident_value=1_000_000_000.0,
            unit="V",
        )
        assert dev.is_exceeded is True
        assert dev.severity_level == SeverityLevel.CRITICAL
        assert dev.deviation_percent > 99_999_000.0

    def test_exact_15_percent_threshold_classification(self):
        """15.0% exactly is HIGH (since rule is > 15.0% -> CRITICAL). 15.01% is CRITICAL."""
        dev_exact = OEMDeviation(
            parameter_name="Vibration",
            oem_envelope_limit=100.0,
            actual_incident_value=115.0,
            unit="mm/s",
        )
        assert dev_exact.deviation_percent == 15.0
        assert dev_exact.severity_level == SeverityLevel.HIGH

        dev_critical = OEMDeviation(
            parameter_name="Vibration",
            oem_envelope_limit=100.0,
            actual_incident_value=115.01,
            unit="mm/s",
        )
        assert dev_critical.deviation_percent == 15.01
        assert dev_critical.severity_level == SeverityLevel.CRITICAL


# ==============================================================================
# SECTION 3: SHA-256 CANONICAL HASH INVARIANCE & TAMPER DETECTION
# ==============================================================================

class TestSHA256CanonicalHashingAndTampering:
    """Verifies cryptographic tamper detection and canonical formatting invariance."""

    def test_canonical_hash_invariance_under_field_order_perturbations(self, base_valid_report_dict):
        """Canonical SHA-256 must be identical regardless of how dict keys are ordered in the input payload."""
        payload1 = copy.deepcopy(base_valid_report_dict)
        # Construct payload2 with inverted/permuted top-level and nested key ordering
        keys_reversed = list(reversed(list(payload1.keys())))
        payload2 = {k: payload1[k] for k in keys_reversed}

        # Permute d1_team keys as well
        payload2["d1_team"] = {
            "members": payload1["d1_team"]["members"],
            "champion": payload1["d1_team"]["champion"],
            "leader": payload1["d1_team"]["leader"],
        }

        report1 = EightDIncidentReport.model_validate(payload1)
        report2 = EightDIncidentReport.model_validate(payload2)

        hash1 = report1.compute_canonical_sha256()
        hash2 = report2.compute_canonical_sha256()

        assert hash1 == hash2, "Canonical hash differed under field order perturbation!"
        assert len(hash1) == 64
        assert report1.verify_checksum() is True
        assert report2.verify_checksum() is True

    def test_canonical_hash_invariance_nested_parameter_keys(self, base_valid_report_dict):
        """Nested dictionaries inside telemetry parameters must have deterministic key sorting."""
        payload1 = copy.deepcopy(base_valid_report_dict)
        payload1["timeline"][0]["parameters"] = {"vibration": 5.8, "temperature": 65.0, "rpm": 1450}

        payload2 = copy.deepcopy(base_valid_report_dict)
        payload2["timeline"][0]["parameters"] = {"rpm": 1450, "vibration": 5.8, "temperature": 65.0}

        r1 = EightDIncidentReport.model_validate(payload1)
        r2 = EightDIncidentReport.model_validate(payload2)

        assert r1.compute_canonical_sha256() == r2.compute_canonical_sha256()

    def test_uninitialized_checksum_fails_verification(self, sample_report_instance):
        """A report without a computed checksum must fail verify_checksum()."""
        sample_report_instance.checksum_sha256 = ""
        assert sample_report_instance.verify_checksum() is False
        assert sample_report_instance.verify_sha256() is False

    @pytest.mark.parametrize(
        "mutation_path, new_value",
        [
            ("severity_score", 9),
            ("occurrence_score", 6),
            ("detection_score", 2),
            ("asset_tag", "Pump-A99"),
            ("report_id", "8D-2023-PUMP-A12-999"),
            ("created_at", "2023-11-04T12:00:01Z"),
            ("d1_team.leader", "Imposter Leader"),
            ("d1_team.champion", "Different Champion"),
            ("d2_problem.what", "Completely different problem description"),
            ("d2_problem.how_many", "1000 liters spilled"),
            ("d3_containment.0.action", "Containment tampered with"),
            ("d3_containment.0.effectiveness_pct", 50.0),
            ("d4_root_causes.occurrence_root_cause", "Forged occurrence cause"),
            ("d4_root_causes.five_why_chain.0.cause_statement", "Tampered 5-Why answer"),
            ("d5_permanent_actions.0.feasibility_score", 2),
            ("d5_permanent_actions.0.action", "Tampered permanent action"),
            ("d6_validation.metrics", "Tampered validation metrics"),
            ("d7_preventative_controls.horizontal_assets", ["Pump-A11", "Pump-A99"]),
            ("d8_recognition.approver_name", "Fake Approver"),
            ("timeline.0.description", "Tampered timeline event narrative"),
            ("timeline.0.timestamp", "2023-11-02T09:00:00Z"),
            ("citations.0.excerpt", "Tampered citation excerpt string"),
        ],
    )
    def test_single_field_tamper_detection(self, sample_report_instance, mutation_path, new_value):
        """Mutating ANY field after SHA-256 seal generation MUST invalidate verify_checksum()."""
        original_hash = sample_report_instance.compute_canonical_sha256()
        assert sample_report_instance.verify_checksum() is True

        # Apply mutation
        target = sample_report_instance
        parts = mutation_path.split(".")
        for part in parts[:-1]:
            if part.isdigit():
                target = target[int(part)]
            else:
                target = getattr(target, part)

        final_key = parts[-1]
        if final_key.isdigit():
            target[int(final_key)] = new_value
        else:
            setattr(target, final_key, new_value)

        # Tampered state verification
        assert sample_report_instance.verify_checksum() is False, f"Tamper undetected for path {mutation_path}!"
        # And recomputing must yield a different hash
        new_hash = sample_report_instance.compute_canonical_sha256()
        assert new_hash != original_hash


# ==============================================================================
# SECTION 4: TIMESTAMPS, FORMATS & MALFORMED STRINGS
# ==============================================================================

class TestTimestampsAndStringParsing:
    """Stress tests ISO 8601 parsing, string lengths, empty values, and injection patterns."""

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
    def test_timeline_event_valid_iso_timestamps(self, valid_iso):
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
            "2023-02-31T00:00:00Z",   # Invalid day in Feb
            "2023-13-01T00:00:00Z",   # Month 13
            "2023-11-04T25:00:00Z",   # Hour 25
            "2023/11/04 08:00:00",    # Slash separator
            "Nov 4, 2023 8:00 AM",    # English text
            "yesterday at noon",
            "1699084800",             # Unix timestamp as string
            "\x00\x00\x00",           # Null bytes
        ],
    )
    def test_timeline_event_rejects_malformed_timestamps(self, malformed_iso):
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
            "CITE-",             # Missing suffix
            "CITE",              # Missing hyphen
            "cite-pump-001",     # Lowercase prefix
            "CITE PUMP 001",     # Spaces
            "CITE-PUMP@001",     # Illegal symbol '@'
            "CITE-PUMP#001",     # Illegal symbol '#'
            "CITE-PUMP$001",     # Illegal symbol '$'
            "INVALID-PUMP-001",  # Wrong prefix
        ],
    )
    def test_citation_id_regex_strictness(self, invalid_cite_id):
        with pytest.raises(ValidationError):
            CitationObject(
                citation_id=invalid_cite_id,
                source_doc="doc.txt",
                excerpt="Valid excerpt of text here",
            )

    @pytest.mark.parametrize(
        "invalid_report_id",
        [
            "",
            "   ",
            "8D-23-PUMP",            # Year must be 4 digits
            "8D-ABCD-PUMP",          # Non-numeric year
            "8D-2023-",              # Missing slug
            "REPORT-2023-PUMP-001",  # Missing 8D- prefix
            "8D_2023_PUMP_001",      # Underscore instead of hyphen
        ],
    )
    def test_report_id_regex_strictness(self, base_valid_report_dict, invalid_report_id):
        payload = copy.deepcopy(base_valid_report_dict)
        payload["report_id"] = invalid_report_id
        with pytest.raises(ValidationError):
            EightDIncidentReport.model_validate(payload)

    def test_citation_excerpt_whitespace_only_rejected(self):
        with pytest.raises(ValidationError):
            CitationObject(
                citation_id="CITE-001",
                source_doc="doc.txt",
                excerpt="      \t\n   ",
            )

    def test_team_formation_whitespace_names_rejected(self):
        with pytest.raises(ValidationError):
            TeamFormation(leader="", champion="Champion")
        with pytest.raises(ValidationError):
            TeamFormation(leader="Leader", champion="")

    def test_five_why_node_level_bounds(self):
        # 1 to 10 are valid
        for lvl in range(1, 11):
            node = FiveWhyNode(why_id=f"W-{lvl}", level=lvl, cause_statement="Valid statement text")
            assert node.level == lvl

        # 0 and 11 are invalid
        with pytest.raises(ValidationError):
            FiveWhyNode(why_id="W-0", level=0, cause_statement="Valid statement text")
        with pytest.raises(ValidationError):
            FiveWhyNode(why_id="W-11", level=11, cause_statement="Valid statement text")


# ==============================================================================
# SECTION 5: ENUMS & CASE NORMALIZATION STRESS TESTS
# ==============================================================================

class TestEnumAndNormalizationStrictness:
    """Probes enum boundary values and case-insensitivity mapping."""

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
            ("milieu", "Environment"),  # French 6M variant
            ("  machine  ", "Machine"), # Surrounding spaces
        ],
    )
    def test_fishbone_category_normalization(self, cat_input, expected_normalized):
        branch = FishboneBranch(category=cat_input, causes=["Test cause"], citation_ids=["CITE-01"])
        assert branch.category == expected_normalized

    @pytest.mark.parametrize("invalid_cat", ["Software", "Quality", "Finance", "Management", ""])
    def test_fishbone_category_invalid_rejected(self, invalid_cat):
        with pytest.raises(ValidationError):
            FishboneBranch(category=invalid_cat, causes=["Test cause"])

    @pytest.mark.parametrize("invalid_status", ["DONE", "FINISHED", "CANCELLED", "COMPLETE", "1"])
    def test_action_status_rejects_invalid_values(self, invalid_status):
        with pytest.raises(ValidationError):
            ContainmentAction(
                action="Test action",
                owner="Owner",
                status=invalid_status,
            )

    @pytest.mark.parametrize(
        "fmt_input, expected_fmt",
        [
            ("html", "html"),
            ("HTML", "html"),
            ("json", "json"),
            ("JSON", "json"),
            ("Json", "json"),
        ],
    )
    def test_export_evidence_request_format_case_insensitivity(self, fmt_input, expected_fmt):
        req = ExportEvidenceRequest(report_id="8D-2023-PUMP-001", format=fmt_input)
        assert req.format == expected_fmt

    @pytest.mark.parametrize("invalid_format", ["pdf", "xml", "csv", "xlsx", "", "markdown"])
    def test_export_evidence_request_rejects_unsupported_formats(self, invalid_format):
        with pytest.raises(ValidationError):
            ExportEvidenceRequest(report_id="8D-2023-PUMP-001", format=invalid_format)


# ==============================================================================
# SECTION 6: ROUND-TRIP SERIALIZATION & EXTRA FIELDS ISOLATION
# ==============================================================================

class TestSerializationAndIsolation:
    """Tests model_dump_json -> model_validate_json persistence and extra field handling."""

    def test_model_dump_json_roundtrip_preserves_checksum_and_state(self, sample_report_instance):
        """Serializing to JSON string and parsing back must yield identical checksum and pass verification."""
        sample_report_instance.compute_canonical_sha256()
        original_checksum = sample_report_instance.checksum_sha256
        assert sample_report_instance.verify_checksum() is True

        # Round-trip through JSON
        json_str = sample_report_instance.model_dump_json()
        assert isinstance(json_str, str)
        assert original_checksum in json_str

        # Validate back from JSON
        restored = EightDIncidentReport.model_validate_json(json_str)
        assert restored.report_id == sample_report_instance.report_id
        assert restored.checksum_sha256 == original_checksum
        assert restored.verify_checksum() is True
        assert restored.compute_canonical_sha256() == original_checksum

    def test_extra_fields_ignored_without_corrupting_canonical_hash(self, base_valid_report_dict):
        """Attacker injecting arbitrary unknown fields must have them safely ignored (extra='ignore')."""
        payload_with_injection = copy.deepcopy(base_valid_report_dict)
        payload_with_injection["__malicious_injected_root__"] = "DROP TABLE reports;"
        payload_with_injection["d1_team"]["__attacker_secret__"] = "root_access_token"
        payload_with_injection["d4_root_causes"]["five_why_chain"][0]["extra_untrusted_field"] = 12345

        # Must parse cleanly
        clean_report = EightDIncidentReport.model_validate(base_valid_report_dict)
        injected_report = EightDIncidentReport.model_validate(payload_with_injection)

        # Injected fields must NOT appear in model_dump or affect canonical hash
        clean_hash = clean_report.compute_canonical_sha256()
        injected_hash = injected_report.compute_canonical_sha256()

        assert clean_hash == injected_hash
        assert "__malicious_injected_root__" not in injected_report.model_dump()


# ==============================================================================
# SECTION 7: CITATION GROUNDING ENGINE INTEGRITY
# ==============================================================================

class TestCitationGroundingIntegrity:
    """Verifies that ungrounded 5-Why and Fishbone nodes are flagged as unsubstantiated assumptions."""

    def test_orphaned_citation_id_marks_node_unsubstantiated(self, base_valid_report_dict):
        """If 5-Why node cites CITE-999 which does NOT exist in report.citations, it must be marked unsubstantiated."""
        payload = copy.deepcopy(base_valid_report_dict)
        payload["d4_root_causes"]["five_why_chain"][0]["citation_ids"] = ["CITE-NON-EXISTENT"]
        report = EightDIncidentReport.model_validate(payload)

        # Cross-validation in EightDIncidentReport should detect that CITE-NON-EXISTENT is not in report.citations
        node = report.d4_root_causes.five_why_chain[0]
        assert node.is_unsubstantiated is True
        assert node.assumed_flag is True

    def test_empty_citations_in_report_flags_all_why_nodes(self, base_valid_report_dict):
        """If entire report has zero citations, all causal nodes must be marked unsubstantiated."""
        payload = copy.deepcopy(base_valid_report_dict)
        payload["citations"] = []
        report = EightDIncidentReport.model_validate(payload)

        for node in report.d4_root_causes.five_why_chain:
            assert node.is_unsubstantiated is True
            assert node.assumed_flag is True
            assert node.assumption_flag is True

    def test_fishbone_branch_without_causes_is_not_unsubstantiated(self):
        """An empty fishbone branch (no causes listed) is not unsubstantiated."""
        branch = FishboneBranch(category="Man", causes=[], citation_ids=[])
        assert branch.is_unsubstantiated is False

    def test_fishbone_branch_with_causes_and_no_citations_is_unsubstantiated(self):
        """A fishbone branch claiming causes but citing no evidence is unsubstantiated."""
        branch = FishboneBranch(category="Machine", causes=["Fatigue crack on shaft"], citation_ids=[])
        assert branch.is_unsubstantiated is True


# ==============================================================================
# MAIN EXECUTION SCRIPT
# ==============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("RUNNING ADVERSARIAL STRESS TEST SUITE FOR RCA PYDANTIC SCHEMAS")
    print("=" * 80)
    sys.exit(pytest.main(["-v", __file__]))
