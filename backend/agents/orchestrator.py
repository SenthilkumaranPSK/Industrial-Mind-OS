import os
import logging
from typing import TypedDict, List
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from storage.vector_db import vector_db
from storage.graph_db import graph_db
from storage.memory_cache import memory_cache
from core.embeddings import LocalEmbedder
from agents.verification import score_answer

load_dotenv()
logger = logging.getLogger(__name__)

# The "brain" model for synthesis/reasoning-heavy calls; a faster/cheaper model for
# quick query-rephrasing calls where deep reasoning isn't needed.
SYNTHESIS_MODEL = "gemini-2.5-pro"
FAST_MODEL = "gemini-2.5-flash"

# 1. Defined State for All Agents
class AgentState(TypedDict):
    query: str
    original_query: str
    mode: str  # "Private", "Online", or "Hybrid"
    vector_context: List[dict] # [{"source": str, "content": str}]
    graph_context: List[dict]  # [{"source": str, "content": str}]
    memory_context: List[dict] # [{"source": str, "content": str}]
    web_context: List[dict]    # [{"source": str, "content": str}]
    fused_context: str
    citations: List[dict]      # Final list of sources used
    final_answer: str
    confidence: float
    strategy: str
    steps_taken: List[dict]
    retry_count: int
    files: List[str]  # Restricted knowledge scope for this chat
    owner_id: str     # Whose knowledge base to read; None means unscoped

def run_llm(system_prompt: str, user_prompt: str) -> str:
    """Helper to query Gemini (the main reasoning brain) for synthesis"""
    try:
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key or api_key.startswith("paste-") or api_key.startswith("your-"):
            return "GOOGLE_API_KEY is not configured or is a placeholder. Please set a valid Google Gemini API key in `backend/.env` to enable AI synthesis."

        llm = ChatGoogleGenerativeAI(model=SYNTHESIS_MODEL, temperature=0.0, google_api_key=api_key)
        prompt = ChatPromptTemplate.from_messages([("system", "{sys}"), ("human", "{usr}")])
        chain = prompt | llm
        return chain.invoke({"sys": system_prompt, "usr": user_prompt}).content
    except Exception as e:
        logger.error(f"Gemini API Call Failed: {e}")
        return f"Error connecting to Gemini Intelligence: {e}"

# ----------------- AGENT 1: PLANNING AGENT -----------------
def planning_node(state: AgentState):
    logger.info("Agent [Planner]: Decomposing query")
    state["steps_taken"] = state.get("steps_taken", [])
    state["steps_taken"].append({"step": "Root Cause Analysis (RCA) / Query Decomposition", "status": "Done"})
    
    if not state.get("original_query"):
        state["original_query"] = state["query"]
    state["retry_count"] = state.get("retry_count", 0)
    
    # We let the fast model rephrase or simplify the query if needed
    if " and " in state["query"].lower() or "compare" in state["query"].lower():
        system = "You are the Planning Agent. Rephrase the user query into clear search engine keywords. Output ONLY the rephrased query."
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if api_key and not api_key.startswith("paste-") and not api_key.startswith("your-"):
            try:
                llm_fast = ChatGoogleGenerativeAI(model=FAST_MODEL, temperature=0.0, google_api_key=api_key)
                prompt = ChatPromptTemplate.from_messages([("system", system), ("human", f"Fix this: {state['query']}")])
                rephrased_content = (prompt | llm_fast).invoke({}).content
                if rephrased_content:
                    state["query"] = rephrased_content.strip()
                    logger.info(f"Query rephrased to: {state['query']}")
            except Exception as e:
                logger.warning(f"Planning LLM call failed, using original query: {e}")
            
    return state

# ----------------- AGENT 2: ADAPTIVE RETRIEVAL AGENT -----------------
def adaptive_retrieval_node(state: AgentState):
    logger.info("Agent [AdaptiveRetriever]: Selecting search domains")
    state["steps_taken"].append({"step": "Asset Database & Maintenance Log Retrieval", "status": "Done"})
    
    # 1. Fetch Direct Memory (Small files that bypassed RAG, filtered by chat selection)
    # Only in Private or Hybrid mode
    if state.get("mode", "Private") in ("Private", "Hybrid"):
        state["memory_context"] = memory_cache.get_context(
            state.get("files"), owner_id=state.get("owner_id")
        )
    else:
        state["memory_context"] = []
    
    # 2. Qdrant Vector Search (only in Private/Hybrid)
    if state.get("mode", "Private") in ("Private", "Hybrid"):
        try:
            embedder = LocalEmbedder.get_embedder()
            query_vector = embedder.embed_query(state["query"])
            # Pass file filter to vector search for chat isolation
            results = vector_db.search(
                query_vector, limit=10,
                file_filter=state.get("files"), owner_id=state.get("owner_id"),
            )
            state["vector_context"] = [
                {"source": r.payload.get("file_name", "Unknown"), "content": r.payload.get("text", "")} 
                for r in results
            ] if results else []
        except Exception as e:
            logger.warning(f"Vector search failed: {e}")
            state["vector_context"] = []
    else:
        state["vector_context"] = []

    # 3. NetworkX Graph Search (Multi-Hop)
    # Only in Private or Hybrid mode
    if state.get("mode", "Private") in ("Private", "Hybrid"):
        keywords = state["query"].split()
        g_ctx = []
        for w in keywords:
            if len(w) > 4:  # Quick keyword rule
                g_ctx.extend(graph_db.get_context_for_entity(
                    w, file_filter=state.get("files"), owner_id=state.get("owner_id")
                ))
        state["graph_context"] = g_ctx
    else:
        state["graph_context"] = []
    
    # Set the strategy string for Frontend UI tracking
    has_vector = len(state["vector_context"]) > 0
    has_graph = len(state["graph_context"]) > 0
    has_memory = len(state["memory_context"]) > 0
    mode = state.get("mode", "Private")
    
    if mode == "Online":
        state["strategy"] = "Live Web Intelligence Search"
    elif mode == "Hybrid":
        state["strategy"] = "Hybrid: Private Documents + Web Search"
    elif has_memory and not has_vector:
        state["strategy"] = "Direct Knowledge Injection (Small Files)"
    elif has_vector and has_graph:
        state["strategy"] = "Deep Hybrid (Vectors + Graph)"
    elif has_vector:
        state["strategy"] = "Vector Semantic Search"
    else:
        state["strategy"] = "Fallback Deterministic Search"
        
    return state

# ----------------- AGENT 3: WEB SEARCH NODE -----------------
def web_search_node(state: AgentState):
    """Fetches live internet results using Tavily (Primary), FireCrawl, or DDGS"""
    mode = state.get("mode", "Private")
    if mode not in ("Online", "Hybrid"):
        state["web_context"] = []
        return state

    logger.info(f"Agent [WebSearch]: Fetching live web results (mode={mode})")
    state["steps_taken"].append({"step": "External Industry Standards & Web Fetch", "status": "Done"})
    
    search_query = state["query"]
    # 0. Quick Keyword Refinement
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if api_key and not api_key.startswith("paste-") and not api_key.startswith("your-"):
        try:
            refine_sys = "You are a Search Expert. Convert the user query into 3-5 high-intent search keywords. Output ONLY keywords."
            llm_fast = ChatGoogleGenerativeAI(model=FAST_MODEL, temperature=0.0, google_api_key=api_key)
            search_query = llm_fast.invoke([("system", refine_sys), ("human", state["query"])]).content
            logger.info(f"Refined Web Query: {search_query}")
        except Exception:
            pass

    # 1. PRIMARY: TAVILY SEARCH (Optimized for RAG)
    tavily_key = os.getenv("TAVILY_API_KEY")
    if tavily_key:
        try:
            from tavily import TavilyClient
            tavily = TavilyClient(api_key=tavily_key)
            # Use 'context' search for RAG-ready data
            response = tavily.search(query=search_query, search_depth="advanced", max_results=5)
            if response and "results" in response:
                state["web_context"] = [
                    {
                        "source": f"Web: {r.get('title', 'Tavily Intelligence')}", 
                        "content": r.get("content", ""), 
                        "url": r.get("url")
                    } 
                    for r in response["results"]
                ]
                logger.info(f"Tavily: Fetched {len(state['web_context'])} premium results.")
                return state
        except Exception as e:
            logger.warning(f"Tavily search failed: {e}. Falling back...")

    # 2. SECONDARY: FIRE_CRAWL (If Tavily fails)
    firecrawl_key = os.getenv("FIRE_CRAWL_API_KEY")
    if firecrawl_key:
        try:
            from firecrawl import FirecrawlApp
            app = FirecrawlApp(api_key=firecrawl_key)
            search_result = app.search(search_query) # Modern SDK usage
            
            # Safely handle Pydantic object return types
            if hasattr(search_result, "model_dump"):
                search_result = search_result.model_dump()
            elif hasattr(search_result, "dict"):
                search_result = search_result.dict()
            elif not isinstance(search_result, dict):
                search_result = vars(search_result)
                
            data = search_result.get("data", []) if isinstance(search_result, dict) else getattr(search_result, "data", [])
            
            # Also safely cast items inside data
            safe_data = []
            for item in data:
                if hasattr(item, "model_dump"): safe_data.append(item.model_dump())
                elif hasattr(item, "dict"): safe_data.append(item.dict())
                elif not isinstance(item, dict): safe_data.append(vars(item))
                else: safe_data.append(item)

            if safe_data:
                state["web_context"] = [
                    {
                        "source": f"Web: {r.get('metadata', {}).get('title', 'Firecrawl Intelligence')}", 
                        "content": r.get("markdown", r.get("content", ""))[:1500],
                        "url": r.get("url")
                    } 
                    for r in safe_data[:3]
                ]
                logger.info(f"Firecrawl: Extracted {len(state['web_context'])} deep pages.")
                return state
        except Exception as e:
            logger.warning(f"Firecrawl failed: {e}.")

    # 3. FALLBACK: DUCKDUCKGO (If all else fails)
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            # Modern usage for DDGS 6.x
            results = list(ddgs.text(search_query, max_results=8))
            state["web_context"] = [
                {"source": f"Web: {r.get('title') or r.get('href', 'Web')}", "content": r.get("body", ""), "url": r.get("href")} 
                for r in results if r.get("body")
            ]
        logger.info(f"WebSearch: Fetched {len(state['web_context'])} DDG results.")
    except Exception as e:
        logger.error(f"All web search methods failed: {e}")
        state["web_context"] = []
    return state

# ----------------- AGENT 4: MEMORY BUILDER -----------------
def memory_builder_node(state: AgentState):
    logger.info("Agent [MemoryBuilder]: Fusing distinct records")
    state["steps_taken"].append({"step": "Unified Asset Brain Fusion", "status": "Done"})
    
    all_records = (
        state.get("vector_context", []) +
        state.get("graph_context", []) +
        state.get("memory_context", []) +
        state.get("web_context", [])
    )
    
    # Deduplicate based on content
    seen_content = set()
    unique_records = []
    for r in all_records:
        if r and r.get("content") and str(r["content"]).strip():
            content = str(r["content"]).strip()
            if content not in seen_content:
                seen_content.add(content)
                unique_records.append({
                    "source": r.get("source", "Unknown Source"),
                    "content": content,
                    "url": r.get("url")
                })
    
    state["citations"] = unique_records
    
    if unique_records:
        state["fused_context"] = "\n\n---\n\n".join([f"Source: {r['source']}\n{r['content']}" for r in unique_records])
    else:
        state["fused_context"] = "SYSTEM: No exact contexts found. Use general knowledge carefully."
        
    return state

# ----------------- AGENT 4: SYNTHESIS AGENT -----------------
def synthesis_node(state: AgentState):
    logger.info("Agent [Synthesizer]: Crafting final response structure")
    state["steps_taken"].append({"step": "Industrial Copilot Synthesis & Formatting", "status": "Done"})

    # Cap context to 5000 chars for richer synthesis
    context = state['fused_context'][:5000] if state['fused_context'] else ""
    mode = state.get("mode", "Private")
    
    # Mode-specific instruction
    mode_inst = ""
    if mode == "Online":
        mode_inst = "STRICT: You are in LIVE WEB mode. Use ONLY web search results. If the search yielded no results, state 'No web information found' instead of generic LLM refusal."
    elif mode == "Hybrid":
        mode_inst = "STRICT: You are in HYBRID mode. Synthesize information from both internal documents and web results. If they conflict, prioritize internal documents but mention the web alternative."
    else:
        mode_inst = "STRICT: You are in PRIVATE mode. Use ONLY the provided internal document context."

    system = (
        "You are Industrial Mind OS, an elite Industrial Knowledge Intelligence Copilot. "
        f"{mode_inst}\n\n"
        "Your goal is to provide a structured, professional, and HIGH-END response for Field Technicians and Plant Engineers.\n\n"
        "STRICT ARTIFACT RULES:\n"
        "1. FOR COMPARISONS OR PROCEDURES: You MUST use the [ARTIFACT] block for a 'Premium Designer Dashboard'. DO NOT output raw markdown tables.\n"
        "2. DESIGNER DASHBOARD (HTML): Generate professional HTML + Tailwind CSS code. Use a modern industrial/SaaS aesthetic.\n"
        "   Format: [ARTIFACT: Dashboard Name] <div class='...'> ... </div> [/ARTIFACT]\n"
        "3. FORMATTING: Structure your answer using Markdown with specific sub-sections when relevant: 'Root Cause Analysis', 'Maintenance Recommendations', or 'Compliance Checks'.\n"
        "4. CITATIONS: Use brackets [Source: Name] at the end of relevant points to prove safety and compliance.\n"
        "5. If information is missing in context, clearly state 'Information not found in the selected asset manuals'."
    )
    user = f"CONTEXT:\n{context or 'No search results or documents found.'}\n\nUSER QUERY: {state['original_query']}\n\nFINAL RESPONSE (Concise & Structured):"
    
    ans = run_llm(system, user)
    state["final_answer"] = ans
    return state


# ----------------- AGENT 5: VERIFIER AGENT (Heuristic, No LLM Call) -----------------
def verifier_node(state: AgentState):
    logger.info("Agent [Verifier]: Grading the Synthesis Output")
    state["steps_taken"].append({"step": "Safety & Compliance Validation", "status": "Done"})

    # Scoring rules live in agents/verification.py so they stay unit-testable
    score = score_answer(state.get("final_answer", ""), bool(state.get("fused_context")))

    state["confidence"] = score
    # Only retry once if score is really low and data exists
    state["retry_count"] = state.get("retry_count", 0) + 1
    logger.info(f"Heuristic confidence score: {score}")
    return state

# ----------------- CONDITIONAL EDGE -----------------
def should_loop(state: AgentState):
    """Only retry once if confidence is genuinely low (not just a no-context case)."""
    logger.info(f"Verification Score computed: {state['confidence']}")
    # Never loop more than once; never loop if answer exists with real content
    if state["confidence"] < 60.0 and state.get("retry_count", 0) < 2:
        logger.warning(f"Agentic Loop Triggered: Confidence {state['confidence']}. Retry #{state['retry_count']}")
        return "planner"
    return END

# ================= COMPILING LANGGRAPH =================
workflow = StateGraph(AgentState)

workflow.add_node("planner", planning_node)
workflow.add_node("adaptive_retrieval", adaptive_retrieval_node)
workflow.add_node("web_search", web_search_node)
workflow.add_node("memory_builder", memory_builder_node)
workflow.add_node("synthesizer", synthesis_node)
workflow.add_node("verifier", verifier_node)

# Flow: planner → retrieval → web_search → memory_builder → synthesizer → verifier
workflow.set_entry_point("planner")
workflow.add_edge("planner", "adaptive_retrieval")
workflow.add_edge("adaptive_retrieval", "web_search")
workflow.add_edge("web_search", "memory_builder")
workflow.add_edge("memory_builder", "synthesizer")
workflow.add_edge("synthesizer", "verifier")

# The Verification Branch Loop
workflow.add_conditional_edges("verifier", should_loop, {"planner": "planner", END: END})

orchestrator_target = workflow.compile()

def process_query_workflow(query: str, mode: str = "Private", files: List[str] = None,
                           owner_id: str = None):
    """Triggers the multi-agent pipeline with the chosen mode, file filter and owner scope."""
    initial_state = {
        "query": query,
        "original_query": "",
        "mode": mode,
        "vector_context": [],
        "graph_context": [],
        "memory_context": [],
        "web_context": [],
        "fused_context": "",
        "citations": [],
        "final_answer": "",
        "confidence": 0.0,
        "strategy": "",
        "steps_taken": [],
        "retry_count": 0,
        "files": files or [],
        "owner_id": owner_id,
    }
    final_output = orchestrator_target.invoke(initial_state)
    return final_output
