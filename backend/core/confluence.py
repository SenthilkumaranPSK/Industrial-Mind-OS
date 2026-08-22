import logging
import httpx
import asyncio
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from typing import Dict

from storage.vector_db import vector_db
from storage.graph_db import graph_db
from storage.memory_cache import memory_cache
from storage.ingestion import ingestion_pipeline

logger = logging.getLogger(__name__)

class ConfluenceSync:
    async def sync_space(self, domain: str, space_key: str, email: str, api_token: str, user_id: str) -> Dict:
        logger.info(f"🔗 ConfluenceSync: Starting Space Sync for {domain} (Space: {space_key})")
        
        try:
            # Format the base domain properly (strip https:// if user provided it)
            domain = domain.replace("https://", "").replace("http://", "").rstrip("/")
            base_url = f"https://{domain}/wiki/rest/api/content"
            
            auth = (email, api_token)
            
            headers = {
                "Accept": "application/json"
            }
            
            total_pages = 0
            start = 0
            limit = 50
            is_last = False
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                while not is_last:
                    logger.info(f"Fetching Confluence pages {start} to {start + limit}...")
                    params = {
                        "spaceKey": space_key,
                        "type": "page",
                        "expand": "body.export_view",
                        "limit": limit,
                        "start": start
                    }
                    
                    response = await client.get(base_url, auth=auth, headers=headers, params=params)
                    
                    if response.status_code != 200:
                        raise Exception(f"Confluence API Error ({response.status_code}): {response.text}")
                        
                    data = response.json()
                    results = data.get("results", [])
                    
                    if not results:
                        break
                        
                    for page in results:
                        title = page.get("title", "Untitled Page")
                        logger.info(f"Processing page: {title}")
                        
                        # 1. HTML Cleaning using BS4
                        html_content = page.get("body", {}).get("export_view", {}).get("value", "")
                        if not html_content:
                            continue
                            
                        soup = BeautifulSoup(html_content, 'html.parser')
                        
                        # Remove specific nasty macros if they slip through
                        for macro in soup.find_all(class_="confluence-information-macro"):
                            macro.unwrap()
                            
                        # 2. Convert to elegant Markdown
                        markdown_text = md(str(soup), heading_style="ATX", bypass_tables=False)
                        
                        filename = f"Confluence: {title}"
                        
                        # 3. Route to proper Ingestion Pipeline
                        nodes = ingestion_pipeline.process_document(filename, markdown_text)
                        
                        # Embed into Vector and Graph
                        from core.embeddings import LocalEmbedder
                        embedder = LocalEmbedder.get_embedder()
                        
                        chunk_vectors = []
                        chunk_payloads = []
                        
                        for node in nodes:
                            vector = embedder.embed_query(node["text"])
                            chunk_vectors.append(vector)
                            chunk_payloads.append({
                                "file_name": filename, 
                                "source": f"https://{domain}/wiki/spaces/{space_key}", 
                                "chunk_index": node.get("metadata", {}).get("chunk_index", 0), 
                                "user_id": user_id,
                                "text": node["text"]
                            })
                            
                        if chunk_vectors:
                            vector_db.upsert_vectors(chunk_vectors, chunk_payloads)
                        
                        # Populate Graph DB using our advanced multi-hop linking
                        ingestion_pipeline.populate_graph(filename, nodes)
                        
                        # Store in fast memory cache for direct retrieval
                        memory_cache.store_file(filename, markdown_text[:5000])
                        
                        total_pages += 1
                        
                    # Check pagination
                    if len(results) < limit:
                        is_last = True
                    else:
                        start += limit
                        
            logger.info(f"✅ ConfluenceSync: Successfully ingested Space '{space_key}' ({total_pages} pages)")
            return {"status": "success", "title": f"Space: {space_key}", "pages": total_pages}
            
        except Exception as e:
            logger.error(f"❌ ConfluenceSync error: {str(e)}")
            return {"status": "error", "message": str(e)}

confluence_sync = ConfluenceSync()
