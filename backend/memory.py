import chromadb
import os
import uuid

class MemoryCore:
    def __init__(self, persist_path=".brain/memory.db"):
        # Ensure the directory exists
        path = os.path.abspath(persist_path)
        os.makedirs(path, exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=path)

    def add_memory(self, collection_name: str, document: str, metadata: dict = None):
        """Adds a text chunk to a specific collection."""
        try:
            collection = self.client.get_or_create_collection(name=collection_name)
            collection.add(
                documents=[document],
                metadatas=[metadata or {}],
                ids=[str(uuid.uuid4())]
            )
            print(f"[MemoryCore] Added memory to '{collection_name}'")
        except Exception as e:
            print(f"[MemoryCore] Error adding memory: {e}")

    def query_memory(self, collection_name: str, query_text: str, n_results: int = 3):
        """Retrieves relevant memory chunks."""
        try:
            collection = self.client.get_or_create_collection(name=collection_name)
            if collection.count() == 0:
                return {"documents": [[]], "metadatas": [[]]}
            
            results = collection.query(
                query_texts=[query_text],
                n_results=n_results
            )
            return results
        except Exception as e:
            print(f"[MemoryCore] Error querying memory: {e}")
            return {"documents": [[]], "metadatas": [[]], "error": str(e)}
