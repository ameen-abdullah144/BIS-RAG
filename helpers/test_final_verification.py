"""
Final verification test of the complete RAG pipeline with working Ollama model
"""
from rag.answer_service import BISAnswerService

def main():
    """Test the complete RAG pipeline with available Ollama model."""
    print("Testing complete RAG pipeline with qwen3:8b")
    print("=" * 50)

    try:
        # Initialize answer service with available model
        answer_service = BISAnswerService(
            ollama_model="qwen3:8b"  # Use the available model instead of llama3:8b
        )
        
        print("Answer service initialized successfully with qwen3:8b")
        
        # Test a simple question
        test_question = "What are the requirements for pressure vessel testing?"
        print(f"\nQuestion: {test_question}")
        print("-" * 50)
        
        # Get answer from the RAG pipeline
        result = answer_service.answer_question(test_question)
        
        print(f"Answer: {result.answer}")
        print(f"Model used: {result.model_used}")
        print(f"Sources found: {len(result.citations)}")
        
        if result.citations:
            print("Top sources:")
            for i, citation in enumerate(result.citations[:2]):  # Show top 2 sources
                metadata = citation.get('metadata', {})
                print(f"  {i+1}. [{metadata.get('is_number', 'N/A')}] "
                      f"{citation.get('text', '')[:100]}...")
        print()
        
        # Show service statistics
        stats = answer_service.get_service_stats()
        print("Service statistics:")
        print(f"  Ollama host: {stats.get('ollama_host', 'N/A')}")
        print(f"  Ollama model: {stats.get('ollama_model', 'N/A')}")
        retriever_stats = stats.get('retriever', {})
        print(f"  Vector store chunks: {retriever_stats.get('total_chunks', 0)}")
        print(f"  Embedding model: {retriever_stats.get('model_name', 'N/A')}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
