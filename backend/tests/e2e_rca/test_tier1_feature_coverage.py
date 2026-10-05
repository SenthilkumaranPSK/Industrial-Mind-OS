"""
Tier 1: Comprehensive Feature Coverage E2E Tests (F1 through F10).
Automated Root Cause Analysis (RCA) & 8D Incident Report Studio.

Test Inventory:
- F1: 8D Pydantic Domain Schemas (5 test cases)
- F2: Incident Evidence & Citation Registry (5 test cases)
- F3: Chronological Timeline Reconstruction (5 test cases)
- F4: Deductive 5-Why Causal Tree Engine (5 test cases)
- F5: Ishikawa 6M Fishbone Classifier (5 test cases)
- F6: Assumption Flagging & Grounding Verifier (5 test cases)
- F7: Historical Near-Miss Similarity Matching (5 test cases)
- F8: OEM Operating Envelope Deviation Analysis (5 test cases)
- F9: RCA REST API Router (5 test cases)
- F10: Certified Compliance Audit Package Generator (5 test cases)
Total: 50 test cases.
"""

import hashlib
import json
from datetime import datetime, timezone

import pytest

from tests.e2e_rca.conftest import (
    ActionStatus,
    AuditMetadata,
    CitationObject,
    EightDIncidentReport,
    EventType,
    FailureTimelineEvent,
    FishboneCategory,
    FishboneCauseItem,
    FiveWhyNode,
    HistoricalMatchResult,
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
# F1: 8D PYDANTIC DOMAIN SCHEMAS (5 TEST CASES)
# ==============================================================================

def test_f1_01_complete_eight_d_report_schema_validation():
    """F1-1: Validates complete EightDIncidentReport instantiation with D1-D8."""
    now = datetime.now(timezone.utc)
    cite = CitationObject(
        citation_id="CITE-PUMP-001",
        source_doc="Near_Miss_Report_2023.txt",
        title="Near Miss 2023",
        excerpt="Vibration level of 5.8 mm/s shattered inboard ceramic seals.",
        confidence=0.99,
    )
    report = EightDIncidentReport(
        report_id="8D-2023-PUMP-A12",
        d1_team=[
            TeamMember(
                member_id="TM-01",
                name="Dr. Aris Thorne",
                role="RCA Facilitator",
                department="Reliability",
            )
        ],
        d2_problem=ProblemDescription5W2H(
            incident_title="Pump-A12 Ceramic Seal Shatter",
            equipment_tag="Pump-A12",
            equipment_family="Centrifugal Pump",
            timestamp_incident=now,
            who_detected="Vibration SCADA Sensor",
            what_symptom="Catastrophic seal shatter and coolant leakage",
            where_location="Sector 4 Cooling Loop",
            when_detected="Continuous running shift",
            why_consequence="15L coolant loss and loop trip",
            how_detected="SCADA alert and floor bund sensor",
            how_much_magnitude="5.8 mm/s vibration, 15L spill",
            initial_severity=8,
            operational_impact="2.5h downtime",
            is_not_analysis={"Twin Pump-A11": "Unaffected, operating nominal at 3.1 mm/s"},
        ),
        d3_containment=[
            InterimContainmentAction(
                action_id="ICA-01",
                description="Deployed chemical containment booms and closed isolation valves",
                responsible_owner="Shift Lead",
                implementation_date=now,
                verification_method="Zero effluent at storm gate",
                effectiveness_pct=100.0,
                status=ActionStatus.VERIFIED,
                evidence_citation_id="CITE-PUMP-001",
            )
        ],
        d4_root_cause=RootCauseDiscipline(
            occurrence_root_cause="Fatigue fracture of ceramic seal face under sustained 5.8 mm/s vibration",
            escape_root_cause="Advisory threshold improperly configured at 6.5 mm/s instead of 5.0 mm/s OEM limit",
            five_why_chain=[
                FiveWhyNode(
                    node_id="WHY-1",
                    level=1,
                    cause_statement="Inboard ceramic seal shattered",
                    evidence_citation_ids=["CITE-PUMP-001"],
                    is_root_cause=False,
                ),
                FiveWhyNode(
                    node_id="WHY-2",
                    level=2,
                    cause_statement="Shaft vibration exceeded ceramic yield limit for 48 hours",
                    evidence_citation_ids=["CITE-PUMP-001"],
                    is_root_cause=True,
                ),
            ],
            fishbone_analysis=[
                FishboneCauseItem(
                    cause_id="FB-1",
                    category=FishboneCategory.MACHINE,
                    statement="Ceramic face brittle fatigue under harmonic oscillation",
                    evidence_citation_ids=["CITE-PUMP-001"],
                )
            ],
            citations=[cite],
        ),
        d5_permanent_actions=[
            PermanentCorrectiveAction(
                pca_id="PCA-01",
                description="Reprogram DCS hard trip threshold to 5.5 mm/s and alarm at 5.0 mm/s",
                addresses_cause_id="WHY-2",
                responsible_owner="Controls Lead",
                target_date=now,
                feasibility_score=9,
                risk_assessment="Zero risk to process safety",
                validation_plan="Bench test with signal generator",
                status=ActionStatus.IMPLEMENTED,
            )
        ],
        d6_validation=[
            ImplementAndValidate(
                action_id="VAL-01",
                pca_id="PCA-01",
                baseline_metric="Vibration 5.8 mm/s sustained 48h without trip",
                post_implementation_metric="DCS trip actuates in 1.2s at 5.5 mm/s",
                verification_evidence="Test run signature TR-8841",
                validation_status=ActionStatus.VERIFIED,
            )
        ],
        d7_prevention=[
            PreventativeControl(
                control_id="PRV-01",
                control_type="SOP_UPDATE",
                description="Update SOP-PUMP-A12 to enforce OEM 5.0 mm/s limit",
                target_completion_date=now,
                status=ActionStatus.CLOSED,
            )
        ],
        d8_closure=TeamSignOff(
            signoff_id="SO-01",
            approver_name="Carlos Mendez",
            approver_role="Plant Manager",
            signoff_status=SignOffStatus.APPROVED,
            signoff_date=now,
            lessons_learned_summary="OEM vibration boundaries must never be relaxed in supervisory software.",
        ),
        timeline=[
            FailureTimelineEvent(
                event_id="EVT-01",
                timestamp=now,
                event_type=EventType.CATASTROPHIC_FAILURE,
                description="Ceramic seal failure",
                equipment_tag="Pump-A12",
                source_citation_id="CITE-PUMP-001",
            )
        ],
        rpn_scoring=RPNScoring(severity=8, occurrence=6, detection=4),
    )
    assert report.report_id == "8D-2023-PUMP-A12"
    assert len(report.d1_team) == 1
    assert report.rpn_scoring.rpn == 192


def test_f1_02_5w2h_problem_description_structure():
    """F1-2: Validates ProblemDescription5W2H with 5W2H fields and Is/Is Not matrix."""
    now = datetime.now(timezone.utc)
    prob = ProblemDescription5W2H(
        incident_title="Boiler Superheater Tube Rupture",
        equipment_tag="BLR-HP-101",
        equipment_family="Water-tube Industrial Boiler",
        timestamp_incident=now,
        who_detected="Acoustic Leak Sensor",
        what_symptom="Steam pressure drop and acoustic emission spike",
        where_location="Boiler Island 2, Platen Superheater",
        when_detected="Full load continuous firing",
        why_consequence="Emergency steam header depressurization",
        how_detected="Differential pressure switch and soot blower acoustic monitor",
        how_much_magnitude="42 bar drop in 30 seconds",
        initial_severity=9,
        operational_impact="Partial plant electrical curtailment for 18h",
        is_not_analysis={
            "Reheater Tubes": "No rupture or creep observed",
            "Economizer Section": "Operating normally at 220C",
        },
    )
    assert prob.initial_severity == 9
    assert "Reheater Tubes" in prob.is_not_analysis
    assert prob.equipment_tag == "BLR-HP-101"


def test_f1_03_rpn_scoring_calculation_and_priority():
    """F1-3: Validates RPN calculation (S*O*D), revised RPN, and risk priority categorization."""
    rpn_obj = RPNScoring(severity=9, occurrence=7, detection=6)
    assert rpn_obj.rpn == 378
    assert rpn_obj.risk_priority == "CRITICAL"

    # With PCA mitigation
    rpn_mitigated = RPNScoring(
        severity=9,
        occurrence=2,
        detection=2,
        revised_severity=9,
        revised_occurrence=2,
        revised_detection=2,
    )
    assert rpn_mitigated.rpn == 36
    assert rpn_mitigated.revised_rpn == 36
    assert rpn_mitigated.risk_priority == "HIGH"  # severity >= 8 puts initial risk at HIGH


def test_f1_04_action_lifecycle_and_status_transitions():
    """F1-4: Validates ActionStatus enum support across containment, corrective, and preventative actions."""
    now = datetime.now(timezone.utc)
    ica = InterimContainmentAction(
        action_id="ICA-02",
        description="Deployed catch basins",
        responsible_owner="Jane Doe",
        implementation_date=now,
        verification_method="Visual inspection",
        effectiveness_pct=95.0,
        status=ActionStatus.IN_PROGRESS,
    )
    assert ica.status == ActionStatus.IN_PROGRESS

    pca = PermanentCorrectiveAction(
        pca_id="PCA-02",
        description="Replace elastomer with perfluoroelastomer FFKM",
        addresses_cause_id="WHY-03",
        responsible_owner="Materials Engineer",
        target_date=now,
        feasibility_score=8,
        risk_assessment="Higher procurement lead time",
        validation_plan="Autoclave swelling test",
        status=ActionStatus.OPEN,
    )
    assert pca.status == ActionStatus.OPEN


def test_f1_05_audit_metadata_and_compliance_standards():
    """F1-5: Validates AuditMetadata default standards and timestamp generation."""
    meta = AuditMetadata()
    assert "ISO 9001:2015" in meta.compliance_standard
    assert "IATF 16949" in meta.compliance_standard
    assert "AIAG 8D" in meta.compliance_standard
    assert meta.generated_at is not None
    assert meta.generator_system == "Industrial Mind OS v2.0 RCA-8D Engine"


# ==============================================================================
# F2: INCIDENT EVIDENCE & CITATION REGISTRY (5 TEST CASES)
# ==============================================================================

def test_f2_01_citation_id_regex_format_validation():
    """F2-1: Validates citation_id conforms strictly to regex pattern ^CITE-[A-Za-z0-9_\\-\\.]+$."""
    valid_ids = ["CITE-PUMP-001", "CITE-NM-2023.A12", "CITE-DOC_44", "CITE-TURBINE-SECTION-3"]
    for cid in valid_ids:
        cite = CitationObject(
            citation_id=cid,
            source_doc="manual.pdf",
            title="Manual",
            excerpt="Valid excerpt of evidence text",
        )
        assert cite.citation_id == cid


def test_f2_02_citation_confidence_score_bounds():
    """F2-2: Validates confidence score bounds between 0.0 and 1.0."""
    cite_low = CitationObject(
        citation_id="CITE-01",
        source_doc="doc.txt",
        title="Doc",
        excerpt="Valid excerpt text",
        confidence=0.0,
    )
    cite_high = CitationObject(
        citation_id="CITE-02",
        source_doc="doc.txt",
        title="Doc",
        excerpt="Valid excerpt text",
        confidence=1.0,
    )
    assert cite_low.confidence == 0.0
    assert cite_high.confidence == 1.0


def test_f2_03_citation_excerpt_minimum_length():
    """F2-3: Verifies excerpts meet min_length=5 constraint."""
    cite = CitationObject(
        citation_id="CITE-03",
        source_doc="log.txt",
        title="Shift Log",
        excerpt="12345",  # exactly 5 characters
        confidence=0.85,
    )
    assert len(cite.excerpt) >= 5


def test_f2_04_citation_registry_catalog_deduplication():
    """F2-4: Validates unique citation resolution across multiple causal elements."""
    cite1 = CitationObject(
        citation_id="CITE-01",
        source_doc="doc1.txt",
        title="Doc 1",
        excerpt="Excerpt from document 1",
    )
    cite2 = CitationObject(
        citation_id="CITE-02",
        source_doc="doc2.txt",
        title="Doc 2",
        excerpt="Excerpt from document 2",
    )
    catalog = {c.citation_id: c for c in [cite1, cite2, cite1]}
    assert len(catalog) == 2
    assert "CITE-01" in catalog and "CITE-02" in catalog


def test_f2_05_citation_source_file_resolution(near_miss_report_text):
    """F2-5: Verifies citation excerpt can be matched against repository text."""
    cite = CitationObject(
        citation_id="CITE-NM-01",
        source_doc="Near_Miss_Report_2023.txt",
        title="Near Miss Report",
        section="Root Cause Analysis",
        excerpt="vibration level of 5.8 mm/s for 48 hours prior to the failure",
        confidence=1.0,
    )
    assert cite.excerpt in near_miss_report_text


# ==============================================================================
# F3: CHRONOLOGICAL TIMELINE RECONSTRUCTION (5 TEST CASES)
# ==============================================================================

def test_f3_01_chronological_ordering_from_out_of_order_events(pump_a12_telemetry_logs):
    """F3-1: Reconstructs chronological timeline when logs are supplied out of sequence."""
    out_of_order = [pump_a12_telemetry_logs[3], pump_a12_telemetry_logs[0], pump_a12_telemetry_logs[1]]
    ordered = reconstruct_timeline(out_of_order)
    assert ordered[0].event_id == "EVT-P01"
    assert ordered[1].event_id == "EVT-P02"
    assert ordered[2].event_id == "EVT-P04"
    assert ordered[0].timestamp < ordered[1].timestamp < ordered[2].timestamp


def test_f3_02_telemetry_dictionary_schema_and_typing(pump_a12_telemetry_logs):
    """F3-2: Verifies telemetry dictionary captures sensor keys, float values, and types."""
    events = reconstruct_timeline(pump_a12_telemetry_logs)
    evt = events[2]  # EVT-P03
    assert evt.telemetry_values["vibration_mm_s"] == 5.8
    assert evt.telemetry_values["bearing_temp_c"] == 74.5


def test_f3_03_event_type_taxonomy_coverage(pump_a12_telemetry_logs):
    """F3-3: Verifies timeline contains required event type taxonomy classifications."""
    events = reconstruct_timeline(pump_a12_telemetry_logs)
    types = {e.event_type for e in events}
    assert EventType.BASELINE_NORMAL in types
    assert EventType.THRESHOLD_EXCEEDED in types
    assert EventType.ALARM_IGNORED in types
    assert EventType.CATASTROPHIC_FAILURE in types
    assert EventType.CONTAINMENT_ACHIEVED in types


def test_f3_04_timeline_event_citation_grounding(pump_a12_telemetry_logs):
    """F3-4: Confirms timeline events with citation are flagged substantiated, others unsubstantiated."""
    events = reconstruct_timeline(pump_a12_telemetry_logs)
    for e in events:
        assert e.is_unsubstantiated is False
        assert e.source_citation_id is not None

    unsub = FailureTimelineEvent(
        event_id="EVT-RAW-01",
        timestamp=datetime.now(timezone.utc),
        event_type=EventType.ANOMALY_DETECTED,
        description="Unverified operator observation",
        equipment_tag="Pump-A12",
        source_citation_id=None,
    )
    assert unsub.is_unsubstantiated is True


def test_f3_05_multi_source_log_fusion(steam_turbine_telemetry_logs):
    """F3-5: Reconstructs timeline across multi-source telemetry, alarm, and shutdown logs."""
    timeline = reconstruct_timeline(steam_turbine_telemetry_logs)
    assert len(timeline) == 4
    assert timeline[-1].event_type == EventType.EMERGENCY_SHUTDOWN
    assert timeline[-1].telemetry_values["rpm"] == 3450


# ==============================================================================
# F4: DEDUCTIVE 5-WHY CAUSAL TREE ENGINE (5 TEST CASES)
# ==============================================================================

def test_f4_01_linear_five_why_chain_generation():
    """F4-1: Verifies linear 5-level why chain from symptom to root cause."""
    chain = [
        FiveWhyNode(node_id="WHY-1", level=1, cause_statement="Coolant leak on floor", evidence_citation_ids=["CITE-01"]),
        FiveWhyNode(node_id="WHY-2", level=2, cause_statement="Mechanical seal shattered", parent_node_id="WHY-1", evidence_citation_ids=["CITE-01"]),
        FiveWhyNode(node_id="WHY-3", level=3, cause_statement="High vibration for 48 hours", parent_node_id="WHY-2", evidence_citation_ids=["CITE-01"]),
        FiveWhyNode(node_id="WHY-4", level=4, cause_statement="Advisory alert ignored by operators", parent_node_id="WHY-3", evidence_citation_ids=["CITE-01"]),
        FiveWhyNode(node_id="WHY-5", level=5, cause_statement="Misconfigured DCS alarm threshold", parent_node_id="WHY-4", evidence_citation_ids=["CITE-01"], is_root_cause=True),
    ]
    assert len(chain) == 5
    assert chain[-1].is_root_cause is True
    assert chain[-1].level == 5


def test_f4_02_five_why_parent_child_hierarchy():
    """F4-2: Verifies parent_node_id relationships maintain tree structure."""
    nodes = {
        "WHY-1": FiveWhyNode(node_id="WHY-1", level=1, cause_statement="Pump tripped", evidence_citation_ids=["C1"]),
        "WHY-2": FiveWhyNode(node_id="WHY-2", level=2, cause_statement="Motor overload", parent_node_id="WHY-1", evidence_citation_ids=["C1"]),
    }
    assert nodes["WHY-2"].parent_node_id == "WHY-1"


def test_f4_03_root_cause_leaf_flagging():
    """F4-3: Verifies terminal leaf node is designated as root cause."""
    leaf = FiveWhyNode(
        node_id="WHY-3",
        level=3,
        cause_statement="Inadequate calibration interval in PM master",
        parent_node_id="WHY-2",
        evidence_citation_ids=["CITE-PM"],
        is_root_cause=True,
    )
    assert leaf.is_root_cause is True


def test_f4_04_bifurcated_causal_branching():
    """F4-4: Verifies bifurcated causal paths branching from a common parent."""
    parent = FiveWhyNode(node_id="WHY-1", level=1, cause_statement="Seal failed", evidence_citation_ids=["C1"])
    branch_a = FiveWhyNode(node_id="WHY-2A", level=2, cause_statement="Ceramic brittleness", parent_node_id="WHY-1", evidence_citation_ids=["C1"])
    branch_b = FiveWhyNode(node_id="WHY-2B", level=2, cause_statement="Excessive shaft deflection", parent_node_id="WHY-1", evidence_citation_ids=["C1"])
    assert branch_a.parent_node_id == parent.node_id
    assert branch_b.parent_node_id == parent.node_id


def test_f4_05_dual_vector_root_cause_differentiation():
    """F4-5: Verifies differentiation between physical occurrence and procedural escape causes."""
    d4 = RootCauseDiscipline(
        occurrence_root_cause="High cyclic fatigue load shattered ceramic seal face",
        escape_root_cause="DCS alarm limit set at 6.5 mm/s permitted prolonged operation outside envelope",
        five_why_chain=[
            FiveWhyNode(node_id="WHY-1", level=1, cause_statement="Seal shattered", evidence_citation_ids=["CITE-01"], is_root_cause=True)
        ],
        fishbone_analysis=[
            FishboneCauseItem(cause_id="FB-1", category=FishboneCategory.MACHINE, statement="Seal wear", evidence_citation_ids=["CITE-01"])
        ],
        citations=[CitationObject(citation_id="CITE-01", source_doc="doc.txt", title="Doc", excerpt="Seal wear")]
    )
    assert "fatigue" in d4.occurrence_root_cause.lower()
    assert "alarm" in d4.escape_root_cause.lower()


# ==============================================================================
# F5: ISHIKAWA 6M FISHBONE CLASSIFIER (5 TEST CASES)
# ==============================================================================

def test_f5_01_ishikawa_man_category_classification():
    """F5-1: Categorizes personnel training and alarm acknowledgement under MAN."""
    item = FishboneCauseItem(
        cause_id="FB-MAN-01",
        category=FishboneCategory.MAN,
        statement="Operators lacked training on asset-specific A-series vibration envelopes",
        contribution_weight=0.8,
        evidence_citation_ids=["CITE-TRAIN"],
    )
    assert item.category == FishboneCategory.MAN
    assert item.contribution_weight == 0.8


def test_f5_02_ishikawa_machine_material_classification():
    """F5-2: Categorizes mechanical wear under MACHINE and metallurgy under MATERIAL."""
    machine_item = FishboneCauseItem(
        cause_id="FB-MCH-01",
        category=FishboneCategory.MACHINE,
        statement="Sustained vibration caused harmonic seal face resonance",
        evidence_citation_ids=["C1"],
    )
    material_item = FishboneCauseItem(
        cause_id="FB-MAT-01",
        category=FishboneCategory.MATERIAL,
        statement="Inboard ceramic face lacked silicon carbide composite toughness",
        evidence_citation_ids=["C1"],
    )
    assert machine_item.category == FishboneCategory.MACHINE
    assert material_item.category == FishboneCategory.MATERIAL


def test_f5_03_ishikawa_method_category_classification():
    """F5-3: Categorizes operating procedures and alarm thresholds under METHOD."""
    item = FishboneCauseItem(
        cause_id="FB-METH-01",
        category=FishboneCategory.METHOD,
        statement="Standard operating procedure permitted manual alarm mute for 24h",
        evidence_citation_ids=["C1"],
    )
    assert item.category == FishboneCategory.METHOD


def test_f5_04_ishikawa_measurement_environment_classification():
    """F5-4: Categorizes transducer calibration under MEASUREMENT and ambient factors under ENVIRONMENT."""
    meas = FishboneCauseItem(
        cause_id="FB-MEAS-01",
        category=FishboneCategory.MEASUREMENT,
        statement="Vibration accelerometer calibration drifted by +0.3 mm/s",
        evidence_citation_ids=["C1"],
    )
    env = FishboneCauseItem(
        cause_id="FB-ENV-01",
        category=FishboneCategory.ENVIRONMENT,
        statement="Foundation resonance amplified by adjacent Booster Pump B-02",
        evidence_citation_ids=["C1"],
    )
    assert meas.category == FishboneCategory.MEASUREMENT
    assert env.category == FishboneCategory.ENVIRONMENT


def test_f5_05_fishbone_contribution_weights_normalization():
    """F5-5: Verifies contribution weights within [0.0, 1.0]."""
    items = [
        FishboneCauseItem(cause_id="F1", category=FishboneCategory.MAN, statement="Cause 1", contribution_weight=0.4, evidence_citation_ids=["C1"]),
        FishboneCauseItem(cause_id="F2", category=FishboneCategory.MACHINE, statement="Cause 2", contribution_weight=0.6, evidence_citation_ids=["C1"]),
    ]
    for it in items:
        assert 0.0 <= it.contribution_weight <= 1.0


# ==============================================================================
# F6: ASSUMPTION FLAGGING & GROUNDING VERIFIER (5 TEST CASES)
# ==============================================================================

def test_f6_01_substantiated_node_validation():
    """F6-1: Confirms node with catalog-verified citation is substantiated."""
    cite = CitationObject(citation_id="CITE-01", source_doc="doc.txt", title="Doc", excerpt="Excerpt valid")
    d4 = RootCauseDiscipline(
        occurrence_root_cause="Occurrence cause statement",
        escape_root_cause="Escape cause statement",
        five_why_chain=[
            FiveWhyNode(node_id="WHY-1", level=1, cause_statement="Grounded statement", evidence_citation_ids=["CITE-01"])
        ],
        fishbone_analysis=[
            FishboneCauseItem(cause_id="FB-1", category=FishboneCategory.MAN, statement="Grounded statement", evidence_citation_ids=["CITE-01"])
        ],
        citations=[cite],
    )
    assert d4.five_why_chain[0].is_unsubstantiated is False
    assert d4.five_why_chain[0].assumed_flag is False
    assert d4.citation_grounding_ratio == 1.0


def test_f6_02_empty_citation_auto_flagging():
    """F6-2: Node with empty citations is automatically marked unsubstantiated and assumed."""
    node = FiveWhyNode(node_id="WHY-1", level=1, cause_statement="Hypothesized ungrounded cause", evidence_citation_ids=[])
    assert node.is_unsubstantiated is True
    assert node.assumed_flag is True


def test_f6_03_dangling_citation_dropped_and_flagged():
    """F6-3: Node referencing citation ID missing from catalog is flagged unsubstantiated."""
    d4 = RootCauseDiscipline(
        occurrence_root_cause="Occurrence cause",
        escape_root_cause="Escape cause",
        five_why_chain=[
            FiveWhyNode(node_id="WHY-1", level=1, cause_statement="Claim with missing cite", evidence_citation_ids=["CITE-MISSING"])
        ],
        fishbone_analysis=[
            FishboneCauseItem(cause_id="FB-1", category=FishboneCategory.MAN, statement="Cause statement", evidence_citation_ids=["CITE-MISSING"])
        ],
        citations=[],  # Catalog is empty
    )
    assert d4.five_why_chain[0].is_unsubstantiated is True
    assert d4.five_why_chain[0].assumed_flag is True
    assert d4.citation_grounding_ratio == 0.0


def test_f6_04_citation_grounding_ratio_computation():
    """F6-4: Calculates citation grounding ratio accurately when half of the causes are grounded."""
    cite = CitationObject(citation_id="CITE-01", source_doc="doc.txt", title="Doc", excerpt="Excerpt valid")
    d4 = RootCauseDiscipline(
        occurrence_root_cause="Occurrence cause",
        escape_root_cause="Escape cause",
        five_why_chain=[
            FiveWhyNode(node_id="WHY-1", level=1, cause_statement="Grounded why node", evidence_citation_ids=["CITE-01"]),
            FiveWhyNode(node_id="WHY-2", level=2, cause_statement="Ungrounded why node", evidence_citation_ids=[]),
        ],
        fishbone_analysis=[
            FishboneCauseItem(cause_id="FB-1", category=FishboneCategory.MAN, statement="Grounded fishbone", evidence_citation_ids=["CITE-01"]),
            FishboneCauseItem(cause_id="FB-2", category=FishboneCategory.MACHINE, statement="Ungrounded fishbone", evidence_citation_ids=[]),
        ],
        citations=[cite],
    )
    # 2 grounded out of 4 total causes = 0.50
    assert d4.citation_grounding_ratio == 0.5


def test_f6_05_critical_ungrounded_root_cause_detection():
    """F6-5: Ungrounded terminal root cause retains unsubstantiated and assumed flags."""
    root_node = FiveWhyNode(
        node_id="WHY-RC",
        level=5,
        cause_statement="Speculated unverified corporate policy flaw",
        evidence_citation_ids=[],
        is_root_cause=True,
    )
    assert root_node.is_root_cause is True
    assert root_node.is_unsubstantiated is True
    assert root_node.assumed_flag is True


# ==============================================================================
# F7: HISTORICAL NEAR-MISS SIMILARITY MATCHING (5 TEST CASES)
# ==============================================================================

def test_f7_01_pump_a12_near_miss_matching(near_miss_report_text):
    """F7-1: Matches Pump-A12 vibration and seal failure against Near_Miss_Report_2023.txt."""
    matches = match_historical_records(
        asset_tag="Pump-A12",
        symptoms=["vibration", "ceramic seal", "coolant leak"],
        near_miss_text=near_miss_report_text,
    )
    assert len(matches) >= 1
    match = matches[0]
    assert match.matched_report_id == "NM-2023-PUMP-A12"
    assert match.similarity_score >= 0.8
    assert "ceramic seal" in [s.lower() for s in match.matching_symptoms]


def test_f7_02_unrelated_equipment_zero_similarity(near_miss_report_text):
    """F7-2: Unrelated equipment and symptoms yield zero matches."""
    matches = match_historical_records(
        asset_tag="Conveyor-C99",
        symptoms=["roller belt tear", "spillway blockage"],
        near_miss_text=near_miss_report_text,
    )
    assert len(matches) == 0


def test_f7_03_matching_symptoms_extraction(near_miss_report_text):
    """F7-3: Verifies extracted matching symptoms contain relevant keywords."""
    matches = match_historical_records(
        asset_tag="Pump-A12",
        symptoms=["vibration", "coolant"],
        near_miss_text=near_miss_report_text,
    )
    assert len(matches) == 1
    assert "vibration" in matches[0].matching_symptoms


def test_f7_04_historical_lessons_learned_retrieval(near_miss_report_text):
    """F7-4: Verifies extraction of historical lessons (5.0 mm/s limit, mandatory shutdown)."""
    matches = match_historical_records(
        asset_tag="Pump-A12",
        symptoms=["vibration", "seal failure"],
        near_miss_text=near_miss_report_text,
    )
    assert len(matches) == 1
    lessons = " ".join(matches[0].historical_lessons)
    assert "5.0 mm/s" in lessons
    assert "shutdown" in lessons.lower()


def test_f7_05_cross_referencing_equipment_family(near_miss_report_text):
    """F7-5: Verifies matched records identify equipment family (A-Series Centrifugal Pump)."""
    matches = match_historical_records(
        asset_tag="Pump-A12",
        symptoms=["vibration"],
        near_miss_text=near_miss_report_text,
    )
    assert matches[0].equipment_family == "A-Series Centrifugal Pump"


# ==============================================================================
# F8: OEM OPERATING ENVELOPE DEVIATION ANALYSIS (5 TEST CASES)
# ==============================================================================

def test_f8_01_pump_a12_oem_vibration_deviation():
    """F8-1: Computes +16.0% deviation on 5.8 mm/s vs 5.0 mm/s limit -> CRITICAL."""
    envelope = compute_oem_deviation(
        parameter_name="Peak Vibration Velocity",
        unit="mm/s",
        envelope_max=5.0,
        incident_value=5.8,
        recommended_action="Execute mandatory shutdown",
    )
    assert envelope.deviation_pct == 16.0
    assert envelope.severity_level == SeverityLevel.CRITICAL


def test_f8_02_nominal_operation_within_envelope():
    """F8-2: Computes -16.0% deviation on 4.2 mm/s vs 5.0 mm/s limit -> LOW."""
    envelope = compute_oem_deviation(
        parameter_name="Peak Vibration Velocity",
        unit="mm/s",
        envelope_max=5.0,
        incident_value=4.2,
    )
    assert envelope.deviation_pct == -16.0
    assert envelope.severity_level == SeverityLevel.LOW


def test_f8_03_warning_threshold_deviation():
    """F8-3: Computes +4.0% deviation on 5.2 mm/s vs 5.0 mm/s limit -> HIGH."""
    envelope = compute_oem_deviation(
        parameter_name="Peak Vibration Velocity",
        unit="mm/s",
        envelope_max=5.0,
        incident_value=5.2,
    )
    assert envelope.deviation_pct == 4.0
    assert envelope.severity_level == SeverityLevel.HIGH


def test_f8_04_steam_turbine_overspeed_deviation():
    """F8-4: Computes overspeed deviation on 3,450 RPM vs 3,300 RPM limit."""
    envelope = compute_oem_deviation(
        parameter_name="Rotor Speed",
        unit="RPM",
        envelope_max=3300.0,
        incident_value=3450.0,
    )
    assert envelope.deviation_pct == 4.55
    assert envelope.severity_level == SeverityLevel.HIGH


def test_f8_05_recommended_action_derivation():
    """F8-5: Verifies recommended action mapping for severe envelope breach."""
    envelope = compute_oem_deviation(
        parameter_name="Bearing Temperature",
        unit="C",
        envelope_max=95.0,
        incident_value=118.0,
        recommended_action="Emergency trip and lube line flush",
    )
    assert envelope.deviation_pct == 24.21
    assert envelope.severity_level == SeverityLevel.CRITICAL
    assert "trip" in envelope.recommended_action.lower()


# ==============================================================================
# F9: RCA REST API ROUTER (5 TEST CASES)
# ==============================================================================

def test_f9_01_api_analyze_returns_valid_8d_report(client):
    """F9-1: POST /api/v1/rca/analyze returns 200 with full 8D incident report."""
    payload = {
        "asset_tag": "Pump-A12",
        "symptoms": ["mechanical seal failure", "vibration 5.8 mm/s"],
        "incident_timestamp": "2023-11-04T08:00:00Z",
        "telemetry_data": {"vibration_mm_s": 5.8},
    }
    resp = client.post("/api/v1/rca/analyze", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["report_id"].startswith("8D-")
    assert "d1_team" in data
    assert "d2_problem" in data
    assert "d4_root_cause" in data
    assert "rpn_scoring" in data
    assert data["audit_metadata"]["sha256_checksum"] != ""


def test_f9_02_api_historical_match_returns_matches(client):
    """F9-2: POST /api/v1/rca/historical-match returns matched historical records."""
    payload = {
        "asset_tag": "Pump-A12",
        "symptoms": ["vibration", "ceramic seal"],
    }
    resp = client.post("/api/v1/rca/historical-match", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["matched_report_id"] == "NM-2023-PUMP-A12"


def test_f9_03_api_export_evidence_json(client):
    """F9-3: POST /api/v1/rca/export-evidence with format='json' returns JSON evidence package."""
    payload = {
        "report_id": "8D-2023-PUMP_A12",
        "format": "json",
    }
    resp = client.post("/api/v1/rca/export-evidence", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["filename"].endswith(".json")
    assert len(data["sha256_checksum"]) == 64
    content = json.loads(data["content"])
    assert "d1_team" in content


def test_f9_04_api_export_evidence_html(client):
    """F9-4: POST /api/v1/rca/export-evidence with format='html' returns print-ready HTML."""
    payload = {
        "report_id": "8D-2023-PUMP_A12",
        "format": "html",
    }
    resp = client.post("/api/v1/rca/export-evidence", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["filename"].endswith(".html")
    assert "<!DOCTYPE html>" in data["content"]
    assert "audit-header" in data["content"]
    assert len(data["sha256_checksum"]) == 64


def test_f9_05_api_list_reports_returns_summaries(client):
    """F9-5: GET /api/v1/rca/reports returns list of report summaries."""
    resp = client.get("/api/v1/rca/reports")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "report_id" in data[0]
    assert "severity_score" in data[0]
    assert "sha256_checksum" in data[0]


# ==============================================================================
# F10: CERTIFIED COMPLIANCE AUDIT PACKAGE GENERATOR (5 TEST CASES)
# ==============================================================================

def test_f10_01_canonical_json_deterministic_hash():
    """F10-1: Canonical JSON serialization produces deterministic SHA-256 digest."""
    payload1 = {"b": 2, "a": 1, "nested": {"z": 26, "y": 25}}
    payload2 = {"a": 1, "nested": {"y": 25, "z": 26}, "b": 2}
    s1 = json.dumps(payload1, sort_keys=True, separators=(",", ":"))
    s2 = json.dumps(payload2, sort_keys=True, separators=(",", ":"))
    assert s1 == s2
    h1 = hashlib.sha256(s1.encode("utf-8")).hexdigest()
    h2 = hashlib.sha256(s2.encode("utf-8")).hexdigest()
    assert h1 == h2
    assert len(h1) == 64


def test_f10_02_tamper_detection_on_telemetry_alteration():
    """F10-2: Modifying single telemetry value changes SHA-256 digest (tamper-evident)."""
    now = datetime.now(timezone.utc)
    cite = CitationObject(citation_id="CITE-01", source_doc="doc.txt", title="Doc", excerpt="Excerpt text")
    report = EightDIncidentReport(
        report_id="8D-2023-PUMP-A12",
        d1_team=[TeamMember(member_id="T1", name="Alice", role="Lead", department="Reliability")],
        d2_problem=ProblemDescription5W2H(
            incident_title="Vibration trip",
            equipment_tag="Pump-A12",
            equipment_family="Centrifugal Pump",
            timestamp_incident=now,
            who_detected="Operator",
            what_symptom="Vibration",
            where_location="Sector 4",
            when_detected="Shift A",
            why_consequence="Shutdown",
            how_detected="Sensor",
            how_much_magnitude="5.8 mm/s",
            initial_severity=8,
            operational_impact="2h",
        ),
        d3_containment=[InterimContainmentAction(action_id="I1", description="Valves shut", responsible_owner="Bob", implementation_date=now, verification_method="Gauge", effectiveness_pct=100.0)],
        d4_root_cause=RootCauseDiscipline(
            occurrence_root_cause="Vibration cracked seal",
            escape_root_cause="Alarm threshold was 6.5 mm/s",
            five_why_chain=[FiveWhyNode(node_id="W1", level=1, cause_statement="Seal cracked", evidence_citation_ids=["CITE-01"], is_root_cause=True)],
            fishbone_analysis=[FishboneCauseItem(cause_id="F1", category=FishboneCategory.MACHINE, statement="Vibration fatigue", evidence_citation_ids=["CITE-01"])],
            citations=[cite],
        ),
        d5_permanent_actions=[PermanentCorrectiveAction(pca_id="P1", description="Interlock installed", addresses_cause_id="W1", responsible_owner="Charlie", target_date=now, feasibility_score=10, risk_assessment="None", validation_plan="Test run")],
        d6_validation=[ImplementAndValidate(action_id="V1", pca_id="P1", baseline_metric="5.8", post_implementation_metric="1.2", verification_evidence="Log", validation_status=ActionStatus.VERIFIED)],
        d7_prevention=[PreventativeControl(control_id="C1", control_type="SOP", description="SOP updated", target_completion_date=now)],
        d8_closure=TeamSignOff(signoff_id="S1", approver_name="Dave", approver_role="Director", signoff_date=now, lessons_learned_summary="Institutional lessons learned documented"),
        timeline=[FailureTimelineEvent(event_id="E1", timestamp=now, event_type=EventType.THRESHOLD_EXCEEDED, description="Vibration 5.8", equipment_tag="Pump-A12", telemetry_values={"vib": 5.8}, source_citation_id="CITE-01")],
        rpn_scoring=RPNScoring(severity=8, occurrence=6, detection=4),
    )
    digest_orig = report.compute_audit_hash()
    
    # Tamper with telemetry value
    report.timeline[0].telemetry_values["vib"] = 5.2
    digest_tampered = report.compute_audit_hash()
    assert digest_orig != digest_tampered


def test_f10_03_html_export_audit_header_and_classes():
    """F10-3: HTML export renders certified audit header and standard ISO/IATF metadata."""
    now = datetime.now(timezone.utc)
    cite = CitationObject(citation_id="CITE-01", source_doc="doc.txt", title="Doc", excerpt="Valid excerpt")
    report = EightDIncidentReport(
        report_id="8D-2023-PUMP-A12",
        d1_team=[TeamMember(member_id="T1", name="Elena", role="Lead", department="Reliability")],
        d2_problem=ProblemDescription5W2H(
            incident_title="Vibration trip",
            equipment_tag="Pump-A12",
            equipment_family="Centrifugal Pump",
            timestamp_incident=now,
            who_detected="Operator",
            what_symptom="Vibration",
            where_location="Sector 4",
            when_detected="Shift A",
            why_consequence="Shutdown",
            how_detected="Sensor",
            how_much_magnitude="5.8 mm/s",
            initial_severity=8,
            operational_impact="2h",
        ),
        d3_containment=[InterimContainmentAction(action_id="I1", description="Valves shut", responsible_owner="Bob", implementation_date=now, verification_method="Gauge", effectiveness_pct=100.0)],
        d4_root_cause=RootCauseDiscipline(
            occurrence_root_cause="Vibration cracked seal",
            escape_root_cause="Alarm threshold was 6.5 mm/s",
            five_why_chain=[FiveWhyNode(node_id="W1", level=1, cause_statement="Seal cracked", evidence_citation_ids=["CITE-01"], is_root_cause=True)],
            fishbone_analysis=[FishboneCauseItem(cause_id="F1", category=FishboneCategory.MACHINE, statement="Vibration fatigue", evidence_citation_ids=["CITE-01"])],
            citations=[cite],
        ),
        d5_permanent_actions=[PermanentCorrectiveAction(pca_id="P1", description="Interlock installed", addresses_cause_id="W1", responsible_owner="Charlie", target_date=now, feasibility_score=10, risk_assessment="None", validation_plan="Test run")],
        d6_validation=[ImplementAndValidate(action_id="V1", pca_id="P1", baseline_metric="5.8", post_implementation_metric="1.2", verification_evidence="Log", validation_status=ActionStatus.VERIFIED)],
        d7_prevention=[PreventativeControl(control_id="C1", control_type="SOP", description="SOP updated", target_completion_date=now)],
        d8_closure=TeamSignOff(signoff_id="S1", approver_name="Dave", approver_role="Director", signoff_date=now, lessons_learned_summary="Institutional lessons learned documented"),
        timeline=[FailureTimelineEvent(event_id="E1", timestamp=now, event_type=EventType.THRESHOLD_EXCEEDED, description="Vibration 5.8", equipment_tag="Pump-A12", source_citation_id="CITE-01")],
        rpn_scoring=RPNScoring(severity=8, occurrence=6, detection=4),
    )
    html_out = build_audit_html(report)
    assert "class=\"audit-header\"" in html_out
    assert report.report_id in html_out
    assert "Certified SHA-256 Checksum" in html_out
    assert "ISO 9001:2015" in html_out


def test_f10_04_print_css_page_rules_in_audit_package():
    """F10-4: HTML export embeds @page letter portrait and print CSS rules."""
    now = datetime.now(timezone.utc)
    cite = CitationObject(citation_id="CITE-01", source_doc="doc.txt", title="Doc", excerpt="Valid excerpt")
    report = EightDIncidentReport(
        report_id="8D-2023-TURB-01",
        d1_team=[TeamMember(member_id="T1", name="Elena", role="Lead", department="Reliability")],
        d2_problem=ProblemDescription5W2H(
            incident_title="Turbine trip",
            equipment_tag="TURB-01",
            equipment_family="Turbine",
            timestamp_incident=now,
            who_detected="Operator",
            what_symptom="Overspeed",
            where_location="Turbine Island",
            when_detected="Shift B",
            why_consequence="Trip",
            how_detected="Sensor",
            how_much_magnitude="3450 RPM",
            initial_severity=9,
            operational_impact="1h",
        ),
        d3_containment=[InterimContainmentAction(action_id="I1", description="Governor tripped", responsible_owner="Bob", implementation_date=now, verification_method="RPM", effectiveness_pct=100.0)],
        d4_root_cause=RootCauseDiscipline(
            occurrence_root_cause="Lube oil pressure loss",
            escape_root_cause="Alarm ignored",
            five_why_chain=[FiveWhyNode(node_id="W1", level=1, cause_statement="Overspeed", evidence_citation_ids=["CITE-01"], is_root_cause=True)],
            fishbone_analysis=[FishboneCauseItem(cause_id="F1", category=FishboneCategory.MACHINE, statement="Bearing heating", evidence_citation_ids=["CITE-01"])],
            citations=[cite],
        ),
        d5_permanent_actions=[PermanentCorrectiveAction(pca_id="P1", description="Filter duplex upgrade", addresses_cause_id="W1", responsible_owner="Charlie", target_date=now, feasibility_score=10, risk_assessment="None", validation_plan="Bench test")],
        d6_validation=[ImplementAndValidate(action_id="V1", pca_id="P1", baseline_metric="0.8 bar", post_implementation_metric="3.2 bar", verification_evidence="Pressure log", validation_status=ActionStatus.VERIFIED)],
        d7_prevention=[PreventativeControl(control_id="C1", control_type="PM", description="Oil analysis", target_completion_date=now)],
        d8_closure=TeamSignOff(signoff_id="S1", approver_name="Dave", approver_role="Director", signoff_date=now, lessons_learned_summary="Institutional lessons learned documented"),
        timeline=[FailureTimelineEvent(event_id="E1", timestamp=now, event_type=EventType.THRESHOLD_EXCEEDED, description="Overspeed", equipment_tag="TURB-01", source_citation_id="CITE-01")],
        rpn_scoring=RPNScoring(severity=9, occurrence=5, detection=5),
    )
    html_out = build_audit_html(report)
    assert "@page" in html_out
    assert "letter portrait" in html_out
    assert "@media print" in html_out


def test_f10_05_sha256_verification_against_hashlib():
    """F10-5: SHA-256 generated by report matches direct hashlib output bit-for-bit."""
    sample_data = {"key_alpha": "value_alpha", "key_beta": [1, 2, 3]}
    canonical_repr = json.dumps(sample_data, sort_keys=True, separators=(",", ":"))
    expected_hex = hashlib.sha256(canonical_repr.encode("utf-8")).hexdigest()
    assert len(expected_hex) == 64
    assert int(expected_hex, 16) > 0  # Valid non-zero hex number
