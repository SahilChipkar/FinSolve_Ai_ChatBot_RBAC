# src/data_ingestion/text_splitter.py

from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownTextSplitter
from typing import List

class TextSplitter:
    """
    A utility class for splitting text into smaller chunks.
    Utilizes LangChain's text splitters for robust chunking.
    """

    @staticmethod
    def split_text(
        text: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        splitter_type: str = "recursive" # or "markdown"
    ) -> List[str]:
        """
        Splits a given text into smaller chunks.

        Args:
            text (str): The input text to be split.
            chunk_size (int): The maximum size of each chunk.
            chunk_overlap (int): The number of characters to overlap between consecutive chunks.
            splitter_type (str): The type of splitter to use.
                                 "recursive" for general text, "markdown" for Markdown files.

        Returns:
            List[str]: A list of text chunks.
        """
        if not text:
            return []

        if splitter_type == "markdown":
            splitter = MarkdownTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
        elif splitter_type == "recursive":
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                # You can customize separators based on your data if needed
                separators=["\n\n", "\n", " ", ""] 
            )
        else:
            print(f"Warning: Unknown splitter type '{splitter_type}'. Using 'recursive' as default.")
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
        
        chunks = splitter.split_text(text)
        return chunks

# Example usage (for testing purposes)
if __name__ == "__main__":
    print("--- Testing TextSplitters ---")

    long_text = """
    This is a very long paragraph that needs to be split into smaller chunks.
    Text splitting is an essential step in building Retrieval Augmented Generation (RAG)
    systems. It ensures that the pieces of information sent to the embedding model
    are of a manageable size and maintain semantic coherence.
    
    Too large chunks can dilute the meaning and overwhelm the LLM.
    Too small chunks might lose important context.
    
    The chunk size and overlap parameters are crucial for optimizing performance
    and retrieval quality. Overlap helps maintain context across chunk boundaries.

    # Section 1: Introduction
    This is the first section of a markdown document.
    
    ## Subsection 1.1
    Details about subsection 1.1.
    """

    # Test recursive splitter
    recursive_chunks = TextSplitter.split_text(long_text, chunk_size=200, chunk_overlap=50, splitter_type="recursive")
    print(f"\n--- Recursive Splitter (Chunks: {len(recursive_chunks)}) ---")
    for i, chunk in enumerate(recursive_chunks):
        print(f"Chunk {i+1} (len {len(chunk)}):\n'{chunk[:100]}...'\n")

    # Test markdown splitter
    markdown_chunks = TextSplitter.split_text(long_text, chunk_size=150, chunk_overlap=30, splitter_type="markdown")
    print(f"\n--- Markdown Splitter (Chunks: {len(markdown_chunks)}) ---")
    for i, chunk in enumerate(markdown_chunks):
        print(f"Chunk {i+1} (len {len(chunk)}):\n'{chunk[:100]}...'\n")

    short_text = "A short text."
    short_chunks = TextSplitter.split_text(short_text, chunk_size=50, chunk_overlap=10)
    print(f"\n--- Short Text Splitter (Chunks: {len(short_chunks)}) ---")
    for i, chunk in enumerate(short_chunks):
        print(f"Chunk {i+1} (len {len(chunk)}):\n'{chunk}'\n")

    empty_chunks = TextSplitter.split_text("", chunk_size=100)
    print(f"\n--- Empty Text Splitter (Chunks: {len(empty_chunks)}) ---")
    print(empty_chunks) # Expected: []
