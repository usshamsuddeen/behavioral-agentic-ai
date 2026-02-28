"""
Document Processor for Behavioral Agentic AI
Extracts text from various document formats and splits into chunks

Supported Formats:
- PDF (via PyPDF2)
- DOCX (via python-docx)
- TXT (plain text)
- JSON (structured data)
- CSV (tabular data)
- MD (Markdown)

Author: Behavioral Agentic AI Team
Version: 1.0.0
"""

import logging
import json
import csv
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from io import BytesIO, StringIO
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

# Default chunking configuration
DEFAULT_CHUNK_SIZE = 500  # words
DEFAULT_CHUNK_OVERLAP = 50  # words


@dataclass
class DocumentChunk:
    """Container for a document chunk."""
    text: str
    chunk_index: int
    total_chunks: int
    start_position: int
    end_position: int
    word_count: int
    metadata: Dict = field(default_factory=dict)


@dataclass 
class ProcessedDocument:
    """Container for a fully processed document."""
    filename: str
    file_type: str
    total_text_length: int
    chunks: List[DocumentChunk]
    metadata: Dict = field(default_factory=dict)
    error: Optional[str] = None


class DocumentProcessor:
    """
    Document text extraction and chunking service.
    
    Extracts text from various file formats and splits into
    overlapping chunks suitable for embedding and retrieval.
    
    Attributes:
        chunk_size: Target words per chunk
        chunk_overlap: Overlap words between chunks
    """
    
    def __init__(
        self, 
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
    ):
        """
        Initialize document processor.
        
        Args:
            chunk_size: Maximum words per chunk
            chunk_overlap: Overlap words between consecutive chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def process_file(
        self,
        content: bytes,
        filename: str,
        doc_type: str = "general",
        category: str = "general",
        additional_metadata: Optional[Dict] = None
    ) -> ProcessedDocument:
        """
        Process a file and return chunked document.
        
        Args:
            content: File content as bytes
            filename: Original filename
            doc_type: Document type (product, policy, faq, general)
            category: Document category
            additional_metadata: Extra metadata to include
            
        Returns:
            ProcessedDocument with chunks
        """
        # Determine file type from extension
        file_ext = Path(filename).suffix.lower().lstrip(".")
        
        # Build base metadata
        metadata = {
            "source": filename,
            "type": doc_type,
            "category": category,
            "file_extension": file_ext
        }
        if additional_metadata:
            metadata.update(additional_metadata)
        
        try:
            # Extract text based on file type
            text = self._extract_text(content, file_ext)
            
            if not text or not text.strip():
                return ProcessedDocument(
                    filename=filename,
                    file_type=file_ext,
                    total_text_length=0,
                    chunks=[],
                    metadata=metadata,
                    error="No text content extracted"
                )
            
            # Split into chunks
            chunks = self._split_into_chunks(text, metadata)
            
            return ProcessedDocument(
                filename=filename,
                file_type=file_ext,
                total_text_length=len(text),
                chunks=chunks,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to process {filename}: {e}")
            return ProcessedDocument(
                filename=filename,
                file_type=file_ext,
                total_text_length=0,
                chunks=[],
                metadata=metadata,
                error=str(e)
            )
    
    def _extract_text(self, content: bytes, file_type: str) -> str:
        """
        Extract text from file based on type.
        
        Args:
            content: File content as bytes
            file_type: File extension
            
        Returns:
            Extracted text
        """
        extractors = {
            "pdf": self._extract_from_pdf,
            "docx": self._extract_from_docx,
            "doc": self._extract_from_docx,
            "txt": self._extract_from_txt,
            "json": self._extract_from_json,
            "csv": self._extract_from_csv,
            "md": self._extract_from_markdown,
            "markdown": self._extract_from_markdown,
            # ★ V4: Image OCR support
            "png": self._extract_from_image,
            "jpg": self._extract_from_image,
            "jpeg": self._extract_from_image,
            "webp": self._extract_from_image,
        }
        
        extractor = extractors.get(file_type)
        if not extractor:
            # Try as plain text
            logger.warning(f"⚠️ Unknown file type: {file_type}, treating as text")
            return self._extract_from_txt(content)
        
        return extractor(content)
    
    def _extract_from_pdf(self, content: bytes) -> str:
        """Extract text from PDF."""
        try:
            import PyPDF2
            
            pdf_file = BytesIO(content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text_parts = []
            for page_num, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"[Page {page_num + 1}]\n{page_text}")
            
            return "\n\n".join(text_parts)
            
        except ImportError:
            logger.error("❌ PyPDF2 not installed. Run: pip install PyPDF2")
            raise
        except Exception as e:
            logger.error(f"❌ PDF extraction failed: {e}")
            raise
    
    def _extract_from_docx(self, content: bytes) -> str:
        """Extract text from DOCX."""
        try:
            import docx
            
            doc_file = BytesIO(content)
            doc = docx.Document(doc_file)
            
            paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
            return "\n\n".join(paragraphs)
            
        except ImportError:
            logger.error("❌ python-docx not installed. Run: pip install python-docx")
            raise
        except Exception as e:
            logger.error(f"❌ DOCX extraction failed: {e}")
            raise
    
    def _extract_from_txt(self, content: bytes) -> str:
        """Extract text from plain text file."""
        try:
            # Try UTF-8 first, then fallback to latin-1
            try:
                return content.decode("utf-8")
            except UnicodeDecodeError:
                return content.decode("latin-1")
        except Exception as e:
            logger.error(f"❌ Text extraction failed: {e}")
            raise
    
    def _extract_from_json(self, content: bytes) -> str:
        """Extract text from JSON file."""
        try:
            data = json.loads(content.decode("utf-8"))
            return self._json_to_text(data)
        except Exception as e:
            logger.error(f"❌ JSON extraction failed: {e}")
            raise
    
    def _json_to_text(self, data, prefix: str = "") -> str:
        """Recursively convert JSON to text."""
        if isinstance(data, dict):
            parts = []
            for key, value in data.items():
                new_prefix = f"{prefix}{key}: " if prefix else f"{key}: "
                parts.append(self._json_to_text(value, new_prefix))
            return "\n".join(parts)
        elif isinstance(data, list):
            parts = []
            for i, item in enumerate(data):
                parts.append(self._json_to_text(item, f"{prefix}[{i}] "))
            return "\n".join(parts)
        else:
            return f"{prefix}{str(data)}"
    
    def _extract_from_csv(self, content: bytes) -> str:
        """Extract text from CSV file."""
        try:
            text = content.decode("utf-8")
            reader = csv.DictReader(StringIO(text))
            
            rows = []
            for row in reader:
                row_text = " | ".join([f"{k}: {v}" for k, v in row.items() if v])
                rows.append(row_text)
            
            return "\n".join(rows)
        except Exception as e:
            logger.error(f"❌ CSV extraction failed: {e}")
            raise
    
    def _extract_from_markdown(self, content: bytes) -> str:
        """Extract text from Markdown file."""
        try:
            text = content.decode("utf-8")
            
            # Simple markdown to text conversion
            # Remove headers formatting but keep text
            text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
            
            # Remove bold/italic
            text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
            text = re.sub(r'\*([^*]+)\*', r'\1', text)
            text = re.sub(r'__([^_]+)__', r'\1', text)
            text = re.sub(r'_([^_]+)_', r'\1', text)
            
            # Remove links but keep text
            text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
            
            # Remove inline code
            text = re.sub(r'`([^`]+)`', r'\1', text)
            
            return text.strip()
        except Exception as e:
            logger.error(f"❌ Markdown extraction failed: {e}")
            raise
    
    def _extract_from_image(self, content: bytes) -> str:
        """Extract text from image using OCR (V4 NEW)."""
        try:
            # Try pytesseract first
            from PIL import Image
            import pytesseract
            image = Image.open(BytesIO(content))
            text = pytesseract.image_to_string(image)
            if text.strip():
                return text
        except ImportError:
            logger.warning("pytesseract not available, trying easyocr")
        except Exception as e:
            logger.warning(f"pytesseract OCR failed: {e}")

        try:
            # Fallback: easyocr
            import easyocr
            reader = easyocr.Reader(['en'])
            result = reader.readtext(content)
            text = " ".join([item[1] for item in result])
            return text
        except ImportError:
            logger.error("No OCR library available (install pytesseract or easyocr)")
            return "[OCR extraction failed — no OCR library installed]"
        except Exception as e:
            logger.error(f"easyocr OCR failed: {e}")
            return "[OCR extraction failed]"

    def _split_into_chunks(
        self, 
        text: str, 
        base_metadata: Dict
    ) -> List[DocumentChunk]:
        """
        Split text into overlapping chunks.
        
        Args:
            text: Full document text
            base_metadata: Metadata to include with each chunk
            
        Returns:
            List of DocumentChunk objects
        """
        # Clean and normalize text
        text = re.sub(r'\s+', ' ', text).strip()
        words = text.split()
        
        if len(words) <= self.chunk_size:
            # Single chunk for small documents
            return [DocumentChunk(
                text=text,
                chunk_index=0,
                total_chunks=1,
                start_position=0,
                end_position=len(words),
                word_count=len(words),
                metadata=base_metadata.copy()
            )]
        
        chunks = []
        step = self.chunk_size - self.chunk_overlap
        total_chunks = (len(words) - self.chunk_overlap) // step + 1
        
        for i in range(0, len(words), step):
            chunk_words = words[i:i + self.chunk_size]
            
            if len(chunk_words) < self.chunk_overlap:
                # Skip very small final chunks
                break
            
            chunk_text = " ".join(chunk_words)
            chunk_metadata = base_metadata.copy()
            chunk_metadata["chunk_index"] = len(chunks)
            chunk_metadata["total_chunks"] = total_chunks
            
            chunks.append(DocumentChunk(
                text=chunk_text,
                chunk_index=len(chunks),
                total_chunks=total_chunks,
                start_position=i,
                end_position=min(i + self.chunk_size, len(words)),
                word_count=len(chunk_words),
                metadata=chunk_metadata
            ))
        
        # Update total_chunks in all chunks
        for chunk in chunks:
            chunk.total_chunks = len(chunks)
            chunk.metadata["total_chunks"] = len(chunks)
        
        return chunks
    
    def process_faq(
        self,
        faqs: List[Dict],
        filename: str = "faqs.json",
        category: str = "faq"
    ) -> ProcessedDocument:
        """
        Process FAQ data into searchable chunks.
        
        Args:
            faqs: List of FAQ dictionaries with 'question' and 'answer' keys
            filename: Source filename
            category: Category name
            
        Returns:
            ProcessedDocument with FAQ chunks
        """
        chunks = []
        
        for i, faq in enumerate(faqs):
            question = faq.get("question", "")
            answer = faq.get("answer", "")
            
            if question and answer:
                chunk_text = f"Q: {question}\nA: {answer}"
                metadata = {
                    "source": filename,
                    "type": "faq",
                    "category": category,
                    "question": question,
                    "chunk_index": i,
                    "total_chunks": len(faqs)
                }
                
                chunks.append(DocumentChunk(
                    text=chunk_text,
                    chunk_index=i,
                    total_chunks=len(faqs),
                    start_position=0,
                    end_position=len(chunk_text.split()),
                    word_count=len(chunk_text.split()),
                    metadata=metadata
                ))
        
        return ProcessedDocument(
            filename=filename,
            file_type="faq",
            total_text_length=sum(len(c.text) for c in chunks),
            chunks=chunks,
            metadata={"type": "faq", "category": category}
        )


# Singleton instance
_processor: Optional[DocumentProcessor] = None


def get_document_processor() -> DocumentProcessor:
    """
    Get the global document processor instance.
    
    Returns:
        DocumentProcessor instance
    """
    global _processor
    
    if _processor is None:
        _processor = DocumentProcessor()
    
    return _processor
