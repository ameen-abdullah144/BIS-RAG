"""
RAG Answer Service Module
Responsible for end-to-end query processing: retrieval, prompt generation,
LLM invocation (Ollama), and response formatting with citations.
"""

import json
import requests
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from .embedding import BISEmbedder
from .retriever import BISRetriever
from .prompt_templates import BISPromptTemplates, PromptComponents

# Initialize logger
logger = logging.getLogger(__name__)

# Configure logging only if no handlers are configured (to avoid interfering with existing config)
if not logger.handlers:
    logger.setLevel(logging.INFO)
    # Create console handler and set level to info
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # Add formatter to ch
    ch.setFormatter(formatter)
    # Add ch to logger
    logger.addHandler(ch)


@dataclass
class AnswerContract:
    """Format for the final answer returned by the RAG system."""
    answer: str
    citations: List[Dict[str, Any]]
    query: str
    model_used: str
    timestamp: str
    token_usage: Optional[Dict[str, Any]] = None


class BISAnswerService:
    """
    End-to-end RAG answer service for BIS document querying.
    """

    def __init__(self,
                 ollama_host: str = "http://localhost:11434",
                 ollama_model: str = "llama3:8b",
                 retriever: Optional[BISRetriever] = None,
                 prompt_templates: Optional[BISPromptTemplates] = None):
        """
        Initialize the answer service.

        Args:
            ollama_host: Host URL for Ollama API
            ollama_model: Model name to use with Ollama
            retriever: BISRetriever instance (if None, creates new one)
            prompt_templates: BISPromptTemplates instance (if None, creates new one)
        """
        self.ollama_host = ollama_host.rstrip('/')
        self.ollama_model = ollama_model

        # Initialize components
        self.retriever = retriever if retriever else BISRetriever()
        self.prompt_templates = prompt_templates if prompt_templates else BISPromptTemplates()

        # Test Ollama connection
        self._test_ollama_connection()

    def _test_ollama_connection(self) -> None:
        """Test connection to Ollama service."""
        try:
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m.get('name') for m in models]
                if self.ollama_model in model_names:
                    logger.info(f"Connected to Ollama. Model {self.ollama_model} is available.")
                else:
                    logger.warning(f"Model {self.ollama_model} not found. Available models: {model_names}")
                    logger.warning(f"Attempting to use {self.ollama_model} anyway...")
            else:
                logger.warning(f"Could not connect to Ollama at {self.ollama_host}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Ollama connection test failed: {e}")
            logger.warning("Please ensure Ollama is running and accessible.")

    def generate_answer(self,
                       prompt: str,
                       max_tokens: int = 512,
                       temperature: float = 0.7) -> Dict[str, Any]:
        """
        Generate answer using Ollama API.

        Args:
            prompt: The complete prompt to send to the LLM
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Dictionary containing the generated response and metadata
        """
        # Log prompt details for debugging
        logger.info(f"Generating answer with prompt length: {len(prompt)} characters")
        logger.debug(f"Prompt preview (first 200 chars): {prompt[:200]}")
        logger.debug(f"Prompt preview (last 200 chars): {prompt[-200:] if len(prompt) > 200 else prompt}")

        url = f"{self.ollama_host}/api/generate"

        payload = {
            "model": self.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature
            }
        }

        # Log payload details (excluding prompt for brevity)
        logger.debug(f"Ollama payload: model={self.ollama_model}, max_tokens={max_tokens}, temperature={temperature}, stream=False")

        try:
            logger.info(f"Sending request to Ollama at {url} with timeout=200s")
            response = requests.post(url, json=payload, timeout=200)
            response.raise_for_status()

            result = response.json()

            logger.info(f"Received response from Ollama: {len(result.get('response', ''))} characters generated")
            logger.debug(f"Ollama response: {result}")

            return {
                "response": result.get("response", ""),
                "tokens_evaluated": result.get("eval_count", 0),
                "tokens_predicted": result.get("eval_count", 0),  # Simplified
                "model": result.get("model", self.ollama_model),
                "done": result.get("done", False)
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to generate answer from Ollama: {e}")
            raise Exception(f"Failed to generate answer from Ollama: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Ollama response: {e}")
            raise Exception(f"Failed to parse Ollama response: {e}")

    def answer_question(self,
                       query: str,
                       n_results: int = 5,
                       where: Optional[Dict[str, Any]] = None,
                       is_number: Optional[str] = None,
                       doc_type: Optional[str] = None,
                       use_hybrid_search: bool = True) -> AnswerContract:
        """
        Process a question end-to-end: retrieve, prompt, generate, format.

        Args:
            query: User's question
            n_results: Number of chunks to retrieve
            where: Optional metadata filter
            is_number: Optional IS number to filter by
            doc_type: Optional document type to filter by
            use_hybrid_search: Whether to use hybrid search (vector + keyword)

        Returns:
            AnswerContract object with the final answer and citations
        """
        from datetime import datetime

        logger.info(f"Processing question: '{query}' with n_results={n_results}")

        # Check if this is a simple greeting or conversational query
        greetings = ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening', 'how are you', 'thanks', 'thank you']
        query_lower = query.lower().strip()
        if any(greeting in query_lower for greeting in greetings) and len(query.strip()) < 30:
            # For simple greetings, we can give a friendly response without needing document context
            friendly_responses = [
                "Hello! I'm your BIS Standards assistant. How can I help you today?",
                "Hey there! Ready to explore some BIS standards together?",
                "Hi! I'm here to help you find information from BIS documents. What would you like to know?",
                "Hello! Happy to assist you with any questions about BIS standards."
            ]
            import random
            answer_text = random.choice(friendly_responses)

            # Still create an AnswerContract but with empty citations
            answer_contract = AnswerContract(
                answer=answer_text,
                citations=[],
                query=query,
                model_used=self.ollama_model,
                timestamp=datetime.now().isoformat(),
                token_usage={"tokens_evaluated": 0, "tokens_predicted": 0}
            )
            return answer_contract

        # Build where clause from parameters
        final_where = where.copy() if where else {}
        if is_number:
            final_where["is_number"] = is_number
        if doc_type:
            final_where["doc_type"] = doc_type

        # Retrieve relevant chunks
        if use_hybrid_search:
            retrieved_chunks = self.retriever.hybrid_retrieve(
                query=query,
                n_results=n_results,
                where=final_where if final_where else None
            )
        else:
            retrieved_chunks = self.retriever.retrieve(
                query=query,
                n_results=n_results,
                where=final_where if final_where else None
            )

        logger.info(f"Retrieved {len(retrieved_chunks)} chunks")

        # Create prompt
        prompt_components = self.prompt_templates.create_prompt(
            query=query,
            retrieved_chunks=retrieved_chunks
        )

        logger.info(f"Created prompt with length: {len(prompt_components.full_prompt)} characters")

        # Generate answer using Ollama
        try:
            ollama_response = self.generate_answer(prompt_components.full_prompt)
            answer_text = ollama_response.get("response", "").strip()
        except Exception as e:
            # Fallback response if Ollama fails
            answer_text = f"I apologize, but I encountered an error while generating the answer: {str(e)}"
            ollama_response = {
                "tokens_evaluated": 0,
                "tokens_predicted": 0,
                "model": self.ollama_model,
                "done": False
            }
            logger.error(f"Error generating answer: {e}")

        # Extract citations
        citations = self.prompt_templates.extract_citations_from_response(
            answer_text, retrieved_chunks
        )

        # Format citations for AnswerContract
        formatted_citations = []
        for i, citation in enumerate(citations):
            metadata = citation.get('metadata', {})
            formatted_citation = {
                'id': citation.get('chunk_id', f'citation-{i}'),
                'text_preview': citation.get('text', '')[:200] + "..." if len(citation.get('text', '')) > 200 else citation.get('text', ''),
                'is_number': metadata.get('is_number'),
                'doc_type': metadata.get('doc_type'),
                'page_number': metadata.get('page_number'),
                'clause_numbers': metadata.get('clause_numbers', []),
                'relevance_score': citation.get('similarity', citation.get('combined_score', 0.0))
            }
            formatted_citations.append(formatted_citation)

        # Create AnswerContract
        answer_contract = AnswerContract(
            answer=answer_text,
            citations=formatted_citations,
            query=query,
            model_used=ollama_response.get("model", self.ollama_model),
            timestamp=datetime.now().isoformat(),
            token_usage={
                "tokens_evaluated": ollama_response.get("tokens_evaluated", 0),
                "tokens_predicted": ollama_response.get("tokens_predicted", 0)
            }
        )

        return answer_contract

    def answer_by_is_number(self,
                           query: str,
                           is_number: str,
                           n_results: int = 5) -> AnswerContract:
        """
        Answer a question restricted to a specific IS number.

        Args:
            query: User's question
            is_number: IS number to restrict search to
            n_results: Number of chunks to retrieve

        Returns:
            AnswerContract object
        """
        return self.answer_question(
            query=query,
            n_results=n_results,
            is_number=is_number,
            use_hybrid_search=True
        )

    def get_service_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the answer service components.

        Returns:
            Dictionary containing service statistics
        """
        retriever_stats = self.retriever.get_retriever_stats()
        prompt_stats = {}  # Prompt templates don't have complex stats to report

        return {
            'service_type': 'BIS RAG Answer Service',
            'ollama_host': self.ollama_host,
            'ollama_model': self.ollama_model,
            'retriever': retriever_stats,
            'components': ['retriever', 'prompt_templates', 'answer_service']
        }


def main():
    """Main function for testing the answer service."""
    print("Testing answer service...")

    # Initialize answer service (will use test vectorstore if exists)
    try:
        answer_service = BISAnswerService(
            ollama_host="http://localhost:11434",
            ollama_model="llama3:8b"
        )

        # Test with a simple query
        query = "What are the safety requirements for water heaters according to IS 2082?"

        # This will likely return no results since we haven't built the vector store yet
        # but it tests the flow
        answer = answer_service.answer_question(query, n_results=3)

        print(f"Query: {answer.query}")
        print(f"Answer: {answer.answer}")
        print(f"Citations found: {len(answer.citations)}")
        print(f"Model used: {answer.model_used}")

    except Exception as e:
        print(f"Error testing answer service: {e}")
        print("This is expected if Ollama is not running or vector store is empty.")


if __name__ == "__main__":
    main()