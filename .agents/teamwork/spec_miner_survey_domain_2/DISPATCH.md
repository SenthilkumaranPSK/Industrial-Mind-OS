## 2026-10-05T13:29:29Z
You are a read-only specification investigator (RCA 8D Spec Miner Replacement).
Your working directory is:
C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\spec_miner_survey_domain_2

MANDATORY FIRST STEP:
Read the authoritative user request at:
C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\ORIGINAL_REQUEST.md
Also read the predecessor agent's notes at:
C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\spec_miner_survey_domain\progress.md

Your Objective:
Pick up from your predecessor who verified the baselines (backend pytest: 27 passed, frontend build: clean) and was preparing the domain specification.
Mine and define precise domain specifications, schemas, and requirements for the Automated Root Cause Analysis (RCA) & 8D Incident Report Studio.
Specifically document:
1. The Eight Disciplines (8D) standard structure:
   - D1: Team Formation & Roles
   - D2: Problem Description (5W2H format, symptoms, equipment tags, timestamps)
   - D3: Interim Containment Actions (ICA) & effectiveness verification
   - D4: Root Cause Analysis (Deductive 5-Why causal chain and Ishikawa / Fishbone 6M categories: Man, Machine, Material, Method, Measurement, Environment)
   - D5: Permanent Corrective Actions (PCA) & validation plan
   - D6: Implement & Validate Actions (implementation status, before/after metrics)
   - D7: Prevent Recurrence / Preventative Controls (SOP updates, maintenance schedule adjustments, FMEA/risk matrix updates)
   - D8: Team Recognition & Sign-off
2. Data schema specifications:
   - Exact Pydantic schema model definitions for the complete 8D Incident Report.
   - Severity scoring & RPN (Risk Priority Number: Severity, Occurrence, Detection).
   - Citation objects (citation_id, source_doc, title, section, excerpt, page/line, confidence).
   - Failure timeline events (timestamp, event_type, description, source_citation_id, equipment_tag, telemetry_values).
   - 5-Why tree structure (level 1 to 5+, cause_statement, evidence_citation_ids, is_root_cause, is_assumed/unsubstantiated flag).
   - Fishbone structure (category, causes, evidence_citation_ids, contribution_weight).
   - Historical matching result (matched_report_id, similarity_score, equipment_family, matching_symptoms, recurring_risk_assessment).
   - Preventative actions and OEM envelope comparison (oem_parameter, normal_envelope, incident_value, deviation_pct, recommended_action).
3. Verification & Citation Grounding rules:
   - Requirement: EVERY root cause claim and causal assertion MUST link to at least one valid source document or citation ID.
   - Any assertion lacking citation grounding MUST be explicitly flagged as `is_unsubstantiated=True` or `assumption_flag=True`.
4. Compliance Audit Package requirements:
   - Export format: print-ready compliance document (HTML/PDF with dedicated print CSS media query `@media print`, pagination, page break controls, certified audit header with SHA256 checksum and timestamp).

Scope boundaries:
- READ-ONLY: Do NOT modify or create any project source code files.
- Put your metadata in your working directory.

Output requirements:
- Maintain your progress in progress.md in your working directory.
- Write your comprehensive specification report to spec_report.md in your working directory.
- Write a formal handoff report to handoff.md in your working directory following the Handoff Protocol (Observation, Logic Chain, Caveats, Conclusion, Verification Method).
- When done, use send_message to notify the orchestrator (recipient: your caller) with a summary and path to your handoff.md.
