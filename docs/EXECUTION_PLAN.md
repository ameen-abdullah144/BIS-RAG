# BIS Knowledge Ingestion Pipeline - Execution Plan

## Current Status Assessment

### ✅ Already Working:
1. **Configuration**: `config/niches/water_heaters.json` - Complete with 5 IS numbers
2. **Base Collector**: `collectors/base.py` - Robust foundation with rate limiting, retries, error handling
3. **KYS Collector**: `collectors/kys.py` - Successfully collects metadata for IS 2082
4. **Product Manuals Collector**: `collectors/product_manuals.py` - Successfully downloads PDFs for IS 2082
5. **Storage Structure**: `storage/data/IS_2082/metadata.json` - Metadata saved correctly
6. **Verification Scripts**: `verify_kys_single.py`, `verify_pm_single.py` - Working test scripts
7. **Dependencies**: `requirements.txt` - All required packages listed

### ⏳ In Progress / Partial:
- Metadata collection for all 5 IS numbers (only IS 2082 done so far)
- Product manual collection for all 5 IS numbers (only IS 2082 done so far)

### ❌ Not Started:
- Guidelines collector
- Labs collector (lims.bis.gov.in)
- QCO collector
- All processing pipeline modules (pdf_extractor, text_cleaner, metadata_extractor, relationship_mapper)
- All validator modules
- All RAG engine components
- Pipeline orchestrator
- Reporting system

## Execution Philosophy

Following your instructions: **INCREMENTAL DEVELOPMENT WITH VERIFICATION**
- Write code for one specific task
- Execute it immediately
- Verify it works correctly
- Only then move to the next task
- Never build ahead without verification
- Focus on making each piece work perfectly before connecting to the next

## Execution Plan - Phase by Phase

### PHASE 1: COMPLETE DATA COLLECTION FOR ALL 5 IS NUMBERS
*Goal: Ensure we can collect metadata and documents for all IS numbers in our niche*

#### Task 1.1: Complete KYS Collection for All 5 IS Numbers
- **Action**: Modify/test KYS collector to work with all IS numbers in config
- **Execution**: Run collector on all 5 IS numbers sequentially
- **Verification**: 
  - Check that metadata.json files are created for all 5 IS numbers
  - Verify each contains correct IS number, title, collection status
  - Confirm no errors in logs
- **Success Criteria**: 5 metadata.json files in storage/data/IS_*/ directories

#### Task 1.2: Complete Product Manuals Collection for All 5 IS Numbers
- **Action**: Test/product manuals collector on all 5 IS numbers
- **Execution**: Run collector on metadata from all 5 IS numbers
- **Verification**:
  - Check for downloaded PDFs in storage/data/IS_*/documents/ directories
  - Verify SHA-256 hashes are computed
  - Check collection_status updates in metadata.json
- **Success Criteria**: Product manuals downloaded for all available IS numbers (some may not have manuals)

#### Task 1.3: Implement Guidelines Collector
- **Action**: Create `collectors/guidelines.py` based on base collector
- **Execution**: Test on one IS number first, then all
- **Verification**: Guidelines documents downloaded and saved correctly
- **Success Criteria**: Guidelines PDFs stored for IS numbers that have them

#### Task 1.4: Implement Labs Collector (lims.bis.gov.in)
- **Action**: Create `collectors/labs.py` to query lims.bis.gov.in for testing facilities
- **Execution**: Test laboratory lookup for one IS number, then all
- **Verification**: Laboratory data collected and saved in structured format
- **Success Criteria**: Laboratory information available for each IS number where applicable

#### Task 1.5: Implement QCO Collector
- **Action**: Create `collectors/qco.py` to collect QCO gazette notifications
- **Execution**: Test QCO collection for the niche
- **Verification**: QCO gazette PDF downloaded and metadata recorded
- **Success Criteria**: QCO document available and linked to all relevant IS numbers

**Phase 1 Completion Check**: Run verification script that confirms all expected document types are collected for each IS number according to the completeness report format in PRD Section 6.9.

---

### PHASE 2: BUILD PROCESSING PIPELINE (STAGE BY STAGE)
*Goal: Process collected documents into clean, structured data with relationships*

#### Task 2.1: PDF Extractor (PyMuPDF)
- **Action**: Create `processors/pdf_extractor.py` 
- **Execution**: Test on one downloaded PDF (e.g., IS 2082 product manual)
- **Verification**:
  - Extract text with page numbers preserved
  - Output structured format (JSON with page-wise text or clean text file)
  - Confirm no loss of important content
- **Success Criteria**: Readable text extracted from PDF with page tracking

#### Task 2.2: Text Cleaner
- **Action**: Create `processors/text_cleaner.py`
- **Execution**: Test on output from PDF extractor
- **Verification**:
  - Headers/footers removed
  - Line breaks fixed
  - Whitespace normalized
  - Important formatting (clause numbers, headings) preserved
- **Success Criteria**: Clean text that maintains structural integrity

#### Task 2.3: Metadata Extractor
- **Action**: Create `processors/metadata_extractor.py`
- **Execution**: Test on cleaned text from one document
- **Verification**:
  - Deterministic extraction (clause numbers, IS references via regex)
  - LLM-assisted extraction for complex fields (scope, requirements)
  - Original document + URL preserved with extracted facts
- **Success Criteria**: Structured metadata extracted with provenance links

#### Task 2.4: Relationship Mapper
- **Action**: Create `processors/relationship_mapper.py`
- **Execution**: Test on extracted metadata from multiple documents
- **Verification**:
  - Correctly identifies: HAS_PRODUCT_MANUAL, HAS_QCO, BASED_ON, etc.
  - Builds explicit source_id | relationship | target_id table
  - Handles all minimum relationship types from PRD Section 6.7
- **Success Criteria**: Relationship graph built and stored

**Phase 2 Completion Check**: Run processing pipeline on one IS number's complete document set and verify output matches expected structure from PRD.

---

### PHASE 3: IMPLEMENT VALIDATION SYSTEM
*Goal: Ensure data quality and integrity at each stage*

#### Task 3.1: Document Validator
- **Action**: Create `validators/document_validator.py`
- **Execution**: Test on processed document from one IS number
- **Verification**:
  - Official BIS source confirmed
  - Correct IS-number association
  - Readable text
  - Text extraction succeeded
  - No duplicates (URL+hash)
  - Source URL present
  - Access status known
  - Metadata internally consistent
- **Success Criteria**: Validator returns pass/fail with detailed reasons

#### Task 3.2: Corpus Validator
- **Action**: Create `validators/corpus_validator.py`
- **Execution**: Test on processed data from all IS numbers
- **Verification**:
  - Completeness report generated (PRD Section 6.9 format)
  - Cross-IS consistency checked
  - Missing data explicitly recorded as "not_found"
- **Success Criteria**: Generated completeness report showing expected vs found

**Phase 3 Completion Check**: Run validation on full processed corpus and generate acceptable completeness report.

---

### PHASE 4: BUILD RAG ENGINE
*Goal: Create retrieval-augmented generation system with source-backed answers*

#### Task 4.1: Chunker (Semantic Chunking)
- **Action**: Create `rag/chunker.py`
- **Execution**: Test on processed text from one document
- **Verification**:
  - Semantic boundaries first (Section → Subsection → Clause → Paragraph)
  - Fixed-size only as fallback for unstructured text
  - Each chunk gets unique ID
  - Provenance metadata attached (IS number, doc type, page, section, etc.)
- **Success Criteria**: Chunks produced with correct schema (PRD Section 7.2)

#### Task 4.2: Embedding & Indexing (Chroma)
- **Action**: Create `rag/embed_index.py`
- **Execution**: Test indexing chunks from one IS number
- **Verification**:
  - Chroma vector store created/updated
  - Embedding model loads successfully
  - Vectors created for all chunks
  - Metadata indexed with each vector
- **Success Criteria**: Functional vector store with searchable chunks

#### Task 4.3: Retriever (Hybrid)
- **Action**: Create `rag/retriever.py`
- **Execution**: Test retrieval with sample queries
- **Verification**:
  - Vector similarity search works
  - Metadata filtering (by IS number, document type) functions
  - Hybrid retrieval combines both effectively
  - Top-k tuning produces relevant results
- **Success Criteria**: Retriever returns relevant chunks for BIS queries

#### Task 4.4: Prompt Templates
- **Action**: Create `rag/prompt_templates.py`
- **Execution**: Test prompt assembly with retrieved chunks
- **Verification**:
  - Template incorporates retrieved chunks + provenance + user query
  - Instructions to answer only from retrieved chunks
  - Citation format specified (IS no. / doc / page / section)
  - Handling for restricted access standards
- **Success Criteria**: Prompts properly formatted for LLM consumption

#### Task 4.5: Answer Service
- **Action**: Create `rag/answer_service.py`
- **Execution**: Test end-to-end query processing
- **Verification**:
  - Retrieves relevant chunks
  - Assembles prompt with citations
  - Calls Claude API (simulated or actual if available)
  - Extracts answer with citations
  - Returns Answer Contract format (PRD Section 7.5)
  - Handles insufficient evidence case
- **Success Criteria**: Service returns properly formatted answers with citations

**Phase 4 Completion Check**: Run demo queries from PRD Section 11 and verify answers are correct, cited properly, and distinguish standard vs certification.

---

### PHASE 5: PIPELINE ORCHESTRATION & REPORTING
*Goal: Create unified system that runs all stages and produces reports*

#### Task 5.1: Pipeline Orchestrator
- **Action**: Create `pipeline.py`
- **Execution**: Run full pipeline for one IS number
- **Verification**:
  - Orchestrates Stages 1-9 in correct order
  - Handles errors gracefully (per-document try/except)
  - Logs to reports/errors.json
  - Implements deduplication (URL+SHA-256)
  - Supports idempotent re-runs
- **Success Criteria**: One IS number processed completely through all stages

#### Task 5.2: Reporting System
- **Action**: Create reporting functionality in pipeline
- **Execution**: Run pipeline on all 5 IS numbers
- **Verification**:
  - Completeness report generated (PRD Section 6.9 format)
  - Error log maintained
  - Storage structure follows PRD Section 8 layout
  - All intermediate outputs saved appropriately
- **Success Criteria**: Complete, verifiable output for all 5 IS numbers

#### Task 5.3: Scalability Test
- **Action**: Test adding a second niche (config-only change)
- **Execution**: Create new niche config (e.g., for LED lights) and run pipeline
- **Verification**:
  - No code changes required
  - New niche processes correctly
  - Storage isolated by IS number directories
- **Success Criteria**: Second niche works with config-only modification

**Phase 5 Completion Check**: Full system runs end-to-end for target niche, produces verifiable outputs, and demonstrates config-driven scalability.

---

## IMMEDIATE NEXT STEPS (Based on Current State)

Since we have working KYS and Product Manuals collectors for IS 2082, let's start with:

### IMMEDIATE TASK 1: EXTEND COLLECTION TO ALL 5 IS NUMBERS

**Action Items**:
1. Create a test script that runs KYS collector on all 5 IS numbers from config
2. Execute it and verify metadata.json files are created for all 5
3. Create a test script that runs Product Manuals collector on all available metadata
4. Execute it and verify PDFs are downloaded where available
5. Document any IS numbers that fail and investigate why

**Verification Method**:
- List all metadata.json files in storage/data/IS_*/ 
- Check each file's content for correct IS number and collection status
- List all PDF files in storage/data/IS_*/documents/ directories
- Verify SHA-256 hashes are present and valid

**Success Criteria**: 
- metadata.json exists for IS 2082:2018, IS 368:2014, IS 17150:2019, IS 302 (Part 2/Sec 21):2018, IS 302 (Part 2/Sec 35):2017
- At least IS 2082:2018 has product manual PDF downloaded (others may vary)
- No unhandled exceptions in execution logs

Let me know if you'd like me to proceed with Immediate Task 1, or if you have a different priority in mind.