## 2026-10-07T10:36:52Z
[Message] timestamp=2026-10-07T10:36:52Z sender=6083de2c-0790-4fdb-80b8-ee776e04b485 priority=MESSAGE_PRIORITY_HIGH content=You are worker_m4.
Your working directory is:
C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\worker_m4

Authoritative Request:
C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\ORIGINAL_REQUEST.md

Master Project Plan:
C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\orchestrator_1\PROJECT.md

Explorer Reports & Reference Components:
- C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\explorer_m4_1\handoff.md
- C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\explorer_m4_2\handoff.md
- C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\explorer_m4_2\proposed_FiveWhyFishboneTab.jsx
- C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\explorer_m4_2\proposed_TimelineTab.jsx
- C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\explorer_m4_3\handoff.md

Write Ownership:
You own exclusively:
- frontend/src/components/EightDStudio/EightDIncidentStudio.jsx
- frontend/src/components/EightDStudio/OverviewTab.jsx
- frontend/src/components/EightDStudio/FiveWhyFishboneTab.jsx
- frontend/src/components/EightDStudio/TimelineTab.jsx
- frontend/src/components/EightDStudio/CorrectiveActionsTab.jsx
- frontend/src/components/EightDStudio/printStyles.css
- frontend/src/components/ArtifactPanel.jsx
- frontend/src/components/Sidebar.jsx
- frontend/src/App.jsx

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Detailed Implementation Tasks:
1. Create `frontend/src/components/EightDStudio/printStyles.css`:
   - Full @media print stylesheet conforming to ISO 9001:2015 Clause 10.2 / IATF 16949 Section 10.2.3.
   - @page { size: letter portrait; margin: 15mm 18mm; }.
   - Unclipping outer App.jsx wrappers during print, hiding .no-print elements, buttons, sidebars.
   - .page-break and .avoid-break utility classes.

2. Implement `frontend/src/components/EightDStudio/OverviewTab.jsx`:
   - D1 Team card (Leader, Champion, Members, Facilitator).
   - D2 Problem 5W2H card (What, Where, When, Who, Why, How, How Many, Operational Impact).
   - RPN Risk meter card (gauge with Severity x Occurrence x Detection, risk priority level, initial vs mitigated reduction).
   - D8 Team Recognition & Sign-Off card (Quality Manager approval status, date, digital signature hash, lessons learned).

3. Implement `frontend/src/components/EightDStudio/FiveWhyFishboneTab.jsx`:
   - Deploy production version based on explorer_m4_2/proposed_FiveWhyFishboneTab.jsx.
   - Interactive SVG 5-Why tree with levels 1-5, orthogonal bezier connector lines, root cause glowing pulse filter (#root-glow), unsubstantiated assumption badges (is_unsubstantiated=True), and citation pills wired to onSourceClick.
   - Interactive SVG Ishikawa 6M Fishbone with central spine into effect box, 6 category ribs (Man, Machine, Material, Method, Measurement, Environment), sub-branches, citation dots, and category filters.
   - Layout mode switcher (5-Why Tree, Fishbone Diagram, or Dual Split View).

4. Implement `frontend/src/components/EightDStudio/TimelineTab.jsx`:
   - Deploy production version based on explorer_m4_2/proposed_TimelineTab.jsx.
   - Interactive vertical chronological rail with color-coded event dots (SYSTEM_FAILURE, TELEMETRY_ALARM, OPERATOR_ACTION, MAINTENANCE_LOG).
   - Relative (T+...) and absolute timestamps.
   - Telemetry excursion callouts with 3-zone visual gauge.
   - Citation drill-down badges wired to onSourceClick.

5. Implement `frontend/src/components/EightDStudio/CorrectiveActionsTab.jsx`:
   - Action matrices comparing D3 Containment vs D5 Permanent Corrective Actions vs D7 Preventative Controls.
   - OEM Operating Envelope Deviation bars with percentage excursions and threshold limits.
   - Historical Near-Miss Similarity Match cards (similarity score, matching symptoms, recommendations).

6. Implement `frontend/src/components/EightDStudio/EightDIncidentStudio.jsx`:
   - Container component with header displaying Incident Title, Equipment Tag, Severity badge, RPN risk meter, SHA-256 seal badge.
   - Tab bar switching between Overview, 5-Why & Fishbone, Timeline, and Corrective Actions.
   - "Export Audit Package" button with options:
     a) Trigger print dialog (window.print()) with printStyles.css dossier.
     b) Export evidence package via POST /api/v1/rca/export-evidence and trigger browser file download.
   - Wire citation clicks to onSourceClick prop (opening SourceViewerModal).
   - Support embedded mode (inside ArtifactPanel) and full-screen modal mode (launched from Sidebar).

7. Wire into `frontend/src/components/ArtifactPanel.jsx`:
   - When artifact contains an 8D report (e.g. artifact.type === '8d_report' or artifact.data?.d1_team), render EightDIncidentStudio with onSourceClick wired to open SourceViewerModal.

8. Wire into `frontend/src/components/Sidebar.jsx` and `frontend/src/App.jsx`:
   - Add "8D Incident Studio" item/button in Sidebar navigation with an icon (e.g., ClipboardCheck or ShieldAlert).
   - In App.jsx, handle opening the 8D Incident Studio (either via active report, fetching recent reports from GET /api/v1/rca/reports, or loading a demo report).

9. Verification Commands:
   - In frontend/ directory: run `npm run build` via powershell. Must complete cleanly with exit code 0 and 0 errors!
   - In backend/ directory: run `backend\venv\Scripts\pytest.exe backend/tests/ -q`. Ensure 0 regressions!

10. Deliverables:
   Write handoff report to:
   C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\worker_m4\handoff.md
   Maintain progress.md in your directory.
   Notify orchestrator via send_message.
