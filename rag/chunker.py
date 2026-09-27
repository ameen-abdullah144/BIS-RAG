"""
RAG Chunker Module
Responsible for creating semantic chunks from processed BIS documents
with proper metadata preservation for retrieval-augmented generation.
"""

import json
import re
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class DocumentChunk:
    """Represents a chunk of a document with metadata for RAG."""
    chunk_id: str
    text: str
    metadata: Dict[str, Any]


class BISChunker:
    """
    Creates semantic chunks from processed BIS documents.

    Strategy:
    1. Prefer semantic boundaries (Section → Subsection → Clause → Paragraph)
    2. Fall back to fixed-size chunking for unstructured text
    3. Preserve provenance metadata with each chunk
    """

    def __init__(self,
                 chunk_size: int = 512,
                 chunk_overlap: int = 50,
                 min_chunk_size: int = 100):
        """
        Initialize the chunker.

        Args:
            chunk_size: Target size for chunks in characters
            chunk_overlap: Overlap between consecutive chunks in characters
            min_chunk_size: Minimum size for a chunk to be valid
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

        # Patterns for identifying structural elements in BIS documents
        self.section_pattern = re.compile(r'^\s*(\d+)\.\s+(.+)$', re.MULTILINE)
        self.subsection_pattern = re.compile(r'^\s*(\d+\.\d+)\.\s+(.+)$', re.MULTILINE)
        self.clause_pattern = re.compile(r'^\s*(\d+(\.\d+)*)\s+(.+)$', re.MULTILINE)

    def chunk_document(self,
                      document_path: str,
                      doc_type: str,
                      is_number: str) -> List[DocumentChunk]:
        """
        Chunk a single processed document.

        Args:
            document_path: Path to the cleaned JSON document
            doc_type: Type of document (e.g., 'amendment', 'product_manual')
            is_number: IS number (e.g., 'IS 2082')

        Returns:
            List of DocumentChunk objects
        """
        # Load the processed document
        with open(document_path, 'r', encoding='utf-8') as f:
            pages_data = json.load(f)

        chunks = []

        # Process each page
        for page_data in pages_data:
            page_number = page_data.get('page_number', 0)
            text = page_data.get('text', '')
            page_metadata = page_data.get('metadata', {})

            if not text.strip():
                continue

            # Try semantic chunking first
            semantic_chunks = self._semantic_chunking(
                text, page_number, doc_type, is_number, page_metadata
            )

            if semantic_chunks:
                chunks.extend(semantic_chunks)
            else:
                # Fall back to fixed-size chunking
                fixed_chunks = self._fixed_size_chunking(
                    text, page_number, doc_type, is_number, page_metadata
                )
                chunks.extend(fixed_chunks)

        return chunks

    def _semantic_chunking(self,
                          text: str,
                          page_number: int,
                          doc_type: str,
                          is_number: str,
                          base_metadata: Dict[str, Any]) -> List[DocumentChunk]:
        """
        Attempt to chunk text using semantic boundaries.

        Returns empty list if semantic chunking is not suitable.
        """
        # For now, we'll implement a simple approach that looks for clause boundaries
        # In a more sophisticated version, we'd parse the hierarchical structure

        # Split by potential clause boundaries (lines starting with numbers followed by dots)
        lines = text.split('\n')
        chunks = []
        current_chunk = []
        current_size = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if this looks like a clause/section header
            is_header = bool(
                re.match(r'^\d+\.?\d*\s+[A-Z]', line) or  # Numbered header
                re.match(r'^\d+\.\d+\.?\d*\s+[A-Z]', line) or  # Subsection
                line.startswith('(') and ')' in line[:10]  # Parenthetical reference like (Page 4, clause 18.2)
            )

            # If we hit a header and have accumulated enough text, create a chunk
            if is_header and current_size >= self.min_chunk_size and current_chunk:
                chunk_text = ' '.join(current_chunk)
                if len(chunk_text) >= self.min_chunk_size:
                    chunk_id = str(uuid.uuid4())
                    metadata = {
                        **base_metadata,
                        'page_number': page_number,
                        'doc_type': doc_type,
                        'is_number': is_number,
                        'chunk_method': 'semantic'
                    }
                    chunks.append(DocumentChunk(
                        chunk_id=chunk_id,
                        text=chunk_text,
                        metadata=metadata
                    ))
                    # Start new chunk with overlap
                    overlap_lines = current_chunk[-2:] if len(current_chunk) >= 2 else current_chunk
                    current_chunk = overlap_lines + [line]
                    current_size = sum(len(l) + 1 for l in current_chunk)
                else:
                    current_chunk.append(line)
                    current_size += len(line) + 1
            else:
                current_chunk.append(line)
                current_size += len(line) + 1

                # Check if we've exceeded chunk size
                if current_size >= self.chunk_size:
                    # Create chunk from current content
                    chunk_text = ' '.join(current_chunk)
                    if len(chunk_text) >= self.min_chunk_size:
                        chunk_id = str(uuid.uuid4())
                        metadata = {
                            **base_metadata,
                            'page_number': page_number,
                            'doc_type': doc_type,
                            'is_number': is_number,
                            'chunk_method': 'semantic'
                        }
                        chunks.append(DocumentChunk(
                            chunk_id=chunk_id,
                            text=chunk_text,
                            metadata=metadata
                        ))
                        # Start new chunk with overlap
                        overlap_lines = current_chunk[-2:] if len(current_chunk) >= 2 else current_chunk
                        current_chunk = overlap_lines
                        current_size = sum(len(l) + 1 for l in current_chunk)
                    else:
                        # Keep adding if chunk is too small
                        pass

        # Don't forget the last chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:
                chunk_id = str(uuid.uuid4())
                metadata = {
                    **base_metadata,
                    'page_number': page_number,
                    'doc_type': doc_type,
                    'is_number': is_number,
                    'chunk_method': 'semantic'
                }
                chunks.append(DocumentChunk(
                    chunk_id=chunk_id,
                    text=chunk_text,
                    metadata=metadata
                ))

        return chunks

    def _fixed_size_chunking(self,
                            text: str,
                            page_number: int,
                            doc_type: str,
                            is_number: str,
                            base_metadata: Dict[str, Any]) -> List[DocumentChunk]:
        """
        Fallback to fixed-size chunking when semantic chunking fails.
        """
        chunks = []
        words = text.split()

        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk_words = words[i:i + self.chunk_size]
            chunk_text = ' '.join(chunk_words)

            if len(chunk_text) >= self.min_chunk_size:
                chunk_id = str(uuid.uuid4())
                metadata = {
                    **base_metadata,
                    'page_number': page_number,
                    'doc_type': doc_type,
                    'is_number': is_number,
                    'chunk_method': 'fixed_size'
                }
                chunks.append(DocumentChunk(
                    chunk_id=chunk_id,
                    text=chunk_text,
                    metadata=metadata
                ))

        return chunks

    def chunk_all_documents(self,
                           storage_path: str = "storage/data") -> List[DocumentChunk]:
        """
        Chunk all processed documents in the storage directory.

        Args:
            storage_path: Path to the storage directory containing IS_* folders

        Returns:
            List of all DocumentChunk objects from all documents
        """
        all_chunks = []
        storage_dir = Path(storage_path)

        if not storage_dir.exists():
            raise FileNotFoundError(f"Storage directory not found: {storage_path}")

        # Iterate through all IS_* directories
        for is_dir in storage_dir.glob("IS_*"):
            if not is_dir.is_dir():
                continue

            is_number = is_dir.name.replace('_', ' ')

            # Look for cleaned text files
            text_dir = is_dir / "text" / "cleaned"
            if not text_dir.exists():
                continue

            # Process each cleaned JSON file
            for text_file in text_dir.glob("*_cleaned.json"):
                # Determine document type from filename
                filename = text_file.stem.replace('_cleaned', '')
                doc_type = filename  # e.g., 'amendment_0', 'product_manual_...'

                try:
                    chunks = self.chunk_document(
                        document_path=str(text_file),
                        doc_type=doc_type,
                        is_number=is_number
                    )
                    all_chunks.extend(chunks)
                except Exception as e:
                    print(f"Error processing {text_file}: {e}")
                    continue

        return all_chunks


def main():
    """Main function for testing the chunker."""
    chunker = BISChunker()

    # Test with a single document
    test_doc = "storage/data/IS_2082/text/cleaned/amendment_0_cleaned.json"
    try:
        chunks = chunker.chunk_document(
            document_path=test_doc,
            doc_type="amendment_0",
            is_number="IS 2082"
        )
        print(f"Created {len(chunks)} chunks from {test_doc}")
        for i, chunk in enumerate(chunks[:3]):  # Show first 3 chunks
            print(f"\nChunk {i+1}:")
            print(f"ID: {chunk.chunk_id}")
            print(f"Text preview: {chunk.text[:100]}...")
            print(f"Metadata: {chunk.metadata}")
    except Exception as e:
        print(f"Error testing chunker: {e}")


if __name__ == "__main__":
    main()