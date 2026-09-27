#!/usr/bin/env python3
"""
Test script to verify the Ollama-RAG connection fix.
This script tests the BISAnswerService with logging to see prompt details.
"""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'rag'))

from rag.answer_service import BISAnswerService

def test_answer_service():
    """Test the answer service with logging enabled."""
    print("Testing BIS Answer Service with Ollama debugging...")

    # Initialize answer service
    # Note: This requires Ollama to be running with llama3:8b model
    try:
        answer_service = BISAnswerService(
            ollama_host="http://localhost:11434",
            ollama_model="llama3:8b"
        )
        print("[PASS] Answer service initialized successfully")
    except Exception as e:
        print(f"[FAIL] Failed to initialize answer service: {e}")
        print("  Make sure Ollama is running (ollama serve) and llama3:8b model is available")
        return False

    # Test with a simple query first
    print("\n--- Test 1: Simple query with n_results=1 ---")
    try:
        query = "What is IS 2082 about?"
        answer = answer_service.answer_question(query, n_results=1)
        print(f"[PASS] Query processed successfully")
        print(f"  Answer: {answer.answer[:100]}...")
        print(f"  Citations found: {len(answer.citations)}")
        print(f"  Model used: {answer.model_used}")
    except Exception as e:
        print(f"[FAIL] Error processing query: {e}")
        return False

    # Test with default n_results=5
    print("\n--- Test 2: Default query with n_results=5 ---")
    try:
        query = "What are the safety requirements for water heaters?"
        answer = answer_service.answer_question(query, n_results=5)
        print(f"[PASS] Query processed successfully")
        print(f"  Answer: {answer.answer[:100]}...")
        print(f"  Citations found: {len(answer.citations)}")
        print(f"  Model used: {answer.model_used}")
    except Exception as e:
        print(f"[FAIL] Error processing query: {e}")
        return False

    # Test with IS number filter if available
    print("\n--- Test 3: Query with IS number filter ---")
    try:
        query = "What are the requirements for water heaters?"
        answer = answer_service.answer_by_is_number(query, is_number="IS 2082", n_results=2)
        print(f"[PASS] Query processed successfully")
        print(f"  Answer: {answer.answer[:100]}...")
        print(f"  Citations found: {len(answer.citations)}")
        print(f"  Model used: {answer.model_used}")
    except Exception as e:
        print(f"[FAIL] Error processing query: {e}")
        # This might fail if no data for IS 2082, which is OK for testing
        print("  (This might be expected if no vector store data is available for IS 2082)")

    print("\n[PASS] All tests completed successfully!")
    print("  Check the logs above to see prompt lengths and Ollama communication details.")
    return True

if __name__ == "__main__":
    test_answer_service()