#!/usr/bin/env python3
"""
Interactive test script for BIS Answer Service.
Allows users to input their own questions and see results with logging.
"""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'rag'))

from rag.answer_service import BISAnswerService

def interactive_test():
    """Interactive test of the answer service with user input."""
    print("=== BIS RAG Interactive Test ===")
    print("Enter your questions to test the RAG pipeline.")
    print("Type 'quit' or 'exit' to stop.")
    print("You can also specify n_results after your question like: 'question | n_results=3'")
    print()

    # Initialize answer service
    try:
        answer_service = BISAnswerService(
            ollama_host="http://localhost:11434",
            ollama_model="llama3:8b"
        )
        print("[PASS] Answer service initialized successfully")
        print()
    except Exception as e:
        print(f"[FAIL] Failed to initialize answer service: {e}")
        print("  Make sure Ollama is running (ollama serve) and llama3:8b model is available")
        return False

    while True:
        try:
            # Get user input
            user_input = input("\nEnter your question (or 'quit'): ").strip()

            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break

            if not user_input:
                continue

            # Parse optional n_results parameter
            n_results = 5  # default
            query = user_input
            if '|' in user_input:
                parts = user_input.split('|')
                query = parts[0].strip()
                if len(parts) > 1 and 'n_results=' in parts[1]:
                    try:
                        n_results_part = parts[1].strip()
                        if n_results_part.startswith('n_results='):
                            n_results = int(n_results_part.split('=')[1])
                    except ValueError:
                        print(f"[WARNING] Invalid n_results format, using default ({n_results})")

            print(f"\n[INFO] Processing: '{query}' with n_results={n_results}")

            # Process the question
            answer = answer_service.answer_question(query, n_results=n_results)

            # Display results
            print(f"\n[RESULT]")
            print(f"Answer: {answer.answer}")
            print(f"Citations found: {len(answer.citations)}")
            print(f"Model used: {answer.model_used}")

            # Show citation details if any
            if answer.citations:
                print(f"\n[CITATIONS]")
                for i, citation in enumerate(answer.citations, 1):
                    print(f"  {i}. IS {citation.get('is_number', 'N/A')} - "
                          f"{citation.get('doc_type', 'N/A')} - "
                          f"Page {citation.get('page_number', 'N/A')}")

        except KeyboardInterrupt:
            print("\n\nInterrupted by user. Goodbye!")
            break
        except Exception as e:
            print(f"\n[ERROR] Failed to process question: {e}")
            print("Please check that Ollama is running and try again.")

    return True

if __name__ == "__main__":
    interactive_test()