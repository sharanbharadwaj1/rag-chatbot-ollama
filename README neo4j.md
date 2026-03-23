**Practical Mapping to Your Project**

#current RAG:

Document → Chunk → Embedding → Retrieval

#With KG:

Document
   ↓
[1] Chunking + Embeddings → Vector DB
[2] Entity + Relation Extraction → Knowledge Graph (Neo4j)

Query
   ↓
Entity Extraction (from query)
   ↓
Graph Query (Cypher)
   ↓
Vector Retrieval (semantic search)
   ↓
Context Fusion (Graph + Text)
   ↓
LLM → Final Answer