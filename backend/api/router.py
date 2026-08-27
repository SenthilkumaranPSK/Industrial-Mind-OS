import logging
import time
import re
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, BackgroundTasks
from typing import List
from .schemas import QueryRequest, QueryResponse, StatusResponse
from .auth import get_current_user
from storage.ingestion import ingestion_pipeline
from storage.vector_db import vector_db
from storage.memory_cache import memory_cache
from storage.graph_db import graph_db
from agents.orchestrator import process_query_workflow
from core.embeddings import LocalEmbedder
from immune.macrophage import immune_system
from core.confluence import confluence_sync

logger = logging.getLogger(__name__)
def clean_spaced_text(text: str) -> str:
    """
    Detects and fixes 'spaced-out' text (e.g. 'C o n t a i n e r i z a t i o n') 
    which is a common artifact in certain PDF extractions.
    """
    if not text:
        return text
    # Regex for character followed by exactly one space, repeated at least 5 times
    # This avoids collapsing actual words but catches the spaced-out artifacts
    pattern = r'(?:[A-Za-z]\s){5,}'
    
    def replacer(match):
        # Remove the extra spaces from the matched spaced-out block
        return match.group(0).replace(" ", "")

    cleaned = re.sub(pattern, replacer, text)
    return cleaned

api_router = APIRouter()

def process_upload_in_background(filename: str, text_content: str, user_id: int):
    try:
        nodes = ingestion_pipeline.process_document(filename, text_content)
        embedder = LocalEmbedder.get_embedder()
        texts = [n["text"] for n in nodes]
        real_vectors = embedder.embed_documents(texts)
        payloads = [
            {"text": n["text"], "file_name": filename, "user_id": user_id} 
            for n in nodes
        ]
        vector_db.upsert_vectors(real_vectors, payloads)
        # Populate graph DB with keyword relationships from this document
        ingestion_pipeline.populate_graph(filename, nodes)
        logger.info(f"Background processing complete for {filename}: {len(nodes)} chunks indexed.")
    except Exception as e:
        logger.error(f"Background upload processing failed for {filename}: {e}")

@api_router.post("/upload", response_model=StatusResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Ingests PDF, TXT, DOCX, PPTX with proper text extraction per file type.
    """
    try:
        content = await file.read()
        filename = file.filename
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"

        # --- Proper text extraction per file format ---
        text_content = ""
        if ext == "csv":
            try:
                import io, csv
                decoded = content.decode("utf-8-sig", errors="ignore")
                reader = csv.reader(io.StringIO(decoded))
                headers = next(reader, None)
                rows_text = []
                for row_idx, row in enumerate(reader):
                    row_details = []
                    for i, val in enumerate(row):
                        if val.strip():
                            header = headers[i] if headers and i < len(headers) else f"Column {i+1}"
                            row_details.append(f"{header}: {val.strip()}")
                    if row_details:
                        rows_text.append(f"[Record {row_idx+1}] " + " | ".join(row_details))
                text_content = "\n\n".join(rows_text)
                logger.info(f"Extracted {len(rows_text)} records from CSV '{filename}'")
            except Exception as e:
                logger.error(f"CSV extraction failed: {e}")
                raise HTTPException(status_code=422, detail=f"Could not read CSV file: {e}")
                
        elif ext == "pptx":
            try:
                import io
                from pptx import Presentation
                prs = Presentation(io.BytesIO(content))
                slide_texts = []
                for slide in prs.slides:
                    for shape in slide.shapes:
                        if hasattr(shape, "text") and shape.text.strip():
                            slide_texts.append(shape.text.strip())
                text_content = "\n\n".join(slide_texts)
                logger.info(f"Extracted {len(slide_texts)} text blocks from PPTX '{filename}'")
            except Exception as e:
                logger.error(f"PPTX extraction failed: {e}")
                raise HTTPException(status_code=422, detail=f"Could not read PPTX file: {e}")

        elif ext == "pdf":
            try:
                import io
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(content))
                pages = [page.extract_text() or "" for page in reader.pages]
                raw_text = "\n\n".join(p for p in pages if p.strip())
                text_content = clean_spaced_text(raw_text)
                logger.info(f"Extracted and Sanitized {len(reader.pages)} pages from PDF '{filename}'")
            except Exception as e:
                logger.error(f"PDF extraction failed: {e}")
                raise HTTPException(status_code=422, detail=f"Could not read PDF file: {e}")

        elif ext == "docx":
            try:
                import io, docx
                doc = docx.Document(io.BytesIO(content))
                text_content = "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
                logger.info(f"Extracted {len(doc.paragraphs)} paragraphs from DOCX '{filename}'")
            except Exception as e:
                logger.warning(f"DOCX extraction failed, falling back to UTF-8: {e}")
                text_content = content.decode("utf-8", errors="ignore")

        elif ext in ["png", "jpg", "jpeg"]:
            try:
                import base64
                from langchain_anthropic import ChatAnthropic
                from langchain_core.messages import HumanMessage
                import os

                api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    raise Exception("ANTHROPIC_API_KEY missing for Vision OCR.")

                base64_image = base64.b64encode(content).decode('utf-8')
                mime_type = f"image/{'jpeg' if ext == 'jpg' else ext}"

                llm = ChatAnthropic(model="claude-sonnet-5", temperature=0.0, anthropic_api_key=api_key)

                prompt = (
                    "You are an elite Industrial OCR System. "
                    "Extract all text, labels, measurements, component names, and structural data from this engineering diagram or scanned form. "
                    "Format the output as a clear, highly structured markdown document. Do not miss any numbers or technical specifications."
                )

                msg = llm.invoke([
                    HumanMessage(content=[
                        {"type": "text", "text": prompt},
                        {"type": "image", "source": {"type": "base64", "media_type": mime_type, "data": base64_image}}
                    ])
                ])

                text_content = f"--- Vision OCR Extraction for {filename} ---\n\n" + msg.content
                logger.info(f"Vision OCR completed successfully for '{filename}'")
            except Exception as e:
                logger.error(f"Image Vision extraction failed: {e}")
                raise HTTPException(status_code=422, detail=f"Could not analyze image: {e}")

        else:  # txt, md, csv, etc.
            text_content = content.decode("utf-8", errors="ignore")

        if not text_content.strip():
            raise HTTPException(status_code=422, detail="No readable text could be extracted from this file.")

        file_size = len(text_content)
        logger.info(f"Received file: {filename} (Extracted {file_size} chars) from {current_user['username']}")

        # Small file: store in memory cache directly (bypass RAG)
        if file_size < 15000:
            memory_cache.store_file(filename, text_content)
            # Create nodes for graph indexing even if bypassing vector search
            temp_nodes = [{"text": text_content, "metadata": {"file_name": filename}}]
            ingestion_pipeline.populate_graph(filename, temp_nodes)
            
            background_tasks.add_task(immune_system.scan_for_conflicts, text_content, filename)
            return StatusResponse(
                status="success",
                message=f"Document '{filename}' saved to Knowledge Graph. Macrophage scan initiated.",
                data={"chunks_created": 1, "status": "direct_injection"}
            )

        # Large file: embed in background
        background_tasks.add_task(process_upload_in_background, filename, text_content, current_user['id'])
        return StatusResponse(
            status="success",
            message=f"Document '{filename}' successfully ingested. Embedding processing running in background.",
            data={"status": "processing"}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/query", response_model=QueryResponse)
async def query_knowledge(
    request: QueryRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Handles natural language queries and triggers the Multi-Agent LangGraph workflow.
    """
    try:
        logger.info(f"Received query: {request.query} in mode: {request.mode} for user: {current_user['username']}")
        
        # Trigger Multi-Agent LangGraph Workflow directly
        start_time = time.time()
        agent_raw_result = process_query_workflow(request.query, mode=request.mode, files=request.files)
        end_time = time.time()
        
        logger.info(f"LangGraph execution completed in {round(end_time-start_time, 2)}s.")
        
        # Extract metadata from state
        citations = agent_raw_result.get("citations", [])
        sources = list(set([c["source"] for c in citations]))
        
        # Mode-aware source labeling
        if not sources:
            if request.mode == "Online":
                sources = ["No Web Results Found"]
            elif request.mode == "Hybrid":
                sources = ["No matches in Files or Web"]
            else:
                sources = ["No matches in Private Files"]
        elif request.mode == "Online":
            # Filter out any internal labels that might have leaked
            sources = [s for s in sources if "Web:" in s]
            if not sources:
                sources = ["Web (Direct Fetch)"]
            
        return QueryResponse(
            answer=agent_raw_result.get("final_answer", "No answer could be generated."),
            confidence_score=int(agent_raw_result.get("confidence", 0.0)),
            confidence_level="High" if agent_raw_result.get("confidence", 0) > 85 else "Medium",
            strategy=agent_raw_result.get("strategy", "Strict Hybrid Validation"),
            sources=sources,
            citations=[{"source": c["source"], "snippet": c["content"][:400], "url": c.get("url")} for c in agent_raw_result.get("citations", [])],
            steps=agent_raw_result.get("steps_taken", [])
        )
    except Exception as e:
        logger.error(f"Error executing query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/documents/{filename}", response_model=StatusResponse)
async def delete_document(
    filename: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Deletes a document completely from VectorDB and MemoryCache.
    """
    try:
        logger.info(f"User {current_user['username']} requested deletion of {filename}")
        
        # 1. Delete from Vector DB
        vector_db.delete_by_filename(filename)
        
        # 2. Delete from Memory Cache
        memory_cache.delete_file(filename)

        # 3. Delete from Graph DB
        graph_db.delete_by_filename(filename)
        
        return StatusResponse(
            status="success",
            message=f"Document '{filename}' successfully deleted from databases.",
            data={"deleted_file": filename}
        )
    except Exception as e:
        logger.error(f"Error deleting file {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/alerts")
async def get_alerts(current_user: dict = Depends(get_current_user)):
    """Exposes current proactive alerts and patterns to the frontend"""
    alerts = immune_system.alerts
    return {
        "status": "alert" if len(alerts) > 0 else "secure",
        "active_threats": len(alerts),
        "reports": alerts
    }

@api_router.delete("/alerts/{alert_id}")
async def dismiss_alert(alert_id: str, current_user: dict = Depends(get_current_user)):
    """Dismiss a specific alert"""
    immune_system.alerts = [a for a in immune_system.alerts if a["id"] != alert_id]
    return {"status": "success"}

@api_router.get("/documents")
async def list_documents(current_user: dict = Depends(get_current_user)):
    """
    Returns a combined list of all indexed filenames from MemoryCache + VectorDB.
    Used by the frontend to restore the file list after login.
    """
    try:
        # Files in memory cache (small files)
        memory_files = list(memory_cache.cache.keys())

        # Files in vector DB (large files)
        vector_files = []
        if vector_db.client:
            try:
                results = vector_db.client.scroll(
                    collection_name=vector_db.collection_name,
                    limit=500,
                    with_payload=True,
                    with_vectors=False,
                )
                points = results[0] if results else []
                seen = set()
                for pt in points:
                    fname = pt.payload.get("file_name")
                    if fname and fname not in seen:
                        seen.add(fname)
                        vector_files.append(fname)
            except Exception as e:
                logger.warning(f"Could not scroll vector DB for file list: {e}")

        # Combine and deduplicate, preserving order
        all_files = list(dict.fromkeys(memory_files + vector_files))
        return {"files": all_files}
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/graph/data")
async def get_graph_data(current_user: dict = Depends(get_current_user)):
    """Exports full graph data for the 2D visualizer"""
    return graph_db.get_graph_data()

@api_router.get("/suggestions")
async def get_dynamic_suggestions(current_user: dict = Depends(get_current_user)):
    """Fetches random graph entities and dynamically templates them into suggested questions"""
    entities = graph_db.get_random_entities(5)
    
    if not entities:
        return {"suggestions": [
            "What documents are currently uploaded?",
            "Can you summarize the main concepts?",
            "What security policies are available?"
        ]}
        
    import random
    templates = [
        "Explain the significance of '{0}' in the documents.",
        "What are the main findings regarding '{0}'?",
        "Can you summarize the context around '{0}'?",
        "How is '{0}' related to other concepts?"
    ]
    
    suggestions = [tmpl.format(entity) for entity, tmpl in zip(entities, [random.choice(templates) for _ in entities])]
    return {"suggestions": suggestions}

@api_router.post("/confluence/sync", response_model=StatusResponse)
async def sync_confluence(
    request: dict, 
    current_user: dict = Depends(get_current_user)
):
    domain = request.get("domain")
    space_key = request.get("spaceKey")
    email = request.get("email")
    api_token = request.get("apiToken")
    
    if not all([domain, space_key, email, api_token]):
        raise HTTPException(status_code=400, detail="Missing Confluence configuration fields")
    
    # Run sync (this might take a minute depending on space size, client handles timeout or we run it async)
    result = await confluence_sync.sync_space(domain, space_key, email, api_token, current_user['id'])
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    
    return StatusResponse(status="success", message=f"Ingested {result['title']} ({result.get('pages', 0)} pages synced)")

@api_router.get("/graph/stats")
async def get_graph_stats(current_user: dict = Depends(get_current_user)):
    """Debug endpoint to inspect the knowledge graph DB state."""
    nodes = list(graph_db.graph.nodes())
    edges = list(graph_db.graph.edges(data=True))
    sample_nodes = nodes[:20] if nodes else []
    sample_edges = [{"from": u, "to": v, "rel": d.get("relation", "?")} for u, v, d in edges[:20]]
    return {
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "sample_nodes": sample_nodes,
        "sample_edges": sample_edges,
        "memory_cache_files": list(memory_cache.cache.keys()),
        "memory_cache_total_chars": sum(len(v) for v in memory_cache.cache.values()),
    }
