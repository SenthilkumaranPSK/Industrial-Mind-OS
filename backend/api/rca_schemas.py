"""
Industrial Mind OS - Automated Root Cause Analysis (RCA) & 8D Studio Schemas
Authoritative Pydantic v2 Domain Models

Compliant with AIAG 8D, ISO 9001:2015 Clause 10.2, IATF 16949 Section 10.2.3,
and AIAG-VDA FMEA standards.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


# ==============================================================================
# ENUMS & CONSTANTS
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
    MAN = "Man"
    MACHINE = "Machine"
    MATERIAL = "Material"
    METHOD = "Method"
    MEASUREMENT = "Measurement"
    ENVIRONMENT = "Environment"


class EventType(str, Enum):
    BASELINE_NORMAL = "BASELINE_NORMAL"
    TELEMETRY_ALARM = "TELEMETRY_ALARM"
    OPERATOR_ACTION = "OPERATOR_ACTION"
    SYSTEM_FAILURE = "SYSTEM_FAILURE"
    MAINTENANCE_LOG = "MAINTENANCE_LOG"
    ANOMALY_DETECTED = "ANOMALY_DETECTED"
    THRESHOLD_EXCEEDED = "THRESHOLD_EXCEEDED"
    EMERGENCY_SHUTDOWN = "EMERGENCY_SHUTDOWN"
    CONTAINMENT_INITIATED = "CONTAINMENT_INITIATED"
    CONTAINMENT_ACHIEVED = "CONTAINMENT_ACHIEVED"


class SignOffStatus(str, Enum):
    APPROVED = "APPROVED"
    CONDITIONAL = "CONDITIONAL"
    REJECTED = "REJECTED"
    PENDING_REVIEW = "PENDING_REVIEW"


# ==============================================================================
# 1. CITATIONS & EVIDENCE GROUNDING
# ==============================================================================

class CitationObject(BaseModel):
    """
    Verifiable document citation linking an assertion to industrial documentation.
    """
    model_config = ConfigDict(extra="ignore")

    citation_id: str = Field(
        ...,
        description="Unique citation identifier e.g. CITE-PUMP-001",
        pattern=r"^CITE-[A-Za-z0-9_\-\.]+$",
    )
    source_doc: str = Field(..., description="Source document filename or path")
    excerpt: str = Field(..., min_length=3, description="Verbatim text snippet supporting claim")
    section: Optional[str] = Field(None, description="Section heading or clause")
    page_or_line: Optional[str] = Field(None, description="Line number or page indicator")
    title: Optional[str] = Field("", description="Human-readable title of source document")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Extraction confidence score [0.0, 1.0]")

    @field_validator("excerpt")
    @classmethod
    def validate_excerpt_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Excerpt cannot be empty or whitespace only")
        return v.strip()


# ==============================================================================
# 2. TIMELINE EVENT
# ==============================================================================

class TimelineEvent(BaseModel):
    """
    Chronological event logged during incident onset, propagation, and containment.
    """
    model_config = ConfigDict(extra="ignore")

    event_id: str = Field(..., description="Unique event identifier e.g. EVT-001")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp")
    event_type: str = Field(..., description="Event classification e.g. TELEMETRY_ALARM, OPERATOR_ACTION")
    description: str = Field(..., min_length=3, description="Narrative description of what occurred")
    equipment_tag: str = Field(..., description="Equipment tag identifier e.g. Pump-A12")
    citation_ids: List[str] = Field(default_factory=list, description="Associated citation IDs")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Sensor telemetry or event parameters")
    source_citation_id: Optional[str] = Field(None, description="Single citation ID fallback")
    is_unsubstantiated: bool = Field(default=False, description="Flag indicating lack of citation")

    @field_validator("timestamp", mode="before")
    @classmethod
    def validate_iso_timestamp(cls, v: Any) -> str:
        if isinstance(v, datetime):
            dt = v if v.tzinfo else v.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        if isinstance(v, str):
            try:
                dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
                return dt.isoformat()
            except Exception as e:
                raise ValueError(f"Invalid ISO 8601 timestamp '{v}': {e}")
        raise ValueError(f"Timestamp must be string or datetime, got {type(v)}")

    @model_validator(mode="before")
    @classmethod
    def sync_pre_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Map telemetry_values to parameters if provided
            if "telemetry_values" in data and "parameters" not in data:
                data["parameters"] = data["telemetry_values"]
        return data

    @model_validator(mode="after")
    def sync_citations_and_grounding(self):
        if self.source_citation_id and self.source_citation_id not in self.citation_ids:
            self.citation_ids.append(self.source_citation_id)
        if not self.citation_ids:
            self.is_unsubstantiated = True
        else:
            self.is_unsubstantiated = False
        return self


# ==============================================================================
# 3. 5-WHY NODE
# ==============================================================================

class FiveWhyNode(BaseModel):
    """
    A single node in the deductive 5-Why causal tree.
    """
    model_config = ConfigDict(extra="ignore")

    why_id: str = Field(..., description="Unique node identifier e.g. WHY-1")
    level: int = Field(..., ge=1, le=10, description="Deductive depth level (1 to 10)")
    cause_statement: str = Field(..., min_length=3, description="Answer to 'Why did this occur?'")
    parent_node_id: Optional[str] = Field(None, description="Parent node ID in causal tree")
    citation_ids: List[str] = Field(default_factory=list, description="Citations substantiating this cause")
    evidence_citation_ids: Optional[List[str]] = Field(None, description="Alias for citation_ids")
    is_root_cause: bool = Field(default=False, description="True if this is a terminal root cause")
    is_unsubstantiated: bool = Field(default=False, description="True if no citation verifies this node")
    assumed_flag: bool = Field(default=False, description="Flag indicating unverified engineering assumption")
    assumption_flag: Optional[bool] = Field(None, description="Alias for assumed_flag")
    verification_notes: Optional[str] = Field(None, description="Investigative notes or field checks")

    @model_validator(mode="before")
    @classmethod
    def sync_pre_citations(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "evidence_citation_ids" in data and "citation_ids" not in data:
                data["citation_ids"] = data.get("evidence_citation_ids") or []
        return data

    @model_validator(mode="after")
    def enforce_grounding(self):
        # Sync citation_ids and evidence_citation_ids
        if self.evidence_citation_ids and not self.citation_ids:
            self.citation_ids = list(self.evidence_citation_ids)
        elif self.citation_ids and not self.evidence_citation_ids:
            self.evidence_citation_ids = list(self.citation_ids)

        if not self.citation_ids:
            self.is_unsubstantiated = True
            self.assumed_flag = True
            self.assumption_flag = True
        else:
            self.is_unsubstantiated = False
            self.assumed_flag = False
            self.assumption_flag = False
        return self


# ==============================================================================
# 4. FISHBONE BRANCH & ANALYSIS (ISHIKAWA 6M)
# ==============================================================================

class FishboneBranch(BaseModel):
    """
    A single branch in the Ishikawa 6M fishbone diagram.
    """
    model_config = ConfigDict(extra="ignore")

    category: str = Field(..., description="One of Man, Machine, Material, Method, Measurement, Environment")
    causes: List[str] = Field(default_factory=list, description="Contributing causal statements")
    citation_ids: List[str] = Field(default_factory=list, description="Citation IDs backing this branch")
    evidence_citation_ids: Optional[List[str]] = Field(None, description="Alias for citation_ids")
    is_unsubstantiated: bool = Field(default=False, description="True if branch lacks citations")

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        valid_map = {
            "man": "Man",
            "machine": "Machine",
            "material": "Material",
            "method": "Method",
            "measurement": "Measurement",
            "environment": "Environment",
            "milieu": "Environment",
        }
        normalized = valid_map.get(v.strip().lower())
        if not normalized:
            raise ValueError(f"Invalid Fishbone category '{v}'. Must be one of {list(valid_map.values())}")
        return normalized

    @model_validator(mode="before")
    @classmethod
    def sync_pre_citations(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "evidence_citation_ids" in data and "citation_ids" not in data:
                data["citation_ids"] = data.get("evidence_citation_ids") or []
        return data

    @model_validator(mode="after")
    def enforce_grounding(self):
        if self.evidence_citation_ids and not self.citation_ids:
            self.citation_ids = list(self.evidence_citation_ids)
        elif self.citation_ids and not self.evidence_citation_ids:
            self.evidence_citation_ids = list(self.citation_ids)

        if not self.citation_ids and len(self.causes) > 0:
            self.is_unsubstantiated = True
        else:
            self.is_unsubstantiated = False
        return self


class FishboneAnalysis(BaseModel):
    """
    Ishikawa 6M fishbone diagram containing branches.
    """
    model_config = ConfigDict(extra="ignore")

    branches: List[FishboneBranch] = Field(default_factory=list, description="6M branches")

    def get_branch(self, category: str) -> Optional[FishboneBranch]:
        cat_lower = category.strip().lower()
        for b in self.branches:
            if b.category.lower() == cat_lower:
                return b
        return None


# ==============================================================================
# 5. HISTORICAL MATCH & OEM DEVIATION
# ==============================================================================

class HistoricalMatch(BaseModel):
    """
    Cross-referenced historical near-miss or prior incident match.
    """
    model_config = ConfigDict(extra="ignore")

    matched_report_id: str = Field(..., description="Matched historical report identifier")
    title: str = Field(..., description="Title of historical incident")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Semantic similarity score [0.0, 1.0]")
    matching_symptoms: List[str] = Field(default_factory=list, description="Shared failure symptoms")
    preventative_recommendations: List[str] = Field(default_factory=list, description="Lessons learned and actions")
    equipment_family: Optional[str] = Field("Centrifugal Pump", description="Equipment classification")
    recurring_risk_assessment: Optional[str] = Field(None, description="Risk narrative concerning recurrence")
    source_doc_citation_id: Optional[str] = Field(None, description="Citation ID pointing to historical record")


class OEMDeviation(BaseModel):
    """
    Comparison of incident telemetry against OEM manufacturer design boundaries.
    """
    model_config = ConfigDict(extra="ignore")

    parameter_name: str = Field(..., description="Parameter name e.g. Peak Vibration Velocity")
    oem_envelope_limit: float = Field(..., description="OEM upper safe operating boundary")
    actual_incident_value: float = Field(..., description="Observed peak value during incident")
    deviation_percent: float = Field(default=0.0, description="Percentage exceedance over OEM limit")
    unit: str = Field(..., description="Measurement engineering unit e.g. mm/s")
    is_exceeded: bool = Field(default=False, description="True if actual exceeds limit")
    recommended_action: Optional[str] = Field(None, description="Action or interlock threshold recommendation")
    severity_level: SeverityLevel = Field(default=SeverityLevel.LOW, description="Severity rating of deviation")

    @model_validator(mode="after")
    def compute_deviation(self):
        if self.oem_envelope_limit > 0:
            self.deviation_percent = round(
                ((self.actual_incident_value - self.oem_envelope_limit) / self.oem_envelope_limit) * 100.0,
                2,
            )
            self.is_exceeded = self.actual_incident_value > self.oem_envelope_limit
            if self.deviation_percent > 15.0:
                self.severity_level = SeverityLevel.CRITICAL
            elif self.deviation_percent > 0.0:
                self.severity_level = SeverityLevel.HIGH
            else:
                self.severity_level = SeverityLevel.LOW
        else:
            self.deviation_percent = 0.0
            self.is_exceeded = False
            self.severity_level = SeverityLevel.LOW
        return self


# ==============================================================================
# 6. CONTAINMENT ACTION (D3) & CORRECTIVE ACTION (D5)
# ==============================================================================

class ContainmentAction(BaseModel):
    """D3: Interim Containment Action."""
    model_config = ConfigDict(extra="ignore")

    action_id: str = Field(default="ICA-01", description="Containment ID")
    action: str = Field(..., min_length=3, description="Action description")
    verified_effective: bool = Field(default=True, description="Efficacy verification result")
    effectiveness_pct: float = Field(default=100.0, ge=0.0, le=100.0, description="Measured containment efficiency (0-100%)")
    owner: str = Field(..., description="Responsible engineer")
    implementation_date: Optional[str] = Field(None, description="Deployment timestamp")
    verification_method: Optional[str] = Field(None, description="Proof or method of containment verification")
    status: ActionStatus = Field(default=ActionStatus.IMPLEMENTED, description="Status")
    citation_ids: List[str] = Field(default_factory=list, description="Citation IDs")


class CorrectiveAction(BaseModel):
    """D5: Permanent Corrective Action."""
    model_config = ConfigDict(extra="ignore")

    pca_id: str = Field(default="PCA-01", description="Corrective Action ID")
    action: str = Field(..., min_length=3, description="Permanent action description")
    target_cause_id: Optional[str] = Field(None, description="Root cause ID addressed")
    owner: str = Field(..., description="Action owner")
    target_date: Optional[str] = Field(None, description="Target completion date")
    feasibility_score: int = Field(default=5, ge=1, le=10, description="Feasibility rating (1-10)")
    risk_assessment: Optional[str] = Field(None, description="Side effects or risk evaluation")
    validation_plan: Optional[str] = Field(None, description="Efficacy validation protocol")
    status: ActionStatus = Field(default=ActionStatus.OPEN, description="Execution status")


# ==============================================================================
# 7. VALIDATION PLAN (D6) & PREVENTATIVE CONTROLS (D7)
# ==============================================================================

class ValidationPlan(BaseModel):
    """D6: Implementation & Validation Plan."""
    model_config = ConfigDict(extra="ignore")

    validation_id: str = Field(default="VAL-01", description="Validation plan ID")
    metrics: str = Field(..., min_length=3, description="KPI metrics baseline vs post-fix")
    validation_date: Optional[str] = Field(None, description="Validation completion date")
    status: ActionStatus = Field(default=ActionStatus.IN_PROGRESS, description="Validation status")
    verified_by: Optional[str] = Field(None, description="Sign-off reliability engineer")
    verification_evidence: Optional[str] = Field(None, description="Test telemetry or lab report")


class PreventativeControls(BaseModel):
    """D7: Preventative Controls & Horizontal Read-Across."""
    model_config = ConfigDict(extra="ignore")

    control_id: str = Field(default="PRV-01", description="Control ID")
    sop_updates: List[str] = Field(default_factory=list, description="Updated standard operating procedures")
    pm_updates: List[str] = Field(default_factory=list, description="Preventative maintenance schedule revisions")
    oem_deviations: List[OEMDeviation] = Field(default_factory=list, description="OEM envelope parameter changes")
    historical_matches: List[HistoricalMatch] = Field(default_factory=list, description="Historical near-miss cross references")
    horizontal_assets: List[str] = Field(default_factory=list, description="Sister asset tags (read-across)")
    description: Optional[str] = Field(None, description="Narrative description of preventative controls")
    status: ActionStatus = Field(default=ActionStatus.OPEN, description="Implementation status")


# ==============================================================================
# 8. TEAM FORMATION (D1) & PROBLEM DESCRIPTION (D2)
# ==============================================================================

class TeamFormation(BaseModel):
    """D1: 8D Team Formation."""
    model_config = ConfigDict(extra="ignore")

    leader: str = Field(..., min_length=1, description="Team leader")
    champion: str = Field(..., min_length=1, description="Executive sponsor/champion")
    members: List[str] = Field(default_factory=list, description="Cross-functional team members")
    facilitator: Optional[str] = Field(None, description="RCA Facilitator")
    team_details: Optional[List[Dict[str, Any]]] = Field(None, description="Detailed member contacts and roles")


class ProblemDescription(BaseModel):
    """D2: 5W2H Problem Description."""
    model_config = ConfigDict(extra="ignore")

    what: str = Field(..., min_length=3, description="What failure mode or symptom occurred")
    where: str = Field(..., min_length=3, description="Where did the failure occur (plant/loop/asset)")
    when: str = Field(..., min_length=3, description="When did the failure occur (timestamp/phase)")
    who: str = Field(..., min_length=2, description="Who detected or reported the failure")
    why: str = Field(..., min_length=3, description="Why is it a problem (consequence/loss)")
    how: str = Field(..., min_length=3, description="How was it detected (alarm/inspection)")
    how_many: str = Field(..., min_length=1, description="How many / how much (magnitude/downtime)")
    incident_title: Optional[str] = Field(None, description="Short title headline")
    equipment_tag: Optional[str] = Field(None, description="Asset tag e.g. Pump-A12")
    initial_severity: int = Field(default=5, ge=1, le=10, description="Initial severity rating (1-10)")
    operational_impact: Optional[str] = Field(None, description="Operational downtime impact narrative")
    is_not_analysis: Dict[str, str] = Field(default_factory=dict, description="Is / Is Not stratification matrix")


# ==============================================================================
# 9. ROOT CAUSE ANALYSIS (D4) & TEAM RECOGNITION (D8)
# ==============================================================================

class RootCauseAnalysis(BaseModel):
    """D4: Root Cause Analysis containing 5-Why and Fishbone."""
    model_config = ConfigDict(extra="ignore")

    five_why_chain: List[FiveWhyNode] = Field(..., min_length=1, description="Deductive 5-Why chain")
    fishbone_analysis: FishboneAnalysis = Field(..., description="Ishikawa 6M fishbone analysis")
    occurrence_root_cause: str = Field(..., min_length=5, description="Physical occurrence root cause")
    escape_root_cause: str = Field(..., min_length=5, description="Detection/escape root cause")
    citation_grounding_ratio: float = Field(default=0.0, ge=0.0, le=1.0, description="Proportion of grounded causal assertions")

    @model_validator(mode="after")
    def calculate_grounding_ratio(self):
        total_items = len(self.five_why_chain)
        grounded_items = sum(1 for node in self.five_why_chain if not node.is_unsubstantiated)

        fb_branches = self.fishbone_analysis.branches if hasattr(self.fishbone_analysis, "branches") else []
        for branch in fb_branches:
            if branch.causes:
                total_items += 1
                if not branch.is_unsubstantiated:
                    grounded_items += 1

        if total_items > 0:
            self.citation_grounding_ratio = round(grounded_items / total_items, 4)
        return self


class TeamRecognition(BaseModel):
    """D8: Recognition, Sign-Off & Closure."""
    model_config = ConfigDict(extra="ignore")

    recognition_notes: str = Field(..., min_length=3, description="Commendation recognizing response team")
    approver_name: str = Field(..., min_length=1, description="Approver full name")
    approver_role: str = Field(..., min_length=1, description="Approver title/role")
    signoff_status: SignOffStatus = Field(default=SignOffStatus.APPROVED, description="Approval status")
    signoff_date: Optional[str] = Field(None, description="ISO timestamp of sign-off")
    signature_hash: Optional[str] = Field(None, description="Cryptographic signature digest")
    lessons_learned: Optional[str] = Field(None, description="Institutional takeaways")
    financial_impact_total_usd: Optional[float] = Field(None, description="Total incident cost in USD")
    downtime_hours_total: Optional[float] = Field(None, description="Total hours downtime")


# ==============================================================================
# 10. MASTER 8D INCIDENT REPORT
# ==============================================================================

class EightDIncidentReport(BaseModel):
    """
    Master Eight Disciplines (8D) Incident Report Schema.
    """
    model_config = ConfigDict(extra="ignore")

    report_id: str = Field(
        ...,
        description="Unique 8D Incident Report ID e.g. 8D-2023-PUMP-A12-001",
        pattern=r"^8D-[0-9]{4}-[A-Za-z0-9_\-]+$",
    )
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    asset_tag: str = Field(..., description="Target equipment tag e.g. Pump-A12")
    severity_score: int = Field(..., ge=1, le=10, description="Severity score (1-10)")
    occurrence_score: int = Field(default=5, ge=1, le=10, description="Occurrence score (1-10)")
    detection_score: int = Field(default=5, ge=1, le=10, description="Detection score (1-10)")
    rpn_score: int = Field(default=0, ge=0, le=1000, description="Risk Priority Number (S*O*D)")

    d1_team: TeamFormation = Field(..., description="D1: Team Formation")
    d2_problem: ProblemDescription = Field(..., description="D2: Problem Description")
    d3_containment: List[ContainmentAction] = Field(..., min_length=1, description="D3: Containment Actions")
    d4_root_causes: RootCauseAnalysis = Field(..., description="D4: Root Cause Analysis")
    d5_permanent_actions: List[CorrectiveAction] = Field(..., min_length=1, description="D5: Corrective Actions")
    d6_validation: ValidationPlan = Field(..., description="D6: Validation Plan")
    d7_preventative_controls: PreventativeControls = Field(..., description="D7: Preventative Controls")
    d8_recognition: TeamRecognition = Field(..., description="D8: Team Recognition & Sign-off")

    timeline: List[TimelineEvent] = Field(default_factory=list, description="Chronological timeline")
    citations: List[CitationObject] = Field(default_factory=list, description="Documentary citation registry")
    checksum_sha256: str = Field(default="", description="Cryptographic SHA-256 fingerprint")

    @field_validator("created_at", mode="before")
    @classmethod
    def validate_created_at_iso(cls, v: Any) -> str:
        if isinstance(v, datetime):
            dt = v if v.tzinfo else v.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        if isinstance(v, str):
            try:
                dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
                return dt.isoformat()
            except Exception as e:
                raise ValueError(f"Invalid created_at ISO 8601 timestamp '{v}': {e}")
        raise ValueError(f"created_at must be string or datetime, got {type(v)}")

    @model_validator(mode="after")
    def calculate_rpn_and_sort_timeline(self):
        # Auto-compute RPN
        computed_rpn = self.severity_score * self.occurrence_score * self.detection_score
        if self.rpn_score == 0 or self.rpn_score != computed_rpn:
            self.rpn_score = computed_rpn

        # Auto-sort timeline chronologically
        if self.timeline:
            self.timeline.sort(key=lambda evt: evt.timestamp)

        # Cross-reference citations with D4 root causes
        known_cite_ids = {c.citation_id for c in self.citations}
        for node in self.d4_root_causes.five_why_chain:
            valid_cites = [cid for cid in node.citation_ids if cid in known_cite_ids]
            if not valid_cites:
                node.is_unsubstantiated = True
                node.assumed_flag = True
                node.assumption_flag = True
            else:
                node.is_unsubstantiated = False
                node.assumed_flag = False
                node.assumption_flag = False

        return self

    def compute_canonical_sha256(self) -> str:
        """
        Computes SHA-256 cryptographic digest over canonical JSON representation
        (excluding checksum_sha256 itself).
        """
        dumped = self.model_dump(exclude={"checksum_sha256"}, mode="json")
        canonical_json = json.dumps(dumped, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
        self.checksum_sha256 = digest
        return digest

    def compute_sha256(self) -> str:
        """Alias for compute_canonical_sha256."""
        return self.compute_canonical_sha256()

    def verify_checksum(self) -> bool:
        """
        Verifies if checksum_sha256 matches current state.
        """
        if not self.checksum_sha256:
            return False
        dumped = self.model_dump(exclude={"checksum_sha256"}, mode="json")
        canonical_json = json.dumps(dumped, sort_keys=True, separators=(",", ":"))
        recomputed = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
        return self.checksum_sha256 == recomputed

    def verify_sha256(self) -> bool:
        """Alias for verify_checksum."""
        return self.verify_checksum()


# ==============================================================================
# 11. REQUEST & RESPONSE SCHEMAS
# ==============================================================================

class RCAAnalyzeRequest(BaseModel):
    """Input payload for /api/v1/rca/analyze endpoint."""
    model_config = ConfigDict(extra="ignore")

    asset_tag: str = Field(..., description="Target asset tag e.g. Pump-A12")
    symptoms: List[str] = Field(..., min_length=1, description="List of observed failure symptoms")
    incident_timestamp: str = Field(..., description="ISO 8601 incident timestamp")
    telemetry_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Observed sensor telemetry")

    @field_validator("incident_timestamp", mode="before")
    @classmethod
    def validate_timestamp(cls, v: Any) -> str:
        if isinstance(v, datetime):
            dt = v if v.tzinfo else v.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        if isinstance(v, str):
            try:
                dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
                return dt.isoformat()
            except Exception as e:
                raise ValueError(f"Invalid incident_timestamp ISO 8601 string '{v}': {e}")
        raise ValueError(f"incident_timestamp must be string or datetime, got {type(v)}")


class HistoricalMatchRequest(BaseModel):
    """Input payload for /api/v1/rca/historical-match endpoint."""
    model_config = ConfigDict(extra="ignore")

    asset_tag: str = Field(..., description="Target asset tag e.g. Pump-A12")
    symptoms: List[str] = Field(..., min_length=1, description="List of failure symptoms")
    telemetry_features: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Feature extraction dict")


class ExportEvidenceRequest(BaseModel):
    """Input payload for /api/v1/rca/export-evidence endpoint."""
    model_config = ConfigDict(extra="ignore")

    report_id: str = Field(..., description="8D report ID e.g. 8D-2023-PUMP-A12-001")
    format: str = Field(default="html", description="Export format: 'html' or 'json'")

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        if v.lower() not in {"html", "json"}:
            raise ValueError(f"Invalid format '{v}'. Supported formats: 'html', 'json'")
        return v.lower()


class ExportEvidenceResponse(BaseModel):
    """Output payload from /api/v1/rca/export-evidence endpoint."""
    model_config = ConfigDict(extra="ignore")

    content: str = Field(..., description="Rendered HTML string or JSON string")
    sha256_checksum: str = Field(..., description="Cryptographic SHA-256 digest")
    filename: str = Field(..., description="Suggested filename e.g. 8D-2023-PUMP-A12-001_Audit_Package.html")


class EightDIncidentReportSummary(BaseModel):
    """Summary view for listing reports."""
    model_config = ConfigDict(extra="ignore")

    report_id: str
    created_at: str
    asset_tag: str
    severity_score: int
    rpn_score: int
    title: str
    status: str
    checksum_sha256: str
