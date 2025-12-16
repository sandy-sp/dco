import chromadb
import os
import uuid

class MemoryCore:
    def __init__(self, persist_path=".brain/memory.db"):
        self.persist_path = persist_path
        self.client = None
        self._init_client(persist_path)

    def _init_client(self, path):
        """Initializes or re-initializes the ChromaDB client."""
        try:
            abs_path = os.path.abspath(path)
            os.makedirs(abs_path, exist_ok=True)
            self.client = chromadb.PersistentClient(path=abs_path)
            print(f"[MemoryCore] Database loaded at {abs_path}")
        except Exception as e:
            print(f"[MemoryCore] Failed to load DB at {path}: {e}")

    def set_project_path(self, project_path: str):
        """Updates the DB location to be inside the project folder."""
        new_db_path = os.path.join(project_path, ".brain/memory.db")
        if new_db_path != self.persist_path:
            self.persist_path = new_db_path
            self._init_client(new_db_path)

    def add_memory(self, collection_name: str, document: str, metadata: dict = None):
        try:
            collection = self.client.get_or_create_collection(name=collection_name)
            collection.add(
                documents=[document],
                metadatas=[metadata or {}],
                ids=[str(uuid.uuid4())]
            )
        except Exception as e:
            print(f"[MemoryCore] Error adding memory: {e}")

    def query_memory(self, collection_name: str, query_text: str, n_results: int = 3):
        try:
            collection = self.client.get_or_create_collection(name=collection_name)
            if collection.count() == 0:
                return {"documents": [[]], "metadatas": [[]]}
            return collection.query(query_texts=[query_text], n_results=n_results)
        except Exception as e:
            print(f"[MemoryCore] Error querying memory: {e}")
            return {"documents": [[]], "metadatas": [[]]}