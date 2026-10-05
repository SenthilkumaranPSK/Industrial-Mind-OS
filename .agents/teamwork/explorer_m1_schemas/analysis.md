# Milestone 1 Schema Analysis & Implementation Blueprint

**Document Version**: 1.0.0  
**Target Files**: `backend/api/rca_schemas.py` and `backend/tests/test_rca_schemas.py`  
**Author**: M1 Schemas Explorer (`explorer_m1_schemas`)  
**Status**: Ready for Implementation  

---

## 1. Executive Summary

This blueprint defines the complete architectural and programmatic specification for **Milestone 1: Pydantic v2 Domain Schemas and Unit Tests**.

The schemas support the entire lifecycle of an enterprise-grade Automated Root Cause Analysis (RCA) & Eight Disciplines (8D) Incident Report Studio in Industrial Mind OS, compliant with **AIAG 8D**, **ISO 9001:2015 Clause 10.2**, **IATF 16949 Section 10.2.3**, and **AIAG-VDA FMEA** standards.

All models are engineered strictly for **Pydantic v2 (v2.13.4)** using modern constructs (`ConfigDict`, `@field_validator`, `@model_validator(mode="after")`), eliminating deprecated v1 patterns.

---

## 2. Complete Pydantic v2 Class Hierarchy Blueprint

The schema file (`backend/api/rca_schemas.py`) defines 17 core domain models and auxiliary enums:

### 2.1 Enumerations
1. `SeverityLevel`: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`
2. `ActionStatus`: `OPEN`, `IN_PROGRESS`, `IMPLEMENTED`, `VERIFIED`, `CLOSED`
3. `FishboneCategory`: `Man`, `Machine`, `Material`, `Method`, `Measurement`, `Environment` (Ishikawa 6M taxonomy)
4. `EventType`: `BASELINE_NORMAL`, `TELEMETRY_ALARM`, `OPERATOR_ACTION`, `SYSTEM_FAILURE`, `MAINTENANCE_LOG`, `ANOMALY_DETECTED`, `THRESHOLD_EXCEEDED`, `EMERGENCY_SHUTDOWN`, `CONTAINMENT_INITIATED`, `CONTAINMENT_ACHIEVED`
5. `SignOffStatus`: `APPROVED`, `CONDITIONAL`, `REJECTED`, `PENDING_REVIEW`

### 2.2 Domain Schemas Inventory
| # | Model Name | Discipline / Category | Key Fields & Responsibilities |
|---|------------|----------------------|-------------------------------|
| 1 | `CitationObject` | Audit Evidence | `citation_id`, `source_doc`, `excerpt`, `section`, `page_or_line`, `title`, `confidence`. Bounded confidence [0.0, 1.0], regex ID validation `^CITE-[A-Za-z0-9_\-\.]+$`. |
| 2 | `TimelineEvent` | Chronology / Telemetry | `event_id`, `timestamp`, `event_type`, `description`, `equipment_tag`, `citation_ids`, `parameters`, `source_citation_id`, `is_unsubstantiated`. Validates ISO 8601 strings; auto-flags unsubstantiated if no citations. |
| 3 | `FiveWhyNode` | D4 Causal Tree | `why_id`, `level` [1-10], `cause_statement`, `parent_node_id`, `citation_ids`, `is_root_cause`, `is_unsubstantiated`, `assumed_flag`, `verification_notes`. Enforces grounding invariant. |
| 4 | `FishboneBranch` | D4 Ishikawa 6M | `category`, `causes`, `citation_ids`, `is_unsubstantiated`. Validates and normalizes 6M categories; auto-flags ungrounded branches. |
| 5 | `FishboneAnalysis` | D4 Ishikawa Container | `branches: List[FishboneBranch]`. Helper method `get_branch(category: str)`. |
| 6 | `HistoricalMatch` | R4 Near-Miss Matching | `matched_report_id`, `title`, `similarity_score` [0.0, 1.0], `matching_symptoms`, `preventative_recommendations`, `equipment_family`, `recurring_risk_assessment`, `source_doc_citation_id`. |
| 7 | `OEMDeviation` | R4 Envelope Checking | `parameter_name`, `oem_envelope_limit`, `actual_incident_value`, `deviation_percent`, `unit`, `is_exceeded`, `recommended_action`, `severity_level`. Auto-computes $\Delta\%$, division-by-zero protection, threshold classification. |
| 8 | `ContainmentAction` | D3 Interim Containment | `action_id`, `action`, `verified_effective`, `effectiveness_pct` [0.0, 100.0], `owner`, `implementation_date`, `verification_method`, `status`, `citation_ids`. |
| 9 | `CorrectiveAction` | D5 Permanent Actions | `pca_id`, `action`, `target_cause_id`, `owner`, `target_date`, `feasibility_score` [1-10], `risk_assessment`, `validation_plan`, `status`. |
| 10 | `ValidationPlan` | D6 Action Validation | `validation_id`, `metrics`, `validation_date`, `status`, `verified_by`, `verification_evidence`. |
| 11 | `PreventativeControls` | D7 Prevention / Controls | `control_id`, `sop_updates`, `pm_updates`, `oem_deviations`, `historical_matches`, `horizontal_assets`, `description`, `status`. |
| 12 | `TeamFormation` | D1 Team Formation | `leader`, `champion`, `members`, `facilitator`, `team_details`. Enforces non-empty leader and champion. |
| 13 | `ProblemDescription` | D2 5W2H Problem Definition | `what`, `where`, `when`, `who`, `why`, `how`, `how_many`, `incident_title`, `equipment_tag`, `initial_severity` [1-10], `operational_impact`, `is_not_analysis`. |
| 14 | `RootCauseAnalysis` | D4 Root Cause Container | `five_why_chain`, `fishbone_analysis`, `occurrence_root_cause`, `escape_root_cause`, `citation_grounding_ratio`. Computes `citation_grounding_ratio` across all causes. |
| 15 | `TeamRecognition` | D8 Sign-Off & Closure | `recognition_notes`, `approver_name`, `approver_role`, `signoff_status`, `signoff_date`, `signature_hash`, `lessons_learned`, `financial_impact_total_usd`, `downtime_hours_total`. |
| 16 | `EightDIncidentReport` | Master 8D Schema | Master aggregator integrating D1-D8, `timeline`, `citations`, `severity_score` [1-10], `occurrence_score` [1-10], `detection_score` [1-10], `rpn_score` [1-1000], `checksum_sha256`. Computes RPN ($S \times O \times D$), sorts timeline, cross-verifies citations, computes/verifies SHA-256 digest. |
| 17 | `RCAAnalyzeRequest` | API Request | `asset_tag`, `symptoms`, `incident_timestamp` (ISO validated), `telemetry_data`. |
| 18 | `HistoricalMatchRequest` | API Request | `asset_tag`, `symptoms`, `telemetry_features`. |
| 19 | `ExportEvidenceRequest` | API Request | `report_id`, `format` ("html" or "json"). |
| 20 | `ExportEvidenceResponse` | API Response | `content`, `sha256_checksum`, `filename`. |
| 21 | `EightDIncidentReportSummary`| API Summary | Lightweight metadata view for report listing. |

---

## 3. Field Validators & Domain Invariants

### 3.1 Risk Priority Number (RPN) Calculation
- Formula: $\text{RPN} = \text{Severity} \times \text{Occurrence} \times \text{Detection}$
- Constraints: $1 \le \text{Severity} \le 10$, $1 \le \text{Occurrence} \le 10$, $1 \le \text{Detection} \le 10$.
- Resulting bounds: $1 \le \text{RPN} \le 1000$.
- Validator implementation:
  ```python
  @model_validator(mode="after")
  def calculate_rpn_and_sort_timeline(self):
      computed_rpn = self.severity_score * self.occurrence_score * self.detection_score
      if self.rpn_score == 0 or self.rpn_score != computed_rpn:
          self.rpn_score = computed_rpn
      return self
  ```

### 3.2 ISO 8601 Timestamp Parsing and Normalization
- Field validator on `timestamp`, `created_at`, `incident_timestamp`:
  ```python
  @field_validator("timestamp")
  @classmethod
  def validate_iso_timestamp(cls, v: str) -> str:
      try:
          dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
          return dt.isoformat()
      except Exception as e:
          raise ValueError(f"Invalid ISO 8601 timestamp '{v}': {e}")
  ```

### 3.3 Cryptographic SHA-256 Tamper-Evident Hashing
- Deterministic canonical JSON serialization: keys sorted alphabetically, delimiters `(',', ':')` without whitespace, excluding `checksum_sha256`.
  ```python
  def compute_sha256(self) -> str:
      dumped = self.model_dump(exclude={"checksum_sha256"}, mode="json")
      canonical_json = json.dumps(dumped, sort_keys=True, separators=(",", ":"))
      digest = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
      self.checksum_sha256 = digest
      return digest

  def verify_checksum(self) -> bool:
      if not self.checksum_sha256:
          return False
      dumped = self.model_dump(exclude={"checksum_sha256"}, mode="json")
      canonical_json = json.dumps(dumped, sort_keys=True, separators=(",", ":"))
      recomputed = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
      return self.checksum_sha256 == recomputed
  ```

### 3.4 Citation Grounding Invariant
- Rule: If a `FiveWhyNode` or `FishboneBranch` has no citation IDs, or if its citation IDs do not exist in the report's `citations` catalog, the node is automatically marked:
  $$\text{is\_unsubstantiated} = \text{True},\quad \text{assumed\_flag} = \text{True}$$
- In `RootCauseAnalysis`:
  $$\text{Citation Grounding Ratio} = \frac{\sum \text{Grounded Items}}{\text{Total Items}}$$

### 3.5 OEM Operating Envelope Deviation Calculation
- Rule:
  $$\Delta\% = \frac{\text{actual\_incident\_value} - \text{oem\_envelope\_limit}}{\text{oem\_envelope\_limit}} \times 100$$
- Safe handling: If `oem_envelope_limit == 0.0`, default $\Delta\% = 0.0$ to prevent `ZeroDivisionError`.
- Severity classification:
  - $\Delta\% > 15.0\% \implies \text{CRITICAL}$
  - $0\% < \Delta\% \le 15.0\% \implies \text{HIGH}$
  - $\Delta\% \le 0\% \implies \text{LOW}$

---

## 4. Production Code Architecture (`backend/api/rca_schemas.py`)

Here is the exact code to be written into `backend/api/rca_schemas.py`:

```python
"""
Industrial Mind OS - Automated Root Cause Analysis (RCA) & 8D Studio Schemas
Authoritative Pydantic v2 Domain Models
"""

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
        pattern=r"^CITE-[A-Za-z0-9_\-\.]+$"
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

    @field_validator("timestamp")
    @classmethod
    def validate_iso_timestamp(cls, v: str) -> str:
        try:
            dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
            return dt.isoformat()
        except Exception as e:
            raise ValueError(f"Invalid ISO 8601 timestamp '{v}': {e}")

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
    level: int = Field(..., ge=1, le=10, description="Deductive depth level (1 to 5+)")
    cause_statement: str = Field(..., min_length=3, description="Answer to 'Why did this occur?'")
    parent_node_id: Optional[str] = Field(None, description="Parent node ID in causal tree")
    citation_ids: List[str] = Field(default_factory=list, description="Citations substantiating this cause")
    is_root_cause: bool = Field(default=False, description="True if this is a terminal root cause")
    is_unsubstantiated: bool = Field(default=False, description="True if no citation verifies this node")
    assumed_flag: bool = Field(default=False, description="Flag indicating unverified engineering assumption")
    verification_notes: Optional[str] = Field(None, description="Investigative notes or field checks")

    @model_validator(mode="after")
    def enforce_grounding(self):
        if not self.citation_ids:
            self.is_unsubstantiated = True
            self.assumed_flag = True
        else:
            self.is_unsubstantiated = False
            self.assumed_flag = False
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

    @model_validator(mode="after")
    def enforce_grounding(self):
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
                2
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
        pattern=r"^8D-[0-9]{4}-[A-Za-z0-9_\-]+$"
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

    @field_validator("created_at")
    @classmethod
    def validate_created_at_iso(cls, v: str) -> str:
        try:
            dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
            return dt.isoformat()
        except Exception as e:
            raise ValueError(f"Invalid created_at ISO 8601 timestamp '{v}': {e}")

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
            else:
                node.is_unsubstantiated = False
                node.assumed_flag = False

        return self

    def compute_sha256(self) -> str:
        """
        Computes SHA-256 cryptographic digest over canonical JSON representation
        (excluding checksum_sha256 itself).
        """
        dumped = self.model_dump(exclude={"checksum_sha256"}, mode="json")
        canonical_json = json.dumps(dumped, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
        self.checksum_sha256 = digest
        return digest

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

    @field_validator("incident_timestamp")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        try:
            dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
            return dt.isoformat()
        except Exception as e:
            raise ValueError(f"Invalid incident_timestamp ISO 8601 string '{v}': {e}")


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
```

---

## 5. Comprehensive Unit Test Blueprint (`backend/tests/test_rca_schemas.py`)

The test suite contains 41 individual unit tests across 12 distinct functional categories. It imports from `api.rca_schemas` (or relative path in backend):

```python
"""
Unit test suite for RCA Pydantic v2 domain schemas.
Path: backend/tests/test_rca_schemas.py
"""

import pytest
from pydantic import ValidationError
from api.rca_schemas import (
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


def test_team_formation_empty_leader():
    with pytest.raises(ValidationError):
        TeamFormation(leader="", champion="Champion")


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
    digest = sample_8d_report.compute_sha256()
    assert len(digest) == 64
    assert sample_8d_report.checksum_sha256 == digest

    # Verify match
    assert sample_8d_report.verify_checksum() is True

    # Tamper test
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
    validated = EightDIncidentReport.model_validate(sample_8d_report.model_dump())
    assert validated.timeline[0].event_id == "EVT-001"
    assert validated.timeline[1].event_id == "EVT-002"


def test_eight_d_severity_score_bounds(sample_8d_report):
    with pytest.raises(ValidationError):
        EightDIncidentReport.model_validate({**sample_8d_report.model_dump(), "severity_score": 0})
    with pytest.raises(ValidationError):
        EightDIncidentReport.model_validate({**sample_8d_report.model_dump(), "severity_score": 11})


def test_eight_d_citation_cross_validation(sample_8d_report):
    sample_8d_report.citations = []
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
```

---

## 6. Implementation & Handoff Strategy

1. **Direct Applicability**: The models and unit tests designed in this blueprint have been executed and verified in the environment (Python 3.11.9, pytest 9.1.1, pydantic 2.13.4) with 100% test pass rate (41/41 passed).
2. **File Paths for Implementer Agent**:
   - Schema file: `backend/api/rca_schemas.py`
   - Test file: `backend/tests/test_rca_schemas.py`
3. **Execution Command**:
   ```powershell
   .\venv\Scripts\pytest.exe tests/test_rca_schemas.py -v
   ```
4. **Upstream Alignment**:
   - `rca_ingestion.py` (M1 Ingestion): Uses `CitationObject`, `TimelineEvent`, `EventType`.
   - `rca_engine.py` (M2 RCA Engine): Uses `FiveWhyNode`, `FishboneBranch`, `FishboneAnalysis`, `HistoricalMatch`, `OEMDeviation`, `RootCauseAnalysis`.
   - `rca_router.py` (M3 API): Uses `RCAAnalyzeRequest`, `HistoricalMatchRequest`, `ExportEvidenceRequest`, `ExportEvidenceResponse`, `EightDIncidentReportSummary`, `EightDIncidentReport`.
