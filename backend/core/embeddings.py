import logging
try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    HuggingFaceEmbeddings = None

logger = logging.getLogger(__name__)

class LocalEmbedder:
    _instance = None
    
    @classmethod
    def get_embedder(cls):
        if cls._instance is None:
            if HuggingFaceEmbeddings is None:
                raise ImportError("langchain-huggingface is not completely installed!")
                
            logger.info("Initializing HuggingFace all-MiniLM-L6-v2 local embeddings model. This may take a minute to download on first run...")
            # We use an extremely fast and powerful local model that natively runs on CPUs
            cls._instance = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        return cls._instance
