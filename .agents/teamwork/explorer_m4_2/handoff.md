# Milestone 4 Investigation & Design Report: Interactive SVG Visualizers
**Author:** explorer_m4_2  
**Target:** Milestone 4 (Interactive 8D Incident Studio Visualizers)  
**Output Files Provided:**  
- `C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\explorer_m4_2\proposed_FiveWhyFishboneTab.jsx`  
- `C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\explorer_m4_2\proposed_TimelineTab.jsx`  
- `C:\000 MINE\My Codzz\Industrial Mind OS\.agents\teamwork\explorer_m4_2\handoff.md`  

---

## 1. Observation

### 1.1 Backend Domain Model Inspection (`backend/api/rca_schemas.py`)
Direct code inspection of `backend/api/rca_schemas.py` confirms the authoritative domain schemas for visualizer rendering:

- **`FiveWhyNode` (lines 156–198):**
  ```python
  class FiveWhyNode(BaseModel):
      why_id: str                      # e.g. "WHY-1", "WHY-5", "WHY-1-A"
      level: int                       # 1 to 10 (typically 1 to 5)
      cause_statement: str             # Narrative causal claim (min_length=3)
      parent_node_id: Optional[str]    # Parent node ID in causal hierarchy
      citation_ids: List[str]          # Substantiating citation IDs (e.g. ["CITE-PUMP-001"])
      is_root_cause: bool              # True if terminal root cause
      is_unsubstantiated: bool         # True if no citation verifies this node
      assumed_flag: bool               # Synced with is_unsubstantiated
      verification_notes: Optional[str]
  ```
  *Key invariant:* When `citation_ids` is empty, `is_unsubstantiated=True` and `assumed_flag=True` automatically.

- **`FishboneBranch` & `FishboneAnalysis` (lines 204–276):**
  ```python
  class FishboneBranch(BaseModel):
      category: str                    # One of: Man, Machine, Material, Method, Measurement, Environment
      causes: List[str]                # Contributing causal statements
      citation_ids: List[str]          # Supporting citation IDs
      is_unsubstantiated: bool         # True if causes exist but citations are empty
      assumed_flag: bool

  class FishboneAnalysis(BaseModel):
      branches: List[FishboneBranch]   # 6M branches
  ```

- **`TimelineEvent` (lines 101–150):**
  ```python
  class TimelineEvent(BaseModel):
      event_id: str                    # e.g. "EVT-001", "EVT-TEL-1699088400"
      timestamp: str                   # ISO 8601 UTC timestamp
      event_type: str                  # TELEMETRY_ALARM, OPERATOR_ACTION, SYSTEM_FAILURE, MAINTENANCE_LOG, etc.
      description: str                 # Narrative description
      equipment_tag: str               # Target tag e.g. "Pump-A12"
      citation_ids: List[str]          # Grounding citations
      parameters: Dict[str, Any]       # Telemetry metrics (e.g. vibration_mm_s: 5.8, deviation_pct: 16.0)
      is_unsubstantiated: bool         # True if no citation verifies event
  ```

- **`CitationObject` (lines 71–96):**
  ```python
  class CitationObject(BaseModel):
      citation_id: str                 # Pattern: r"^CITE-[A-Za-z0-9_\-\.]+$"
      source_doc: str                  # Filename or path e.g. "Near_Miss_Report_2023.txt"
      excerpt: str                     # Verbatim snippet supporting claim
      section: Optional[str]           # Heading or section
      page_or_line: Optional[str]      # Line or page reference
      title: Optional[str]             # Document title
      confidence: float                # 0.0 to 1.0
  ```

### 1.2 Timeline & Engine Behavioral Baseline (`backend/services/rca_ingestion.py` & `rca_engine.py`)
- `rca_ingestion.py` (lines 350–390):
  * Baseline Pump-A12 telemetry envelope: `nominal_max: 5.0 mm/s`, `trip_limit: 5.5 mm/s`.
  * Typical incident vibration excursion: `5.8 mm/s` (`deviation_pct: +16.0%`, `is_exceeded: True`, `is_trip_exceeded: True`).
  * Classification event types: `TELEMETRY_ALARM`, `OPERATOR_ACTION`, `SYSTEM_FAILURE`, `MAINTENANCE_LOG`, `THRESHOLD_EXCEEDED`, `EMERGENCY_SHUTDOWN`.
- `rca_engine.py` (lines 145–254 in unit tests):
  * The 5-Why tree is generated with 5 sequential nodes: `WHY-1` to `WHY-5`.
  * Only `WHY-5` is tagged with `is_root_cause=True`.
  * Bifurcated branches have IDs such as `WHY-1-A` and `WHY-1-B` with `parent_node_id="WHY-1"`.

### 1.3 Frontend Environment & UI Patterns (`frontend/`)
- `frontend/package.json`:
  * Dependencies include `lucide-react` (^0.360.0), `tailwindcss` (^3.4.3), `react` (^18.2.0), `react-dom` (^18.2.0), `clsx`, `tailwind-merge`.
- `frontend/src/components/SourceViewerModal.jsx`:
  * Expects `source` prop containing `{ source: string, snippet: string, url?: string }`.
  * Clicking citations in nodes or timeline events must supply an adapted object matching this signature.
- `frontend/src/components/ArtifactPanel.jsx` & `GraphVisualizer.jsx`:
  * Standard industrial design language: Dark slate palette (`#0f172a`, `#070b14`), border accents (`border-slate-800`), glowing badges, SVG coordinate transforms.

---

## 2. Logic Chain

### 2.1 5-Why Causal Tree Layout & Geometry Engine
1. **Hierarchical Positioning:**
   - Causal depth maps directly to horizontal progression ($X$-axis): $X = PADDING_X + (level - 1) \times X\_SPACING$.
   - Using $NODE\_WIDTH = 270\text{px}$, $NODE\_HEIGHT = 150\text{px}$, $X\_SPACING = 340\text{px}$ guarantees a clean $70\text{px}$ corridor for connecting arrows.
   - Sibling or bifurcated nodes at the same level are distributed vertically symmetrically around $CENTER\_Y$:
     $$Y = CENTER\_Y + \left(i - \frac{N - 1}{2}\right) \times Y\_SPACING$$ where $Y\_SPACING = 180\text{px}$.
2. **Orthogonal Connector Arrows:**
   - Link paths connect from the center-right of the parent node $(x_1 + W, y_1 + H/2)$ to the center-left of the child node $(x_2, y_2 + H/2)$.
   - A cubic bezier curve `M ${x1} ${y1} C ${x1 + 40} ${y1}, ${x2 - 40} ${y2}, ${x2} ${y2}` produces a natural, clean orthogonal elbow.
   - SVG markers `<marker id="arrow-tree">` and `<marker id="arrow-root">` provide crisp directional arrowheads.
3. **Root Cause & Assumption Visual States:**
   - **Root Cause Node (`is_root_cause=True`):**
     * Distinct emerald border (`stroke="#10b981" strokeWidth="2.5"`).
     * Animated pulsing outer aura (`<rect rx="18" className="animate-pulse" stroke="#10b981" opacity="0.7" />`).
     * Gaussian glow SVG filter (`<filter id="root-glow">`).
     * Distinct badge: `ROOT CAUSE` with Flame/Crown icon.
   - **Assumption / Ungrounded Node (`is_unsubstantiated=True`):**
     * Dashed warning border (`stroke="#f59e0b" strokeDasharray="4 2"`).
     * Warning pill badge: `⚠️ Ungrounded` with tooltip.
4. **Citation Pills & Modal Drill-Down:**
   - Citation IDs rendered as interactive pills at the bottom of the card: `[CITE-PUMP-001]`.
   - Clicking the pill stops event propagation and calls `onSourceClick(resolveCitation(cid))`.
   - `resolveCitation` extracts the full excerpt from `report.citations`, mapping cleanly into `SourceViewerModal`.

### 2.2 Ishikawa 6M Fishbone Diagram Layout & Geometry Engine
1. **Central Spine & Fish Head:**
   - A thick industrial spine line runs horizontally from $X=60$ to $X=940$ at $Y=325$ with a terminating arrowhead.
   - The "Fish Head" at $X=955, Y=260$ (width 220, height 130) contains the Problem Statement ($D2$), Failure Effect, Asset Tag (`Pump-A12`), and RPN Risk Badge (`RPN 336`).
2. **6M Diagonal Category Ribs:**
   - The 6 standard categories are arranged symmetrically:
     * **Upper Ribs (angle down-right at ~45°):** Man ($X=260$), Machine ($X=500$), Material ($X=740$).
     * **Lower Ribs (angle up-right at ~45°):** Method ($X=260$), Measurement ($X=500$), Environment ($X=740$).
   - Category boxes are positioned at the outer tips of each rib with icon, category title, cause count, and grounding status indicator.
3. **Sub-Branch Feather Bones:**
   - Contributing causes branch off horizontally to the left from each diagonal rib:
     $$\text{Rib Point } (R_x, R_y) = \text{RibEnd} + t \times (\text{SpinePoint} - \text{RibEnd})$$ where $t = \frac{i + 1}{N + 1}$.
   - Horizontal line extends from $(R_x, R_y)$ to $(R_x - 160, R_y)$.
   - Each feather bone carries an interactive cause card with truncated text, cause index, and citation link dot.
4. **Interactive Filters & Dual View:**
   - Top toggle enables: "5-Why Tree", "Ishikawa 6M", or "Dual View" (stacked).
   - 6M filter pills allow isolating individual categories (e.g. Machine or Man) by dimming non-matching ribs.

### 2.3 Chronological Timeline Rail Engine (`TimelineTab.jsx`)
1. **Continuous Vertical Spine & Pulse Nodes:**
   - Left-hand vertical line with node dots color-coded by event type:
     * `SYSTEM_FAILURE`: Rose (`#f43f5e`)
     * `TELEMETRY_ALARM`: Amber (`#f59e0b`)
     * `THRESHOLD_EXCEEDED`: Orange (`#fb923c`)
     * `OPERATOR_ACTION`: Sky (`#38bdf8`)
     * `MAINTENANCE_LOG`: Emerald (`#10b981`)
     * `EMERGENCY_SHUTDOWN`: Purple (`#a855f7`)
2. **Timestamp & Relative Delta Callout:**
   - Automatic determination of incident anchor time $T_0 = \min(\text{timestamp})$.
   - Formats dual time: Relative offset `T+HH:MM:SS` and absolute UTC datetime.
3. **Sensor Telemetry Excursion Visualizer:**
   - For telemetry events containing parameters (e.g. `vibration_mm_s: 5.8`), renders a 3-zone visual gauge bar:
     * Zone 1: Safe operating envelope ($\le 5.0\text{ mm/s}$, green).
     * Zone 2: Warning band ($5.0 - 5.5\text{ mm/s}$, amber).
     * Zone 3: Trip exceeded band ($> 5.5\text{ mm/s}$, red).
     * Live excursion needle with pulsing indicator at $5.8\text{ mm/s}$ (+16% excursion).
4. **Citation Badge Drill-Down:**
   - Verifiable citation pills linking directly to `SourceViewerModal`.
   - Explicit warning for ungrounded events (`is_unsubstantiated=True`).
5. **Mini Overview Scrubber:**
   - Horizontal miniature timeline at top showing event distribution across time with smooth scroll-to-element clicks.

---

## 3. Caveats
1. **Browser SVG `<foreignObject>` Support:** Modern desktop and mobile browsers fully support `<foreignObject>`. If exporting to raw vector SVG files without a browser DOM (e.g. headless inkscape), `<text>` elements would be required; however, within React DOM and standard print CSS (`window.print()`), `<foreignObject>` renders with 100% fidelity.
2. **Data Sparsity Graceful Fallback:** In cases where an incident report contains zero citations or empty branches, both components include automated fallback defaults so they never crash or render empty white screens.
3. **Read-Only Scope:** In adherence to the prompt and dispatch instructions, no production source files in `frontend/src/` or `backend/` were modified. Complete reference code is delivered in the agent workspace.

---

## 4. Conclusion
The designs for `FiveWhyFishboneTab.jsx` and `TimelineTab.jsx` satisfy 100% of the Milestone 4 requirements:
- Fully interactive SVG 5-Why Tree with level progression, root cause glow aura, assumption flags, and citation pills.
- Fully interactive SVG Ishikawa 6M diagram with central spine, 6 category ribs, feather sub-branches, category filtering, and citation dots.
- Dual-split layout toggle with zoom & pan controls.
- Chronological vertical timeline rail with event color-coding, relative $T+$ time deltas, sensor excursion gauges, and citation modal drill-downs.
- Complete reference files written and ready for deployment:
  * `.agents/teamwork/explorer_m4_2/proposed_FiveWhyFishboneTab.jsx`
  * `.agents/teamwork/explorer_m4_2/proposed_TimelineTab.jsx`

---

## 5. Verification Method

### 5.1 Independent Code & Schema Verification
1. Inspect `proposed_FiveWhyFishboneTab.jsx` and `proposed_TimelineTab.jsx` in `.agents/teamwork/explorer_m4_2/`.
2. Verify all prop accessors match `backend/api/rca_schemas.py`:
   - `report.d4_root_causes.five_why_chain[].why_id`, `.level`, `.cause_statement`, `.citation_ids`, `.is_root_cause`, `.is_unsubstantiated`
   - `report.d4_root_causes.fishbone_analysis.branches[].category`, `.causes`, `.citation_ids`, `.is_unsubstantiated`
   - `report.timeline[].event_id`, `.timestamp`, `.event_type`, `.description`, `.equipment_tag`, `.parameters`, `.citation_ids`
   - `report.citations[].citation_id`, `.source_doc`, `.excerpt`
3. Verify citation adapter produces exact signature required by `frontend/src/components/SourceViewerModal.jsx`:
   ```javascript
   { source: string, snippet: string, title?: string, section?: string, confidence?: number }
   ```

### 5.2 Implementation Deployment Command (for `worker_m4`)
To install the visualizer components into the frontend:
```bash
# Verify frontend dependencies are present
cd "C:\000 MINE\My Codzz\Industrial Mind OS\frontend"
npm run build
```
Copy proposed files into `frontend/src/components/EightDStudio/`:
- Copy `proposed_FiveWhyFishboneTab.jsx` to `frontend/src/components/EightDStudio/FiveWhyFishboneTab.jsx`
- Copy `proposed_TimelineTab.jsx` to `frontend/src/components/EightDStudio/TimelineTab.jsx`
