"""
PDF Processor - Extract text from PDF files

Uses pdfplumber for robust text extraction with page metadata.
"""
   
import io
import re
import logging
from typing import List, Dict

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

logger = logging.getLogger(__name__)


def _clean_text(text: str) -> str:
    """
    Clean extracted text.
    
    - Remove excessive whitespace
    - Normalize line breaks
    - Remove control characters
    """
    if not text:
        return ""
    
    # Remove control characters except newlines and tabs
    text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    
    # Normalize whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    
    # Normalize line breaks (max 2 consecutive)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()


class PDFProcessor:
    """
    PDF text extraction using pdfplumber.
    
    Extracts text page-by-page to preserve page metadata.
    """
    
    def __init__(self):
        """Initialize PDF processor."""
        if pdfplumber is None:
            raise ImportError(
                "pdfplumber is required for PDF processing. "
                "Install with: pip install pdfplumber"
            )
        
        logger.info("PDF Processor initialized (using pdfplumber)")
    
    def extract_text(self, file_bytes: bytes, filename: str = "document.pdf") -> List[Dict]:
        """
        Extract text from PDF file.
        
        Args:
            file_bytes: Raw PDF file bytes
            filename: Name of the PDF file (for logging)
            
        Returns:
            List of page dictionaries with text and metadata
            
        Example:
            [
                {"page": 1, "text": "Page 1 content..."},
                {"page": 2, "text": "Page 2 content..."},
                ...
            ]
        """
        pages = []
        
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                logger.info(f"Processing PDF: {filename} ({len(pdf.pages)} pages)")
                
                for idx, page in enumerate(pdf.pages):
                    try:
                        # Extract text from page
                        raw_text = page.extract_text() or ""
                        cleaned_text = _clean_text(raw_text)
                        
                        pages.append({
                            "page": idx + 1,
                            "text": cleaned_text,
                            "char_count": len(cleaned_text)
                        })
                        
                    except Exception as e:
                        logger.warning(f"Failed to extract text from page {idx + 1}: {e}")
                        pages.append({
                            "page": idx + 1,
                            "text": "",
                            "char_count": 0,
                            "error": str(e)
                        })
                
                # Log statistics
                total_chars = sum(p["char_count"] for p in pages)
                logger.info(
                    f"Extracted {len(pages)} pages, {total_chars} characters from {filename}"
                )
                
        except Exception as e:
            logger.error(f"Failed to process PDF {filename}: {e}", exc_info=True)
            raise
        
        return pages
    
    def get_metadata(self, file_bytes: bytes) -> Dict:
        """
        Extract PDF metadata.
        
        Args:
            file_bytes: Raw PDF file bytes
            
        Returns:
            Dictionary with PDF metadata
        """
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                metadata = pdf.metadata or {}
                
                return {
                    "num_pages": len(pdf.pages),
                    "title": metadata.get("Title", ""),
                    "author": metadata.get("Author", ""),
                    "subject": metadata.get("Subject", ""),
                    "creator": metadata.get("Creator", ""),
                    "producer": metadata.get("Producer", ""),
                    "creation_date": metadata.get("CreationDate", ""),
                    "modification_date": metadata.get("ModDate", ""),
                }
                
        except Exception as e:
            logger.error(f"Failed to extract PDF metadata: {e}")
            return {"num_pages": 0, "error": str(e)}

