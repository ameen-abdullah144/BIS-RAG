"""
BIS RAG Backend Service
FastAPI application that provides a RAG chatbot endpoint for querying BIS documents.
With chat history storage capabilities.
"""

import os
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, Depends, Header, Response
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import json
from pathlib import Path
from rag.answer_service import BISAnswerService, AnswerContract
from backend.database import chat_database


# Initialize FastAPI app
app = FastAPI(
    title="BIS RAG Chatbot API",
    description="Retrieval-Augmented Generation API for Bureau of Indian Standards documents",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the answer service (will be created on startup)
answer_service: Optional[BISAnswerService] = None


# Pydantic models for request/response
class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None  # Optional session ID for chat history
    is_number: Optional[str] = None   # Filter by specific IS number
    doc_type: Optional[str] = None    # Filter by document type
    n_results: int = 5                # Number of results to retrieve
    use_hybrid_search: bool = True    # Whether to use hybrid search


class ChatResponse(BaseModel):
    answer: str
    citations: List[Dict[str, Any]]
    query: str
    session_id: str  # Return the session ID (either provided or newly created)
    model_used: str
    timestamp: str


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class SessionResponse(BaseModel):
    session_id: str
    created_at: str


class MessageResponse(BaseModel):
    id: int
    session_id: str
    role: str
    content: str
    timestamp: str


class SessionListResponse(BaseModel):
    sessions: List[Dict[str, Any]]


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global answer_service
    try:
        # Get configuration from environment variables with defaults
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        ollama_model = os.getenv("OLLAMA_MODEL", "llama3:8b")

        print(f"Initializing BIS RAG service...")
        print(f"Ollama host: {ollama_host}")
        print(f"Ollama model: {ollama_model}")

        answer_service = BISAnswerService(
            ollama_host=ollama_host,
            ollama_model=ollama_model
        )

        # Ensure database is initialized
        # The chat_database singleton initializes on import
        print(f"Chat history database initialized at: {chat_database.db_path}")

        print("BIS RAG service initialized successfully!")

    except Exception as e:
        print(f"Failed to initialize BIS RAG service: {e}")
        # Don't raise the exception here to allow the app to start
        # but the /chat endpoint will fail if answer_service is None


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    if answer_service is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return HealthResponse(
        status="healthy",
        service="BIS RAG Chatbot API",
        version="1.0.0"
    )


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    # Optional authentication - in a real implementation, you'd validate tokens/API keys
    authorization: Optional[str] = Header(None)
):
    """
    Main chat endpoint for querying the BIS RAG system.

    Args:
        request: ChatRequest containing the query and optional filters
        authorization: Optional Authorization header for authentication

    Returns:
        ChatResponse with the answer and citations
    """
    if answer_service is None:
        raise HTTPException(
            status_code=503,
            detail="Service not initialized. Please check server logs."
        )

    # Optional authentication check
    # In a real implementation, you would validate the authorization token here
    # For now, we'll just check if it's present when required
    # if os.getenv("REQUIRE_AUTH", "false").lower() == "true":
    #     if not authorization or not authorization.startswith("Bearer "):
    #         raise HTTPException(status_code=401, detail="Authentication required")

    try:
        # Handle session management
        session_id = request.session_id
        if session_id is None:
            # Create new session if none provided
            session_id = chat_database.create_session()
        elif not chat_database.session_exists(session_id):
            # If session_id provided but doesn't exist, create new one with that ID
            # This allows clients to specify their own session IDs if desired
            chat_database.create_session(session_id=session_id)

        # Store user message in chat history
        chat_database.add_message(
            session_id=session_id,
            role="user",
            content=request.query
        )

        # Process the question using the answer service
        answer_contract = answer_service.answer_question(
            query=request.query,
            n_results=request.n_results,
            is_number=request.is_number,
            doc_type=request.doc_type,
            use_hybrid_search=request.use_hybrid_search
        )

        # Store assistant response in chat history
        chat_database.add_message(
            session_id=session_id,
            role="assistant",
            content=answer_contract.answer,
            metadata={
                "citations": answer_contract.citations,
                "model_used": answer_contract.model_used
            }
        )

        # Convert to ChatResponse format
        response_dict = ChatResponse(
            answer=answer_contract.answer,
            citations=answer_contract.citations,
            query=answer_contract.query,
            session_id=session_id,
            model_used=answer_contract.model_used,
            timestamp=answer_contract.timestamp
        ).dict()

        # Return response with headers to prevent caching
        return Response(
            content=json.dumps(response_dict),
            media_type="application/json",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


@app.post("/sessions", response_model=SessionResponse)
async def create_session():
    """Create a new chat session."""
    session_id = chat_database.create_session()
    # Get the creation timestamp
    with chat_database.get_connection() as conn:
        cursor = conn.execute(
            "SELECT created_at FROM chat_sessions WHERE id = ?",
            (session_id,)
        )
        created_at = cursor.fetchone()["created_at"]

    return SessionResponse(
        session_id=session_id,
        created_at=created_at
    )


@app.get("/sessions/{session_id}/messages", response_model=List[MessageResponse])
async def get_session_messages(session_id: str, limit: Optional[int] = None):
    """Get messages for a specific chat session."""
    if not chat_database.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    messages = chat_database.get_session_messages(session_id, limit=limit)

    return [
        MessageResponse(
            id=msg["id"],
            session_id=msg["session_id"],
            role=msg["role"],
            content=msg["content"],
            timestamp=msg["timestamp"]
        )
        for msg in messages
    ]


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a chat session and all its messages."""
    if not chat_database.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    success = chat_database.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete session")

    return {"message": "Session deleted successfully"}


@app.get("/sessions", response_model=SessionListResponse)
async def list_sessions(limit: int = 100):
    """List all chat sessions (most recently updated first)."""
    sessions = chat_database.get_all_sessions(limit=limit)
    return SessionListResponse(sessions=sessions)


@app.get("/documents/{is_number}")
async def get_document_info(is_number: str):
    """Get metadata and download link for a specific IS number's documents."""
    # Validate IS number format (basic validation)
    if not is_number.startswith("IS_"):
        raise HTTPException(status_code=400, detail="Invalid IS number format")

    # Construct the path to the documents directory
    documents_dir = Path(f"storage/data/{is_number}/documents")

    # Check if directory exists
    if not documents_dir.exists() or not documents_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"No documents found for IS number: {is_number}")

    # Get list of documents
    documents = []
    for doc_file in documents_dir.glob("*.pdf"):
        # Extract document type from filename (remove extension and IS number prefix)
        filename = doc_file.name
        # Try to extract a readable document type from filename
        doc_type = filename.replace(f"{is_number}_", "").replace(".pdf", "")
        if not doc_type:
            doc_type = "Unknown Document"

        documents.append({
            "filename": filename,
            "document_type": doc_type,
            "download_url": f"/documents/{is_number}/download/{filename}",
            "file_size": doc_file.stat().st_size  # Size in bytes
        })

    if not documents:
        raise HTTPException(status_code=404, detail=f"No PDF documents found for IS number: {is_number}")

    return {
        "is_number": is_number,
        "document_count": len(documents),
        "documents": documents,
        "message": f"Found {len(documents)} document(s) for {is_number}"
    }


@app.get("/documents/{is_number}/download/{filename}")
async def download_document(is_number: str, filename: str):
    """Download a specific document file for an IS number."""
    # Validate inputs
    if not is_number.startswith("IS_"):
        raise HTTPException(status_code=400, detail="Invalid IS number format")

    # Security check: ensure filename doesn't contain path traversal attempts
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Construct the file path
    file_path = Path(f"storage/data/{is_number}/documents/{filename}")

    # Check if file exists and is a PDF
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"Document not found: {filename}")

    if not filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files can be downloaded")

    # Return the file
    return FileResponse(
        path=file_path,
        media_type='application/pdf',
        filename=filename
    )


@app.get("/stats")
async def get_stats():
    """Get service statistics."""
    if answer_service is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return answer_service.get_service_stats()


# For running directly with uvicorn
if __name__ == "__main__":
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))

    print(f"Starting BIS RAG API server on {host}:{port}")

    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=False,  # Set to True for development
        log_level="info"
    )