# Industrial Mind OS: Unified Asset & Operations Brain

![Industrial Mind OS Architecture](architecture.jpeg)

**Industrial Mind OS** is an elite, AI-powered Industrial Knowledge Intelligence platform designed to solve the "Knowledge Cliff" in asset-intensive industries. This platform ingests heterogeneous industrial documents (P&IDs, maintenance records, safety procedures, OEM manuals, inspection reports) and transforms them into a living, queryable, and proactive intelligence engine.

It eliminates the fragmentation of operating across multiple disconnected document systems and empowers Field Technicians and Plant Engineers with instant, highly accurate answers backed by compliance evidence and proactive alerts.

---

## 🚀 Core Capabilities & Feature Deep-Dive

### 1. Universal Document Ingestion & Synchronization
Industrial Mind OS acts as a central repository that reads any format an industrial plant uses:
*   **Multi-Format Support:** Natively supports PDF, DOCX, TXT, PPTX, and **CSV** (for structured maintenance logs and spreadsheets).
*   **Computer Vision OCR (Llama-4):** Integrates Groq's multimodal `llama-4-scout-17b` AI to extract text, measurements, valve labels, and structural metadata directly from uploaded `.png`, `.jpg`, and `.jpeg` images (e.g., P&IDs and scanned engineering drawings).
*   **Confluence Enterprise Sync:** Securely connects to enterprise Confluence workspaces to scrape and synchronize living internal wikis.
*   **Smart Deletion Pipeline:** Deleting a document from the UI automatically triggers a background process that scrubs its data from the Vector Database (Qdrant) and prunes orphaned nodes/edges from the Graph Database to prevent "ghost data."

### 2. Multi-Modal Agentic Chat (The Knowledge Copilot)
A highly advanced LangGraph conversational AI orchestrator that mimics human problem-solving:
*   **Triple-Mode RAG Architecture:**
    *   *Private Mode:* Strict zero-hallucination querying using ONLY internally uploaded engineering documents.
    *   *Hybrid Mode:* Searches internal documents first, then dynamically searches the live internet (via Tavily/Firecrawl) to supplement missing specs.
    *   *Live Web Mode:* Acts as a live industrial research assistant bypassing internal data.
*   **Document Gating (Source Selection):** Users can explicitly select which manuals or logs the AI should restrict its search to for a specific chat.
*   **Agentic Thought Process Viewer:** The AI breaks down its LangGraph workflow (Planner → Retriever → WebSearch → MemoryBuilder → Synthesizer → Verifier) inside the chat bubble, building trust with engineers by showing *how* it reached its conclusion.
*   **Rich UI Rendering:** The chat natively renders Markdown, code blocks, and dynamic HTML/Tailwind dashboards directly inside the conversation.

### 3. Retrieval Insight Panel
A persistent right-hand sidebar that acts as the transparent "brain scan" of the AI:
*   **Heuristic Confidence Scoring:** Calculates a real-time confidence percentage (graded dynamically on context quality, lack of refusal signals, and citation density) displayed as a color-coded progress bar.
*   **Retrieval Strategy:** Informs the user exactly which LangChain strategy was deployed.
*   **Verified Citations:** Lists the exact source documents utilized. Inside the chat, these citations render as clickable buttons.
*   **Historical Message Memory:** Clicking any previous message instantly updates the Insight Panel to show the confidence and sources for that specific historical interaction.

### 4. Proactive Auditor Engine (Background Intelligence)
An asynchronous LangChain agent that transforms the platform from "reactive" to "proactive":
*   **Continuous Scanning:** Whenever a new document (e.g., a daily maintenance log) is uploaded, the Auditor Engine silently scans it against the entire existing Knowledge Graph.
*   **Compliance Gap Detection:** Automatically detects if a new log violates a safety limit specified in an older OEM manual.
*   **Historical Pattern Recognition:** Identifies if a new symptom matches a near-miss incident report from years ago.
*   **Push Notifications (Bell System):** Triggers a red flashing notification bell in the UI, dropping down a detailed alert warning the engineering team before a catastrophic failure occurs.

### 5. Quality & Regulatory Compliance Export
Built specifically for Quality Management System (QMS) integration and auditing:
*   **Export Audit Report:** With a single click at the bottom of any AI response, the system strips out raw code and UI elements, formatting the Root Cause Analysis (RCA) and its cited sources into a beautifully styled HTML layout.
*   **Native PDF Evidence:** Instantly triggers the browser's native print engine to allow technicians to "Save as PDF", producing a professional, timestamped Audit Evidence Package for regulatory inspectors.

### 6. The Asset Relationship Graph (Topology Visualizer)
A visual explorer for complex industrial ontologies:
*   **Automated Graph Extraction:** As documents are indexed, a NetworkX graph database automatically constructs Entity nodes (Contexts and Hubs).
*   **D3.js Interactive Visualization:** A stunning 3D/2D force-directed physics graph in the sidebar.
*   **Browser Crash Safeguards:** Intelligently caps rendering at the Top 300 most relevant nodes to ensure the frontend remains buttery smooth even when thousands of documents are ingested.

---

## 🛠️ Technology Stack

**Frontend:**
*   React.js + Vite
*   Tailwind CSS (Glassmorphism & Industrial UI Design)
*   Lucide React (Iconography)
*   React Markdown (Rich text rendering)

**Backend Intelligence:**
*   FastAPI (Python)
*   LangChain & LangGraph (Multi-Agent Orchestration)
*   Groq API (Llama-3.3-70b-versatile for synthesis, Llama-4 for Vision/OCR)
*   Qdrant (Vector Database for semantic search)
*   NetworkX (Graph Database processing)

**Infrastructure & Search:**
*   Supabase (PostgreSQL Auth & Session Management)
*   Tavily & Firecrawl (Web scraping & RAG context augmentation)

---

## ⚙️ Quick Start (Local Development)

### 1. Clone & Setup
```bash
git clone https://github.com/YourUsername/IndustrialMindOS.git
cd IndustrialMindOS
```

### 2. Backend (FastAPI + AI Agents)
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Create a .env file and add your API Keys (Groq, Supabase, Tavily, Firecrawl)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev
```

*Industrial Mind OS — Connecting the dots that no individual team member can connect alone.*
