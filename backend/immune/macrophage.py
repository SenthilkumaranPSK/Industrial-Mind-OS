import logging
import os
from dotenv import load_dotenv
from typing import List, Dict
from storage.memory_cache import memory_cache
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()
logger = logging.getLogger(__name__)

class ImmunitySystem:
    """
    Industrial Mind OS Immune System.
    Runs asynchronously in the background mapping newly ingested files against
    the global memory structure to identify intellectual contradictions.
    """
    def __init__(self):
        self.alerts: List[Dict] = []
        
    def scan_for_conflicts(self, new_text: str, filename: str):
        logger.info(f"🦠 Immune System [Auditor Agent]: Activating scan on {filename}...")
        
        ctx = memory_cache.get_context()
        existing_knowledge = "\n\n".join([f"Source: {c['source']}\n{c['content']}" for c in ctx])
        
        # We don't scan if there is nothing to compare against
        if not existing_knowledge or existing_knowledge.strip() == "":
            logger.info("Macrophage: Clean system. No prior knowledge to cross-reference.")
            return {"status": "safe", "alerts": []}
            
        system_prompt = (
            "You are the Industrial Mind OS Proactive Auditor Agent. "
            "Your ONLY job is to blindly compare the NEW DOCUMENT against the EXISTING KNOWLEDGE. "
            "Look for three specific things:\n"
            "1. CONTRADICTION: Does the new document explicitly contradict existing limits or facts?\n"
            "2. COMPLIANCE GAP: Does the new document show an operational state that violates a regulation in the existing knowledge?\n"
            "3. HISTORICAL PATTERN: Does the new document describe a situation that matches a past incident or failure in the existing knowledge?\n\n"
            "If you find ANY of these, output a concise 1-sentence warning starting with the exact type:\n"
            "e.g., 'COMPLIANCE GAP: The valve pressure of 120psi exceeds the OISD-118 limit of 100psi.'\n"
            "e.g., 'HISTORICAL PATTERN: The vibration of 6.2mm/s matches the conditions that caused the 2023 seal failure.'\n"
            "If everything is safe and unrelated, output EXACTLY the word 'SAFE'."
        )
        
        user_prompt = f"EXISTING KNOWLEDGE:\n{existing_knowledge}\n\nNEW DOCUMENT:\n{new_text[:4000]}"
        
        try:
            import os
            import time
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                logger.error("Macrophage: GOOGLE_API_KEY missing.")
                return {"status": "error"}

            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0.0, google_api_key=api_key)
            prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", user_prompt)])
            
            chain = prompt | llm
            report = chain.invoke({}).content
            
            if "SAFE" in report or "safe" in report.lower():
                logger.info("✅ Auditor: System Secure. No gaps or patterns found.")
                return {"status": "secure"}
            else:
                logger.warning(f"⚠️ PROACTIVE ALERT DETECTED! {report}")
                alert_type = "conflict"
                if "COMPLIANCE" in report: alert_type = "compliance"
                elif "PATTERN" in report: alert_type = "pattern"
                
                alert_obj = {
                    "id": str(int(time.time() * 1000)),
                    "type": alert_type,
                    "message": report.replace("COMPLIANCE GAP:", "").replace("HISTORICAL PATTERN:", "").replace("CONTRADICTION:", "").strip(),
                    "source": filename
                }
                
                # Deduplicate similar alerts
                if not any(a["message"] == alert_obj["message"] for a in self.alerts):
                    self.alerts.append(alert_obj)
                    
                return {"status": "alert", "report": report}
                
        except Exception as e:
            logger.error(f"Macrophage biological failure: {str(e)[:50]}")
            return {"status": "error"}

immune_system = ImmunitySystem()
