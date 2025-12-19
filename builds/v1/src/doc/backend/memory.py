import chromadb
import os
import datetime
import uuid

class MemoryCore:
    def __init__(self, persist_path=".brain/memory.db"):
        self.persist_path = persist_path
        self.client = None
        self._init_client(persist_path)
        self.project_path = os.path.dirname(os.path.dirname(os.path.abspath(persist_path))) # Initialize project_path

    def _init_client(self, path):
        """Initializes or re-initializes the ChromaDB client."""
        try:
            abs_path = os.path.abspath(path)
            os.makedirs(abs_path, exist_ok=True)
            self.client = chromadb.PersistentClient(path=abs_path)
            print(f"[MemoryCore] Database loaded at {abs_path}")
        except Exception as e:
            print(f"[MemoryCore] Failed to load DB at {path}: {e}")

    def archive_huddle(self, content: str):
        """Archives the current Huddle content to a timestamped file."""
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_dir = os.path.join(self.project_path, ".brain/logs")
        os.makedirs(archive_dir, exist_ok=True)
        
        filename = f"archive_{timestamp}.md"
        path = os.path.join(archive_dir, filename)
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        
        print(f"[MemoryCore] Huddle archived to {path}")
        return path

    def set_project_path(self, project_path: str):
        """Updates the DB location to be inside the project folder."""
        self.project_path = project_path # Update project_path
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

    # --- HUDDLE / CHAT LOGIC ---

    def log_interaction(self, agent: str, message: str, type: str = "info"):
        """Logs a chat interaction to the huddle_log collection."""
        try:
            collection = self.client.get_or_create_collection(name="huddle_log")
            timestamp = datetime.datetime.now().isoformat()
            
            # Use monotonic time or a sortable string for simple sorting if purely chronologial retrieval is needed
            # For simplicity, we trust insertion order or sort by timestamp metadata later.
            # Adding a strictly increasing ID can help sorting.
            unique_id = f"{datetime.datetime.now().timestamp()}-{uuid.uuid4()}"

            collection.add(
                documents=[message],
                metadatas=[{"agent": agent, "type": type, "timestamp": timestamp}],
                ids=[unique_id]
            )
        except Exception as e:
            print(f"[MemoryCore] Error logging interaction: {e}")

    def get_recent_huddle(self, limit: int = 20) -> str:
        """Retrieves and formats the recent chat history."""
        try:
            collection = self.client.get_or_create_collection(name="huddle_log")
            count = collection.count()
            if count == 0:
                return "*Huddle is empty*"

            # Chroma doesn't strictly support "last N" easily without logic.
            # Using .get() with limit might return random or first items depending on implementation details of Chroma.
            # Best practice with Chroma for *logs* is typically embedding-search, but here we want *chronological*.
            # Chroma 0.4+ supports .get(). sorting might have to happen in app layer.
            results = collection.get(limit=limit, include=["metadatas", "documents"]) # This might not be ordered.
            
            # Since Chroma doesn't guarantee order on .get(), we sort by ID or timestamp metadata.
            # We fetch more than limit if we want to sort and assume we want the *latest*.
            # Actually, `get` returns first N inserted often. To get *last* N, we might need all and slice, or rely on ID structure.
            # For robustness in this CLI tool, let's fetch a larger chunk and sort.
            
            # Optimization: If count is huge, this is slow. But for a CLI tool session, it's fine.
            # Fetch all for now to ensure correctness, assuming session isn't massive yet.
            results = collection.get(include=["metadatas", "documents"])
            
            zipped = list(zip(results["ids"], results["documents"], results["metadatas"]))
            # Sort by ID (which starts with timestamp) ensures valid order
            zipped.sort(key=lambda x: x[0]) 
            
            # Take last 'limit'
            recent = zipped[-limit:]
            
            formatted_lines = []
            for _, doc, meta in recent:
                agent = meta.get("agent", "Unknown")
                formatted_lines.append(f"**{agent}**: {doc}")
                
            return "\n\n".join(formatted_lines)

        except Exception as e:
            return f"*Error reading Huddle: {e}*"

    def get_latest_status(self) -> str:
        """Checks the most recent message to see mission status."""
        try:
            collection = self.client.get_or_create_collection(name="huddle_log")
            if collection.count() == 0:
                return "IDLE"

            # Get last one
            results = collection.get(include=["documents"])
            # Again, assuming we need to sort to find the *true* last one
            # If performance matters, we optimize this.
            ids = results["ids"]
            docs = results["documents"]
            if not ids:
                return "IDLE"
                
            # Zip and get doc with max ID
            last_doc = sorted(zip(ids, docs), key=lambda x: x[0])[-1][1]
            return last_doc
        except:
            return "IDLE"

    def clear_huddle(self):
        """Wipes the huddle log."""
        try:
            self.client.delete_collection("huddle_log")
            print("[MemoryCore] Huddle cleared.")
        except Exception as e:
            print(f"[MemoryCore] Error clearing huddle: {e}")