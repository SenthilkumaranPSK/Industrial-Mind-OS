## 2026-10-07T11:05:19Z
You are worker_m4_remediation.
Your working directory is:
C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\worker_m4_remediation

Authoritative Request:
C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\ORIGINAL_REQUEST.md

Master Project Plan:
C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\orchestrator_1\PROJECT.md

Challenger 2 Report (CHALLENGE_FAILED):
C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\challenger_m4_2\handoff.md

Challenger 1 Report (APPROVE with edge-case observations):
C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\challenger_m4_1\handoff.md

Write Ownership:
You own exclusively:
- frontend/src/components/EightDStudio/EightDIncidentStudio.jsx
- frontend/src/components/EightDStudio/printStyles.css
- frontend/src/components/EightDStudio/FiveWhyFishboneTab.jsx
- frontend/src/components/EightDStudio/OverviewTab.jsx
- frontend/src/components/EightDStudio/mockReportData.js
Do not modify any other files.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Tasks to Remediate:
1. Render 6M Ishikawa Table & D4 Root Causes in `<EightDAuditPrintDossier />` (`frontend/src/components/EightDStudio/EightDIncidentStudio.jsx`):
   Inside `<EightDAuditPrintDossier />` under D4 (Root Cause Analysis):
   - Add Root Causes Summary block/table rendering `d4.occurrence_root_cause` and `d4.escape_root_cause`, plus citation grounding ratio if available.
   - Add full Ishikawa 6M Cause Classification table:
     Iterate through `(d4.fishbone_analysis?.branches || [])` and render a table with columns: Category (e.g. Man, Machine, Material, Method, Measurement, Environment), Potential Causes, Verifiable Citations, and Risk / Substantiation Status.
     Ensure that for each branch, each cause string or object is properly displayed.

2. Modal Print Unclipping in `frontend/src/components/EightDStudio/printStyles.css`:
   Add unclipping for modal wrappers so printing from modal view does not pin content to page 1 or print dark backdrop overlays:
   ```css
   .fixed,
   .fixed.inset-0,
   .backdrop-blur-md,
   .bg-slate-950\/80 {
     position: static !important;
     inset: auto !important;
     background: transparent !important;
     backdrop-filter: none !important;
     padding: 0 !important;
     margin: 0 !important;
     box-shadow: none !important;
     border: none !important;
   }
   ```

3. SVG Math Hardening in `frontend/src/components/EightDStudio/FiveWhyFishboneTab.jsx`:
   In line ~154:
   Change `const maxLevel = Math.max(...positionedNodes.map((n) => n.level), 5);`
   to:
   `const maxLevel = Math.max(...positionedNodes.map((n) => Number(n.level) || 1), 5);`
   to ensure `maxLevel` is never NaN even if a node has undefined level.

4. RPN Hardening in `frontend/src/components/EightDStudio/OverviewTab.jsx`:
   In line ~49:
   Change:
   ```javascript
   const mitigatedRpn = Math.min(initialRpn, Math.max(1, Math.round(initialRpn * 0.05)));
   const rpnReductionPct = initialRpn > 0 ? Math.max(0, Math.min(99, Math.round(((initialRpn - mitigatedRpn) / initialRpn) * 100))) : 0;
   ```
   so that for small initial RPNs (< 16), mitigated RPN never exceeds initial RPN and risk reduction percentage is never negative.

5. Verification Commands:
   In frontend/:
   - `npm run build` (must exit 0)
   - `node run_stress_suite.mjs` (must pass 100% of tests with exit 0)
   In project root:
   - `backend\venv\Scripts\pytest.exe backend/tests/ -q` (must pass 554 tests with 0 failures)

6. Deliverables:
   Write handoff report to:
   C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\worker_m4_remediation\handoff.md
   Maintain progress.md in your directory.
   Notify orchestrator via send_message.
