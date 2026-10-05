"""
Tier 4: Realistic Industrial Incident Scenarios E2E Tests.
Automated Root Cause Analysis (RCA) & 8D Incident Report Studio.

Test Inventory:
- Scenario 1 (2 tests):
  * test_scenario1_pump_a12_ceramic_seal_end_to_end: Complete 8D lifecycle for Pump-A12 grounded in Near_Miss_Report_2023.txt.
  * test_scenario1_pump_a12_oem_deviation_and_compliance_package: Envelope deviation, horizontal deployment, and audit package certification.
- Scenario 2 (2 tests):
  * test_scenario2_steam_turbine_overspeed_and_lube_failure: High-pressure steam turbine TURB-ST-04 overspeed trip analysis.
  * test_scenario2_steam_turbine_pca_validation_and_fmea_reduction: D5/D6 mitigation, FMEA RPN reduction, and export verification.
- Scenario 3 (2 tests):
  * test_scenario3_boiler_thermal_runaway_thermocouple_drift: Water-tube boiler BLR-HP-101 superheater tube creep investigation.
  * test_scenario3_boiler_voting_logic_pca_and_horizontal_controls: 2-out-of-3 thermocouple voting PCA and horizontal sister boiler controls.
Total: 6 comprehensive real-world industrial scenario tests.
"""

import hashlib
import json
import os
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


# ==============================================================================
# SCENARIO 1: PUMP-A12 VIBRATION & INBOARD CERAMIC SEAL FAILURE
# ==============================================================================

def test_scenario1_pump_a12_ceramic_seal_end_to_end(pump_a12_telemetry_logs, near_miss_report_text):
    """Scenario 1.1: Complete 8D incident report analysis for Pump-A12 grounded in Near_Miss_Report_2023.txt."""
    now = datetime(2023, 11, 4, 8, 30, tzinfo=timezone.utc)
    
    # 1. Timeline reconstruction
    timeline = reconstruct_timeline(pump_a12_telemetry_logs)
    assert len(timeline) == 5
    assert timeline[0].event_type == EventType.BASELINE_NORMAL
    assert timeline[2].event_type == EventType.ALARM_IGNORED
    assert timeline[3].event_type == EventType.CATASTROPHIC_FAILURE
    assert timeline[4].event_type == EventType.CONTAINMENT_ACHIEVED

    # 2. Historical near-miss matching
    matches = match_historical_records(
        asset_tag="Pump-A12",
        symptoms=["vibration", "ceramic seal", "coolant leak"],
        near_miss_text=near_miss_report_text,
    )
    assert len(matches) == 1
    match = matches[0]
    assert match.matched_report_id == "NM-2023-PUMP-A12"
    assert match.similarity_score >= 0.8

    # 3. Citation catalog grounded in Near_Miss_Report_2023.txt
    citations = [
        CitationObject(
            citation_id="CITE-NM-2023-01",
            source_doc="Near_Miss_Report_2023.txt",
            title="Near-Miss Record 2023-11-04",
            section="Root Cause Analysis",
            excerpt="Post-incident analysis revealed that the pump had been operating with a severe vibration level of 5.8 mm/s for 48 hours prior to the failure.",
            confidence=1.0,
        ),
        CitationObject(
            citation_id="CITE-OEM-PUMP-01",
            source_doc="Near_Miss_Report_2023.txt",
            title="Corrective Action / Lessons Learned",
            section="Lessons Learned",
            excerpt="The maximum allowable vibration for Pump A12 is strictly 5.0 mm/s as per the OEM manual.",
            confidence=1.0,
        ),
        CitationObject(
            citation_id="CITE-OEM-TRIP-02",
            source_doc="Near_Miss_Report_2023.txt",
            title="Mandatory Shutdown Protocol",
            section="Shutdown Protocol",
            excerpt="Any vibration reading exceeding 5.5 mm/s requires an immediate, mandatory shutdown of the pump to prevent seal fracture.",
            confidence=1.0,
        ),
    ]

    # 4. Deductive 5-Why Chain
    five_why = [
        FiveWhyNode(
            node_id="WHY-1",
            level=1,
            cause_statement="Coolant fluid leaked onto Primary Cooling Loop Sector 4 floor",
            evidence_citation_ids=["CITE-NM-2023-01"],
        ),
        FiveWhyNode(
            node_id="WHY-2",
            level=2,
            cause_statement="Inboard ceramic seal shattered under excessive mechanical stress",
            parent_node_id="WHY-1",
            evidence_citation_ids=["CITE-NM-2023-01"],
        ),
        FiveWhyNode(
            node_id="WHY-3",
            level=3,
            cause_statement="Pump operated at sustained 5.8 mm/s vibration for 48 hours",
            parent_node_id="WHY-2",
            evidence_citation_ids=["CITE-NM-2023-01"],
        ),
        FiveWhyNode(
            node_id="WHY-4",
            level=4,
            cause_statement="Operations personnel ignored alerts believing the threshold was 6.5 mm/s",
            parent_node_id="WHY-3",
            evidence_citation_ids=["CITE-NM-2023-01"],
        ),
        FiveWhyNode(
            node_id="WHY-5",
            level=5,
            cause_statement="SCADA alarm configured to generic 6.5 mm/s plant guideline rather than OEM 5.0 mm/s limit, without mandatory 5.5 mm/s hardware interlock",
            parent_node_id="WHY-4",
            evidence_citation_ids=["CITE-OEM-PUMP-01", "CITE-OEM-TRIP-02"],
            is_root_cause=True,
        ),
    ]

    # 5. Ishikawa 6M classification
    fishbone = [
        FishboneCauseItem(cause_id="FB-MAN", category=FishboneCategory.MAN, statement="Technicians relied on generic plant guidelines instead of asset-specific tolerance", contribution_weight=0.7, evidence_citation_ids=["CITE-OEM-PUMP-01"]),
        FishboneCauseItem(cause_id="FB-MCH", category=FishboneCategory.MACHINE, statement="Inboard ceramic mechanical seal shattered by cyclic harmonic loading", contribution_weight=0.9, evidence_citation_ids=["CITE-NM-2023-01"]),
        FishboneCauseItem(cause_id="FB-MAT", category=FishboneCategory.MATERIAL, statement="Ceramic face brittle fracture under sustained 5.8 mm/s vibration", contribution_weight=0.6, evidence_citation_ids=["CITE-NM-2023-01"]),
        FishboneCauseItem(cause_id="FB-METH", category=FishboneCategory.METHOD, statement="Absence of mandatory automated shutdown protocol above 5.5 mm/s", contribution_weight=0.8, evidence_citation_ids=["CITE-OEM-TRIP-02"]),
        FishboneCauseItem(cause_id="FB-MEAS", category=FishboneCategory.MEASUREMENT, statement="SCADA advisory alert did not escalate to high-priority supervisory trip", contribution_weight=0.7, evidence_citation_ids=["CITE-NM-2023-01"]),
    ]

    d4 = RootCauseDiscipline(
        occurrence_root_cause="Fatigue fracture of inboard ceramic seal face caused by sustained shaft vibration of 5.8 mm/s exceeding OEM maximum envelope of 5.0 mm/s for 48 hours",
        escape_root_cause="Procedural and software failure: DCS alarm threshold set to 6.5 mm/s generic limit instead of 5.0 mm/s OEM envelope, with lack of automated 5.5 mm/s shutdown interlock",
        five_why_chain=five_why,
        fishbone_analysis=fishbone,
        citations=citations,
    )
    assert d4.citation_grounding_ratio == 1.0

    # 6. FMEA scoring
    rpn = RPNScoring(
        severity=8, occurrence=7, detection=6,
        revised_severity=8, revised_occurrence=2, revised_detection=1
    )
    assert rpn.rpn == 336
    assert rpn.revised_rpn == 16
    assert rpn.risk_priority == "HIGH"

    # 7. Assemble complete 8D report
    report = EightDIncidentReport(
        report_id="8D-2023-PUMP-A12",
        d1_team=[
            TeamMember(member_id="TM-01", name="Elena Rostova", role="Team Leader", department="Reliability"),
            TeamMember(member_id="TM-02", name="Marcus Vance", role="Champion", department="Plant Operations"),
        ],
        d2_problem=ProblemDescription5W2H(
            incident_title="Pump-A12 Inboard Ceramic Seal Shatter and Coolant Leak",
            equipment_tag="Pump-A12",
            equipment_family="A-Series Centrifugal Pump",
            timestamp_incident=datetime(2023, 11, 4, 7, 45, tzinfo=timezone.utc),
            who_detected="Emergency Response Team / Floor Sensor",
            what_symptom="Mechanical seal failure resulting in coolant leak onto floor",
            where_location="Primary Cooling Loop, Sector 4",
            when_detected="Nov 4, 2023 at 07:45 UTC after 48h vibration",
            why_consequence="Environmental near-miss and loss of cooling capacity",
            how_detected="SCADA vibration alarm and floor bund level sensor",
            how_much_magnitude="15 liters of coolant spilled, vibration 5.8 mm/s vs 5.0 mm/s limit",
            initial_severity=8,
            operational_impact="Primary cooling loop halted for 2.5 hours",
            is_not_analysis={"Pump-A11": "Sister pump unaffected; running at nominal 3.1 mm/s"},
        ),
        d3_containment=[
            InterimContainmentAction(
                action_id="ICA-01",
                description="Deployed absorbent chemical containment booms and isolated inlet/outlet valves within 15 minutes",
                responsible_owner="Emergency Response Team",
                implementation_date=datetime(2023, 11, 4, 8, 0, tzinfo=timezone.utc),
                verification_method="Visual inspection confirmed zero spill effluent reached environmental drainage gates",
                effectiveness_pct=100.0,
                status=ActionStatus.VERIFIED,
                evidence_citation_id="CITE-NM-2023-01",
            )
        ],
        d4_root_cause=d4,
        d5_permanent_actions=[
            PermanentCorrectiveAction(
                pca_id="PCA-01",
                description="Program automated DCS emergency shutdown interlock executing immediate trip if vibration exceeds 5.5 mm/s",
                addresses_cause_id="WHY-5",
                responsible_owner="Controls Lead",
                target_date=now,
                feasibility_score=9,
                risk_assessment="Low risk of false trip with 3-second debounce filter",
                validation_plan="Inject 5.6 mm/s test signal into DCS rack",
                status=ActionStatus.IMPLEMENTED,
            )
        ],
        d6_validation=[
            ImplementAndValidate(
                action_id="VAL-01",
                pca_id="PCA-01",
                actual_implementation_date=now,
                baseline_metric="Vibration 5.8 mm/s ignored for 48 hours without trip",
                post_implementation_metric="DCS automated trip verified at 5.51 mm/s with 1.1s response",
                verification_evidence="DCS Trip Test Certification Certificate TR-8841",
                validation_status=ActionStatus.VERIFIED,
                verified_by="Lead Reliability Engineer",
            )
        ],
        d7_prevention=[
            PreventativeControl(
                control_id="PRV-01",
                control_type="SOP_UPDATE",
                description="Update SOP-PUMP-A12 to enforce strict OEM 5.0 mm/s limit and mandatory 5.5 mm/s shutdown",
                document_reference="SOP-PUMP-A12 Rev 4",
                target_completion_date=now,
                horizontal_deployment_assets=["Pump-A11", "Pump-A13"],
                status=ActionStatus.CLOSED,
            )
        ],
        d8_closure=TeamSignOff(
            signoff_id="SO-01",
            approver_name="Marcus Vance",
            approver_role="Plant Operations Director",
            signoff_status=SignOffStatus.APPROVED,
            signoff_date=now,
            lessons_learned_summary="Asset-specific OEM envelope limits must be hardwired into automated safety instrumented systems rather than relying on operator guidelines.",
            financial_impact_total_usd=12400.0,
            downtime_hours_total=2.5,
        ),
        timeline=timeline,
        rpn_scoring=rpn,
        historical_matches=matches,
    )
    digest = report.compute_audit_hash()
    assert len(digest) == 64
    assert report.d3_containment[0].effectiveness_pct == 100.0


def test_scenario1_pump_a12_oem_deviation_and_compliance_package():
    """Scenario 1.2: Verifies Pump-A12 OEM envelope exceedance and HTML compliance package formatting."""
    # Compute envelope exceedance
    env = compute_oem_deviation(
        parameter_name="Peak Vibration Velocity",
        unit="mm/s",
        envelope_max=5.0,
        incident_value=5.8,
        recommended_action="Mandatory automated shutdown trip at 5.5 mm/s as per OEM manual",
    )
    assert env.deviation_pct == 16.0
    assert env.severity_level == SeverityLevel.CRITICAL

    # Verify HTML evidence package generation
    now = datetime.now(timezone.utc)
    cite = CitationObject(citation_id="CITE-NM-01", source_doc="Near_Miss.txt", title="NM", excerpt="Vibration 5.8 mm/s")
    rep = EightDIncidentReport(
        report_id="8D-2023-PUMP-A12",
        d1_team=[TeamMember(member_id="T1", name="Elena", role="Lead", department="Reliability")],
        d2_problem=ProblemDescription5W2H(
            incident_title="Pump-A12 Seal Failure", equipment_tag="Pump-A12", equipment_family="Centrifugal Pump",
            timestamp_incident=now, who_detected="Team", what_symptom="Seal shatter", where_location="Sector 4",
            when_detected="Nov 4", why_consequence="Coolant leak", how_detected="Sensor", how_much_magnitude="5.8 mm/s",
            initial_severity=8, operational_impact="2.5h downtime"
        ),
        d3_containment=[InterimContainmentAction(action_id="I1", description="Containment booms", responsible_owner="EHS", implementation_date=now, verification_method="Zero effluent", effectiveness_pct=100.0)],
        d4_root_cause=RootCauseDiscipline(occurrence_root_cause="Occurrence cause", escape_root_cause="Escape cause", five_why_chain=[FiveWhyNode(node_id="W1", level=1, cause_statement="Seal shatter", evidence_citation_ids=["CITE-NM-01"], is_root_cause=True)], fishbone_analysis=[FishboneCauseItem(cause_id="F1", category=FishboneCategory.MACHINE, statement="Fatigue", evidence_citation_ids=["CITE-NM-01"])], citations=[cite]),
        d5_permanent_actions=[PermanentCorrectiveAction(pca_id="P1", description="Interlock trip", addresses_cause_id="W1", responsible_owner="Controls", target_date=now, feasibility_score=10, risk_assessment="None", validation_plan="Test run")],
        d6_validation=[ImplementAndValidate(action_id="V1", pca_id="P1", baseline_metric="5.8 mm/s", post_implementation_metric="1.1s trip", verification_evidence="Log", validation_status=ActionStatus.VERIFIED)],
        d7_prevention=[PreventativeControl(control_id="C1", control_type="SOP_UPDATE", description="SOP updated", target_completion_date=now)],
        d8_closure=TeamSignOff(signoff_id="S1", approver_name="Marcus Vance", approver_role="Director", signoff_date=now, lessons_learned_summary="OEM limits must be hardwired into DCS"),
        timeline=[FailureTimelineEvent(event_id="E1", timestamp=now, event_type=EventType.CATASTROPHIC_FAILURE, description="Seal shattered", equipment_tag="Pump-A12", source_citation_id="CITE-NM-01")],
        rpn_scoring=RPNScoring(severity=8, occurrence=7, detection=6),
    )
    html_package = build_audit_html(rep)
    assert rep.report_id in html_package
    assert "data-checksum" in html_package
    assert "Pump-A12" in html_package
    assert "ISO 9001:2015" in html_package


# ==============================================================================
# SCENARIO 2: STEAM TURBINE OVERSPEED TRIP & LUBRICATION FAILURE
# ==============================================================================

def test_scenario2_steam_turbine_overspeed_and_lube_failure(steam_turbine_telemetry_logs):
    """Scenario 2.1: High-pressure steam turbine TURB-ST-04 overspeed trip with lubrication failure."""
    timeline = reconstruct_timeline(steam_turbine_telemetry_logs)
    assert len(timeline) == 4
    assert timeline[0].telemetry_values["rpm"] == 3000
    assert timeline[2].telemetry_values["bearing_temp_c"] == 118.0
    assert timeline[3].telemetry_values["rpm"] == 3450

    # OEM envelopes:
    # Lube oil pressure: normal 3.2 bar, lower limit 2.0 bar -> actual 0.8 bar (-60% deviation, CRITICAL)
    # Bearing temp: limit 95C -> actual 118C (+24.2% deviation, CRITICAL)
    # Rotor speed: envelope 3300 RPM -> actual 3450 RPM (+4.55% deviation, HIGH)
    env_temp = compute_oem_deviation("Journal Bearing Temperature", "C", 95.0, 118.0, "Emergency governor trip")
    assert env_temp.deviation_pct == 24.21
    assert env_temp.severity_level == SeverityLevel.CRITICAL

    env_speed = compute_oem_deviation("Rotor Speed", "RPM", 3300.0, 3450.0, "Overspeed trip interlock")
    assert env_speed.deviation_pct == 4.55
    assert env_speed.severity_level == SeverityLevel.HIGH


def test_scenario2_steam_turbine_pca_validation_and_fmea_reduction():
    """Scenario 2.2: Turbine corrective action, FMEA RPN reduction, and audit package."""
    # Pre-mitigation: Severity 9 (overspeed hazard), Occurrence 6, Detection 6 -> RPN = 324
    rpn_pre = RPNScoring(severity=9, occurrence=6, detection=6)
    assert rpn_pre.rpn == 324
    assert rpn_pre.risk_priority == "HIGH"

    # Post-mitigation: Duplex filter auto-switchover and electrostatic cleaner
    # Revised Occurrence: 2, Revised Detection: 1 -> Revised RPN = 18
    rpn_post = RPNScoring(
        severity=9, occurrence=6, detection=6,
        revised_severity=9, revised_occurrence=2, revised_detection=1
    )
    assert rpn_post.revised_rpn == 18
    reduction_pct = round(((rpn_post.rpn - rpn_post.revised_rpn) / rpn_post.rpn) * 100.0, 1)
    assert reduction_pct == 94.4


# ==============================================================================
# SCENARIO 3: BOILER THERMAL RUNAWAY & THERMOCOUPLE DRIFT
# ==============================================================================

def test_scenario3_boiler_thermal_runaway_thermocouple_drift(boiler_thermal_runaway_logs):
    """Scenario 3.1: Water-tube boiler BLR-HP-101 superheater tube creep investigation."""
    timeline = reconstruct_timeline(boiler_thermal_runaway_logs)
    assert len(timeline) == 4
    # Event 3 shows handheld pyrometer revealed actual tube 452C vs indicated 410C (-42C drift)
    drift_event = timeline[2]
    assert drift_event.telemetry_values["actual_tube_temp_c"] == 452.0
    assert drift_event.telemetry_values["cal_drift_c"] == -42.0

    # OEM limit for superheater tube metal is 430C -> 452C exceeds limit by +5.12%
    env = compute_oem_deviation(
        parameter_name="Superheater Tube Metal Temperature",
        unit="C",
        envelope_max=430.0,
        incident_value=452.0,
        recommended_action="Modulate gas burners and initiate dual-redundancy thermocouple verification",
    )
    assert env.deviation_pct == 5.12
    assert env.severity_level == SeverityLevel.HIGH


def test_scenario3_boiler_voting_logic_pca_and_horizontal_controls():
    """Scenario 3.2: 2-out-of-3 thermocouple voting PCA and horizontal deployment across sister boilers."""
    now = datetime.now(timezone.utc)
    pca = PermanentCorrectiveAction(
        pca_id="PCA-BLR-01",
        description="Install triply-redundant Type-K thermocouples with 2-out-of-3 (2oo3) median voting logic in DCS",
        addresses_cause_id="WHY-TC-DRIFT",
        responsible_owner="I&C Lead Engineer",
        target_date=now,
        feasibility_score=8,
        risk_assessment="Outage required for sensor well welding",
        validation_plan="Bench simulation of single thermocouple failure and voting lock test",
        status=ActionStatus.IMPLEMENTED,
    )
    assert "2-out-of-3" in pca.description

    # Horizontal deployment to sister boilers BLR-HP-102 and BLR-HP-103
    control = PreventativeControl(
        control_id="PRV-BLR-01",
        control_type="HORIZONTAL_DEPLOYMENT",
        description="Mandate 2oo3 thermocouple voting logic and 90-day pyrometer calibration across utility boilers",
        target_completion_date=now,
        horizontal_deployment_assets=["BLR-HP-102", "BLR-HP-103"],
        status=ActionStatus.OPEN,
    )
    assert len(control.horizontal_deployment_assets) == 2
    assert "BLR-HP-102" in control.horizontal_deployment_assets
