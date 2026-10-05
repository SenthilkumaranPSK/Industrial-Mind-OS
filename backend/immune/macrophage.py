import json
import logging
import os
import time
from typing import List, Dict, Optional

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate

from storage.memory_cache import memory_cache

load_dotenv()
logger = logging.getLogger(__name__)

ALERTS_FILE = os.path.join(os.path.dirname(__file__), "..", "alerts.json")

# The auditor prompt is expensive; bound what we feed it so a large knowledge
# base can't blow past the model's context window or run up a huge bill.
MAX_EXISTING_KNOWLEDGE_CHARS = 20000
MAX_NEW_DOC_CHARS = 8000


class ImmunitySystem:
    """
    Industrial Mind OS Immune System.
    Runs asynchronously in the background mapping newly ingested files against
    the global memory structure to identify intellectual contradictions.

    Alerts are the product of an LLM call, so they persist to disk rather than
    evaporating on restart.
    """
    def __init__(self):
        self.alerts: List[Dict] = []
        self._load()

    def _load(self):
        if not os.path.exists(ALERTS_FILE):
            return
        try:
            with open(ALERTS_FILE, "r", encoding="utf-8") as f:
                self.alerts = json.load(f)
            logger.info(f"ImmunitySystem: Restored {len(self.alerts)} alert(s) from disk.")
        except Exception as e:
            logger.warning(f"Could not load alerts from disk: {e}")

    def _save(self):
        try:
            with open(ALERTS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.alerts, f, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Could not save alerts to disk: {e}")

    def list_alerts(self, owner_id: Optional[str] = None) -> List[Dict]:
        """Alerts raised on this user's documents (plus legacy un-owned ones)."""
        return [
            a for a in self.alerts
            if a.get("owner_id") is None or owner_id is None or str(a.get("owner_id")) == str(owner_id)
        ]

    def dismiss(self, alert_id: str, owner_id: Optional[str] = None) -> bool:
        """Removes an alert this user can see. Returns whether anything was removed."""
        visible_ids = {a["id"] for a in self.list_alerts(owner_id)}
        if alert_id not in visible_ids:
            return False
        self.alerts = [a for a in self.alerts if a["id"] != alert_id]
        self._save()
        return True

    def scan_for_conflicts(self, new_text: str, filename: str, owner_id: Optional[str] = None):
        logger.info(f"🦠 Immune System [Auditor Agent]: Activating scan on {filename}...")

        ctx = memory_cache.get_context(owner_id=owner_id)
        # Don't compare a document against itself.
        ctx = [c for c in ctx if c["source"] != filename]
        existing_knowledge = "\n\n".join([f"Source: {c['source']}\n{c['content']}" for c in ctx])
        existing_knowledge = existing_knowledge[:MAX_EXISTING_KNOWLEDGE_CHARS]

        # We don't scan if there is nothing to compare against
        if not existing_knowledge.strip():
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

        user_prompt = (
            f"EXISTING KNOWLEDGE:\n{existing_knowledge}\n\n"
            f"NEW DOCUMENT:\n{new_text[:MAX_NEW_DOC_CHARS]}"
        )

        try:
            api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            if not api_key or api_key.startswith("paste-") or api_key.startswith("your-"):
                logger.warning("Macrophage: Valid GOOGLE_API_KEY not configured. Skipping proactive audit.")
                return {"status": "skipped"}

            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0.0, google_api_key=api_key)
            prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", user_prompt)])

            chain = prompt | llm
            report = chain.invoke({}).content

            if "SAFE" in report or "safe" in report.lower():
                logger.info("✅ Auditor: System Secure. No gaps or patterns found.")
                return {"status": "secure"}

            logger.warning(f"⚠️ PROACTIVE ALERT DETECTED! {report}")
            alert_type = "conflict"
            if "COMPLIANCE" in report:
                alert_type = "compliance"
            elif "PATTERN" in report:
                alert_type = "pattern"

            alert_obj = {
                "id": str(int(time.time() * 1000)),
                "type": alert_type,
                "message": report.replace("COMPLIANCE GAP:", "").replace("HISTORICAL PATTERN:", "").replace("CONTRADICTION:", "").strip(),
                "source": filename,
                "owner_id": str(owner_id) if owner_id else None,
            }

            # Deduplicate similar alerts for same file & owner
            if not any(a["message"] == alert_obj["message"] and a.get("owner_id") == alert_obj["owner_id"] and a.get("source") == alert_obj["source"] for a in self.alerts):
                self.alerts.append(alert_obj)
                self._save()

            return {"status": "alert", "report": report}

        except Exception as e:
            logger.error(f"Macrophage biological failure: {e}")
            return {"status": "error"}


immune_system = ImmunitySystem()
