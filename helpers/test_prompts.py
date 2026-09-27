#!/usr/bin/env python3
"""
Simple test script for specific prompts.
Users can modify the prompts below to test their own questions.
"""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'rag'))

from rag.answer_service import BISAnswerService

def test_specific_prompts():
    """Test specific prompts provided by the user."""
    print("=== BIS RAG Specific Prompts Test ===")

    # Initialize answer service
    try:
        answer_service = BISAnswerService(
            ollama_host="http://localhost:11434",
            ollama_model="llama3:8b"
        )
        print("[PASS] Answer service initialized successfully")
        print(f"[INFO] Timeout set to 200 seconds for Ollama requests")
        print()
    except Exception as e:
        print(f"[FAIL] Failed to initialize answer service: {e}")
        print("  Make sure Ollama is running (ollama serve) and llama3:8b model is available")
        return False

    # Define test prompts - users can modify these
    test_prompts = [
        {
            "question": "What are the safety requirements for water heaters?",
            "n_results": 5,
            "description": "Default test with 5 results"
        },
        {
            "question": "What is IS 2082 about?",
            "n_results": 1,
            "description": "Simple query with 1 result"
        },
        {
            "question": "What are the requirements for water heaters?",
            "is_number": "IS 2082",
            "n_results": 2,
            "description": "IS number filtered query"
        }
    ]

    # Process each test prompt
    for i, test_case in enumerate(test_prompts, 1):
        print(f"--- Test {i}: {test_case['description']} ---")
        print(f"Question: {test_case['question']}")

        try:
            # Extract parameters
            query = test_case["question"]
            n_results = test_case.get("n_results", 5)
            is_number = test_case.get("is_number")

            # Process the question
            if is_number:
                answer = answer_service.answer_by_is_number(
                    query=query,
                    is_number=is_number,
                    n_results=n_results
                )
            else:
                answer = answer_service.answer_question(
                    query=query,
                    n_results=n_results
                )

            # Display results
            print(f"[PASS] Query processed successfully")
            print(f"Answer: {answer.answer[:200]}{'...' if len(answer.answer) > 200 else ''}")
            print(f"Citations found: {len(answer.citations)}")
            print(f"Model used: {answer.model_used}")
            print()

        except Exception as e:
            print(f"[FAIL] Error processing query: {e}")
            print()

    print("[INFO] Test completed. Check logs above for prompt lengths and Ollama communication details.")
    return True

if __name__ == "__main__":
    test_specific_prompts()