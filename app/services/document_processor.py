import fitz  # PyMuPDF
from PIL import Image
import pytesseract
import re
from pathlib import Path
import logging
from typing import Dict, List, Tuple, Union
import io

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self):
        self.pii_patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b(\+\d{1,2}\s?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'credit_card': r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
        }

    async def process_document(self, file_path: Path) -> Dict:
        """
        Process a document file (PDF or image) and extract text, metadata, and PII.
        
        Args:
            file_path (Path): Path to the document file
            
        Returns:
            Dict: Dictionary containing extracted text, metadata, and PII information
        """
        try:
            file_extension = file_path.suffix.lower()
            
            if file_extension == '.pdf':
                text, metadata = await self._process_pdf(file_path)
            elif file_extension in ['.jpg', '.jpeg', '.png']:
                text, metadata = await self._process_image(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_extension}")

            # Extract PII
            pii_findings = self._extract_pii(text)
            
            return {
                'text': text,
                'metadata': metadata,
                'pii_findings': pii_findings
            }
            
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            raise Exception(f"Failed to process document: {str(e)}")

    async def _process_pdf(self, file_path: Path) -> Tuple[str, Dict]:
        """Process a PDF file and extract text and metadata."""
        try:
            doc = fitz.open(file_path)
            text = ""
            
            for page in doc:
                text += page.get_text()
            
            metadata = {
                'title': doc.metadata.get('title', ''),
                'author': doc.metadata.get('author', ''),
                'subject': doc.metadata.get('subject', ''),
                'keywords': doc.metadata.get('keywords', ''),
                'page_count': len(doc),
            }
            
            doc.close()
            return text, metadata
            
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            raise Exception(f"Failed to process PDF: {str(e)}")

    async def _process_image(self, file_path: Path) -> Tuple[str, Dict]:
        """Process an image file and extract text using OCR."""
        try:
            with Image.open(file_path) as img:
                # Extract text using OCR
                text = pytesseract.image_to_string(img)
                
                metadata = {
                    'format': img.format,
                    'size': img.size,
                    'mode': img.mode,
                }
                
                return text, metadata
                
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            raise Exception(f"Failed to process image: {str(e)}")

    def _extract_pii(self, text: str) -> Dict[str, List[str]]:
        """Extract PII from text using regex patterns."""
        findings = {}
        
        for pii_type, pattern in self.pii_patterns.items():
            matches = re.finditer(pattern, text)
            findings[pii_type] = [match.group() for match in matches]
            
        return findings

# Initialize the document processor
document_processor = DocumentProcessor() 