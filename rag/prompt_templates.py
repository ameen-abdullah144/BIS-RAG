"""
RAG Prompt Templates Module
Responsible for assembling prompts for the LLM with retrieved chunks,
instructions, and citation formatting for BIS question-answering.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from .embedding import DocumentChunk


@dataclass
class PromptComponents:
    """Components of a RAG prompt."""
    system_instructions: str
    context: str
    query: str
    citation_guidelines: str
    full_prompt: str


class BISPromptTemplates:
    """
    Manages prompt templates for BIS RAG system.
    """

    def __init__(self):
        """Initialize prompt templates."""
        # System instructions for the LLM
        self.system_instructions = """You are a helpful and friendly assistant specializing in Bureau of Indian Standards (BIS) specifications.
Your goal is to help users find and understand information from BIS documents in an easy-to-understand way.
When answering questions:
1. Base your answers primarily on the provided BIS document excerpts
2. Explain technical concepts in clear, simple language when possible
3. Cite your sources so users can verify the information
4. If the context doesn't contain sufficient information, be helpful about what you can and cannot answer
5. Feel free to engage in pleasant conversation while staying grounded in the document context"""

        # Citation guidelines
        self.citation_guidelines = """CITATION FORMAT:
When referencing information from the provided context, use this format:
[IS Number: Document Type, Page X, Clause Y.Z]
For example: [IS 2082: Product Manual, Page 5, Clause 18.2]

If clause information is not available, use:
[IS Number: Document Type, Page X]

Only cite information that actually appears in the provided context."""

        # Prompt templates for different scenarios
        self.prompt_templates = {
            'standard': self._get_standard_prompt(),
            'no_context': self._get_no_context_prompt(),
            'multilingual': self._get_multilingual_prompt()
        }

    def _get_standard_prompt(self) -> str:
        """Get the standard RAG prompt template."""
        return """{system_instructions}

CONTEXT:
{context}

{citation_guidelines}

QUESTION:
{query}

ANSWER:"""

    def _get_no_context_prompt(self) -> str:
        """Get the prompt template when no relevant context is found."""
        return """{system_instructions}

I couldn't find specific information about that in the available BIS document excerpts.
However, I'm still happy to help with what I can or suggest related topics you might find interesting.

{citation_guidelines}

QUESTION:
{query}

ANSWER:"""

    def _get_multilingual_prompt(self) -> str:
        """Get the prompt template for multilingual queries."""
        return """{system_instructions}

You can respond in the same language as the user's question.
Please provide your answer in {language} using only the information from the provided context.

CONTEXT:
{context}

{citation_guidelines}

QUESTION ({language}):
{query}

ANSWER ({language}):"""

    def format_chunks_for_context(self, chunks: List[Dict[str, Any]]) -> str:
        """
        Format retrieved chunks into a context string for the prompt.

        Args:
            chunks: List of retrieved chunk dictionaries

        Returns:
            Formatted context string
        """
        if not chunks:
            return "No relevant excerpts found."

        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            metadata = chunk.get('metadata', {})
            text = chunk.get('text', '')

            # Build citation info
            is_number = metadata.get('is_number', 'Unknown IS')
            doc_type = metadata.get('doc_type', 'Unknown Document')
            page_number = metadata.get('page_number', 'Unknown Page')

            # Try to get clause information from metadata
            clause_numbers = metadata.get('clause_numbers', [])
            clause_info = ""
            if clause_numbers:
                clause_info = f", Clause {', '.join(map(str, clause_numbers[:3]))}"  # Show first 3 clauses

            citation = f"[Excerpt {i}: {is_number}: {doc_type}, Page {page_number}{clause_info}]"

            context_parts.append(f"{citation}\n{text}\n")

        return "\n---\n".join(context_parts)

    def create_prompt(self,
                     query: str,
                     retrieved_chunks: List[Dict[str, Any]],
                     language: str = "English",
                     template_name: str = "standard") -> PromptComponents:
        """
        Create a complete prompt for the LLM.

        Args:
            query: User's question
            retrieved_chunks: List of retrieved chunks from the vector store
            language: Language for response (used in multilingual template)
            template_name: Name of template to use

        Returns:
            PromptComponents object with all prompt parts
        """
        # Select template
        template = self.prompt_templates.get(template_name, self.prompt_templates['standard'])

        # Format context from chunks
        context = self.format_chunks_for_context(retrieved_chunks)

        # Handle no context case
        if not retrieved_chunks or len(retrieved_chunks) == 0:
            template = self.prompt_templates['no_context']
            context = "No relevant excerpts found in the BIS document collection."

        # Format the prompt
        if template_name == 'multilingual':
            full_prompt = template.format(
                system_instructions=self.system_instructions,
                context=context,
                citation_guidelines=self.citation_guidelines,
                query=query,
                language=language
            )
        else:
            full_prompt = template.format(
                system_instructions=self.system_instructions,
                context=context,
                citation_guidelines=self.citation_guidelines,
                query=query
            )

        return PromptComponents(
            system_instructions=self.system_instructions,
            context=context,
            query=query,
            citation_guidelines=self.citation_guidelines,
            full_prompt=full_prompt
        )

    def extract_citations_from_response(self,
                                       response: str,
                                       retrieved_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract citations mentioned in the LLM response and validate them against retrieved chunks.

        Args:
            response: LLM's response text
            retrieved_chunks: List of retrieved chunks that were provided as context

        Returns:
            List of validated citation dictionaries
        """
        # This is a simplified implementation
        # In a more sophisticated version, we'd parse the response for citation patterns
        # and verify they match the provided chunks

        citations = []
        # For now, we'll return all chunks that were provided as context
        # assuming the LLM followed instructions and only cited from context
        for chunk in retrieved_chunks:
            citations.append({
                'chunk_id': chunk.get('id'),
                'text': chunk.get('text', '')[:100] + "...",  # Preview
                'metadata': chunk.get('metadata', {})
            })

        return citations


def main():
    """Main function for testing the prompt templates."""
    print("Testing prompt templates...")

    # Initialize prompt templates
    prompt_templates = BISPromptTemplates()

    # Test chunks
    test_chunks = [
        {
            'id': 'chunk-001',
            'text': 'AMENDMENT NO. 1 JULY 2019 TO IS 2082 : 2018 STATIONARY STORAGE TYPE ELECTRIC WATER HEATERS — SPECIFICATION',
            'metadata': {
                'is_number': 'IS 2082',
                'doc_type': 'amendment_0',
                'page_number': 1,
                'clause_numbers': ['18.2', '22.1.3']
            }
        },
        {
            'id': 'chunk-002',
            'text': 'The mixing factor shall be as declared by the manufacturer.',
            'metadata': {
                'is_number': 'IS 2082',
                'doc_type': 'amendment_0',
                'page_number': 4,
                'clause_numbers': ['18.2']
            }
        }
    ]

    # Test standard prompt
    query = "What is the mixing factor requirement for water heaters according to IS 2082?"
    prompt_components = prompt_templates.create_prompt(
        query=query,
        retrieved_chunks=test_chunks
    )

    print("=== STANDARD PROMPT ===")
    print(prompt_components.full_prompt)
    print("\n" + "="*50 + "\n")

    # Test no context case
    prompt_components_no_context = prompt_templates.create_prompt(
        query=query,
        retrieved_chunks=[]
    )

    print("=== NO CONTEXT PROMPT ===")
    print(prompt_components_no_context.full_prompt)
    print("\n" + "="*50 + "\n")

    # Test multilingual prompt
    prompt_components_multi = prompt_templates.create_prompt(
        query="पानी हीटर के मिश्रण कारक की आवश्यकता क्या है?",  # Hindi: What is the mixing factor requirement for water heaters?
        retrieved_chunks=test_chunks,
        language="Hindi",
        template_name='multilingual'
    )

    print("=== MULTILINGUAL PROMPT ===")
    print(prompt_components_multi.full_prompt)


if __name__ == "__main__":
    main()