# src/core/rag_chain.py

import os
import sys
import logging
from typing import List, Dict, Tuple, Set
from collections import Counter # Import Counter for counting department occurrences

# Add the project root to sys.path to resolve 'src' imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.sys.path.insert(0, project_root)

from src.core.embedding import get_ollama_embedding # Keep for nomic-embed-text if still using Ollama for embeddings
from src.core.llm import generate_llm_response
from src.core.vector_store import ChromaVectorStore
from src.core.rbac import get_chroma_filter_for_role, ROLE_PERMISSIONS, ALL_DEPARTMENTS

# --- Logging Configuration (for this module) ---
logger = logging.getLogger(__name__)

# --- Keyword Mapping for Department Inference ---
DEPARTMENT_KEYWORDS = {
    "finance": ["revenue", "expense", "budget", "financial", "income", "profit", "audit", "cash flow", "balance sheet", "tax", "quarterly report", "earnings"],
    "marketing": ["campaign", "acquisition", "customer", "brand", "market", "advertising", "sales pipeline", "lead generation", "promotional", "digital marketing", "media spend", "target audience", "social media"],
    "hr": ["employee", "hr", "human resources", "policy", "onboarding", "leave", "benefits", "recruitment", "training", "payroll", "workforce"],
    "engineering": ["architecture", "microservices", "development", "tech stack", "deployment", "software", "product roadmap", "system design", "code", "infrastructure", "backend", "frontend"]
    # Add more as needed. General category queries might not have strong keywords.
}
MIN_KEYWORD_MATCHES = 1 # Minimum number of keyword matches to infer a department

class RAGChain:
    """
    Orchestrates the Retrieval Augmented Generation (RAG) process.
    It combines embedding generation, document retrieval from ChromaDB (with RBAC),
    and response generation using an LLM (now Gemini API).
    """
    def __init__(self, collection_name: str = "finsolve_organizational_data"):
        """
        Initializes the RAGChain with the vector store.
        """
        self.vector_store = ChromaVectorStore(collection_name=collection_name)
        logger.info("RAGChain initialized. Ensure Ollama 'nomic-embed-text' is pulled and Gemini API is accessible.")

    def _infer_query_department(self, query: str) -> str | None:
        """
        Infers the likely department the user's query is targeting based on keywords.
        """
        query_lower = query.lower()
        department_scores = {}

        for dept, keywords in DEPARTMENT_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in query_lower)
            if score >= MIN_KEYWORD_MATCHES:
                department_scores[dept] = score
        
        if not department_scores:
            return None # No clear department inferred

        # Return the department with the highest score
        inferred_dept = max(department_scores, key=department_scores.get)
        
        # Simple threshold: if the top score is not significantly higher than others, maybe it's ambiguous
        # For simplicity, returning the max for now. Can add a more complex thresholding if needed.
        logger.debug(f"Inferred department for query '{query}': {inferred_dept} (Scores: {department_scores})")
        return inferred_dept

    async def retrieve_and_generate(self, user_query: str, user_role: str) -> Tuple[str, List[Dict]]:
        """
        Executes the RAG process:
        1. Infers query department.
        2. Proactively denies access if query targets restricted department.
        3. Embeds the user query.
        4. Performs a global retrieval to see if any relevant data exists.
        5. Applies RBAC filters and performs a filtered retrieval.
        6. Determines if access was denied or info is missing based on retrieval results.
        7. Augments the query with retrieved context.
        8. Generates a response using the LLM.

        Args:
            user_query (str): The natural language query from the user.
            user_role (str): The role of the authenticated user (e.g., "Finance Team", "C-Level Executives").

        Returns:
            Tuple[str, List[Dict]]: A tuple containing:
                - The generated chatbot response.
                - A list of dictionaries, where each dictionary represents a source document
                  with at least 'source_file' and 'chunk_index'.
        """
        if not user_query:
            logger.warning("Received empty user query.")
            return "Please provide a query.", []

        # 1. Get RBAC filter based on user role
        rbac_filter = get_chroma_filter_for_role(user_role)
        logger.info(f"Applying RBAC filter for role '{user_role}': {rbac_filter}")

        # Determine the user's explicitly permitted departments from ROLE_PERMISSIONS
        user_permitted_departments: Set[str] = set()
        role_filter_definition = ROLE_PERMISSIONS.get(user_role, {})
        
        if isinstance(role_filter_definition, dict):
            if 'department' in role_filter_definition:
                user_permitted_departments.add(role_filter_definition['department'])
            elif '$or' in role_filter_definition:
                for or_condition in role_filter_definition['$or']:
                    if isinstance(or_condition, dict) and 'department' in or_condition:
                        user_permitted_departments.add(or_condition['department'])
        
        # --- PROACTIVE DENIAL based on query intent (NEW) ---
        inferred_query_department = self._infer_query_department(user_query)
        
        # If a clear target department is inferred and the user does NOT have access to it
        # and the user is not a high-level role with full access.
        if inferred_query_department and \
           inferred_query_department not in user_permitted_departments and \
           user_role not in ["Admin", "C-Level Executives"]:
            
            denied_dept_str = inferred_query_department.capitalize()
            logger.warning(f"Proactive denial: Query '{user_query}' inferred to target restricted department '{inferred_query_department}' for user '{user_role}'.")
            return f"Sorry, based on your '{user_role}' role, you do not have permission to access information related to the {denied_dept_str} department.", []
        
        # 2. Embed the user query using Ollama's nomic-embed-text
        query_embedding = await get_ollama_embedding(user_query, model_name="nomic-embed-text")
        if query_embedding is None:
            logger.error("Failed to generate embedding for user query.")
            return "Sorry, I couldn't process your query. Failed to generate embedding.", []

        # --- Enhanced Logic for 'No Access' vs. 'Not Found' (Existing, now acts as fallback) ---

        # Step A: First, retrieve all semantically relevant documents globally (no RBAC filter)
        all_relevant_results = await self.vector_store.query_documents(
            query_embedding=query_embedding,
            n_results=10
        )
        all_relevant_chunks_texts = all_relevant_results.get('documents', [[]])[0]
        all_relevant_chunks_metadatas = all_relevant_results.get('metadatas', [[]])[0]
        
        # Step B: Retrieve relevant documents WITH the RBAC filter
        retrieval_results_with_filter = await self.vector_store.query_documents(
            query_embedding=query_embedding,
            where_clause=rbac_filter,
            n_results=5
        )

        retrieved_chunks_texts = retrieval_results_with_filter.get('documents', [[]])[0]
        retrieved_chunks_metadatas = retrieval_results_with_filter.get('metadatas', [[]])[0]
        
        # Step C: Decision Logic for initial filtering (this now covers cases not caught by proactive denial)
        if not retrieved_chunks_texts:
            logger.info(f"No documents found for '{user_query}' with RBAC filter for role '{user_role}'.")
            if not all_relevant_chunks_texts:
                logger.info("No relevant documents found globally for the query.")
                return "I couldn't find any relevant information for your query in our knowledge base. Please try rephrasing or check if the information exists.", []
            else:
                denied_departments = set()
                for meta in all_relevant_chunks_metadatas:
                    dept = meta.get('department')
                    if dept and dept not in user_permitted_departments and user_role not in ["Admin", "C-Level Executives"]:
                        denied_departments.add(dept.capitalize())
                
                if denied_departments:
                    denied_dept_str = " or ".join(list(denied_departments))
                    logger.warning(f"Access denied for user '{user_role}' to departments: {denied_dept_str}")
                    return f"Sorry, based on your '{user_role}' role, you do not have permission to access information related to the {denied_dept_str} department.", []
                else:
                    logger.warning(f"Globally relevant chunks found but none returned by filtered query for role '{user_role}'. Ambiguous relevance or specific access_level restriction.")
                    return "I couldn't find any specific information for your query within your allowed access. Please try rephrasing.", []
        
        # If retrieved_chunks_texts IS NOT empty, we proceed to LLM generation.
        logger.info(f"Successfully retrieved {len(retrieved_chunks_texts)} chunks for processing.")

        # 4. Prepare context for the LLM and collect source information
        context_strings = []
        source_documents = []

        for i, chunk_text in enumerate(retrieved_chunks_texts):
            context_strings.append(f"Document chunk {i+1}:\n{chunk_text}")
            
            metadata = retrieved_chunks_metadatas[i]
            source_info = {
                "source_file": metadata.get('source_file', 'Unknown File'),
                "department": metadata.get('department', 'Unknown Department'),
                "chunk_index": metadata.get('chunk_index', -1)
            }
            if tuple(source_info.items()) not in [tuple(s.items()) for s in source_documents]:
                source_documents.append(source_info)
        
        context_str = "\n\n".join(context_strings)
        logger.debug(f"Context sent to LLM:\n{context_str[:500]}...")
        
        # 5. Formulate the prompt for the LLM
        permitted_depts_display = ", ".join([d.capitalize() for d in user_permitted_departments]) if user_permitted_departments else "all accessible departments"

        prompt = f"""
        You are an AI assistant for FinSolve Technologies.
        The current user has the role '{user_role}' and is permitted to access information primarily from the {permitted_depts_display} department(s).
        
        Your task is to answer the user's question concisely and accurately **based ONLY on the provided context**.
        
        If the answer is not in the provided context, clearly state that the information is not available within the provided context.
        Do NOT make up information.
        If you can answer, always include the source document(s) by referencing their 'source_file' and 'department'.

        User Question: {user_query}

        Context (from relevant and permitted documents):
        {context_str}

        Source Documents provided in metadata: {source_documents}
        """
        logger.debug(f"Prompt sent to LLM:\n{prompt[:1000]}...")
        
        # 6. Generate response using Gemini API
        response_text = await generate_llm_response(prompt, model_name="gemini-2.0-flash")
        
        if response_text:
            return response_text, source_documents
        else:
            logger.error("LLM failed to generate a response.")
            return "Sorry, I encountered an issue generating a response.", []

# Example usage (for testing purposes)
if __name__ == "__main__":
    import asyncio

    # Setup basic logging for local test run if not run via main app
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    async def test_rag_chain():
        logger.info("--- Testing RAGChain in standalone mode ---")
        
        rag_chain = RAGChain()

        # IMPORTANT: For this test to work, you need to have run `src/data_ingestion/ingest.py` first

        logger.info("\n--- Test Case 1: Finance Team Query (Expected Access) ---")
        finance_query = "What were the key financial highlights for Q1 2024?"
        finance_role = "Finance Team"
        response, sources = await rag_chain.retrieve_and_generate(finance_query, finance_role)
        logger.info(f"Query: '{finance_query}' (Role: {finance_role})")
        logger.info(f"Response:\n{response}")
        logger.info(f"Sources: {sources}\n")

        logger.info("\n--- Test Case 2: Marketing Team Query (Expected Access) ---")
        marketing_query = "Can you provide a breakdown of marketing spend for Q3 2024?"
        marketing_role = "Marketing Team"
        response, sources = await rag_chain.retrieve_and_generate(marketing_query, marketing_role)
        logger.info(f"Query: '{marketing_query}' (Role: {marketing_role})")
        logger.info(f"Response:\n{response}")
        logger.info(f"Sources: {sources}\n")

        logger.info("\n--- Test Case 3: Unauthorized Access Attempt (Marketing trying Finance) ---")
        unauthorized_query = "What was the total revenue for FinSolve Technologies in Q4 2024?" # Finance data
        unauthorized_role = "Marketing Team"
        response, sources = await rag_chain.retrieve_and_generate(unauthorized_query, unauthorized_role)
        logger.info(f"Query: '{unauthorized_query}' (Role: {unauthorized_role})")
        logger.info(f"Response:\n{response}")
        logger.info(f"Sources: {sources}\n")

        logger.info("\n--- Test Case 4: Employee Level Query (General Access) ---")
        employee_query = "Where can I find information about company events?"
        employee_role = "Employee Level"
        response, sources = await rag_chain.retrieve_and_generate(employee_query, employee_role)
        logger.info(f"Query: '{employee_query}' (Role: {employee_role})")
        logger.info(f"Response:\n{response}")
        logger.info(f"Sources: {sources}\n")
        
        logger.info("\n--- Test Case 5: C-Level Executive Query (Full Access, Engineering Data) ---")
        c_level_query = "Summarize the engineering architecture document."
        c_level_role = "C-Level Executives"
        response, sources = await rag_chain.retrieve_and_generate(c_level_query, c_level_role)
        logger.info(f"Query: '{c_level_query}' (Role: {c_level_role})")
        logger.info(f"Response:\n{response}")
        logger.info(f"Sources: {sources}\n")

        logger.info("\n--- Test Case 6: Query for Non-Existent Info (Even with Full Access) ---")
        non_existent_query = "What is the capital of Mars?"
        non_existent_role = "C-Level Executives" # Should not find this anywhere
        response, sources = await rag_chain.retrieve_and_generate(non_existent_query, non_existent_role)
        logger.info(f"Query: '{non_existent_query}' (Role: {non_existent_role})")
        logger.info(f"Response:\n{response}")
        logger.info(f"Sources: {sources}\n")

        logger.info("\n--- Test Case 7: Unauthorized Access Attempt (Finance trying Engineering) ---")
        finance_eng_query = "Explain FinSolve's microservices architecture." # Engineering data
        finance_eng_role = "Finance Team"
        response, sources = await rag_chain.retrieve_and_generate(finance_eng_query, finance_eng_role)
        logger.info(f"Query: '{finance_eng_query}' (Role: {finance_eng_role})")
        logger.info(f"Response:\n{response}")
        logger.info(f"Sources: {sources}\n")

        logger.info("\n--- Test Case 8: Finance User, Finance Query (Ambiguous Answer in Context) ---")
        finance_ambiguous_query = "Generate a summary of our revenue streams."
        finance_ambiguous_role = "Finance Team"
        response, sources = await rag_chain.retrieve_and_generate(finance_ambiguous_query, finance_ambiguous_role)
        logger.info(f"Query: '{finance_ambiguous_query}' (Role: {finance_ambiguous_role})")
        logger.info(f"Response:\n{response}")
        logger.info(f"Sources: {sources}\n")

        logger.info("\n--- NEW TEST CASE: Finance User, Marketing Query (Expected Explicit Denial) ---")
        finance_marketing_query = "What were the customer acquisition targets for Q1 2025?"
        finance_marketing_role = "Finance Team"
        response, sources = await rag_chain.retrieve_and_generate(finance_marketing_query, finance_marketing_role)
        logger.info(f"Query: '{finance_marketing_query}' (Role: {finance_marketing_role})")
        logger.info(f"Response:\n{response}")
        logger.info(f"Sources: {sources}\n")


    asyncio.run(test_rag_chain())
