from typing import Dict, Optional
import json
from pathlib import Path
import logging
import os

logger = logging.getLogger(__name__)

class DocumentStorage:
    def __init__(self):
        # Get the base directory (2 levels up from this file)
        self.base_dir = Path(__file__).resolve().parent.parent.parent
        self.storage_dir = self.base_dir / "storage" / "documents"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized DocumentStorage at {self.storage_dir}")
    
    def save_document(self, document_id: str, content: Dict) -> None:
        """Save document content to storage"""
        try:
            if not document_id:
                raise ValueError("document_id cannot be empty")
            if not content:
                raise ValueError("content cannot be empty")
            if 'text' not in content:
                raise ValueError("Document content must contain 'text' field")

            file_path = self.storage_dir / f"{document_id}.json"
            logger.info(f"Saving document {document_id} to {file_path}")
            
            # Ensure the storage directory exists
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Successfully saved document {document_id}")
        except Exception as e:
            logger.error(f"Error saving document {document_id}: {str(e)}")
            raise
    
    def get_document(self, document_id: str) -> Optional[Dict]:
        """Retrieve document content from storage"""
        try:
            if not document_id:
                raise ValueError("document_id cannot be empty")

            file_path = self.storage_dir / f"{document_id}.json"
            logger.info(f"Attempting to retrieve document {document_id} from {file_path}")
            
            if not file_path.exists():
                logger.warning(f"Document {document_id} not found at {file_path}")
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
                
            if not content:
                logger.warning(f"Empty content for document {document_id}")
                return None
                
            if 'text' not in content:
                logger.warning(f"Document {document_id} does not contain 'text' field")
                return None
                
            logger.info(f"Successfully retrieved document {document_id}")
            return content
            
        except Exception as e:
            logger.error(f"Error retrieving document {document_id}: {str(e)}")
            return None
    
    def delete_document(self, document_id: str) -> bool:
        """Delete document from storage"""
        try:
            if not document_id:
                raise ValueError("document_id cannot be empty")

            file_path = self.storage_dir / f"{document_id}.json"
            logger.info(f"Attempting to delete document {document_id} from {file_path}")
            
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Successfully deleted document {document_id}")
                return True
            
            logger.warning(f"Document {document_id} not found for deletion")
            return False
            
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {str(e)}")
            return False

document_storage = DocumentStorage() 