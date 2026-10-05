"""
E2E RCA Test Suite Fixtures and Contract Test Harness.
Automated Root Cause Analysis (RCA) & 8D Incident Report Studio.

This module provides offline, standalone test fixtures, contract-conforming
Pydantic v2 domain schemas, pure-Python reference engines, and a mock FastAPI
TestClient for opaque-box testing of Features F1 through F10.
Runs completely offline with zero external network or Gemini API dependencies.
"""

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import pytest
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field, model_validator


# ==============================================================================
# 1. CONTRACT DOMAIN MODELS (AIAG 8D / ISO 9001:2015 / IATF 16949 / FMEA)
# ==============================================================================

class SeverityLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ActionStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    IMPLEMENTED = "IMPLEMENTED"
    VERIFIED = "VERIFIED"
    CLOSED = "CLOSED"


class FishboneCategory(str, Enum):
    MAN = "MAN"
    MACHINE = "MACHINE"
    MATERIAL = "MATERIAL"
    METHOD = "METHOD"
    MEASUREMENT = "MEASUREMENT"
    ENVIRONMENT = "ENVIRONMENT"


class EventType(str, Enum):
    BASELINE_NORMAL = "BASELINE_NORMAL"
    ANOMALY_DETECTED = "ANOMALY_DETECTED"
    ALERT_TRIGGERED = "ALERT_TRIGGERED"
    ALARM_IGNORED = "ALARM_IGNORED"
    THRESHOLD_EXCEEDED = "THRESHOLD_EXCEEDED"
    FAILURE_ONSET = "FAILURE_ONSET"
    CATASTROPHIC_FAILURE = "CATASTROPHIC_FAILURE"
    EMERGENCY_SHUTDOWN = "EMERGENCY_SHUTDOWN"
    CONTAINMENT_INITIATED = "CONTAINMENT_INITIATED"
    CONTAINMENT_ACHIEVED = "CONTAINMENT_ACHIEVED"
    POST_INCIDENT_INSPECTION = "POST_INCIDENT_INSPECTION"


class SignOffStatus(str, Enum):
    APPROVED = "APPROVED"
    CONDITIONAL = "CONDITIONAL"
    REJECTED = "REJECTED"
    PENDING_REVIEW = "PENDING_REVIEW"


class CitationObject(BaseModel):
    citation_id: str = Field(
        ...,
        description="Unique citation identifier e.g. CITE-PUMP-001",
        pattern=r"^CITE-[A-Za-z0-9_\-\.]+$",
    )
    source_doc: str = Field(..., description="Document filename e.g. Near_Miss_Report_2023.txt")
    title: str = Field(..., description="Human-readable title")
    section: Optional[str] = Field(None, description="Section heading")
    page_or_line: Optional[str] = Field(None, description="Line/page indicator")
    excerpt: str = Field(..., min_length=5, description="Verbatim text snippet")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class FailureTimelineEvent(BaseModel):
    event_id: str = Field(..., description="Unique event identifier")
    timestamp: datetime = Field(..., description="ISO-8601 UTC timestamp")
    event_type: EventType = Field(..., description="Event category")
    description: str = Field(..., min_length=5)
    equipment_tag: str = Field(...)
    telemetry_values: Dict[str, Union[float, int, str, bool]] = Field(default_factory=dict)
    source_citation_id: Optional[str] = Field(None)
    is_unsubstantiated: bool = Field(default=False)

    @model_validator(mode="after")
    def validate_citation_grounding(self):
        if not self.source_citation_id:
            self.is_unsubstantiated = True
        return self


class FiveWhyNode(BaseModel):
    node_id: str = Field(..., description="Node ID e.g. WHY-1")
    level: int = Field(..., ge=1, le=10)
    cause_statement: str = Field(..., min_length=5)
    parent_node_id: Optional[str] = Field(None)
    evidence_citation_ids: List[str] = Field(default_factory=list)
    is_root_cause: bool = Field(default=False)
    is_unsubstantiated: bool = Field(default=False)
    assumed_flag: bool = Field(default=False)
    verification_notes: Optional[str] = Field(None)

    @model_validator(mode="after")
    def enforce_grounding(self):
        if not self.evidence_citation_ids:
            self.is_unsubstantiated = True
            self.assumed_flag = True
        return self


class FishboneCauseItem(BaseModel):
    cause_id: str = Field(..., description="Cause ID e.g. FB-1")
    category: FishboneCategory = Field(...)
    statement: str = Field(..., min_length=5)
    contribution_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence_citation_ids: List[str] = Field(default_factory=list)
    is_unsubstantiated: bool = Field(default=False)

    @model_validator(mode="after")
    def enforce_grounding(self):
        if not self.evidence_citation_ids:
            self.is_unsubstantiated = True
        return self


class RPNScoring(BaseModel):
    severity: int = Field(..., ge=1, le=10)
    occurrence: int = Field(..., ge=1, le=10)
    detection: int = Field(..., ge=1, le=10)
    rpn: int = Field(default=0, ge=0, le=1000)
    revised_severity: Optional[int] = Field(None, ge=1, le=10)
    revised_occurrence: Optional[int] = Field(None, ge=1, le=10)
    revised_detection: Optional[int] = Field(None, ge=1, le=10)
    revised_rpn: Optional[int] = Field(None, ge=0, le=1000)
    risk_priority: str = Field(default="LOW")

    @model_validator(mode="after")
    def calculate_rpn_metrics(self):
        self.rpn = self.severity * self.occurrence * self.detection
        if self.revised_severity and self.revised_occurrence and self.revised_detection:
            self.revised_rpn = self.revised_severity * self.revised_occurrence * self.revised_detection
        if self.rpn >= 350 or self.severity == 10:
            self.risk_priority = "CRITICAL"
        elif self.rpn >= 200 or self.severity >= 8:
            self.risk_priority = "HIGH"
        elif self.rpn >= 100:
            self.risk_priority = "MEDIUM"
        else:
            self.risk_priority = "LOW"
        return self


class HistoricalMatchResult(BaseModel):
    matched_report_id: str = Field(...)
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    equipment_family: str = Field(...)
    matching_symptoms: List[str] = Field(...)
    recurring_risk_assessment: str = Field(...)
    historical_lessons: List[str] = Field(default_factory=list)
    source_doc_citation_id: Optional[str] = Field(None)


class OEMOperatingEnvelope(BaseModel):
    oem_parameter: str = Field(...)
    unit: str = Field(...)
    envelope_min: Optional[float] = Field(None)
    envelope_max: float = Field(...)
    incident_value: float = Field(...)
    deviation_pct: float = Field(default=0.0)
    severity_level: SeverityLevel = Field(default=SeverityLevel.LOW)
    recommended_action: str = Field(...)

    @model_validator(mode="after")
    def compute_deviation(self):
        if self.envelope_max > 0:
            self.deviation_pct = round(((self.incident_value - self.envelope_max) / self.envelope_max) * 100.0, 2)
            if self.deviation_pct > 15.0:
                self.severity_level = SeverityLevel.CRITICAL
            elif self.deviation_pct > 0.0:
                self.severity_level = SeverityLevel.HIGH
            else:
                self.severity_level = SeverityLevel.LOW
        else:
            self.deviation_pct = 0.0
            self.severity_level = SeverityLevel.LOW
        return self


class TeamMember(BaseModel):
    member_id: str = Field(...)
    name: str = Field(...)
    role: str = Field(...)
    department: str = Field(...)
    contact: Optional[str] = Field(None)


class ProblemDescription5W2H(BaseModel):
    incident_title: str = Field(..., min_length=5)
    equipment_tag: str = Field(...)
    equipment_family: str = Field(...)
    timestamp_incident: datetime = Field(...)
    who_detected: str = Field(...)
    what_symptom: str = Field(...)
    where_location: str = Field(...)
    when_detected: str = Field(...)
    why_consequence: str = Field(...)
    how_detected: str = Field(...)
    how_much_magnitude: str = Field(...)
    initial_severity: int = Field(..., ge=1, le=10)
    operational_impact: str = Field(...)
    is_not_analysis: Dict[str, str] = Field(default_factory=dict)


class InterimContainmentAction(BaseModel):
    action_id: str = Field(...)
    description: str = Field(..., min_length=5)
    responsible_owner: str = Field(...)
    implementation_date: datetime = Field(...)
    verification_method: str = Field(...)
    effectiveness_pct: float = Field(..., ge=0.0, le=100.0)
    status: ActionStatus = Field(default=ActionStatus.OPEN)
    evidence_citation_id: Optional[str] = Field(None)


class RootCauseDiscipline(BaseModel):
    occurrence_root_cause: str = Field(..., min_length=10)
    escape_root_cause: str = Field(..., min_length=10)
    five_why_chain: List[FiveWhyNode] = Field(..., min_length=1)
    fishbone_analysis: List[FishboneCauseItem] = Field(..., min_length=1)
    citations: List[CitationObject] = Field(default_factory=list)
    citation_grounding_ratio: float = Field(default=0.0, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_grounding(self):
        known_cites = {c.citation_id for c in self.citations}
        total_causes = len(self.five_why_chain) + len(self.fishbone_analysis)
        grounded = 0
        for node in self.five_why_chain:
            valid_cites = [cid for cid in node.evidence_citation_ids if cid in known_cites]
            if not valid_cites:
                node.is_unsubstantiated = True
                node.assumed_flag = True
            else:
                node.is_unsubstantiated = False
                node.assumed_flag = False
                grounded += 1

        for item in self.fishbone_analysis:
            valid_cites = [cid for cid in item.evidence_citation_ids if cid in known_cites]
            if not valid_cites:
                item.is_unsubstantiated = True
            else:
                item.is_unsubstantiated = False
                grounded += 1

        if total_causes > 0:
            self.citation_grounding_ratio = round(grounded / total_causes, 4)
        return self


class PermanentCorrectiveAction(BaseModel):
    pca_id: str = Field(...)
    description: str = Field(..., min_length=5)
    addresses_cause_id: str = Field(...)
    responsible_owner: str = Field(...)
    target_date: datetime = Field(...)
    feasibility_score: int = Field(..., ge=1, le=10)
    risk_assessment: str = Field(...)
    validation_plan: str = Field(...)
    status: ActionStatus = Field(default=ActionStatus.OPEN)


class ImplementAndValidate(BaseModel):
    action_id: str = Field(...)
    pca_id: str = Field(...)
    actual_implementation_date: Optional[datetime] = Field(None)
    baseline_metric: str = Field(...)
    post_implementation_metric: str = Field(...)
    verification_evidence: str = Field(...)
    validation_status: ActionStatus = Field(...)
    verified_by: Optional[str] = Field(None)


class PreventativeControl(BaseModel):
    control_id: str = Field(...)
    control_type: str = Field(...)
    description: str = Field(..., min_length=5)
    document_reference: Optional[str] = Field(None)
    target_completion_date: datetime = Field(...)
    oem_envelope_adjustments: List[OEMOperatingEnvelope] = Field(default_factory=list)
    horizontal_deployment_assets: List[str] = Field(default_factory=list)
    status: ActionStatus = Field(default=ActionStatus.OPEN)


class TeamSignOff(BaseModel):
    signoff_id: str = Field(...)
    approver_name: str = Field(...)
    approver_role: str = Field(...)
    signoff_status: SignOffStatus = Field(default=SignOffStatus.PENDING_REVIEW)
    signoff_date: datetime = Field(...)
    signature_hash: Optional[str] = Field(None)
    recognition_notes: Optional[str] = Field(None)
    lessons_learned_summary: str = Field(..., min_length=10)
    financial_impact_total_usd: Optional[float] = Field(None)
    downtime_hours_total: Optional[float] = Field(None)


class AuditMetadata(BaseModel):
    sha256_checksum: str = Field(default="")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    generator_system: str = Field(default="Industrial Mind OS v2.0 RCA-8D Engine")
    compliance_standard: str = Field(
        default="ISO 9001:2015 Clause 10.2 / IATF 16949 Section 10.2.3 / AIAG 8D"
    )


class EightDIncidentReport(BaseModel):
    report_id: str = Field(..., pattern=r"^8D-[0-9]{4}-[A-Za-z0-9_\-]+$")
    schema_version: str = Field(default="1.0.0")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    d1_team: List[TeamMember] = Field(..., min_length=1)
    d2_problem: ProblemDescription5W2H = Field(...)
    d3_containment: List[InterimContainmentAction] = Field(..., min_length=1)
    d4_root_cause: RootCauseDiscipline = Field(...)
    d5_permanent_actions: List[PermanentCorrectiveAction] = Field(..., min_length=1)
    d6_validation: List[ImplementAndValidate] = Field(...)
    d7_prevention: List[PreventativeControl] = Field(...)
    d8_closure: TeamSignOff = Field(...)

    timeline: List[FailureTimelineEvent] = Field(..., min_length=1)
    rpn_scoring: RPNScoring = Field(...)
    historical_matches: List[HistoricalMatchResult] = Field(default_factory=list)
    audit_metadata: AuditMetadata = Field(default_factory=AuditMetadata)

    def compute_audit_hash(self) -> str:
        data_copy = self.model_dump(exclude={"audit_metadata": {"sha256_checksum"}}, mode="json")
        canonical_str = json.dumps(data_copy, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()
        self.audit_metadata.sha256_checksum = digest
        return digest


class RCAAnalyzeRequest(BaseModel):
    asset_tag: str
    symptoms: List[str] = Field(..., min_length=1)
    incident_timestamp: str
    telemetry_data: Optional[Dict[str, Any]] = None


class HistoricalMatchRequest(BaseModel):
    asset_tag: str
    symptoms: List[str]
    telemetry_features: Optional[Dict[str, Any]] = None


class ExportEvidenceRequest(BaseModel):
    report_id: str
    format: str = "html"


class ExportEvidenceResponse(BaseModel):
    content: str
    sha256_checksum: str
    filename: str


class EightDIncidentReportSummary(BaseModel):
    report_id: str
    incident_title: str
    asset_tag: str
    severity_score: int
    rpn_score: int
    created_at: str
    sha256_checksum: str


# ==============================================================================
# 2. REFERENCE DEDUCTIVE RCA & INGESTION ENGINES
# ==============================================================================

def reconstruct_timeline(raw_events: List[Dict[str, Any]]) -> List[FailureTimelineEvent]:
    """Sorts events chronologically and instantiates FailureTimelineEvent models."""
    parsed_events = []
    for evt in raw_events:
        ts = evt["timestamp"]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        parsed_events.append(
            FailureTimelineEvent(
                event_id=evt["event_id"],
                timestamp=ts,
                event_type=evt.get("event_type", EventType.ANOMALY_DETECTED),
                description=evt["description"],
                equipment_tag=evt["equipment_tag"],
                telemetry_values=evt.get("telemetry_values", {}),
                source_citation_id=evt.get("source_citation_id"),
            )
        )
    return sorted(parsed_events, key=lambda e: e.timestamp)


def compute_oem_deviation(
    parameter_name: str,
    unit: str,
    envelope_max: float,
    incident_value: float,
    recommended_action: str = "Inspect system",
) -> OEMOperatingEnvelope:
    """Computes OEM envelope percentage deviation and assigns severity."""
    return OEMOperatingEnvelope(
        oem_parameter=parameter_name,
        unit=unit,
        envelope_max=envelope_max,
        incident_value=incident_value,
        recommended_action=recommended_action,
    )


def match_historical_records(
    asset_tag: str, symptoms: List[str], near_miss_text: str
) -> List[HistoricalMatchResult]:
    """Matches symptoms and equipment tags against near miss records."""
    matches = []
    # Normalize strings for comparison
    text_lower = near_miss_text.lower()
    tag_lower = asset_tag.lower()
    
    matched_symptoms = [s for s in symptoms if s.lower() in text_lower]
    
    score = 0.0
    if tag_lower in text_lower:
        score += 0.5
    if symptoms:
        score += 0.5 * (len(matched_symptoms) / len(symptoms))
        
    score = min(round(score, 2), 1.0)
    
    if score >= 0.3:
        matches.append(
            HistoricalMatchResult(
                matched_report_id="NM-2023-PUMP-A12",
                similarity_score=score,
                equipment_family="A-Series Centrifugal Pump",
                matching_symptoms=matched_symptoms or symptoms[:2],
                recurring_risk_assessment="High risk of repeat ceramic seal fracture under sustained vibration > 5.0 mm/s.",
                historical_lessons=[
                    "Strict adherence to 5.0 mm/s OEM manual limit",
                    "Mandatory automated shutdown trip at 5.5 mm/s",
                    "Operator retraining on equipment-specific envelope guidelines",
                ],
                source_doc_citation_id="CITE-NM-2023-01",
            )
        )
    return matches


def build_audit_html(report: EightDIncidentReport) -> str:
    """Renders print-ready compliance audit HTML package with SHA-256 seal."""
    hash_val = report.audit_metadata.sha256_checksum or report.compute_audit_hash()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>8D Compliance Audit Package - {report.report_id}</title>
  <style>
    @page {{ size: letter portrait; margin: 15mm 18mm; }}
    @media print {{ body {{ font-family: sans-serif; }} }}
    .audit-header {{ border: 2px solid #1e3a8a; padding: 12px; margin-bottom: 20px; }}
    .sha-seal {{ font-family: monospace; background: #f1f5f9; padding: 4px; }}
  </style>
</head>
<body>
  <div class="audit-header" data-checksum="{hash_val}">
    <h1>8D INCIDENT COMPLIANCE AUDIT EVIDENCE PACKAGE</h1>
    <p>Report ID: {report.report_id} | Asset: {report.d2_problem.equipment_tag}</p>
    <p class="sha-seal">Certified SHA-256 Checksum: {hash_val}</p>
    <p>Standard: {report.audit_metadata.compliance_standard}</p>
  </div>
  <div class="problem-statement">
    <h2>D2: Problem Description (5W2H)</h2>
    <p><strong>What:</strong> {report.d2_problem.what_symptom}</p>
    <p><strong>Where:</strong> {report.d2_problem.where_location}</p>
    <p><strong>RPN Score:</strong> {report.rpn_scoring.rpn} ({report.rpn_scoring.risk_priority})</p>
  </div>
</body>
</html>"""


# ==============================================================================
# 3. FASTAPI TEST CLIENT HARNESS
# ==============================================================================

@pytest.fixture(scope="session")
def test_app():
    """Initializes isolated FastAPI test harness mounting /api/v1/rca routes."""
    app = FastAPI(title="E2E RCA Studio Test Harness")
    
    # In-memory storage for test reports
    reports_db: Dict[str, EightDIncidentReport] = {}

    @app.post("/api/v1/rca/analyze", response_model=EightDIncidentReport)
    def analyze_rca(req: RCAAnalyzeRequest):
        if not req.asset_tag or not req.symptoms:
            raise HTTPException(status_code=422, detail="Invalid payload: asset_tag and symptoms required")
        
        # Build baseline timeline
        dt = datetime.fromisoformat(req.incident_timestamp.replace("Z", "+00:00"))
        events = [
            FailureTimelineEvent(
                event_id="EVT-01",
                timestamp=dt,
                event_type=EventType.THRESHOLD_EXCEEDED,
                description=f"Incident detected on {req.asset_tag}: {', '.join(req.symptoms)}",
                equipment_tag=req.asset_tag,
                telemetry_values=req.telemetry_data or {"vibration_mm_s": 5.8},
                source_citation_id="CITE-PUMP-001",
            )
        ]
        
        cite = CitationObject(
            citation_id="CITE-PUMP-001",
            source_doc="Near_Miss_Report_2023.txt",
            title="Near Miss Investigation 2023",
            excerpt="Post-incident analysis revealed severe vibration of 5.8 mm/s prior to seal failure.",
            confidence=0.98,
        )
        
        d4 = RootCauseDiscipline(
            occurrence_root_cause=f"High vibration caused structural failure on {req.asset_tag}",
            escape_root_cause="Alarm set too high; missed warning thresholds",
            five_why_chain=[
                FiveWhyNode(
                    node_id="WHY-1",
                    level=1,
                    cause_statement=f"Seal cracked on {req.asset_tag}",
                    evidence_citation_ids=["CITE-PUMP-001"],
                    is_root_cause=False,
                ),
                FiveWhyNode(
                    node_id="WHY-2",
                    level=2,
                    cause_statement="Sustained vibration exceeded ceramic tolerance",
                    evidence_citation_ids=["CITE-PUMP-001"],
                    is_root_cause=True,
                ),
            ],
            fishbone_analysis=[
                FishboneCauseItem(
                    cause_id="FB-1",
                    category=FishboneCategory.MACHINE,
                    statement="Ceramic seal embrittlement under vibration",
                    evidence_citation_ids=["CITE-PUMP-001"],
                )
            ],
            citations=[cite],
        )
        
        rpn = RPNScoring(severity=9, occurrence=7, detection=5)
        
        report = EightDIncidentReport(
            report_id=f"8D-2023-{req.asset_tag.upper().replace('-', '_')}",
            d1_team=[
                TeamMember(
                    member_id="TM-01",
                    name="Elena Rostova",
                    role="Leader",
                    department="Reliability Engineering",
                )
            ],
            d2_problem=ProblemDescription5W2H(
                incident_title=f"Failure Incident on {req.asset_tag}",
                equipment_tag=req.asset_tag,
                equipment_family="Centrifugal Pump",
                timestamp_incident=dt,
                who_detected="Automated SCADA / Shift Operator",
                what_symptom=", ".join(req.symptoms),
                where_location="Sector 4 Loop",
                when_detected="Continuous Operation Shift A",
                why_consequence="Coolant leak and operational downtime",
                how_detected="Vibration sensor and leak detection tray",
                how_much_magnitude="15 liters lost, vibration 5.8 mm/s",
                initial_severity=8,
                operational_impact="2.5 hours total loop shutdown",
            ),
            d3_containment=[
                InterimContainmentAction(
                    action_id="ICA-01",
                    description="Isolate inlet/outlet valves and deploy containment booms",
                    responsible_owner="Shift Supervisor",
                    implementation_date=dt,
                    verification_method="Zero drainage effluent inspection",
                    effectiveness_pct=100.0,
                    status=ActionStatus.VERIFIED,
                    evidence_citation_id="CITE-PUMP-001",
                )
            ],
            d4_root_cause=d4,
            d5_permanent_actions=[
                PermanentCorrectiveAction(
                    pca_id="PCA-01",
                    description="Install automatic DCS shutdown interlock at 5.5 mm/s",
                    addresses_cause_id="WHY-2",
                    responsible_owner="Controls Engineer",
                    target_date=dt,
                    feasibility_score=9,
                    risk_assessment="Low risk of false trip",
                    validation_plan="Simulated sensor trip verification",
                    status=ActionStatus.IMPLEMENTED,
                )
            ],
            d6_validation=[
                ImplementAndValidate(
                    action_id="VAL-01",
                    pca_id="PCA-01",
                    baseline_metric="Vibration 5.8 mm/s alarm delayed",
                    post_implementation_metric="Vibration trip executed in 1.2s",
                    verification_evidence="Test run log TR-994",
                    validation_status=ActionStatus.VERIFIED,
                )
            ],
            d7_prevention=[
                PreventativeControl(
                    control_id="PRV-01",
                    control_type="SOP_UPDATE",
                    description=f"Update SOP-{req.asset_tag} vibration limits to 5.0 mm/s",
                    target_completion_date=dt,
                    status=ActionStatus.CLOSED,
                )
            ],
            d8_closure=TeamSignOff(
                signoff_id="SO-01",
                approver_name="Marcus Vance",
                approver_role="Plant Quality Director",
                signoff_status=SignOffStatus.APPROVED,
                signoff_date=dt,
                lessons_learned_summary="Mandatory equipment envelope limits must be hardwired into DCS.",
            ),
            timeline=events,
            rpn_scoring=rpn,
        )
        report.compute_audit_hash()
        reports_db[report.report_id] = report
        return report

    @app.post("/api/v1/rca/historical-match", response_model=List[HistoricalMatchResult])
    def match_history(req: HistoricalMatchRequest):
        near_miss_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "Near_Miss_Report_2023.txt"
        )
        near_miss_text = ""
        if os.path.exists(near_miss_path):
            with open(near_miss_path, "r", encoding="utf-8") as f:
                near_miss_text = f.read()
        return match_historical_records(req.asset_tag, req.symptoms, near_miss_text)

    @app.post("/api/v1/rca/export-evidence", response_model=ExportEvidenceResponse)
    def export_evidence(req: ExportEvidenceRequest):
        if req.format not in ["html", "json"]:
            raise HTTPException(status_code=400, detail="Unsupported format: must be 'html' or 'json'")
        
        report = reports_db.get(req.report_id)
        if not report:
            # Fallback to demo report for export testing
            req_dummy = RCAAnalyzeRequest(
                asset_tag="Pump-A12",
                symptoms=["mechanical seal failure", "high vibration"],
                incident_timestamp="2023-11-04T08:00:00Z",
            )
            report = analyze_rca(req_dummy)
            reports_db[report.report_id] = report

        if req.format == "json":
            content = json.dumps(report.model_dump(mode="json"), indent=2)
            digest = report.compute_audit_hash()
            filename = f"{report.report_id}_evidence_package.json"
        else:
            content = build_audit_html(report)
            digest = report.audit_metadata.sha256_checksum or report.compute_audit_hash()
            filename = f"{report.report_id}_compliance_audit.html"

        return ExportEvidenceResponse(
            content=content,
            sha256_checksum=digest,
            filename=filename,
        )

    @app.get("/api/v1/rca/reports", response_model=List[EightDIncidentReportSummary])
    def list_reports():
        summaries = []
        for rep in reports_db.values():
            summaries.append(
                EightDIncidentReportSummary(
                    report_id=rep.report_id,
                    incident_title=rep.d2_problem.incident_title,
                    asset_tag=rep.d2_problem.equipment_tag,
                    severity_score=rep.d2_problem.initial_severity,
                    rpn_score=rep.rpn_scoring.rpn,
                    created_at=rep.created_at.isoformat(),
                    sha256_checksum=rep.audit_metadata.sha256_checksum,
                )
            )
        return summaries

    return app


@pytest.fixture(scope="session")
def client(test_app):
    """Provides FastAPI TestClient for E2E API tests."""
    with TestClient(test_app) as c:
        yield c


# ==============================================================================
# 4. FIXTURES FOR INDUSTRIAL EQUIPMENT INCIDENTS & LOGS
# ==============================================================================

@pytest.fixture
def near_miss_report_text():
    """Returns actual text of Near_Miss_Report_2023.txt."""
    path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "Near_Miss_Report_2023.txt")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return """# INCIDENT REPORT & NEAR-MISS RECORD (2023-11-04)
## Equipment Tag: Pump-A12
High vibration of 5.8 mm/s shattered inboard ceramic seals. Maximum limit 5.0 mm/s. Mandatory shutdown 5.5 mm/s."""


@pytest.fixture
def pump_a12_telemetry_logs():
    """Chronological telemetry logs for Pump-A12 ceramic seal failure."""
    return [
        {
            "event_id": "EVT-P01",
            "timestamp": "2023-11-02T08:00:00Z",
            "event_type": EventType.BASELINE_NORMAL,
            "description": "Routine shift start: vibration 4.2 mm/s, bearing temp 54C",
            "equipment_tag": "Pump-A12",
            "telemetry_values": {"vibration_mm_s": 4.2, "bearing_temp_c": 54.0},
            "source_citation_id": "CITE-PUMP-LOG-01",
        },
        {
            "event_id": "EVT-P02",
            "timestamp": "2023-11-02T14:30:00Z",
            "event_type": EventType.THRESHOLD_EXCEEDED,
            "description": "Vibration velocity stepped up to 5.2 mm/s exceeding OEM envelope 5.0 mm/s",
            "equipment_tag": "Pump-A12",
            "telemetry_values": {"vibration_mm_s": 5.2, "bearing_temp_c": 62.1},
            "source_citation_id": "CITE-PUMP-LOG-02",
        },
        {
            "event_id": "EVT-P03",
            "timestamp": "2023-11-03T10:15:00Z",
            "event_type": EventType.ALARM_IGNORED,
            "description": "SCADA advisory alarm triggered at 5.8 mm/s. Ignored due to mistaken 6.5 mm/s threshold assumption",
            "equipment_tag": "Pump-A12",
            "telemetry_values": {"vibration_mm_s": 5.8, "bearing_temp_c": 74.5},
            "source_citation_id": "CITE-PUMP-LOG-03",
        },
        {
            "event_id": "EVT-P04",
            "timestamp": "2023-11-04T07:45:00Z",
            "event_type": EventType.CATASTROPHIC_FAILURE,
            "description": "Inboard ceramic seal shattered; coolant leak detected on floor",
            "equipment_tag": "Pump-A12",
            "telemetry_values": {"vibration_mm_s": 6.4, "leak_flow_l_min": 1.2},
            "source_citation_id": "CITE-PUMP-LOG-04",
        },
        {
            "event_id": "EVT-P05",
            "timestamp": "2023-11-04T08:00:00Z",
            "event_type": EventType.CONTAINMENT_ACHIEVED,
            "description": "Emergency response team isolated valves and deployed catch basins in 15 min",
            "equipment_tag": "Pump-A12",
            "telemetry_values": {"vibration_mm_s": 0.0, "coolant_spill_liters": 15.0},
            "source_citation_id": "CITE-PUMP-LOG-05",
        },
    ]


@pytest.fixture
def steam_turbine_telemetry_logs():
    """Chronological telemetry logs for steam turbine overspeed incident."""
    return [
        {
            "event_id": "EVT-T01",
            "timestamp": "2024-03-12T02:00:00Z",
            "event_type": EventType.BASELINE_NORMAL,
            "description": "Turbine running nominal 3,000 RPM, lube oil 3.2 bar",
            "equipment_tag": "TURB-ST-04",
            "telemetry_values": {"rpm": 3000, "lube_oil_bar": 3.2, "bearing_temp_c": 68.0},
            "source_citation_id": "CITE-TURB-01",
        },
        {
            "event_id": "EVT-T02",
            "timestamp": "2024-03-12T02:40:00Z",
            "event_type": EventType.ANOMALY_DETECTED,
            "description": "Lube oil filter DP alarm; pressure dropped to 1.1 bar",
            "equipment_tag": "TURB-ST-04",
            "telemetry_values": {"rpm": 3005, "lube_oil_bar": 1.1, "bearing_temp_c": 88.0},
            "source_citation_id": "CITE-TURB-02",
        },
        {
            "event_id": "EVT-T03",
            "timestamp": "2024-03-12T02:48:00Z",
            "event_type": EventType.THRESHOLD_EXCEEDED,
            "description": "Journal bearing temperature spiked to 118C (envelope max 95C)",
            "equipment_tag": "TURB-ST-04",
            "telemetry_values": {"rpm": 3220, "lube_oil_bar": 0.8, "bearing_temp_c": 118.0},
            "source_citation_id": "CITE-TURB-03",
        },
        {
            "event_id": "EVT-T04",
            "timestamp": "2024-03-12T02:51:00Z",
            "event_type": EventType.EMERGENCY_SHUTDOWN,
            "description": "Overspeed trip actuated at 3,450 RPM (limit 3,300 RPM); governor trip executed",
            "equipment_tag": "TURB-ST-04",
            "telemetry_values": {"rpm": 3450, "trip_actuation_ms": 320},
            "source_citation_id": "CITE-TURB-04",
        },
    ]


@pytest.fixture
def boiler_thermal_runaway_logs():
    """Chronological telemetry logs for boiler thermocouple drift incident."""
    return [
        {
            "event_id": "EVT-B01",
            "timestamp": "2024-06-15T12:00:00Z",
            "event_type": EventType.BASELINE_NORMAL,
            "description": "Superheater indicated temperature 410C on DCS",
            "equipment_tag": "BLR-HP-101",
            "telemetry_values": {"dcs_temp_c": 410.0, "steam_pressure_bar": 88.0},
            "source_citation_id": "CITE-BLR-01",
        },
        {
            "event_id": "EVT-B02",
            "timestamp": "2024-06-15T16:00:00Z",
            "event_type": EventType.ALERT_TRIGGERED,
            "description": "Acoustic soot-blower sensor alerted to anomalous tube metal stress",
            "equipment_tag": "BLR-HP-101",
            "telemetry_values": {"acoustic_stress_khz": 44.2},
            "source_citation_id": "CITE-BLR-02",
        },
        {
            "event_id": "EVT-B03",
            "timestamp": "2024-06-15T18:30:00Z",
            "event_type": EventType.THRESHOLD_EXCEEDED,
            "description": "Pyrometer handheld check revealed actual tube metal 452C vs limit 430C (-42C TC drift)",
            "equipment_tag": "BLR-HP-101",
            "telemetry_values": {"actual_tube_temp_c": 452.0, "cal_drift_c": -42.0},
            "source_citation_id": "CITE-BLR-03",
        },
        {
            "event_id": "EVT-B04",
            "timestamp": "2024-06-15T19:00:00Z",
            "event_type": EventType.POST_INCIDENT_INSPECTION,
            "description": "Borescope confirmed superheater tube wall bulging due to thermal creep",
            "equipment_tag": "BLR-HP-101",
            "telemetry_values": {"bulge_diameter_mm": 54.2, "nominal_od_mm": 50.8},
            "source_citation_id": "CITE-BLR-04",
        },
    ]
