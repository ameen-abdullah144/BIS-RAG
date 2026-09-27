# BIS Knowledge Ingestion Pipeline - RAG Phase

![Team Legio VI Logo](TEAM%20LOGO.jpeg)

This phase implements a Retrieval-Augmented Generation (RAG) system for querying Bureau of Indian Standards (BIS) documents using natural language.

## Overview

The RAG system allows users to ask questions in natural language and receive grounded answers with citations from the BIS document collection. The system consists of:

1. **Vector Store**: FAISS index storing document embeddings
2. **Backend**: FastAPI service that handles query processing
3. **Frontend**: Simple HTML/JavaScript chat interface
4. **LLM**: Ollama running Llama 3 8B model for answer generation

## Prerequisites

Before setting up the RAG system, ensure you have completed Phases 1-3 of the BIS pipeline, which process and validate the BIS documents.

### Software Requirements

- Python 3.8+
- [Ollama](https://ollama.ai/) (for running the Llama 3 8B model)
- Git

## Setup Instructions

### 1. Install Ollama and Llama 3 Model

First, install Ollama from https://ollama.ai/

Then pull the Llama 3 8B model:
```bash
ollama pull llama3:8b
```

Verify the installation:
```bash
ollama list
```
You should see `llama3:8b` in the list.

### 2. Install Python Dependencies

Navigate to the BIS1 project directory and install the required Python packages:
```bash
pip install -r requirements.txt
```

### 3. Build the Vector Store

The vector store needs to be built from the processed documents (output from Phases 2-3):
```bash
python scripts/build_vectorstore.py
```

This will:
- Read validated Phase 3 outputs from `storage/data/IS_*/text/cleaned/*_cleaned.json`
- Create enriched text chunks using semantic chunking
- Compute multilingual embeddings using sentence-transformers
- Persist the vector store to `storage/vectorstore/`

### 4. Start the Backend Service

Start the FastAPI backend service:
```bash
python backend/main.py
```

The service will be available at:
- API: http://localhost:8000
- Health check: http://localhost:8000/health
- API documentation: http://localhost:8000/docs

### 5. Access the Frontend

Open `frontend/index.html` in your web browser to access the chat interface.

Alternatively, you can serve it with a simple HTTP server:
```bash
# Python 3
python -m http.server 8080

# Then visit: http://localhost:8080
```

## Usage

### Through the Web Interface

1. Open `frontend/index.html` in your browser
2. Type your question in the input field
3. Press Enter or click the Send button
4. Wait for the response with citations

### Through the API Directly

You can also interact with the API directly using curl or any HTTP client:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the safety requirements for water heaters according to IS 2082?",
    "n_results": 5,
    "use_hybrid_search": true
  }'
```

## Configuration

### Environment Variables

The backend can be configured using environment variables:

- `OLLAMA_HOST`: Ollama API URL (default: http://localhost:11434)
- `OLLAMA_MODEL`: Model name to use (default: llama3:8b)
- `HOST`: Backend host to bind to (default: 0.0.0.0)
- `PORT`: Backend port (default: 8000)
- `REQUIRE_AUTH`: Whether to require authentication (default: false)

Example:
```bash
OLLAMA_HOST=http://localhost:11434 OLLAMA_MODEL=llama3:8b python backend/main.py
```

## How It Works

1. **Query Processing**: When a user submits a question, the backend:
   - Receives the query via the `/chat` endpoint
   - Uses the retriever to find relevant document chunks from the vector store
   - Combines vector similarity search with keyword matching (hybrid search)
   - Optionally filters by IS number or document type

2. **Prompt Construction**: The retrieved chunks are formatted into a prompt with:
   - System instructions for the LLM
   - The retrieved context with provenance information
   - Citation guidelines
   - The user's query

3. **Answer Generation**: The prompt is sent to Ollama's Llama 3 8B model, which:
   - Generates an answer based solely on the provided context
   - Includes citations in the specified format
   - Returns "I don't have sufficient information" if the context doesn't contain the answer

4. **Response Formatting**: The backend returns:
   - The generated answer
   - Citations with source information (IS number, document type, page, clauses)
   - Query metadata and timing information

## Extending the System

### Adding New Document Types

The system automatically processes any documents found in the `storage/data/IS_*/text/cleaned/` directory that match the `*_cleaned.json` pattern.

### Changing the Embedding Model

To use a different sentence-transformer model, modify the `model_name` parameter in `scripts/build_vectorstore.py` and `backend/main.py`.

### Adjusting Chunk Size

To change the chunk size for better precision or recall, modify the `chunk_size` parameter in the `BISChunker` class in `rag/chunker.py`.

## Troubleshooting

### Common Issues

1. **Ollama not running**: Make sure Ollama is running with `ollama serve` and the model is pulled
2. **Vector store empty**: Run `python scripts/build_vectorstore.py` to build the vector store from processed documents
3. **Backend connection errors**: Check that the backend is running on the expected port and host
4. **Slow responses**: The first query may be slower as the model loads; subsequent queries should be faster

### Logs

Check the console output of the backend service for detailed logs about query processing, retrieval, and generation.

## Performance Notes

- The system is designed to be lightweight and can run on consumer hardware
- Embedding generation is done once during vector store creation
- Query processing time depends on the length of the context and model speed
- Typical response times should be under 2 seconds for most queries

## Technologies Used

- **Backend**: Python 3.8+ with FastAPI framework
- **Frontend**: HTML5/CSS3/Vanilla JavaScript (no frameworks)
- **AI/ML**: 
  - Sentence Transformers (all-MiniLM-L6-v2) for text embeddings
  - Ollama serving Llama 3 8B for answer generation
- **Vector Store**: FAISS (Facebook AI Similarity Search) for efficient document retrieval
- **Document Processing**: 
  - PyMuPDF (PDF text extraction)
  - BeautifulSoup4 (HTML parsing)
  - Requests (HTTP client)
- **Data**: Pandas (data manipulation)
- **Server**: Uvicorn (ASGI server)
- **Database**: SQLite (chat history storage)

## Implementation Methodology (RAG Pipeline)

### 1. Document Ingestion
- Collect BIS documents (PDFs/HTML) from official sources
- Extract text using format-specific parsers (PyMuPDF for PDFs, BeautifulSoup for HTML)
- Clean text (normalize whitespace, remove artifacts)
- Segment into overlapping chunks (500-1000 tokens)

### 2. Embedding & Storage
- Generate numerical embeddings for chunks using Sentence Transformers
- Store vectors in FAISS index with metadata (source, chunk ID)
- FAISS enables millisecond-scale similarity search over dense vectors

### 3. Query Processing Pipeline
1. **User Query**: Convert question to embedding using same text model
2. **Retrieval**: Search FAISS for top-k (typically 5) most similar document chunks
3. **Context Assembly**: Combine retrieved chunks with original query
4. **Generation**: Feed context + query to Llama 3 8B via Ollama
5. **Response**: Model produces grounded answer with source citations
6. **Chat Log**: Exchange stored in SQLite for multi-turn context

### 4. System Architecture
- **Backend Service** (`backend/main.py`): FastAPI API with endpoints for:
  - `/chat`: Main RAG query processing
  - `/sessions`: Conversation session management  
  - `/health`: Service health checks
- **Frontend** (`frontend/index.html`): 
  - Real-time chat interface using Fetch API
  - Session persistence via localStorage
  - Citation linking to source documents
- **Utilities** (`helpers/`): Debug/test/verification scripts for development
- **Data Storage** (`storage/`):
  - FAISS vector index (`storage/vectorstore/`)
  - Processed documents (`storage/data/`)
  - Chat history (`storage/chat_history.db`)

### Key Design Principles
- **Grounded Responses**: Answers strictly derived from retrieved documents (minimizes hallucination)
- **Source Attribution**: All facts traceable to specific BIS document clauses
- **Modular Design**: Separation of concerns (ingest, embed, retrieve, generate)
- **Team Collaboration**: Helper scripts and documentation in GitHub for teammate access
- **Efficiency**: FAISS provides fast similarity search; lightweight frontend

## License

This project is part of the BIS Knowledge Ingestion Pipeline. See the main project repository for licensing information.