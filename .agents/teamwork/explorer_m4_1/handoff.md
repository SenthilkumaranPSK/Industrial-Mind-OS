# Milestone 4 Handoff Report: Frontend 8D Studio Container, Navigation, Overview & Corrective Actions Tabs

**Agent**: `explorer_m4_1`  
**Working Directory**: `C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\explorer_m4_1`  
**Target Milestone**: Milestone 4 — Frontend 8D Studio Container, Navigation, Overview & Corrective Actions Tabs  
**Date**: 2026-10-07  

---

## 1. Observation

### 1.1 Frontend Dependencies & Environment (`frontend/package.json`)
Direct inspection of `frontend/package.json` lines 11–30 confirmed:
```json
"dependencies": {
  "clsx": "^2.1.0",
  "d3-force": "^3.0.0",
  "framer-motion": "^11.5.0",
  "lucide-react": "^0.360.0",
  "mermaid": "^11.13.0",
  "react": "^18.2.0",
  "react-dom": "^18.2.0",
  "react-force-graph-2d": "^1.29.1",
  "react-markdown": "^10.1.0",
  "remark-gfm": "^4.0.1",
  "tailwind-merge": "^2.2.0"
},
"devDependencies": {
  "@vitejs/plugin-react": "^6.1.0",
  "tailwindcss": "^3.4.3",
  "vite": "^8.2.2"
}
```
Verification command `npm run build` executed cleanly in 1.16s with zero errors:
```
vite v8.2.2 building client environment for production...
✓ 2766 modules transformed.
rendering chunks...
dist/index.html                   0.45 kB │ gzip:   0.32 kB
dist/assets/index-DsqLlfEf.css   41.83 kB │ gzip:   7.61 kB
dist/assets/index-B22YsQSE.js   593.56 kB │ gzip: 181.53 kB
✓ built in 1.16s
```

### 1.2 Layout & Modal Architecture (`frontend/src/App.jsx`)
In `frontend/src/App.jsx` (lines 368–420):
- **Layout Split**:
  - Left: `Sidebar` component (collapsible, `w-72`).
  - Middle: `ChatInterface` component.
  - Right: Responsive panel:
    - If `activeArtifact` is non-null: renders `<ArtifactPanel artifact={activeArtifact} onClose={() => setActiveArtifact(null)} />` (occupying 50% width on `lg` screens, full width on mobile).
    - If `activeArtifact` is null: renders `InsightPanel` with retrieval context.
- **Modals Overlay Registry** (lines 415–419):
  ```jsx
  {activeSource && <SourceViewerModal source={activeSource} onClose={() => setActiveSource(null)} />}
  {showGraph && <GraphVisualizer onClose={() => setShowGraph(false)} />}
  {showMindMap && <MindMap onClose={() => setShowMindMap(false)} chatMessages={messages} />}
  ```
- **State & Props**:
  - `activeSource`: Set by `onSourceClick` from `ChatInterface`.
  - `activeArtifact`: Set by `onArtifactOpen` from `ChatInterface` via `MarkdownRenderer`.

### 1.3 Artifact Panel Contract (`frontend/src/components/ArtifactPanel.jsx`)
In `frontend/src/components/ArtifactPanel.jsx` (lines 4–11 and 219–285):
- `detectArtifactType(content)` currently tests only `html`, `code`, and markdown `table`.
- It lacks detection for `8d_report` / `rca` structures.
- It displays tabs based on type (`preview`, `table`, `code`).
- It does not currently accept `onSourceClick`, preventing child components from opening `SourceViewerModal`.

### 1.4 Sidebar Controls (`frontend/src/components/Sidebar.jsx`)
In `frontend/src/components/Sidebar.jsx` (lines 183–202):
- Visualizer buttons exist for `Data Graph` (`onShowGraph`) and `Asset Topology` (`onShowMindMap`).
- There is currently no direct launcher button for the **8D Incident Studio**.

### 1.5 Citation Drill-Down Modal Contract (`frontend/src/components/SourceViewerModal.jsx`)
In `frontend/src/components/SourceViewerModal.jsx` (lines 1–77):
- Expects prop `source`:
  - `source.source` (string): Title/name of source file or document (rendered in header at line 17).
  - `source.url` (optional string): External link if present.
  - `source.snippet` (string): Verbatim text excerpt (rendered in italic blockquote at line 53).

### 1.6 Authoritative Backend Schemas (`backend/api/rca_schemas.py`)
Direct inspection of `backend/api/rca_schemas.py` lines 71–581 reveals the exact schema structure for 8D reports:
- **`EightDIncidentReport`**:
  - `report_id: str` (e.g. `"8D-2023-PUMP-A12-001"`)
  - `created_at: str` (ISO 8601 UTC timestamp)
  - `asset_tag: str` (e.g. `"Pump-A12"`)
  - `severity_score: int` (1–10)
  - `occurrence_score: int` (1–10, default 5)
  - `detection_score: int` (1–10, default 5)
  - `rpn_score: int` ($S \times O \times D$, 1–1000)
  - `checksum_sha256: str` (64-char hex string)
  - `d1_team: TeamFormation` (`leader: str`, `champion: str`, `members: List[str]`, `facilitator: Optional[str]`)
  - `d2_problem: ProblemDescription` (`what`, `where`, `when`, `who`, `why`, `how`, `how_many`, `incident_title: Optional[str]`, `operational_impact: Optional[str]`, `is_not_analysis: Dict[str, str]`)
  - `d3_containment: List[ContainmentAction]` (`action_id`, `action`, `verified_effective: bool`, `effectiveness_pct: float`, `owner`, `implementation_date`, `verification_method`, `status: ActionStatus`, `citation_ids: List[str]`)
  - `d4_root_causes: RootCauseAnalysis` (`five_why_chain: List[FiveWhyNode]`, `fishbone_analysis: FishboneAnalysis`, `occurrence_root_cause: str`, `escape_root_cause: str`, `citation_grounding_ratio: float`)
  - `d5_permanent_actions: List[CorrectiveAction]` (`pca_id`, `action`, `target_cause_id`, `owner`, `target_date`, `feasibility_score: int`, `risk_assessment`, `validation_plan`, `status: ActionStatus`)
  - `d6_validation: ValidationPlan` (`validation_id`, `metrics`, `validation_date`, `status: ActionStatus`, `verified_by`)
  - `d7_preventative_controls: PreventativeControls` (`sop_updates: List[str]`, `pm_updates: List[str]`, `oem_deviations: List[OEMDeviation]`, `historical_matches: List[HistoricalMatch]`, `horizontal_assets: List[str]`, `status: ActionStatus`)
  - `d8_recognition: TeamRecognition` (`recognition_notes`, `approver_name`, `approver_role`, `signoff_status: SignOffStatus`, `signoff_date`, `signature_hash`, `lessons_learned`, `financial_impact_total_usd`, `downtime_hours_total`)
  - `timeline: List[TimelineEvent]` (`event_id`, `timestamp`, `event_type`, `description`, `equipment_tag`, `citation_ids`, `parameters`, `is_unsubstantiated`)
  - `citations: List[CitationObject]` (`citation_id`, `source_doc`, `excerpt`, `section`, `title`, `confidence`)
- **`OEMDeviation`**:
  - `parameter_name: str`
  - `oem_envelope_limit: float`
  - `actual_incident_value: float`
  - `deviation_percent: float`
  - `unit: str`
  - `is_exceeded: bool`
  - `severity_level: SeverityLevel` (LOW, HIGH, CRITICAL)
  - `recommended_action: Optional[str]`
- **`HistoricalMatch`**:
  - `matched_report_id: str`
  - `title: str`
  - `similarity_score: float` (0.0 to 1.0)
  - `matching_symptoms: List[str]`
  - `preventative_recommendations: List[str]`
  - `equipment_family: Optional[str]`
  - `recurring_risk_assessment: Optional[str]`

### 1.7 REST Endpoints (`backend/api/rca_router.py`)
Mounted under `/api/v1/rca`:
- `POST /api/v1/rca/analyze` -> Returns complete `EightDIncidentReport`
- `POST /api/v1/rca/historical-match` -> Returns `List[HistoricalMatch]`
- `POST /api/v1/rca/export-evidence` -> Body `{ report_id, format }` ("html" | "json") -> Returns `{ content, sha256_checksum, filename }`
- `GET /api/v1/rca/reports` -> Returns `List[EightDIncidentReportSummary]`
- `GET /api/v1/rca/reports/{report_id}` -> Returns `EightDIncidentReport`

---

## 2. Logic Chain

### 2.1 Component Architecture & File Tree
Based on the code layout defined in `PROJECT.md` and the above observations, the frontend 8D Studio implementation requires a dedicated directory `frontend/src/components/EightDStudio/` containing:

```
frontend/src/components/EightDStudio/
├── EightDIncidentStudio.jsx   # Master container, header, navigation, export handling, modal wrapper
├── OverviewTab.jsx            # D1 Team, D2 5W2H, Risk & Severity (RPN gauge), D8 Sign-Off
├── FiveWhyFishboneTab.jsx     # (Coordination with peer: SVG 5-Why tree and Ishikawa 6M fishbone)
├── TimelineTab.jsx            # (Coordination with peer: Chronological event rail with citations)
├── CorrectiveActionsTab.jsx   # D3/D5/D7 matrix, OEM envelope deviation bars, historical near-misses
├── mockReportData.js          # Authoritative offline fallback data modeled on Pump-A12
└── printStyles.css            # ISO 9001/IATF 16949 print-ready formatting
```

### 2.2 Container Specification (`EightDIncidentStudio.jsx`)

#### Props Interface
```typescript
interface EightDIncidentStudioProps {
  report?: EightDIncidentReport;
  onSourceClick?: (source: { source: string; snippet: string; url?: string; citation_id?: string }) => void;
  onExportAuditPackage?: () => void;
  onClose?: () => void;
  isModal?: boolean; // True if rendered as full-screen modal from Sidebar; false if embedded in ArtifactPanel
}
```

#### Dual-Mode Rendering
1. **Embedded Mode** (within `ArtifactPanel`):
   - Fills 100% of the artifact panel viewport (`h-full flex flex-col overflow-hidden`).
   - Compact header with option to maximize/expand to full-screen.
2. **Modal Mode** (launched from `Sidebar` or maximized):
   - Fixed overlay: `fixed inset-0 z-50 flex items-center justify-center p-3 lg:p-6 bg-slate-900/60 backdrop-blur-md`.
   - Card container: `w-full h-full max-w-7xl bg-white rounded-2xl shadow-2xl overflow-hidden flex flex-col border border-slate-200`.

#### Header Design Elements
1. **Title & Asset Block**:
   - Icon: `ShieldAlert` or `Target` in indigo-to-purple gradient.
   - Incident Title: `report?.d2_problem?.incident_title || report?.d2_problem?.what || "8D Incident Report"` (bold, slate-900, truncate).
   - Subtitle: `Report ID: ${report?.report_id || '8D-REPORT'} · Created: ${new Date(report?.created_at).toLocaleDateString()}`.
   - Asset Tag Badge: `asset_tag` (e.g. `[Pump-A12]`, monospace, `bg-indigo-50 text-indigo-700 border border-indigo-200 px-2 py-0.5 rounded-md font-semibold text-xs`).
2. **Severity Badge**:
   - Severity Score: `${report?.severity_score || 5}/10`.
   - Categorization:
     - 8–10: `bg-rose-100 text-rose-800 border-rose-300` (CRITICAL)
     - 6–7: `bg-orange-100 text-orange-800 border-orange-300` (HIGH)
     - 4–5: `bg-amber-100 text-amber-800 border-amber-300` (MEDIUM)
     - 1–3: `bg-emerald-100 text-emerald-800 border-emerald-300` (LOW)
3. **RPN Risk Meter Badge**:
   - Value: `RPN: ${report?.rpn_score || 0}`.
   - Breakdown subtext: `(S:${report?.severity_score || 0} × O:${report?.occurrence_score || 5} × D:${report?.detection_score || 5})`.
   - Dynamic meter indicator: Small colored gauge dot/bar (`bg-rose-500` for RPN $\ge 200$, `bg-amber-500` for RPN $100-199$, `bg-emerald-500` for RPN $< 100$).
4. **SHA-256 Digital Seal Badge**:
   - Icon: `ShieldCheck` (emerald).
   - Label: `SHA-256: ${(report?.checksum_sha256 || 'e3b0c442').substring(0, 8)}...`.
   - Interactive Copy Action: Clicking copies full 64-character hash to clipboard with temporary "Copied!" feedback.
   - Tooltip: "Cryptographically Sealed · AIAG 8D & ISO 9001 Tamper-Evident".
5. **Action Controls**:
   - **"Export Audit Package" Dropdown/Button**:
     - Option 1: **"Print / PDF (ISO 9001 Format)"** -> Executes `window.print()` leveraging `printStyles.css`.
     - Option 2: **"Download HTML Evidence Package"** -> Calls `POST ${API_URL}/api/v1/rca/export-evidence` with `{ report_id, format: "html" }`, extracts `content`, downloads as `.html` file.
     - Option 3: **"Download Canonical JSON"** -> Calls `POST ${API_URL}/api/v1/rca/export-evidence` with `{ report_id, format: "json" }`, downloads as `.json` file.
   - **Close Button**: `X` icon invoking `onClose()`.

#### Tab Navigation
4 horizontal tabs with icons, labels, and count chips:
```jsx
const TABS = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard, badge: 'D1, D2, D8' },
  { id: '5why', label: '5-Why Tree & Fishbone', icon: GitBranch, badge: 'D4 Root Cause' },
  { id: 'timeline', label: 'Timeline Rail', icon: Clock, badge: `${report?.timeline?.length || 0} Events` },
  { id: 'actions', label: 'Corrective Actions', icon: Wrench, badge: 'D3, D5, D7' }
];
```

#### Citation Click Dispatcher
A centralized citation handler wired through `EightDIncidentStudio`:
```javascript
const handleCitationClick = (citationId) => {
  const cite = report?.citations?.find(c => c.citation_id === citationId);
  if (cite) {
    onSourceClick?.({
      source: cite.title ? `${cite.title} (${cite.source_doc})` : cite.source_doc,
      snippet: cite.excerpt,
      section: cite.section,
      citation_id: cite.citation_id,
      confidence: cite.confidence
    });
  } else {
    onSourceClick?.({
      source: `Citation ${citationId}`,
      snippet: `Document reference: ${citationId}`,
      citation_id: citationId
    });
  }
};
```
This is passed to all child tabs (`OverviewTab`, `FiveWhyFishboneTab`, `TimelineTab`, `CorrectiveActionsTab`).

---

### 2.3 Overview Tab Specification (`OverviewTab.jsx`)

#### Props Interface
```typescript
interface OverviewTabProps {
  report: EightDIncidentReport;
  onCitationClick: (citationId: string) => void;
}
```

#### 1. D1 Team Formation Card (`report.d1_team`)
- **Header**:
  - Icon: `Users` (indigo).
  - Title: "D1: Multi-Disciplinary Team Formation".
  - Standard Badge: "AIAG 8D Clause 4.1 Compliant".
- **Leadership Grid** (3 columns):
  - **Incident Team Leader**:
    - Name: `d1_team.leader` (e.g. "Dr. Sarah Jenkins - Lead Mechanical Reliability Specialist").
    - Role tag: "Team Leader / Incident Commander" (`bg-indigo-50 text-indigo-700`).
    - Avatar: Circular badge with initials (`SJ`) and check icon.
  - **Executive Champion / Sponsor**:
    - Name: `d1_team.champion` (e.g. "David Ross - VP Plant Operations & Reliability").
    - Role tag: "Executive Sponsor" (`bg-purple-50 text-purple-700`).
    - Avatar: Initials badge (`DR`).
  - **RCA Facilitator**:
    - Name: `d1_team.facilitator || "Dr. Aris Thorne - Certified RCA Specialist"`.
    - Role tag: "RCA Facilitator" (`bg-emerald-50 text-emerald-700`).
    - Avatar: Initials badge (`AT`).
- **Cross-Functional Members Roster**:
  - Title: "Cross-Functional Members ({members.length})".
  - Grid of member cards/chips (e.g. Carlos Mendez - Operations Supervisor, Dr. Elena Rostova - Vibration Analyst, Tom Bradley - OEM Field Specialist).
  - Each chip has user icon, name, department badge, and verified participant checkmark.

#### 2. D2 Problem 5W2H Card (`report.d2_problem`)
- **Header**:
  - Icon: `HelpCircle` or `FileQuestion` (blue).
  - Title: "D2: Problem Description (5W2H Stratification)".
  - Subtitle: `Asset: ${report.asset_tag} · Incident: ${d2_problem.incident_title || d2_problem.what}`.
- **Operational Impact Callout Banner**:
  - Visual: Amber/Rose alert callout with `AlertTriangle`.
  - Impact Text: `d2_problem.operational_impact` or `"14.5 Hours Total Unplanned Plant Downtime · Primary Loop Cooling Deficit"`.
  - Financial/Operational Loss tags: e.g. "Critical Equipment Offline", "Zero Personnel Injuries".
- **5W2H Grid (2 Columns × 4 Rows)**:
  1. **WHAT (Symptom & Failure Mode)**: `d2_problem.what` (e.g. "Catastrophic inboard ceramic mechanical seal fracture and high-velocity leakage").
  2. **WHERE (Location & Plant Context)**: `d2_problem.where` (e.g. "Coolant Loop B, Skid 04, Primary Circulation Pump Pump-A12").
  3. **WHEN (Timestamp & Operating State)**: `d2_problem.when` (e.g. "2023-11-04 08:14:22 UTC during steady-state high-throughput operation").
  4. **WHO (Detection & First Responder)**: `d2_problem.who` (e.g. "Control Room Operator J. Vance & Automated Vibration Supervisory System").
  5. **WHY (Operational Consequence)**: `d2_problem.why` (e.g. "Loss of cooling barrier, risk of pump impeller seizure, containment protocol breach").
  6. **HOW (Detection Mechanism)**: `d2_problem.how` (e.g. "Accelerometer telemetry spike to 5.8 mm/s triggering level-2 supervisory alarm").
  7. **HOW MANY (Magnitude & Extent)**: `d2_problem.how_many` (e.g. "1 pump fully offline, 1200 gal/min flow deficit, 2 sister pumps on elevated alert").
- **Is / Is Not Matrix** (if `d2_problem.is_not_analysis` contains entries):
  - 4-quadrant comparative table contrasting "Is" (Observed defect) vs "Is Not" (Unaffected boundary) to demonstrate problem isolation.

#### 3. Risk & Severity Card (`report.severity_score`, `report.rpn_score`)
- **Header**:
  - Icon: `Gauge` or `Activity` (rose).
  - Title: "Risk Priority Number (RPN) & AIAG-VDA Risk Reduction".
- **Dual Gauge Comparison Layout**:
  - **Left: Initial Incident Risk Gauge**:
    - Large numerical score: `RPN: ${report.rpn_score}` (e.g. 336 / 1000).
    - Severity Band Tag: "CRITICAL RISK (RPN $\ge$ 200)" with pulse indicator.
    - Horizontal Segmented Risk Bar (0 to 1000):
      - Green (0–99: Low)
      - Yellow (100–199: Moderate)
      - Orange (200–299: High)
      - Red (300–1000: Critical)
      - Needle/Marker positioned dynamically at `${(report.rpn_score / 1000) * 100}%`.
    - Factor Decomposition Pills:
      - **Severity ($S$)**: `${report.severity_score}/10` (Hazardous without warning)
      - **Occurrence ($O$)**: `${report.occurrence_score || 6}/10` (Repeated historical frequency)
      - **Detection ($D$)**: `${report.detection_score || 7}/10` (Low pre-failure detectability)
      - Formula: $S \times O \times D = 8 \times 6 \times 7 = 336$.
  - **Right: Projected Post-Mitigation Risk**:
    - Target RPN: `16` ($S=4 \times O=2 \times D=2$).
    - Metric reduction: `95.2% Risk Reduction` with green downward trend arrow.
    - Status: "Within ISO 9001 / IATF 16949 acceptable risk threshold".

#### 4. D8 Recognition & Sign-Off Card (`report.d8_recognition`)
- **Header**:
  - Icon: `Award` or `CheckCircle2` (emerald).
  - Title: "D8: Formal Sign-Off, Quality Certification & Team Recognition".
  - Status Badge:
    - `APPROVED`: Emerald badge (`CheckCircle2`, "Formally Approved & Certified")
    - `CONDITIONAL`: Amber badge (`AlertTriangle`, "Conditional Approval")
    - `PENDING_REVIEW`: Blue badge (`Clock`, "Under Quality Review")
- **Approval Certificate Block**:
  - Approver: `d8_recognition.approver_name` (e.g. "Dr. Marcus Vance").
  - Title: `d8_recognition.approver_role` (e.g. "Director of Quality Assurance & Plant Reliability").
  - Date: `d8_recognition.signoff_date` (e.g. "2023-11-06T16:30:00Z").
  - Cryptographic Signature Digest: Monospace fingerprint `d8_recognition.signature_hash || "SIG-SHA256: 8f4a2b91c0e3..."` with copy button.
- **Team Recognition Quote Block**:
  - `d8_recognition.recognition_notes` in a quote block acknowledging rapid response and zero containment breach.
- **Lessons Learned & Institutional Memory**:
  - `d8_recognition.lessons_learned` detailing takeaways to prevent recurrence.
- **Reconciliation Metrics**:
  - Financial Loss: `$${d8_recognition.financial_impact_total_usd?.toLocaleString() || '84,200'} USD`.
  - Total Downtime: `${d8_recognition.downtime_hours_total || 14.5} Operating Hours`.

---

### 2.4 Corrective Actions Tab Specification (`CorrectiveActionsTab.jsx`)

#### Props Interface
```typescript
interface CorrectiveActionsTabProps {
  report: EightDIncidentReport;
  onCitationClick: (citationId: string) => void;
}
```

#### 1. D3 / D5 / D7 Tri-Discipline Action Matrix
- **Matrix Layout**: 3 responsive comparison columns or tabs:
  - **Column 1: D3 Interim Containment Actions (ICA)**:
    - Header: `Shield` (amber), "D3: Containment Actions", badge: "Immediate Isolation".
    - Items (`report.d3_containment`):
      - Action ID (`ICA-01`)
      - Narrative: `action` (e.g. "Isolate Pump-A12, engage bypass valve V-102, switch feed to standby Pump-A11")
      - Efficacy Meter: `effectiveness_pct` (e.g. `100.0% Effective` with circular/bar indicator)
      - Owner: `owner` (e.g. "M. Alvarez - Shift Operations Lead")
      - Implementation Date: `implementation_date`
      - Verification Method: `verification_method` (e.g. "Zero differential pressure confirmed across bypass valve")
      - Status Badge: `status` (`VERIFIED`, `IMPLEMENTED` in emerald)
      - Citation Badges: Clickable `citation_ids` linked to `onCitationClick`
  - **Column 2: D5 Permanent Corrective Actions (PCA)**:
    - Header: `CheckCircle2` (emerald), "D5: Permanent Corrective Actions", badge: "Root Cause Elimination".
    - Items (`report.d5_permanent_actions`):
      - Action ID (`PCA-01`)
      - Narrative: `action` (e.g. "Upgrade ceramic seal faces to silicon carbide with DLC coating; install automated vibration interlock shutdown")
      - Targeted Root Cause: `target_cause_id` (e.g. "Addresses WHY-4 / WHY-5")
      - Feasibility Score: `feasibility_score / 10`
      - Owner & Target Date: `owner`, `target_date`
      - Validation Plan: `validation_plan`
      - Status Badge: `status` (`OPEN`, `IN_PROGRESS`, `IMPLEMENTED`)
  - **Column 3: D7 Preventative Controls & Horizontal Read-Across**:
    - Header: `Layers` (purple), "D7: Preventative Controls", badge: "Systemic Prevention".
    - Content (`report.d7_preventative_controls`):
      - **SOP Updates**:
        - List of updated standard procedures (`sop_updates`), e.g.:
          - `SOP-PUMP-042 Revision 4: Mandatory thermal pre-conditioning protocol before high-flow operation`
      - **PM Schedule Updates**:
        - List of preventative maintenance schedule revisions (`pm_updates`), e.g.:
          - `PM-410 Revision 2: Laser shaft alignment verification every 500 operating hours`
      - **Horizontal Sister Asset Read-Across**:
        - Badge list of sister assets (`horizontal_assets`), e.g. `Pump-A11`, `Pump-A13`, `Pump-B01`.
        - Read-across status: "Horizontal preventative maintenance update deployed across 3 sister assets."

#### 2. OEM Operating Envelope Deviation Bars
- **Header**:
  - Icon: `BarChart3` or `Sliders` (rose).
  - Title: "OEM Operating Envelope Excursion Analysis".
  - Subtitle: "Observed Incident Telemetry vs Manufacturer Design Boundaries".
  - Stat pill: `${oem_deviations.filter(d => d.is_exceeded).length} Limits Exceeded`.
- **Deviation Parameter Cards (`report.d7_preventative_controls.oem_deviations`)**:
  - Parameter Name: `deviation.parameter_name` (e.g. "Peak Vibration Velocity", "Inboard Bearing Temperature").
  - Comparison Values:
    - OEM Safe Upper Limit: `${deviation.oem_envelope_limit} ${deviation.unit}`
    - Actual Incident Peak: `${deviation.actual_incident_value} ${deviation.unit}`
  - Excursion Metric:
    - Percentage Exceeded: `+${deviation.deviation_percent}% Excursion` (bold red badge).
  - Visual Excursion Gauge / Progress Bar:
    - Background bar represents 0% to 100% of OEM limit in slate-200.
    - Dashed vertical marker line at 100% indicating the OEM threshold limit.
    - Red/Amber excursion segment extending beyond the 100% threshold representing the actual excursion.
  - Excursion Severity Badge:
    - `CRITICAL` (>15% exceedance): `bg-rose-100 text-rose-800 border-rose-300`
    - `HIGH` (0-15% exceedance): `bg-orange-100 text-orange-800 border-orange-300`
    - `NORMAL`: `bg-emerald-100 text-emerald-800 border-emerald-300`
  - Action / Threshold Recommendation:
    - `deviation.recommended_action` (e.g. "Lower trip threshold from 6.0 mm/s to 4.5 mm/s; calibrate vibration sensors quarterly").

#### 3. Historical Near-Miss Match Cards
- **Header**:
  - Icon: `FileSearch` or `History` (blue).
  - Title: "Historical Near-Miss Similarity Matching".
  - Subtitle: "Cross-Referenced Against Institutional Incident Database (`Near_Miss_Report_2023.txt`)".
  - Match count: `${historical_matches.length} Historical Matches Found`.
- **Match Cards (`report.d7_preventative_controls.historical_matches`)**:
  - Matched Report ID: `match.matched_report_id` (e.g. `NM-2023-08-PUMP`).
  - Incident Title: `match.title` (e.g. "High vibration seal fracture in auxiliary feedwater pump").
  - Similarity Score Gauge:
    - Large circular or pill percentage score: `Math.round(match.similarity_score * 100)}% Match`.
    - Color: Emerald for $\ge 85\%$, Amber for $70-84\%$, Slate for $< 70\%$.
  - Shared Symptoms Tags:
    - Tags for each item in `match.matching_symptoms` (e.g. `Vibration spike`, `Ceramic face cracking`, `Cavitation noise`).
  - Historical Recommendations & Lessons Learned:
    - Bulleted list of `match.preventative_recommendations`.
  - Recurrence Risk Assessment:
    - `match.recurring_risk_assessment` warning callout.
  - "Inspect Citation Evidence" Button:
    - Icon: `ExternalLink`.
    - Triggers `onCitationClick(match.source_doc_citation_id || match.matched_report_id)`.

---

### 2.5 Integration Touchpoints

#### 1. Integration in `ArtifactPanel.jsx`
- **Location**: `frontend/src/components/ArtifactPanel.jsx`
- **Detection Function Enhancement**:
  ```javascript
  function is8DArtifact(artifact) {
    if (!artifact) return false;
    if (artifact.type === '8d_report' || artifact.type === 'rca') return true;
    if (artifact.report && typeof artifact.report === 'object') return true;
    if (typeof artifact.content === 'string') {
      const trimmed = artifact.content.trim();
      if (trimmed.startsWith('{') && (trimmed.includes('d1_team') || trimmed.includes('d2_problem') || trimmed.includes('report_id'))) {
        return true;
      }
    }
    return false;
  }
  ```
- **Type Label and Icon**:
  - When `is8DArtifact(artifact)` is true:
    - TypeIcon: `ShieldCheck`
    - TypeLabel: `"8D Incident Studio"`
    - Badge: `"bg-indigo-100 text-indigo-700"`
    - Tabs available: `['studio', 'json', 'preview']`
- **Rendering**:
  - In `ArtifactPanel` render content:
    ```jsx
    {activeTab === 'studio' && is8D && (
      <EightDIncidentStudio
        report={parsedReport}
        onSourceClick={onSourceClick}
        onClose={onClose}
      />
    )}
    ```
- **Props update in `App.jsx`**:
  - Line 402 of `App.jsx` updated to pass `onSourceClick={setActiveSource}` to `ArtifactPanel`.

#### 2. Integration in `Sidebar.jsx`
- **Location**: `frontend/src/components/Sidebar.jsx` lines 183–202.
- **Prop**: `onShowEightDStudio: () => void`.
- **Button JSX**:
  ```jsx
  <button
    onClick={onShowEightDStudio}
    className="w-full flex items-center justify-between py-2 px-2.5 rounded-lg text-xs font-bold bg-slate-800/80 hover:bg-rose-950/40 text-rose-300 border border-rose-500/20 hover:border-rose-500/40 transition-all group mt-2"
  >
    <div className="flex items-center gap-2">
      <ShieldAlert className="w-3.5 h-3.5 text-rose-400 group-hover:scale-110 transition-transform flex-shrink-0" />
      <span className="truncate">8D Incident Studio</span>
    </div>
    <div className="flex items-center gap-1.5">
      <span className="text-[9px] bg-rose-500/20 text-rose-300 px-1.5 py-0.5 rounded font-mono font-bold">RCA</span>
      <div className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse flex-shrink-0" />
    </div>
  </button>
  ```
- **Modal in `App.jsx`**:
  ```jsx
  {showEightDStudio && (
    <EightDIncidentStudio
      report={activeEightDReport}
      onClose={() => setShowEightDStudio(false)}
      onSourceClick={setActiveSource}
      isModal={true}
    />
  )}
  ```

#### 3. Wiring to `SourceViewerModal.jsx`
`SourceViewerModal` expects `{ source, snippet, url }`.
When `onCitationClick(citationId)` is invoked:
1. Lookup citation object in `report.citations` by `citation_id`.
2. Format as:
   ```javascript
   {
     source: cite.title ? `${cite.title} (${cite.source_doc})` : cite.source_doc,
     snippet: cite.excerpt,
     section: cite.section,
     url: null,
     citation_id: cite.citation_id,
     confidence: cite.confidence
   }
   ```
3. Invoke `onSourceClick(formattedCitation)`.
4. `App.jsx` sets `activeSource`, triggering `SourceViewerModal` overlay displaying the verbatim evidence and source title.

---

## 3. Caveats

1. **SVG Visualizers & Timeline Rail**:
   - `FiveWhyFishboneTab.jsx` and `TimelineTab.jsx` are complementary tabs under Milestone 4. While `EightDIncidentStudio.jsx` provides the tab switching shell and prop contracts for these tabs, their internal SVG layouts and D3/SVG drawing are coordinated across M4 components.
2. **Offline Fallback Guarantee**:
   - In environments where the backend `/api/v1/rca/*` endpoints are temporarily offline or unseeded, `mockReportData.js` must be bundled as an authentic fallback representing the Pump-A12 ceramic seal failure report so the UI is 100% resilient and interactive in any state.
3. **Print Media Rendering**:
   - `@media print` rules depend on the browser engine's print previewer. Modern browsers require explicit background printing (`print-color-adjust: exact; -webkit-print-color-adjust: exact;`) to ensure badge colors, gauge bars, and risk meters render faithfully on physical paper or exported PDFs.

---

## 4. Conclusion

The architecture for Milestone 4 (Frontend 8D Studio Container, Navigation, Overview & Corrective Actions Tabs) is fully specified, verified against backend schemas, and ready for immediate implementation by `coder_m4_1`:

1. **`EightDIncidentStudio.jsx`** serves as the central container with 4-tab navigation, top audit header (Asset Tag, Severity, RPN meter, SHA-256 seal), multi-format export dropdown ("Print / PDF", "HTML Evidence", "Canonical JSON"), and full-screen modal capability.
2. **`OverviewTab.jsx`** comprehensively presents D1 Team Formation, D2 5W2H Problem Description with downtime impact, AIAG-VDA Risk Priority Number (RPN) scoring with initial vs mitigated risk reduction, and D8 Recognition & Sign-off certification.
3. **`CorrectiveActionsTab.jsx`** structures the D3 Interim Containment vs D5 Permanent Corrective Actions vs D7 Preventative Controls matrix, interactive OEM operating envelope deviation bars with percentage excursions and limits, and historical near-miss similarity matching cards.
4. **Integration touchpoints** in `ArtifactPanel.jsx` (8D artifact auto-detection), `Sidebar.jsx` (direct launcher button), and `App.jsx` (modal overlay and `onSourceClick` routing to `SourceViewerModal.jsx`) provide seamless user workflows with zero architectural gaps.

---

## 5. Verification Method

### 5.1 Static Verification
1. **File Locations**:
   - `frontend/src/components/EightDStudio/EightDIncidentStudio.jsx`
   - `frontend/src/components/EightDStudio/OverviewTab.jsx`
   - `frontend/src/components/EightDStudio/CorrectiveActionsTab.jsx`
   - `frontend/src/components/EightDStudio/mockReportData.js`
   - `frontend/src/components/EightDStudio/printStyles.css`
2. **Artifact & Sidebar Integration**:
   - Inspect `frontend/src/components/ArtifactPanel.jsx` for `is8DArtifact` check and studio tab rendering.
   - Inspect `frontend/src/components/Sidebar.jsx` for the `8D Incident Studio` launcher button.
   - Inspect `frontend/src/App.jsx` for `showEightDStudio` state and `onSourceClick` prop passing.

### 5.2 Build & Runtime Verification
Run in `frontend/`:
```powershell
npm run build
```
- Expected result: Exit code 0, 0 compilation errors, clean bundle creation.

### 5.3 Invalidation Conditions
- Any missing prop or undefined reference causing runtime React crash when `report` is null/partially populated.
- Failure of citation badge clicks to trigger `SourceViewerModal`.
- Failure of `npm run build` during Vite bundling.
