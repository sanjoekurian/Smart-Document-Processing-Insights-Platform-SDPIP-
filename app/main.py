from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path
import logging
import uvicorn
import os
import uuid
from datetime import datetime
from pydantic import BaseModel

# Import services
from app.services.document_processor import document_processor
from app.services.openai_service import openai_service
from app.services.report_generator import report_generator
from app.services.document_storage import document_storage

# Create base directory for the application
BASE_DIR = Path(__file__).resolve().parent.parent
APP_DIR = BASE_DIR / "app"

# Create necessary directories
UPLOAD_DIR = BASE_DIR / "uploads"
REPORTS_DIR = BASE_DIR / "reports"
LOGS_DIR = BASE_DIR / "logs"
STORAGE_DIR = BASE_DIR / "storage"
STORAGE_DOCUMENTS_DIR = STORAGE_DIR / "documents"

# Ensure all directories exist
for dir_path in [UPLOAD_DIR, REPORTS_DIR, LOGS_DIR, STORAGE_DIR, STORAGE_DOCUMENTS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / 'app.log', mode='a'),
        logging.StreamHandler()
    ]
)

# Create logger for this module
logger = logging.getLogger(__name__)
logger.info("Application starting up...")
logger.info(f"Base directory: {BASE_DIR}")
logger.info(f"Storage directory: {STORAGE_DIR}")

# Initialize FastAPI app
app = FastAPI(
    title="Smart Document Processing & Insights Platform",
    description="A platform for document analysis, PII detection, and AI-powered summarization",
    version="1.0.0"
)

# Setup static files and templates
app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))

class ChatRequest(BaseModel):
    question: str
    document_id: str

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the home page with upload form."""
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    """
    Handle file upload and process the document.
    """
    try:
        # Validate file type
        allowed_types = ["application/pdf", "image/jpeg", "image/png"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail="Only PDF and image files (JPEG, PNG) are allowed"
            )

        # Generate unique filename and ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        document_id = str(uuid.uuid4())
        file_extension = Path(file.filename).suffix
        safe_filename = f"{timestamp}_{document_id[:8]}{file_extension}"
        
        logger.info(f"Processing upload for file: {file.filename} (ID: {document_id})")
        
        # Save file
        file_path = UPLOAD_DIR / safe_filename
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        logger.info(f"File saved successfully: {safe_filename}")

        # Process document
        document_data = await document_processor.process_document(file_path)
        if not document_data:
            raise ValueError("Failed to process document")
        
        if 'text' not in document_data:
            raise ValueError("No text content extracted from document")
            
        logger.info("Document processed successfully")
        logger.info(f"Extracted text length: {len(document_data['text'])}")

        # Generate AI summary and analysis
        summary = await openai_service.generate_summary(document_data['text'])
        sentiment_analysis = await openai_service.analyze_sentiment(document_data['text'])
        
        logger.info("AI analysis completed")

        # Prepare document content for storage
        document_content = {
            'text': document_data['text'],
            'metadata': document_data.get('metadata', {}),
            'summary': summary,
            'sentiment': sentiment_analysis,
            'filename': file.filename,
            'upload_time': timestamp,
            'pii_findings': document_data.get('pii_findings', {}),
            'file_type': file.content_type,
            'processed_file': safe_filename
        }

        # Store document content
        try:
            document_storage.save_document(document_id, document_content)
            logger.info(f"Document {document_id} saved to storage successfully")
        except Exception as e:
            logger.error(f"Failed to save document to storage: {str(e)}")
            raise ValueError(f"Failed to save document: {str(e)}")
        
        # Generate report
        report_filename = f"report_{timestamp}_{document_id[:8]}.pdf"
        report_path = REPORTS_DIR / report_filename
        
        await report_generator.generate_report(
            output_path=report_path,
            document_data=document_data,
            summary=summary,
            sentiment_analysis=sentiment_analysis
        )
        
        logger.info("Report generated successfully")
        
        return {
            "status": "success",
            "message": "Document processed successfully",
            "document_id": document_id,
            "original_filename": file.filename,
            "report_filename": report_filename,
            "summary": summary,
            "metadata": document_data.get('metadata', {}),
            "pii_detected": any(findings for findings in document_data.get('pii_findings', {}).values()),
            "sentiment": sentiment_analysis.get('sentiment', 'N/A')
        }
    
    except ValueError as ve:
        logger.error(f"Validation error: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/report/{filename}")
async def get_report(filename: str):
    """Download a generated report."""
    try:
        report_path = REPORTS_DIR / filename
        if not report_path.exists():
            raise HTTPException(status_code=404, detail="Report not found")
            
        return FileResponse(
            path=report_path,
            filename=filename,
            media_type="application/pdf"
        )
        
    except Exception as e:
        logger.error(f"Error retrieving report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/")
async def chat_with_document(chat_request: ChatRequest):
    """
    Handle chat requests for a specific document.
    """
    try:
        logger.info(f"Processing chat request for document: {chat_request.document_id}")
        
        # Validate request
        if not chat_request.document_id:
            raise HTTPException(status_code=400, detail="Document ID is required")
        if not chat_request.question.strip():
            raise HTTPException(status_code=400, detail="Question cannot be empty")
            
        # Get the document context from storage
        document_context = document_storage.get_document(chat_request.document_id)
        
        if not document_context:
            logger.warning(f"Document not found: {chat_request.document_id}")
            raise HTTPException(status_code=404, detail="Document not found")
        
        if not document_context.get('text'):
            logger.error(f"Document {chat_request.document_id} has no text content")
            raise HTTPException(status_code=400, detail="Document has no text content")
        
        logger.info(f"Retrieved document context. Text length: {len(document_context['text'])}")
        logger.info("Generating chat response")
        
        # Generate response
        response = openai_service.generate_chat_response(
            question=chat_request.question,
            document_context=document_context
        )
        
        if not response:
            raise HTTPException(status_code=500, detail="Failed to generate response")
            
        logger.info("Chat response generated successfully")
        
        return {
            "response": response,
            "status": "success"
        }
    except HTTPException as he:
        logger.warning(f"HTTP error in chat endpoint: {str(he)}")
        raise
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 