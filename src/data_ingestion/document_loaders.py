# src/data_ingestion/document_loaders.py

import os
import pandas as pd
from typing import List, Dict, Tuple

# For DOCX and PDF, you'd typically need libraries like python-docx and pypdf.
# You might need to install them: pip install python-docx pypdf
# from docx import Document
# from pypdf import PdfReader # Use PdfReader from pypdf for modern usage

class DocumentLoader:
    """
    A utility class to load content from various document types.
    """

    @staticmethod
    def load_markdown(file_path: str) -> str | None:
        """Loads content from a Markdown file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except Exception as e:
            print(f"Error loading Markdown file {file_path}: {e}")
            return None

    @staticmethod
    def load_csv(file_path: str) -> str | None:
        """
        Loads content from a CSV file.
        For simplicity, this converts the entire CSV to a string.
        For complex CSVs, you might want to summarize or process rows.
        """
        try:
            df = pd.read_csv(file_path)
            # Convert DataFrame to a string representation, suitable for embedding
            # You might want to customize this for better context for the LLM
            content = df.to_string(index=False)
            return content
        except Exception as e:
            print(f"Error loading CSV file {file_path}: {e}")
            return None

    # @staticmethod
    # def load_docx(file_path: str) -> str | None:
    #     """Loads content from a .docx file."""
    #     try:
    #         document = Document(file_path)
    #         full_text = []
    #         for para in document.paragraphs:
    #             full_text.append(para.text)
    #         return "\n".join(full_text)
    #     except Exception as e:
    #         print(f"Error loading DOCX file {file_path}: {e}")
    #         return None

    # @staticmethod
    # def load_pdf(file_path: str) -> str | None:
    #     """Loads content from a PDF file."""
    #     try:
    #         reader = PdfReader(file_path)
    #         full_text = []
    #         for page in reader.pages:
    #             full_text.append(page.extract_text())
    #         return "\n".join(full_text)
    #     except Exception as e:
    #         print(f"Error loading PDF file {file_path}: {e}")
    #         return None

    @staticmethod
    def load_document(file_path: str) -> Tuple[str | None, str]:
        """
        Loads content from a file based on its extension.

        Args:
            file_path (str): The full path to the document file.

        Returns:
            Tuple[str | None, str]: A tuple containing the extracted text content
                                     (or None if an error occurred) and the file extension.
        """
        file_extension = os.path.splitext(file_path)[1].lower()

        if file_extension == ".md":
            content = DocumentLoader.load_markdown(file_path)
        elif file_extension == ".csv":
            content = DocumentLoader.load_csv(file_path)
        # elif file_extension == ".docx":
        #     content = DocumentLoader.load_docx(file_path)
        # elif file_extension == ".pdf":
        #     content = DocumentLoader.load_pdf(file_path)
        else:
            print(f"Warning: Unsupported file type: {file_extension} for {file_path}")
            content = None
        
        return content, file_extension

# Example usage (for testing purposes)
if __name__ == "__main__":
    print("--- Testing DocumentLoaders ---")

    # Create dummy files for testing
    dummy_data_dir = "temp_test_data"
    os.makedirs(dummy_data_dir, exist_ok=True)

    with open(os.path.join(dummy_data_dir, "test.md"), "w") as f:
        f.write("# Test Markdown\n\nThis is a sample markdown file.")
    
    with open(os.path.join(dummy_data_dir, "test.csv"), "w") as f:
        f.write("Name,Age\nAlice,30\nBob,24")

    # Test Markdown
    md_content, md_ext = DocumentLoader.load_document(os.path.join(dummy_data_dir, "test.md"))
    print(f"\nMarkdown Content ({md_ext}):\n{md_content[:50]}...")

    # Test CSV
    csv_content, csv_ext = DocumentLoader.load_document(os.path.join(dummy_data_dir, "test.csv"))
    print(f"\nCSV Content ({csv_ext}):\n{csv_content[:50]}...")

    # Test unsupported
    with open(os.path.join(dummy_data_dir, "test.txt"), "w") as f:
        f.write("This is a plain text file.")
    txt_content, txt_ext = DocumentLoader.load_document(os.path.join(dummy_data_dir, "test.txt"))
    print(f"\nText Content ({txt_ext}):\n{txt_content}") # Should print warning and None

    # Clean up dummy files
    os.remove(os.path.join(dummy_data_dir, "test.md"))
    os.remove(os.path.join(dummy_data_dir, "test.csv"))
    os.remove(os.path.join(dummy_data_dir, "test.txt"))
    os.rmdir(dummy_data_dir)
