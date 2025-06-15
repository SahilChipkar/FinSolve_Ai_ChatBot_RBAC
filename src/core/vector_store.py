import chromadb
import os
import sys

# Define the path where ChromaDB will store its persistent data
# This path should ideally be relative to your project root or an absolute path
CHROMA_DB_PATH = os.path.join(os.getcwd(), "chroma_db") # Stores in project_root/chroma_db

class ChromaVectorStore:
    def __init__(self, collection_name: str = "finsolve_organizational_data"):
        """
        Initializes the ChromaDB client and gets/creates a collection.

        Args:
            collection_name (str): The name of the ChromaDB collection to use.
        """
        try:
            # Initialize a persistent ChromaDB client
            # This will create/load the database at CHROMA_DB_PATH
            self.client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
            
            # Get or create the collection
            self.collection = self.client.get_or_create_collection(name=collection_name)
            print(f"ChromaDB initialized. Collection '{collection_name}' ready at {CHROMA_DB_PATH}")
        except Exception as e:
            print(f"Error initializing ChromaDB: {e}")
            self.client = None
            self.collection = None

    async def add_documents(self, documents: list[str], metadatas: list[dict], embeddings: list[list[float]], ids: list[str]):
        """
        Adds documents, their metadata, and embeddings to the ChromaDB collection.

        Args:
            documents (list[str]): A list of text content strings.
            metadatas (list[dict]): A list of dictionaries containing metadata for each document.
            embeddings (list[list[float]]): A list of vector embeddings for each document.
            ids (list[str]): A list of unique IDs for each document.
        """
        if not self.collection:
            print("ChromaDB collection not initialized. Cannot add documents.")
            return

        try:
            # Ensure consistency in list lengths
            if not (len(documents) == len(metadatas) == len(embeddings) == len(ids)):
                raise ValueError("All input lists (documents, metadatas, embeddings, ids) must have the same length.")

            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings,
                ids=ids
            )
            print(f"Successfully added {len(documents)} documents to ChromaDB.")
        except Exception as e:
            print(f"Error adding documents to ChromaDB: {e}")

    async def query_documents(self, query_embedding: list[float], n_results: int = 5, where_clause: dict = None) -> dict:
        """
        Queries the ChromaDB collection for similar documents, with optional metadata filtering.

        Args:
            query_embedding (list[float]): The embedding of the user's query.
            n_results (int): The number of top results to retrieve.
            where_clause (dict): An optional dictionary for metadata filtering.
                                 e.g., {"department": "Finance"} or {"$and": [{"department": "HR"}, {"access_level": "Restricted"}]}

        Returns:
            dict: The query results from ChromaDB, containing documents, metadatas, etc.
        """
        if not self.collection:
            print("ChromaDB collection not initialized. Cannot query documents.")
            return {"documents": [], "metadatas": [], "ids": []}

        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_clause, # Apply the RBAC filter here
                include=['documents', 'metadatas', 'distances'] # Include what you need
            )
            return results
        except Exception as e:
            print(f"Error querying ChromaDB: {e}")
            return {"documents": [], "metadatas": [], "ids": []}

    async def count_documents(self) -> int:
        """
        Returns the number of documents in the collection.
        """
        if not self.collection:
            return 0
        return self.collection.count()

    async def clear_collection(self):
        """
        Clears all documents from the collection. Use with caution!
        """
        if self.collection:
            try:
                self.client.delete_collection(name=self.collection.name)
                # Re-create the collection after deletion
                self.collection = self.client.get_or_create_collection(name=self.collection.name)
                print(f"Collection '{self.collection.name}' cleared and re-created.")
            except Exception as e:
                print(f"Error clearing collection: {e}")

# Example usage (for testing purposes)
if __name__ == "__main__":
    import asyncio
    
    # Add the project root to sys.path to resolve 'src' imports when running directly
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from src.core.embedding import get_ollama_embedding # Now this import should work

    async def test_vector_store():
        print("--- Testing ChromaVectorStore ---")
        
        # 1. Initialize store
        vector_store = ChromaVectorStore()

        # 2. Clear existing data for a clean test (optional, but good for testing ingestion)
        await vector_store.clear_collection()
        await asyncio.sleep(1) # Give a moment for collection to be ready

        # 3. Prepare some dummy data
        test_docs = [
            "Financial report for Q1 2024 showing revenue trends.",
            "HR policy on vacation leave and sick days for employees.",
            "Engineering documentation on microservices architecture.",
            "Marketing campaign performance for digital ads in Q3 2024."
        ]
        test_metadatas = [
            {"department": "Finance", "year": "2024", "quarter": "Q1"},
            {"department": "HR", "document_type": "Policy"},
            {"department": "Engineering", "document_type": "Documentation"},
            {"department": "Marketing", "year": "2024", "quarter": "Q3"}
        ]
        test_ids = [f"doc_{i}" for i in range(len(test_docs))]

        test_embeddings = []
        for doc in test_docs:
            embedding = await get_ollama_embedding(doc)
            if embedding:
                test_embeddings.append(embedding)
            else:
                print(f"Could not get embedding for: {doc}")
                return

        # 4. Add documents
        if test_embeddings:
            await vector_store.add_documents(test_docs, test_metadatas, test_embeddings, test_ids)
            await asyncio.sleep(1) # Give a moment for documents to be added
            count = await vector_store.count_documents()
            print(f"Documents in store after addition: {count}")

            # 5. Test querying with RBAC filters
            print("\n--- Querying with Filters ---")

            # Finance query (should retrieve only Finance doc)
            finance_query = "What were the financial results for the first quarter?"
            finance_query_embedding = await get_ollama_embedding(finance_query)
            if finance_query_embedding:
                finance_filter = {"department": "Finance"}
                finance_results = await vector_store.query_documents(
                    finance_query_embedding,
                    where_clause=finance_filter
                )
                print("\nFinance Query Results (filtered by department: Finance):")
                if finance_results and finance_results['documents'] and finance_results['documents'][0]:
                    for doc, meta in zip(finance_results['documents'][0], finance_results['metadatas'][0]):
                        print(f"  Doc: '{doc[:50]}...' Meta: {meta}")
                else:
                    print("  No results found for finance query with filter.")
            else:
                print("Failed to get embedding for finance query.")

            # HR query (should retrieve only HR doc)
            hr_query = "Tell me about employee vacation policies."
            hr_query_embedding = await get_ollama_embedding(hr_query)
            if hr_query_embedding:
                hr_filter = {"department": "HR"}
                hr_results = await vector_store.query_documents(
                    hr_query_embedding,
                    where_clause=hr_filter
                )
                print("\nHR Query Results (filtered by department: HR):")
                if hr_results and hr_results['documents'] and hr_results['documents'][0]:
                    for doc, meta in zip(hr_results['documents'][0], hr_results['metadatas'][0]):
                        print(f"  Doc: '{doc[:50]}...' Meta: {meta}")
                else:
                    print("  No results found for HR query with filter.")
            else:
                print("Failed to get embedding for HR query.")

            # General query without specific department filter (might return anything)
            general_query = "What is the company's internal structure?"
            general_query_embedding = await get_ollama_embedding(general_query)
            if general_query_embedding:
                general_results = await vector_store.query_documents(
                    general_query_embedding
                )
                print("\nGeneral Query Results (no department filter):")
                if general_results and general_results['documents'] and general_results['documents'][0]:
                    for doc, meta in zip(general_results['documents'][0], general_results['metadatas'][0]):
                        print(f"  Doc: '{doc[:50]}...' Meta: {meta}")
                else:
                    print("  No results found for general query.")
            else:
                print("Failed to get embedding for general query.")

            # Test a query for a department that doesn't exist in dummy data with filter
            non_existent_query = "What about the legal department's guidelines?"
            non_existent_query_embedding = await get_ollama_embedding(non_existent_query)
            if non_existent_query_embedding:
                non_existent_filter = {"department": "Legal"}
                non_existent_results = await vector_store.query_documents(
                    non_existent_query_embedding,
                    where_clause=non_existent_filter
                )
                print("\nNon-Existent Department Query Results (filtered by department: Legal):")
                if non_existent_results and non_existent_results['documents'] and non_existent_results['documents'][0]:
                    for doc, meta in zip(non_existent_results['documents'][0], non_existent_results['metadatas'][0]):
                        print(f"  Doc: '{doc[:50]}...' Meta: {meta}")
                else:
                    print("  As expected, no results found for non-existent department query with filter.")
            else:
                print("Failed to get embedding for non-existent query.")


        else:
            print("No embeddings to add. Skipping document addition and query tests.")

    asyncio.run(test_vector_store())
