import os
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from langchain_huggingface import HuggingFaceEmbeddings

class VectorDatabaseAdapter:
    def __init__(self):
        # Defaulting to an in-memory or local Qdrant instance for ease of use
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        self.client = AsyncQdrantClient(url=qdrant_url)
        self.collection_name = "k8s_logs"
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self._initialized = False

    async def initialize(self):
        if self._initialized:
            return
        
        collections = await self.client.get_collections()
        exists = any(c.name == self.collection_name for c in collections.collections)
        if not exists:
            # all-MiniLM-L6-v2 has 384 dimensions
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )
        self._initialized = True

    async def embed_and_store_log(self, log_id: str, pod_name: str, log_text: str):
        """Embeds a log message and stores it with context payload."""
        await self.initialize()
        vector = await self.embeddings.aembed_query(log_text)
        
        point = PointStruct(
            id=log_id,
            vector=vector,
            payload={"pod": pod_name, "text": log_text}
        )
        await self.client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )

    async def search_similar_logs(self, query_text: str, limit: int = 5):
        """Searches for similar log signatures to detect repeating errors."""
        await self.initialize()
        vector = await self.embeddings.aembed_query(query_text)
        
        results = await self.client.search(
            collection_name=self.collection_name,
            query_vector=vector,
            limit=limit
        )
        return [{"pod": r.payload["pod"], "text": r.payload["text"], "score": r.score} for r in results]

vector_db = VectorDatabaseAdapter()
