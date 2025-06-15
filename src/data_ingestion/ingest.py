# src/data_ingestion/ingest.py

import os
import sys
import asyncio
import logging
from typing import List, Dict, Any

# Add the project root to sys.path to resolve 'src' imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.data_ingestion.document_loaders import DocumentLoader
from src.data_ingestion.text_splitter import TextSplitter
from src.core.embedding import get_ollama_embedding
from src.core.vector_store import ChromaVectorStore

# --- Logging Configuration (for this module) ---
logger = logging.getLogger(__name__) # Get logger instance configured in main.py or globally

# Define the path to your raw organizational data
DATA_DIR = os.path.join(project_root, "data")
# Define the collection name for ChromaDB
COLLECTION_NAME = "finsolve_organizational_data"

async def ingest_data_into_chromadb():
    """
    Processes raw organizational documents, chunks them, generates embeddings,
    and loads them into ChromaDB with appropriate metadata for RBAC.
    """
    logger.info(f"--- Starting data ingestion into ChromaDB collection '{COLLECTION_NAME}' ---")
    logger.info(f"Source data directory: {DATA_DIR}")

    vector_store = ChromaVectorStore(collection_name=COLLECTION_NAME)
    
    if not vector_store.collection:
        logger.error("ChromaDB initialization failed. Exiting ingestion.")
        return

    # Clear existing data in the collection for a fresh start
    logger.info(f"Clearing existing data from collection '{COLLECTION_NAME}'...")
    await vector_store.clear_collection()
    await asyncio.sleep(1) # Small delay to ensure collection is ready after clearing

    documents_to_add: List[str] = []
    metadatas_to_add: List[Dict[str, Any]] = []
    embeddings_to_add: List[List[float]] = []
    ids_to_add: List[str] = []

    total_chunks_processed = 0

    # Walk through the data directory to find all files
    for root, _, files in os.walk(DATA_DIR):
        # Extract the department name from the folder structure
        relative_path = os.path.relpath(root, DATA_DIR)
        # Use the first part of the relative path as department, or 'general' if root is DATA_DIR itself
        department = relative_path.split(os.sep)[0] if relative_path != "." else "general" 
        
        # Ensure department name is lowercase for consistent metadata filtering with RBAC
        department = department.lower() 

        for file_name in files:
            file_path = os.path.join(root, file_name)
            logger.info(f"Processing file: {file_path} (Department: {department})")

            # Load document content
            content, file_extension = DocumentLoader.load_document(file_path)
            if content is None:
                logger.warning(f"Skipping file {file_name} due to content loading error or unsupported type.")
                continue

            # Determine splitter type based on file extension
            splitter_type = "markdown" if file_extension == ".md" else "recursive"
            # Chunk the document content
            chunks = TextSplitter.split_text(
                content,
                chunk_size=1000, # Adjust chunk size as needed
                chunk_overlap=200, # Adjust overlap as needed
                splitter_type=splitter_type
            )
            
            if not chunks:
                logger.warning(f"No chunks generated for {file_name}. Skipping.")
                continue

            # Generate embeddings and prepare for addition to ChromaDB
            for i, chunk_text in enumerate(chunks):
                total_chunks_processed += 1 # Counts every chunk we attempt to process
                
                # Generate embedding for the chunk
                embedding = await get_ollama_embedding(chunk_text, model_name="nomic-embed-text")
                if embedding is None:
                    logger.error(f"Failed to get embedding for chunk {i} of '{file_name}'. Skipping this chunk.")
                    continue # If embedding fails, skip this chunk from being added
                
                # --- Create rich metadata for RBAC ---
                metadata: Dict[str, Any] = {
                    "department": department, # Primary RBAC filter (lowercase)
                    "source_file": file_name,
                    "chunk_index": i,
                    "file_path": file_path, # Full path for debugging/reference
                    "file_extension": file_extension,
                }

                # Add more specific metadata based on your problem statement & metadata.txt
                # This logic should be kept in sync with ROLE_PERMISSIONS in src/core/rbac.py
                if department == "engineering":
                    metadata["document_type"] = "Technical Architecture"
                    metadata["access_level"] = "Restricted"
                    metadata["owners"] = "Engineering Team, C-Level Executives"
                elif department == "finance":
                    metadata["document_type"] = "Financial Report"
                    metadata["access_level"] = "Restricted"
                    metadata["owners"] = "Finance Team, C-Level Executives"
                    # Extract year/quarter from filename if applicable
                    if "quarterly_financial_report" in file_name.lower():
                        parts = file_name.lower().replace('.md', '').split('_')
                        if len(parts) >= 3 and parts[-2].startswith("q") and parts[-1].isdigit():
                            metadata["quarter"] = parts[-2].upper()
                            metadata["year"] = parts[len(parts)-1] # Ensure this gets the 4-digit year
                    elif "financial_summary" in file_name.lower():
                         metadata["year"] = "2024" # Example default for summary if not in filename
                elif department == "general":
                    metadata["document_type"] = "Employee Handbook"
                    metadata["access_level"] = "General Employee"
                    metadata["owners"] = "Human Resources Department"
                elif department == "hr":
                    metadata["document_type"] = "HR Dataset"
                    metadata["access_level"] = "Restricted" # Assuming sensitive HR data
                    metadata["owners"] = "HR & People Analytics Team"
                elif department == "marketing":
                    metadata["document_type"] = "Marketing Report"
                    metadata["access_level"] = "General Employee" 
                    metadata["owners"] = "Marketing Team"
                    # Extract year/quarter from filename if applicable
                    if "q" in file_name.lower():
                        parts = file_name.lower().replace('.md', '').split('_')
                        for part in parts:
                            if part.startswith("q") and len(part) == 2 and part[1].isdigit():
                                metadata["quarter"] = part.upper()
                            if part.isdigit() and len(part) == 4:
                                metadata["year"] = part


                documents_to_add.append(chunk_text)
                metadatas_to_add.append(metadata)
                # Use a more robust ID, perhaps incorporating hash of content to ensure uniqueness
                # For now, this existing ID generation should be fine, but consider for production
                ids_to_add.append(f"{department}_{file_name.replace('.', '_')}_chunk_{i}")
                embeddings_to_add.append(embedding)

    logger.info("\n--- Debugging Ingestion List Lengths ---")
    logger.info(f"Documents to add: {len(documents_to_add)} items")
    logger.info(f"Metadatas to add: {len(metadatas_to_add)} items")
    logger.info(f"Embeddings to add: {len(embeddings_to_add)} items")
    logger.info(f"IDs to add: {len(ids_to_add)} items")
    logger.info("-------------------------------------------\n")

    # Add all collected documents to ChromaDB
    if documents_to_add:
        # Final check for consistency before adding
        if not (len(documents_to_add) == len(metadatas_to_add) == len(embeddings_to_add) == len(ids_to_add)):
            logger.critical("Mismatched list lengths detected just before add_documents! Data integrity issue.")
            # In a production system, you might raise an exception here.
            return 

        await vector_store.add_documents(documents_to_add, metadatas_to_add, embeddings_to_add, ids_to_add)
        logger.info(f"Total {len(documents_to_add)} chunks successfully ingested into ChromaDB.")
    else:
        logger.info("No documents were processed or added to ChromaDB.")

    logger.info("--- Data ingestion complete ---")


if __name__ == "__main__":
    # Setup basic logging for local test run if not run via main app
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Ensure the 'data' directory exists at the project root for testing
    if not os.path.exists(DATA_DIR):
        logger.error(f"Error: Data directory '{DATA_DIR}' not found.")
        logger.error("Please ensure your data folder structure is set up as described.")
        logger.error("You can use 'mkdir -p data/{{engineering,finance,general,hr,marketing}}' to create it.")
        sys.exit(1)

    # Note: Running this will clear your existing ChromaDB collection 'finsolve_organizational_data'
    # and re-ingest all data.
    asyncio.run(ingest_data_into_chromadb())
