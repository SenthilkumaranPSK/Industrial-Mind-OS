"""
Comprehensive unit test suite for RCA Pydantic v2 schemas.
Verifies valid instantiations, boundary conditions, invalid input rejections,
RPN calculation, ISO 8601 parsing, SHA-256 canonical hashing, and JSON Schema exports.
"""

import pytest
from pydantic import ValidationError
from scratch_schema_test import (
    SeverityLevel,
    ActionStatus,
    FishboneCategory,
    EventType,
    SignOffStatus,
    CitationObject,
    TimelineEvent,
    FiveWhyNode,
    FishboneBranch,
    FishboneAnalysis,
    HistoricalMatch,
    OEMDeviation,
    ContainmentAction,
    CorrectiveAction,
    ValidationPlan,
    PreventativeControls,
    TeamFormation,
    ProblemDescription,
    RootCauseAnalysis,
    TeamRecognition,
    EightDIncidentReport,
    RCAAnalyzeRequest,
    HistoricalMatchRequest,
    ExportEvidenceRequest,
    ExportEvidenceResponse,
    EightDIncidentReportSummary,
)


# ==============================================================================
# 1. CITATION OBJECT TESTS
# ==============================================================================

def test_citation_object_valid():
    cite = CitationObject(
        citation_id="CITE-PUMP-001",
        source_doc="Near_Miss_Report_2023.txt",
        excerpt="The maximum allowable vibration for Pump A12 is strictly 5.0 mm/s.",
        section="Section 4",
        page_or_line="Lines 16-17",
        title="Incident Report & Near-Miss Record",
        confidence=0.95
    )
    assert cite.citation_id == "CITE-PUMP-001"
    assert cite.confidence == 0.95
    assert cite.source_doc == "Near_Miss_Report_2023.txt"


def test_citation_object_invalid_confidence():
    with pytest.raises(ValidationError):
        CitationObject(
            citation_id="CITE-001",
            source_doc="doc.txt",
            excerpt="valid excerpt here",
            confidence=1.5  # Out of range > 1.0
        )

    with pytest.raises(ValidationError):
        CitationObject(
            citation_id="CITE-001",
            source_doc="doc.txt",
            excerpt="valid excerpt here",
            confidence=-0.1  # Out of range < 0.0
        )


def test_citation_object_invalid_id_regex():
    with pytest.raises(ValidationError):
        CitationObject(
            citation_id="INVALID_ID_WITHOUT_PREFIX",
            source_doc="doc.txt",
            excerpt="valid excerpt here"
        )


def test_citation_object_empty_excerpt():
    with pytest.raises(ValidationError):
        CitationObject(
            citation_id="CITE-001",
            source_doc="doc.txt",
            excerpt="   "  # Whitespace only
        )


# ==============================================================================
# 2. TIMELINE EVENT TESTS
# ==============================================================================

def test_timeline_event_valid():
    evt = TimelineEvent(
        event_id="EVT-001",
        timestamp="2023-11-04T08:00:00Z",
        event_type="TELEMETRY_ALARM",
        description="Vibration exceeded normal threshold",
        equipment_tag="Pump-A12",
        citation_ids=["CITE-PUMP-001"],
        parameters={"vibration_mm_s": 5.8}
    )
    assert evt.is_unsubstantiated is False
    assert evt.citation_ids == ["CITE-PUMP-001"]
    assert "+00:00" in evt.timestamp or "Z" in evt.timestamp


def test_timeline_event_invalid_timestamp():
    with pytest.raises(ValidationError):
        TimelineEvent(
            event_id="EVT-001",
            timestamp="yesterday morning at 8am",  # Invalid ISO 8601
            event_type="TELEMETRY_ALARM",
            description="Vibration exceeded threshold",
            equipment_tag="Pump-A12"
        )


def test_timeline_event_unsubstantiated_auto_flag():
    evt = TimelineEvent(
        event_id="EVT-002",
        timestamp="2023-11-04T08:15:00Z",
        event_type="OPERATOR_ACTION",
        description="Operator ignored warning banner",
        equipment_tag="Pump-A12",
        citation_ids=[]
    )
    assert evt.is_unsubstantiated is True


# ==============================================================================
# 3. 5-WHY NODE TESTS
# ==============================================================================

def test_five_why_node_valid_and_grounded():
    node = FiveWhyNode(
        why_id="WHY-1",
        level=1,
        cause_statement="Mechanical ceramic seal fractured",
        citation_ids=["CITE-PUMP-001"],
        is_root_cause=False
    )
    assert node.is_unsubstantiated is False
    assert node.assumed_flag is False


def test_five_why_node_unsubstantiated_when_no_citations():
    node = FiveWhyNode(
        why_id="WHY-2",
        level=2,
        cause_statement="Coolant viscosity degraded",
        citation_ids=[]
    )
    assert node.is_unsubstantiated is True
    assert node.assumed_flag is True


def test_five_why_node_invalid_level():
    with pytest.raises(ValidationError):
        FiveWhyNode(
            why_id="WHY-1",
            level=0,  # Below minimum 1
            cause_statement="Valid statement"
        )

    with pytest.raises(ValidationError):
        FiveWhyNode(
            why_id="WHY-1",
            level=15,  # Exceeds maximum 10
            cause_statement="Valid statement"
        )


# ==============================================================================
# 4. FISHBONE BRANCH & ANALYSIS TESTS
# ==============================================================================

def test_fishbone_branch_valid_categories():
    categories = ["man", "MACHINE", "Material", "method", "Measurement", "Environment", "milieu"]
    for cat in categories:
        branch = FishboneBranch(category=cat, causes=["Test cause"], citation_ids=["CITE-001"])
        assert branch.category in ["Man", "Machine", "Material", "Method", "Measurement", "Environment"]
        assert branch.is_unsubstantiated is False


def test_fishbone_branch_invalid_category():
    with pytest.raises(ValidationError):
        FishboneBranch(category="Marketing", causes=["Bad marketing"])


def test_fishbone_branch_unsubstantiated():
    branch = FishboneBranch(category="Machine", causes=["Fatigue failure"], citation_ids=[])
    assert branch.is_unsubstantiated is True


def test_fishbone_analysis_get_branch():
    branch = FishboneBranch(category="Machine", causes=["Seal wear"], citation_ids=["CITE-01"])
    analysis = FishboneAnalysis(branches=[branch])
    found = analysis.get_branch("machine")
    assert found is not None
    assert found.category == "Machine"
    assert analysis.get_branch("Man") is None


# ==============================================================================
# 5. HISTORICAL MATCH & OEM DEVIATION TESTS
# ==============================================================================

def test_historical_match_valid():
    match = HistoricalMatch(
        matched_report_id="NM-2023-11-04-PUMP-A12",
        title="Pump A12 Ceramic Seal Failure Near-Miss",
        similarity_score=0.92,
        matching_symptoms=["high vibration", "seal leakage"],
        preventative_recommendations=["Enforce 5.0 mm/s limit", "Mandatory trip at 5.5 mm/s"]
    )
    assert match.similarity_score == 0.92
    assert len(match.matching_symptoms) == 2


def test_historical_match_invalid_score():
    with pytest.raises(ValidationError):
        HistoricalMatch(
            matched_report_id="NM-01",
            title="Title",
            similarity_score=1.5  # Exceeds 1.0
        )


def test_oem_deviation_nominal():
    dev = OEMDeviation(
        parameter_name="Peak Vibration Velocity",
        oem_envelope_limit=5.0,
        actual_incident_value=4.5,
        unit="mm/s"
    )
    assert dev.deviation_percent == -10.0
    assert dev.is_exceeded is False
    assert dev.severity_level == SeverityLevel.LOW


def test_oem_deviation_critical():
    # 5.8 mm/s vs 5.0 mm/s = +16.0% deviation -> CRITICAL (>15%)
    dev = OEMDeviation(
        parameter_name="Peak Vibration Velocity",
        oem_envelope_limit=5.0,
        actual_incident_value=5.8,
        unit="mm/s"
    )
    assert dev.deviation_percent == 16.0
    assert dev.is_exceeded is True
    assert dev.severity_level == SeverityLevel.CRITICAL


def test_oem_deviation_zero_limit_safety():
    dev = OEMDeviation(
        parameter_name="Zero limit parameter",
        oem_envelope_limit=0.0,
        actual_incident_value=5.0,
        unit="bar"
    )
    assert dev.deviation_percent == 0.0
    assert dev.is_exceeded is False


# ==============================================================================
# 6. CONTAINMENT & CORRECTIVE ACTION TESTS
# ==============================================================================

def test_containment_action_valid():
    ca = ContainmentAction(
        action_id="ICA-01",
        action="Isolate discharge valve and deploy spill berms",
        verified_effective=True,
        effectiveness_pct=100.0,
        owner="Dave Miller"
    )
    assert ca.effectiveness_pct == 100.0
    assert ca.status == ActionStatus.IMPLEMENTED


def test_containment_action_invalid_pct():
    with pytest.raises(ValidationError):
        ContainmentAction(
            action_id="ICA-01",
            action="Action description",
            effectiveness_pct=120.0,  # Exceeds 100.0
            owner="Dave Miller"
        )


def test_corrective_action_valid():
    pca = CorrectiveAction(
        pca_id="PCA-01",
        action="Reprogram DCS alarm and interlock logic to trip at 5.5 mm/s",
        target_cause_id="WHY-3",
        owner="Elena Rostova",
        feasibility_score=9
    )
    assert pca.feasibility_score == 9
    assert pca.status == ActionStatus.OPEN


def test_corrective_action_invalid_feasibility():
    with pytest.raises(ValidationError):
        CorrectiveAction(
            pca_id="PCA-01",
            action="Action description",
            owner="Owner",
            feasibility_score=0  # Below 1
        )
    with pytest.raises(ValidationError):
        CorrectiveAction(
            pca_id="PCA-01",
            action="Action description",
            owner="Owner",
            feasibility_score=11  # Above 10
        )


# ==============================================================================
# 7. VALIDATION PLAN & PREVENTATIVE CONTROLS TESTS
# ==============================================================================

def test_validation_plan_valid():
    vp = ValidationPlan(
        validation_id="VAL-01",
        metrics="Vibration reduced from 5.8 mm/s to 1.8 mm/s post-alignment",
        status=ActionStatus.IN_PROGRESS
    )
    assert vp.validation_id == "VAL-01"


def test_preventative_controls_valid():
    pc = PreventativeControls(
        control_id="PRV-01",
        sop_updates=["SOP-PUMP-A12 Rev 4"],
        pm_updates=["Weekly vibration laser scanning"],
        horizontal_assets=["Pump-A11", "Pump-A13"]
    )
    assert len(pc.horizontal_assets) == 2


# ==============================================================================
# 8. TEAM FORMATION & PROBLEM DESCRIPTION TESTS
# ==============================================================================

def test_team_formation_valid():
    tf = TeamFormation(
        leader="Sarah Jenkins",
        champion="Robert Vance",
        members=["Dave Miller", "Elena Rostova", "Marcus Bell"]
    )
    assert tf.leader == "Sarah Jenkins"
    assert len(tf.members) == 3


def test_problem_description_valid():
    pd = ProblemDescription(
        what="Ceramic seal shattered and leaked coolant fluid",
        where="Primary Cooling Loop, Sector 4",
        when="2023-11-04T08:30:00Z",
        who="Shift Supervisor B",
        why="Environmental containment risk and downtime",
        how="SCADA vibration alarm alert at 5.8 mm/s",
        how_many="15 liters spilled, 2.5 hours downtime",
        initial_severity=8
    )
    assert pd.initial_severity == 8


def test_problem_description_initial_severity_bounds():
    with pytest.raises(ValidationError):
        ProblemDescription(
            what="What",
            where="Where",
            when="When",
            who="Who",
            why="Why",
            how="How",
            how_many="How many",
            initial_severity=12  # Exceeds 10
        )


# ==============================================================================
# 9. ROOT CAUSE ANALYSIS & GROUNDING RATIO TESTS
# ==============================================================================

def test_root_cause_analysis_grounding_ratio():
    node1 = FiveWhyNode(why_id="W1", level=1, cause_statement="Statement 1", citation_ids=["C1"])
    node2 = FiveWhyNode(why_id="W2", level=2, cause_statement="Statement 2", citation_ids=[])
    fb = FishboneAnalysis(branches=[
        FishboneBranch(category="Machine", causes=["Cause FB1"], citation_ids=["C1"])
    ])
    rca = RootCauseAnalysis(
        five_why_chain=[node1, node2],
        fishbone_analysis=fb,
        occurrence_root_cause="Occurrence cause",
        escape_root_cause="Escape cause"
    )
    # Total items = 2 nodes + 1 branch = 3 items. Grounded = node1 (1) + fb (1) = 2.
    # Grounding ratio = 2/3 = 0.6667
    assert rca.citation_grounding_ratio == pytest.approx(0.6667, 0.01)


# ==============================================================================
# 10. MASTER 8D INCIDENT REPORT & RPN / SHA-256 / TAMPER TESTS
# ==============================================================================

@pytest.fixture
def sample_8d_report():
    cite = CitationObject(
        citation_id="CITE-PUMP-001",
        source_doc="Near_Miss_Report_2023.txt",
        excerpt="The maximum allowable vibration for Pump A12 is strictly 5.0 mm/s.",
        section="Section 4",
        page_or_line="Lines 16-17",
        confidence=0.98
    )
    evt = TimelineEvent(
        event_id="EVT-001",
        timestamp="2023-11-04T08:00:00Z",
        event_type="TELEMETRY_ALARM",
        description="Vibration at 5.8 mm/s",
        equipment_tag="Pump-A12",
        citation_ids=["CITE-PUMP-001"]
    )
    why = FiveWhyNode(
        why_id="WHY-1",
        level=1,
        cause_statement="Ceramic seal shattered under vibration",
        citation_ids=["CITE-PUMP-001"]
    )
    fb = FishboneAnalysis(branches=[
        FishboneBranch(category="Machine", causes=["Seal fatigue"], citation_ids=["CITE-PUMP-001"])
    ])
    rca = RootCauseAnalysis(
        five_why_chain=[why],
        fishbone_analysis=fb,
        occurrence_root_cause="Sustained 5.8 mm/s vibration exceeded seal limit",
        escape_root_cause="Alarm set to 6.5 mm/s instead of 5.0 mm/s limit"
    )
    return EightDIncidentReport(
        report_id="8D-2023-PUMP-A12-001",
        created_at="2023-11-04T12:00:00Z",
        asset_tag="Pump-A12",
        severity_score=8,
        occurrence_score=5,
        detection_score=4,
        d1_team=TeamFormation(leader="Sarah J", champion="Robert V", members=["Dave M"]),
        d2_problem=ProblemDescription(
            what="Seal shattered", where="Loop 4", when="2023-11-04T08:30:00Z",
            who="Shift B", why="Coolant leak", how="Alarm", how_many="15L", initial_severity=8
        ),
        d3_containment=[ContainmentAction(action="Isolate valve", owner="Dave M")],
        d4_root_causes=rca,
        d5_permanent_actions=[CorrectiveAction(action="Reprogram DCS trip to 5.5 mm/s", owner="Elena R")],
        d6_validation=ValidationPlan(metrics="Vibration reduced to 1.8 mm/s"),
        d7_preventative_controls=PreventativeControls(horizontal_assets=["Pump-A11"]),
        d8_recognition=TeamRecognition(
            recognition_notes="Prompt response", approver_name="Dr. Bell", approver_role="VP Quality"
        ),
        timeline=[evt],
        citations=[cite]
    )


def test_eight_d_rpn_calculation(sample_8d_report):
    # S=8, O=5, D=4 -> RPN = 8 * 5 * 4 = 160
    assert sample_8d_report.rpn_score == 160


def test_eight_d_sha256_canonical_and_tamper(sample_8d_report):
    # 1. Compute digest
    digest = sample_8d_report.compute_sha256()
    assert len(digest) == 64
    assert sample_8d_report.checksum_sha256 == digest

    # 2. Verify match
    assert sample_8d_report.verify_checksum() is True

    # 3. Tamper test: alter field -> verify failure
    sample_8d_report.severity_score = 9
    assert sample_8d_report.verify_checksum() is False


def test_eight_d_timeline_auto_sort(sample_8d_report):
    evt1 = TimelineEvent(
        event_id="EVT-002",
        timestamp="2023-11-04T09:00:00Z",
        event_type="OPERATOR_ACTION",
        description="Later event",
        equipment_tag="Pump-A12"
    )
    evt2 = TimelineEvent(
        event_id="EVT-001",
        timestamp="2023-11-04T07:00:00Z",
        event_type="BASELINE_NORMAL",
        description="Earlier event",
        equipment_tag="Pump-A12"
    )
    sample_8d_report.timeline = [evt1, evt2]
    # Re-validate
    validated = EightDIncidentReport.model_validate(sample_8d_report.model_dump())
    assert validated.timeline[0].event_id == "EVT-001"
    assert validated.timeline[1].event_id == "EVT-002"


def test_team_formation_empty_leader():
    with pytest.raises(ValidationError):
        TeamFormation(leader="", champion="Champion")


def test_eight_d_severity_score_bounds(sample_8d_report):
    with pytest.raises(ValidationError):
        EightDIncidentReport.model_validate({**sample_8d_report.model_dump(), "severity_score": 0})
    with pytest.raises(ValidationError):
        EightDIncidentReport.model_validate({**sample_8d_report.model_dump(), "severity_score": 11})


def test_eight_d_citation_cross_validation(sample_8d_report):
    # Set a citation ID on node that is not in report citations catalog
    sample_8d_report.citations = []  # Clear citations
    validated = EightDIncidentReport.model_validate(sample_8d_report.model_dump())
    assert validated.d4_root_causes.five_why_chain[0].is_unsubstantiated is True
    assert validated.d4_root_causes.five_why_chain[0].assumed_flag is True


# ==============================================================================
# 11. REQUEST & RESPONSE SCHEMAS TESTS
# ==============================================================================

def test_rca_analyze_request_valid():
    req = RCAAnalyzeRequest(
        asset_tag="Pump-A12",
        symptoms=["mechanical seal failure", "coolant leak", "high vibration"],
        incident_timestamp="2023-11-04T08:30:00Z",
        telemetry_data={"vibration_mm_s": 5.8}
    )
    assert req.asset_tag == "Pump-A12"
    assert len(req.symptoms) == 3


def test_rca_analyze_request_invalid_timestamp():
    with pytest.raises(ValidationError):
        RCAAnalyzeRequest(
            asset_tag="Pump-A12",
            symptoms=["leak"],
            incident_timestamp="invalid-timestamp-string"
        )


def test_export_evidence_request_valid():
    req_html = ExportEvidenceRequest(report_id="8D-2023-PUMP-A12-001", format="html")
    assert req_html.format == "html"
    req_json = ExportEvidenceRequest(report_id="8D-2023-PUMP-A12-001", format="JSON")
    assert req_json.format == "json"


def test_export_evidence_request_invalid_format():
    with pytest.raises(ValidationError):
        ExportEvidenceRequest(report_id="8D-2023-PUMP-A12-001", format="pdf_raw")


def test_export_evidence_response_valid():
    res = ExportEvidenceResponse(
        content="<html><body>Audit Report</body></html>",
        sha256_checksum="a" * 64,
        filename="8D-2023-PUMP-A12-001_Audit_Package.html"
    )
    assert res.sha256_checksum == "a" * 64


# ==============================================================================
# 12. JSON SCHEMA EXPORT TEST (ALL 17 SCHEMAS)
# ==============================================================================

def test_all_17_schemas_json_schema_export():
    schemas_to_test = [
        CitationObject,
        TimelineEvent,
        FiveWhyNode,
        FishboneBranch,
        FishboneAnalysis,
        HistoricalMatch,
        OEMDeviation,
        ContainmentAction,
        CorrectiveAction,
        ValidationPlan,
        PreventativeControls,
        TeamFormation,
        ProblemDescription,
        EightDIncidentReport,
        RCAAnalyzeRequest,
        ExportEvidenceRequest,
        ExportEvidenceResponse,
    ]
    assert len(schemas_to_test) == 17

    for model in schemas_to_test:
        schema = model.model_json_schema()
        assert isinstance(schema, dict), f"{model.__name__} failed to produce dict schema"
        assert "properties" in schema, f"{model.__name__} schema missing 'properties'"
        assert "title" in schema, f"{model.__name__} schema missing 'title'"
