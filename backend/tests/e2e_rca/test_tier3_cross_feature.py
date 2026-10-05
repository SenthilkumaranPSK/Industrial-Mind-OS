"""
Tier 3: Cross-Feature Combinations & Pairwise Integration E2E Tests.
Automated Root Cause Analysis (RCA) & 8D Incident Report Studio.

Test Inventory:
- test_cross_01_timeline_to_five_why_deduction: Chronological events provide factual basis for 5-Why chain levels.
- test_cross_02_oem_deviation_to_preventative_controls: Envelope exceedance drives D7 SOP and PM threshold updates.
- test_cross_03_historical_matching_to_horizontal_deployment: Near-miss lessons drive horizontal deployment across sister assets.
- test_cross_04_citation_registry_shared_across_dual_causal_models: Shared citation catalog validates 5-Why and Ishikawa simultaneously.
- test_cross_05_root_cause_to_corrective_action_and_validation: D4 root causes map 1:1 to D5 PCAs and D6 measured KPI verification.
- test_cross_06_fmea_rpn_scoring_to_action_prioritization: High initial RPN triggers critical priority; revised RPN validates risk reduction.
- test_cross_07_end_to_end_8d_assembly_to_tamper_evident_export: Full 8D report generation through canonical SHA-256 package generation.
- test_cross_08_full_api_workflow_pipeline: End-to-end API call pipeline: /analyze -> /historical-match -> /export-evidence.
- test_cross_09_dual_vector_causes_coupled_with_ishikawa_and_containment: Physical vs escape causes combined with 6M breakdown and ICA efficiency.
- test_cross_10_regulatory_audit_trail_and_closure_signoff: Complete ISO 9001 / IATF 16949 audit trail with D8 executive sign-off seal.
Total: 10 comprehensive pairwise integration test cases.
"""

import hashlib
import json
from datetime import datetime, timezone

import pytest

from tests.e2e_rca.conftest import (
    ActionStatus,
    CitationObject,
    EightDIncidentReport,
    EventType,
    FailureTimelineEvent,
    FishboneCategory,
    FishboneCauseItem,
    FiveWhyNode,
    ImplementAndValidate,
    InterimContainmentAction,
    OEMOperatingEnvelope,
    PermanentCorrectiveAction,
    PreventativeControl,
    ProblemDescription5W2H,
    RPNScoring,
    RootCauseDiscipline,
    SeverityLevel,
    SignOffStatus,
    TeamMember,
    TeamSignOff,
    build_audit_html,
    compute_oem_deviation,
    match_historical_records,
    reconstruct_timeline,
)


def test_cross_01_timeline_to_five_why_deduction(pump_a12_telemetry_logs):
    """Pairwise 1: Timeline event progression directly correlates with 5-Why deductive levels."""
    timeline = reconstruct_timeline(pump_a12_telemetry_logs)
    assert len(timeline) == 5

    # Event 0: Normal -> Event 1: Exceeded -> Event 2: Ignored -> Event 3: Failure -> Event 4: Containment
    # 5-Why chain mirrors the chronological causality:
    # Level 1: Seal shattered (from Event 3)
    # Level 2: Vibration sustained 5.8 mm/s (from Event 2)
    # Level 3: Advisory threshold set to 6.5 mm/s (from Event 2 description)
    # Level 4: Configuration deviated from OEM manual 5.0 mm/s limit (from Event 1)
    # Level 5: Absence of automated DCS trip interlock (Root cause)
    why_chain = [
        FiveWhyNode(node_id="WHY-1", level=1, cause_statement=f"Seal shattered: {timeline[3].description}", evidence_citation_ids=["CITE-01"]),
        FiveWhyNode(node_id="WHY-2", level=2, cause_statement=f"Vibration sustained at {timeline[2].telemetry_values['vibration_mm_s']} mm/s", parent_node_id="WHY-1", evidence_citation_ids=["CITE-01"]),
        FiveWhyNode(node_id="WHY-3", level=3, cause_statement=timeline[2].description, parent_node_id="WHY-2", evidence_citation_ids=["CITE-01"]),
        FiveWhyNode(node_id="WHY-4", level=4, cause_statement=f"Vibration exceeded envelope: {timeline[1].description}", parent_node_id="WHY-3", evidence_citation_ids=["CITE-01"]),
        FiveWhyNode(node_id="WHY-5", level=5, cause_statement="Lack of automated hardware trip interlock in DCS configuration", parent_node_id="WHY-4", evidence_citation_ids=["CITE-01"], is_root_cause=True),
    ]
    assert len(why_chain) == len(timeline)
    assert why_chain[-1].is_root_cause is True
    assert "interlock" in why_chain[-1].cause_statement.lower()


def test_cross_02_oem_deviation_to_preventative_controls():
    """Pairwise 2: Calculated OEM envelope deviation automatically drives D7 Preventative Controls."""
    # Step 1: Compute deviation
    env = compute_oem_deviation(
        parameter_name="Peak Vibration Velocity",
        unit="mm/s",
        envelope_max=5.0,
        incident_value=5.8,
        recommended_action="Enforce mandatory automated shutdown trip at 5.5 mm/s",
    )
    assert env.deviation_pct == 16.0
    assert env.severity_level == SeverityLevel.CRITICAL

    # Step 2: Feed deviation directly into D7 Preventative Control
    now = datetime.now(timezone.utc)
    control = PreventativeControl(
        control_id="PRV-OEM-01",
        control_type="OEM_ENVELOPE_UPDATE",
        description=f"Recalibrate DCS envelope based on OEM manual limit of {env.envelope_max} {env.unit}: {env.recommended_action}",
        document_reference="SOP-PUMP-A12 Rev 4",
        target_completion_date=now,
        oem_envelope_adjustments=[env],
        status=ActionStatus.IMPLEMENTED,
    )
    assert len(control.oem_envelope_adjustments) == 1
    assert control.oem_envelope_adjustments[0].deviation_pct == 16.0
    assert "5.5 mm/s" in control.description


def test_cross_03_historical_matching_to_horizontal_deployment(near_miss_report_text):
    """Pairwise 3: Historical near-miss match lessons directly populate D7 horizontal deployment sister assets."""
    # Step 1: Match incident
    matches = match_historical_records(
        asset_tag="Pump-A12",
        symptoms=["vibration", "ceramic seal", "coolant leak"],
        near_miss_text=near_miss_report_text,
    )
    assert len(matches) == 1
    hist_match = matches[0]

    # Step 2: Deploy preventative controls across all sister assets in the A-Series equipment family
    sister_assets = ["Pump-A11", "Pump-A13", "Pump-A14"]
    now = datetime.now(timezone.utc)
    control = PreventativeControl(
        control_id="PRV-HORIZ-01",
        control_type="HORIZONTAL_DEPLOYMENT",
        description=f"Propagate lessons learned from {hist_match.matched_report_id} to sister assets: {', '.join(hist_match.historical_lessons)}",
        target_completion_date=now,
        horizontal_deployment_assets=sister_assets,
        status=ActionStatus.OPEN,
    )
    assert len(control.horizontal_deployment_assets) == 3
    assert "Pump-A11" in control.horizontal_deployment_assets
    assert hist_match.matched_report_id in control.description


def test_cross_04_citation_registry_shared_across_dual_causal_models():
    """Pairwise 4: Shared citation catalog verifies both 5-Why and Ishikawa models in RootCauseDiscipline."""
    cites = [
        CitationObject(citation_id="CITE-NM-01", source_doc="Near_Miss.txt", title="Near Miss", excerpt="Vibration 5.8 mm/s shattered seals"),
        CitationObject(citation_id="CITE-OEM-02", source_doc="Manual.pdf", title="OEM Manual", excerpt="Max allowable vibration 5.0 mm/s"),
    ]
    why_chain = [
        FiveWhyNode(node_id="W1", level=1, cause_statement="Seal face cracked", evidence_citation_ids=["CITE-NM-01"]),
        FiveWhyNode(node_id="W2", level=2, cause_statement="Vibration exceeded OEM limit", evidence_citation_ids=["CITE-OEM-02"], is_root_cause=True),
    ]
    fishbone = [
        FishboneCauseItem(cause_id="FB-1", category=FishboneCategory.MACHINE, statement="Ceramic fatigue", evidence_citation_ids=["CITE-NM-01"]),
        FishboneCauseItem(cause_id="FB-2", category=FishboneCategory.METHOD, statement="Alarm configured higher than OEM limit", evidence_citation_ids=["CITE-OEM-02"]),
    ]
    d4 = RootCauseDiscipline(
        occurrence_root_cause="Vibration cracked ceramic face",
        escape_root_cause="Alarm set too high",
        five_why_chain=why_chain,
        fishbone_analysis=fishbone,
        citations=cites,
    )
    # 4 causes, all 4 link to catalog citations -> CGR = 1.0
    assert d4.citation_grounding_ratio == 1.0
    assert all(not node.is_unsubstantiated for node in d4.five_why_chain)
    assert all(not item.is_unsubstantiated for item in d4.fishbone_analysis)


def test_cross_05_root_cause_to_corrective_action_and_validation():
    """Pairwise 5: Root cause ID explicitly links to D5 PCA, and D6 validates baseline vs post metrics."""
    now = datetime.now(timezone.utc)
    root_cause = FiveWhyNode(
        node_id="WHY-RC-01",
        level=5,
        cause_statement="Lack of DCS automated hardware shutdown interlock at 5.5 mm/s",
        evidence_citation_ids=["CITE-01"],
        is_root_cause=True,
    )
    pca = PermanentCorrectiveAction(
        pca_id="PCA-01",
        description="Implement hardware interlock trip at 5.5 mm/s in DCS rack 4",
        addresses_cause_id=root_cause.node_id,
        responsible_owner="Senior Controls Engineer",
        target_date=now,
        feasibility_score=9,
        risk_assessment="Zero operational impact",
        validation_plan="Inject 5.6 mm/s 4-20mA test signal and measure relay drop time",
        status=ActionStatus.IMPLEMENTED,
    )
    assert pca.addresses_cause_id == "WHY-RC-01"

    validation = ImplementAndValidate(
        action_id="VAL-01",
        pca_id=pca.pca_id,
        actual_implementation_date=now,
        baseline_metric="Vibration 5.8 mm/s sustained for 48h with zero alarm trip",
        post_implementation_metric="DCS relay tripped within 850ms at 5.51 mm/s",
        verification_evidence="Oscilloscope test run TR-8841",
        validation_status=ActionStatus.VERIFIED,
        verified_by="Chief Electrical Engineer",
    )
    assert validation.pca_id == "PCA-01"
    assert validation.validation_status == ActionStatus.VERIFIED
    assert "850ms" in validation.post_implementation_metric


def test_cross_06_fmea_rpn_scoring_to_action_prioritization():
    """Pairwise 6: Initial RPN triggers CRITICAL priority; mitigation recalculates revised RPN with 88% reduction."""
    # Pre-PCA state: Severity 8, Occurrence 7, Detection 7 -> RPN = 392 (CRITICAL)
    rpn_pre = RPNScoring(severity=8, occurrence=7, detection=7)
    assert rpn_pre.rpn == 392
    assert rpn_pre.risk_priority == "CRITICAL"

    # Post-PCA state: Automated trip drops Detection from 7 to 2, training drops Occurrence from 7 to 3
    rpn_post = RPNScoring(
        severity=8,
        occurrence=7,
        detection=7,
        revised_severity=8,
        revised_occurrence=3,
        revised_detection=2,
    )
    assert rpn_post.rpn == 392
    assert rpn_post.revised_rpn == 48  # 8 * 3 * 2
    # Verify reduction percentage
    rpn_reduction_pct = round(((rpn_post.rpn - rpn_post.revised_rpn) / rpn_post.rpn) * 100.0, 1)
    assert rpn_reduction_pct == 87.8


def test_cross_07_end_to_end_8d_assembly_to_tamper_evident_export(client):
    """Pairwise 7: Full 8D report generation through canonical SHA-256 evidence package."""
    # Step 1: Generate full report via API
    payload = {
        "asset_tag": "Pump-A12",
        "symptoms": ["mechanical seal shatter", "coolant leak 15L"],
        "incident_timestamp": "2023-11-04T08:00:00Z",
        "telemetry_data": {"vibration_mm_s": 5.8, "spill_liters": 15.0},
    }
    resp = client.post("/api/v1/rca/analyze", json=payload)
    assert resp.status_code == 200
    report_data = resp.json()
    rep_id = report_data["report_id"]
    sha_orig = report_data["audit_metadata"]["sha256_checksum"]
    assert len(sha_orig) == 64

    # Step 2: Export JSON audit package
    export_resp = client.post(
        "/api/v1/rca/export-evidence",
        json={"report_id": rep_id, "format": "json"},
    )
    assert export_resp.status_code == 200
    export_data = export_resp.json()
    assert export_data["sha256_checksum"] == sha_orig
    assert export_data["filename"].endswith(".json")


def test_cross_08_full_api_workflow_pipeline(client):
    """Pairwise 8: Complete workflow pipeline: /analyze -> /historical-match -> /export-evidence (HTML & JSON)."""
    # 1. Analyze
    analyze_resp = client.post(
        "/api/v1/rca/analyze",
        json={
            "asset_tag": "Pump-A12",
            "symptoms": ["vibration 5.8 mm/s", "ceramic seal fracture"],
            "incident_timestamp": "2023-11-04T08:00:00Z",
        },
    )
    assert analyze_resp.status_code == 200
    rep = analyze_resp.json()
    rep_id = rep["report_id"]

    # 2. Match
    match_resp = client.post(
        "/api/v1/rca/historical-match",
        json={"asset_tag": "Pump-A12", "symptoms": ["vibration", "ceramic seal"]},
    )
    assert match_resp.status_code == 200
    matches = match_resp.json()
    assert len(matches) >= 1

    # 3. Export HTML
    html_resp = client.post(
        "/api/v1/rca/export-evidence",
        json={"report_id": rep_id, "format": "html"},
    )
    assert html_resp.status_code == 200
    html_data = html_resp.json()
    assert "<!DOCTYPE html>" in html_data["content"]
    assert rep_id in html_data["content"]
    assert len(html_data["sha256_checksum"]) == 64


def test_cross_09_dual_vector_causes_coupled_with_ishikawa_and_containment():
    """Pairwise 9: Occurrence vs Escape root causes integrated with 6M classification and 100% containment."""
    now = datetime.now(timezone.utc)
    ica = InterimContainmentAction(
        action_id="ICA-01",
        description="Isolated upstream isolation valves and deployed spill absorbents",
        responsible_owner="EHS Response Lead",
        implementation_date=now,
        verification_method="Visual inspection and storm drain water sampling",
        effectiveness_pct=100.0,
        status=ActionStatus.VERIFIED,
        evidence_citation_id="CITE-01",
    )
    assert ica.effectiveness_pct == 100.0

    cite = CitationObject(citation_id="CITE-01", source_doc="report.txt", title="Report", excerpt="Excerpt valid")
    d4 = RootCauseDiscipline(
        occurrence_root_cause="Harmonic shaft vibration at 5.8 mm/s fractured brittle inboard ceramic seal face",
        escape_root_cause="Supervisory SCADA alarm threshold was erroneously configured at 6.5 mm/s",
        five_why_chain=[
            FiveWhyNode(node_id="W1", level=1, cause_statement="Seal cracked", evidence_citation_ids=["CITE-01"], is_root_cause=True)
        ],
        fishbone_analysis=[
            FishboneCauseItem(cause_id="FB-1", category=FishboneCategory.MACHINE, statement="Ceramic face fatigue", evidence_citation_ids=["CITE-01"]),
            FishboneCauseItem(cause_id="FB-2", category=FishboneCategory.METHOD, statement="Alarm setpoint misconfiguration", evidence_citation_ids=["CITE-01"]),
        ],
        citations=[cite],
    )
    assert "ceramic seal face" in d4.occurrence_root_cause
    assert "6.5 mm/s" in d4.escape_root_cause
    cats = {item.category for item in d4.fishbone_analysis}
    assert FishboneCategory.MACHINE in cats
    assert FishboneCategory.METHOD in cats


def test_cross_10_regulatory_audit_trail_and_closure_signoff():
    """Pairwise 10: Full ISO 9001 / IATF 16949 audit trail with D8 executive sign-off seal."""
    now = datetime.now(timezone.utc)
    signoff = TeamSignOff(
        signoff_id="SO-IATF-01",
        approver_name="Dr. Miriam O'Connor",
        approver_role="Vice President of Global Quality",
        signoff_status=SignOffStatus.APPROVED,
        signoff_date=now,
        signature_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        recognition_notes="Commendation to Reliability and Operations teams for zero-loss containment under 15 minutes.",
        lessons_learned_summary="OEM baseline operating envelope thresholds must be cryptographically locked in DCS configurations.",
        financial_impact_total_usd=14500.0,
        downtime_hours_total=2.5,
    )
    assert signoff.signoff_status == SignOffStatus.APPROVED
    assert signoff.financial_impact_total_usd == 14500.0
    assert signoff.downtime_hours_total == 2.5
    assert len(signoff.signature_hash) == 64
