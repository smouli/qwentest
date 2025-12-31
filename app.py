from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from langchain_openai import ChatOpenAI
from pydantic_settings import BaseSettings
from typing import Optional
from pydantic import BaseModel, ConfigDict
import PyPDF2
import io
import os
import uvicorn
import logging
import re
from evaluator import Evaluator, EvaluatorSettings
from rubric_evaluator import RubricEvaluator, RubricSettings
from msa_parser import MSAParser
from risk_assessor import RiskAssessor

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra="ignore")
    
    OPENAI_API_KEY: str
    OPEN_AI_MODEL: str = "gpt-4o"  # Using OpenAI's GPT-4o model
    OPENAI_TEMPERATURE: float = 0
    # Qwen model settings for MSA parsing
    QWEN_MODEL: str = "Qwen3-32B"
    QWEN_API_KEY: str = "sk-f91a49b77055e003e779c6429e509438"  # Optional, can use same as OpenAI key
    QWEN_INFERENCE_SERVER_URL: str = "https://llm-api.annotet.com"

settings = Settings()

# Initialize LangChain LLM with OpenAI API
llm = ChatOpenAI(
    model=settings.OPEN_AI_MODEL,
    temperature=settings.OPENAI_TEMPERATURE,
    openai_api_key=settings.OPENAI_API_KEY,
    timeout=600,  # 10 minutes timeout
    max_retries=2
)

# Initialize Qwen LLM for MSA parsing
qwen_api_key = settings.QWEN_API_KEY if settings.QWEN_API_KEY else settings.OPENAI_API_KEY
qwen_llm = ChatOpenAI(
    model=settings.QWEN_MODEL,
    temperature=settings.OPENAI_TEMPERATURE,
    openai_api_key=qwen_api_key,
    openai_api_base=settings.QWEN_INFERENCE_SERVER_URL,
    timeout=600,  # 10 minutes timeout
    max_retries=2
)

# Initialize evaluator
evaluator = Evaluator(EvaluatorSettings())

# Initialize rubric evaluator and load rubric
rubric_evaluator = RubricEvaluator(RubricSettings())
rubric_content = ""
try:
    with open("evaluation_rubric.txt", "r", encoding="utf-8") as f:
        rubric_content = f.read()
    logger.info("Loaded evaluation rubric")
except FileNotFoundError:
    logger.warning("evaluation_rubric.txt not found. Rubric evaluation will be disabled.")

# Initialize MSA parser with Qwen LLM
msa_parser = MSAParser(qwen_llm)
logger.info(f"MSA parser initialized with Qwen model: {settings.QWEN_MODEL}")

# Initialize Risk Assessor with OpenAI LLM (for risk assessment)
risk_assessor = RiskAssessor(llm)
logger.info("Risk assessor initialized")

app = FastAPI(title="PDF Chat Server")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# System prompt for contract parsing
CONTRACT_PARSING_PROMPT = """SYSTEM PROMPT: You are an advanced Contract Parsing AI designed for legal-grade deterministic extraction. Your task is to convert the contract into multi-Q&A pairs for every clause.

🔹 OBJECTIVE
For each clause (e.g., 1.1, 1.2, 3(a), 5(e)), generate multiple Q&A pairs that fully capture:
- the legal meaning
- operational implications
- obligations
- restrictions
- rights
- timelines
- triggers
- exceptions
- risks

🔹 OUTPUT FORMAT (MANDATORY)
For each clause:
SECTION X.X — [CLAUSE TITLE]
Q1: …
A1: …
Q2: …
A2: …
Q3: …
A3: …

🔹 RULES
- Multiple Q&A pairs per clause
  - Minimum: 2
  - Typical: 4–6
  - For long clauses: 8–10+
- No hallucination: Answers must come strictly from the contract text.
- Keep clause order: Preserve numbering (1.1, 1.2, 1.3… or 3(a), 3(b)…).
- Stay literal: Interpret clauses accurately, without adding legal interpretation beyond the text.
- Respect definitions: When terms are defined, apply the definition consistently.
- Focus on these elements (when applicable):
  - rights
  - obligations
  - deadlines
  - payment terms
  - IP ownership
  - indemnification
  - liability caps
  - confidentiality
  - compliance
  - breach consequences
  - exceptions
  - survival
- Do NOT:
  - summarize
  - paraphrase whole sections
  - merge clauses
  - give opinions
  - omit content
- High fidelity: Ensure every clause is represented fully and distinctly."""


def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF file content."""
    try:
        pdf_file = io.BytesIO(file_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error extracting PDF text: {str(e)}")


def chunk_text_by_sections(text: str, max_chunk_size: int = 8000) -> list:
    """
    Split text into chunks, trying to break at section boundaries (e.g., clause numbers).
    Ensures chunks never exceed max_chunk_size.
    """
    if len(text) <= max_chunk_size:
        return [text]
    
    chunks = []
    # Try to split by common section markers
    section_patterns = [
        r'\n\s*\d+\.\d+',  # 1.1, 2.3, etc.
        r'\n\s*\d+\([a-z]\)',  # 1(a), 2(b), etc.
        r'\n\s*SECTION\s+\d+',
        r'\n\s*Article\s+\d+',
        r'\n\s*Clause\s+\d+',
    ]
    
    # Find all potential split points
    split_points = [0]
    for pattern in section_patterns:
        for match in re.finditer(pattern, text):
            pos = match.start()
            # Only add split points that are reasonably spaced
            if pos > split_points[-1] + max_chunk_size // 3:
                split_points.append(pos)
    
    # Add end point
    split_points.append(len(text))
    
    # Sort and deduplicate split points
    split_points = sorted(set(split_points))
    
    # Create chunks, ensuring they don't exceed max size
    for i in range(len(split_points) - 1):
        start = split_points[i]
        end = split_points[i + 1]
        
        chunk = text[start:end]
        
        # If chunk exceeds max size, split it further by paragraphs
        while len(chunk) > max_chunk_size:
            # Find a good split point (preferably at paragraph boundary)
            split_at = max_chunk_size
            # Try to find paragraph boundary near max_chunk_size (within 40% of max)
            para_boundary = chunk.rfind('\n\n', max_chunk_size - int(max_chunk_size * 0.4), max_chunk_size)
            if para_boundary > max_chunk_size * 0.6:
                split_at = para_boundary + 2
            else:
                # Fall back to line break (within 30% of max)
                line_break = chunk.rfind('\n', max_chunk_size - int(max_chunk_size * 0.3), max_chunk_size)
                if line_break > max_chunk_size * 0.7:
                    split_at = line_break + 1
                else:
                    # Last resort: split at max_chunk_size
                    split_at = max_chunk_size
            
            chunks.append(chunk[:split_at].strip())
            chunk = chunk[split_at:].strip()
        
        if chunk:
            chunks.append(chunk.strip())
    
    # Final safety check: ensure no chunk exceeds max size
    final_chunks = []
    for chunk in chunks:
        if len(chunk) > max_chunk_size:
            # Force split at max_chunk_size
            while len(chunk) > max_chunk_size:
                final_chunks.append(chunk[:max_chunk_size].strip())
                chunk = chunk[max_chunk_size:].strip()
            if chunk:
                final_chunks.append(chunk.strip())
        else:
            final_chunks.append(chunk)
    
    return [c for c in final_chunks if c]  # Remove empty chunks


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main HTML page."""
    with open("static/index.html", "r") as f:
        return HTMLResponse(content=f.read())


@app.post("/api/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """Handle PDF upload and extract text."""
    if not file.filename or not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        file_content = await file.read()
        text = extract_text_from_pdf(file_content)
        
        return JSONResponse(content={
            "filename": file.filename,
            "text": text,
            "text_length": len(text),
            "status": "success"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")


@app.post("/api/chat")
async def chat_with_pdf(request: dict):
    """Send text to LLM and get response."""
    text = request.get("text", "")
    query = request.get("query", "")
    
    if not text:
        raise HTTPException(status_code=400, detail="No text provided")
    
    # Use default prompt if query is empty
    if not query:
        query = CONTRACT_PARSING_PROMPT
    
    try:
        # Combine query with extracted text
        prompt = f"{query}\n\nDocument:\n{text}"
        
        # Get response from LLM
        response = llm.invoke(prompt)
        
        return JSONResponse(content={
            "response": response.content if hasattr(response, 'content') else str(response),
            "status": "success"
        })
    except Exception as e:
        error_msg = str(e)
        # Handle timeout errors specifically
        if "timeout" in error_msg.lower() or "504" in error_msg or "gateway" in error_msg.lower():
            raise HTTPException(
                status_code=504, 
                detail=f"LLM request timed out. The document may be too large or the server is slow. Error: {error_msg}"
            )
        raise HTTPException(status_code=500, detail=f"Error getting LLM response: {str(e)}")


@app.post("/api/process-pdf")
async def process_pdf(
    file: UploadFile = File(...), 
    query: Optional[str] = None,
    evaluate_rubric: bool = True
):
    """Upload PDF, extract text, get LLM response, and automatically evaluate against rubric."""
    if not file.filename or not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        # Extract text from PDF
        file_content = await file.read()
        text = extract_text_from_pdf(file_content)
        
        # Default query if not provided
        if not query:
            query = CONTRACT_PARSING_PROMPT
        
        # Check document size and chunk if necessary
        text_length = len(text)
        word_count = len(text.split())
        logger.info(f"Processing document: {text_length} characters, {word_count} words")
        
        # Maximum safe size (leave room for prompt) - ~8k chars to avoid timeouts
        max_chunk_size = 8000
        chunks = chunk_text_by_sections(text, max_chunk_size) if text_length > max_chunk_size else [text]
        
        logger.info(f"Document split into {len(chunks)} chunk(s)")
        
        # Process chunks
        all_responses = []
        for i, chunk in enumerate(chunks, 1):
            logger.info(f"Processing chunk {i}/{len(chunks)} ({len(chunk)} characters)")
            prompt = f"{query}\n\nDocument Section {i}:\n{chunk}"
            
            try:
                response = llm.invoke(prompt)
                chunk_response = response.content if hasattr(response, 'content') else str(response)
                all_responses.append(f"=== SECTION {i} ===\n{chunk_response}\n")
            except Exception as llm_error:
                error_msg = str(llm_error)
                logger.error(f"LLM error on chunk {i}: {error_msg[:500]}")
                
                # Check for timeout/gateway errors - including HTML error pages
                error_lower = error_msg.lower()
                if any(keyword in error_lower for keyword in ["timeout", "504", "gateway", "timed out", "gateway time-out"]):
                    raise HTTPException(
                        status_code=504,
                        detail=f"LLM API timed out on chunk {i}/{len(chunks)}. "
                               f"Chunk size: {len(chunk)} characters. "
                               f"The document may still be too large even when chunked. "
                               f"The upstream LLM server (nginx) returned a 504 Gateway Timeout. "
                               f"Error details: {error_msg[:300]}"
                    )
                # Re-raise other errors
                raise
        
        # Combine all responses
        combined_response = "\n".join(all_responses)
        
        response_data = {
            "filename": file.filename,
            "text_length": text_length,
            "chunks_processed": len(chunks),
            "query": query[:100] + "..." if len(query) > 100 else query,
            "response": combined_response,
            "status": "success"
        }
        
        # Automatically evaluate against rubric if enabled and rubric is loaded
        if evaluate_rubric and rubric_content:
            try:
                logger.info("Evaluating contract against rubric...")
                risk_assessment = rubric_evaluator.evaluate_contract(
                    contract_text=text,
                    rubric_content=rubric_content
                )
                response_data["risk_assessment"] = risk_assessment.to_dict()
                logger.info(f"Rubric evaluation complete. Overall score: {risk_assessment.overall_score:.2f}, Risk: {risk_assessment.overall_risk_level}")
            except Exception as e:
                logger.error(f"Error in rubric evaluation: {str(e)}")
                response_data["risk_assessment"] = {
                    "error": f"Could not evaluate rubric: {str(e)}",
                    "overall_score": None,
                    "overall_risk_level": "UNKNOWN"
                }
        
        return JSONResponse(content=response_data)
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Unexpected error: {error_msg[:500]}")
        
        # Handle timeout errors specifically - check for HTML error pages too
        error_lower = error_msg.lower()
        if any(keyword in error_lower for keyword in ["timeout", "504", "gateway", "timed out", "gateway time-out"]):
            raise HTTPException(
                status_code=504, 
                detail=f"LLM request timed out. The document may be too large or the server is slow. Error: {error_msg[:500]}"
            )
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)[:500]}")


# Evaluation request models
class EvaluationRequest(BaseModel):
    ground_truth_content: str
    generated_content: str
    llm_weight: float = 0.7
    keyword_weight: float = 0.3


@app.post("/api/evaluate")
async def evaluate_qa_pairs(request: EvaluationRequest):
    """Evaluate generated Q&A pairs against ground truth"""
    try:
        results = evaluator.evaluate_document(
            ground_truth_content=request.ground_truth_content,
            generated_content=request.generated_content,
            llm_weight=request.llm_weight,
            keyword_weight=request.keyword_weight
        )
        
        return JSONResponse(content={
            "status": "success",
            "evaluation": results
        })
    except Exception as e:
        logger.error(f"Error in evaluation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error evaluating Q&A pairs: {str(e)}")


@app.post("/api/evaluate-file")
async def evaluate_from_file(
    ground_truth_file: UploadFile = File(...),
    generated_file: UploadFile = File(...),
    llm_weight: float = 0.7,
    keyword_weight: float = 0.3
):
    """Evaluate Q&A pairs from uploaded files"""
    try:
        # Read ground truth file
        gt_content = (await ground_truth_file.read()).decode('utf-8')
        
        # Read generated file
        gen_content = (await generated_file.read()).decode('utf-8')
        
        # Evaluate
        results = evaluator.evaluate_document(
            ground_truth_content=gt_content,
            generated_content=gen_content,
            llm_weight=llm_weight,
            keyword_weight=keyword_weight
        )
        
        # Generate report
        report = evaluator.generate_report(results)
        
        return JSONResponse(content={
            "status": "success",
            "evaluation": results,
            "report": report
        })
    except Exception as e:
        logger.error(f"Error in file evaluation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error evaluating files: {str(e)}")


@app.post("/api/evaluate-rubric")
async def evaluate_rubric_endpoint(file: UploadFile = File(...)):
    """Evaluate a PDF contract against the rubric"""
    if not file.filename or not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    if not rubric_content:
        raise HTTPException(status_code=500, detail="Evaluation rubric not loaded")
    
    try:
        # Extract text from PDF
        file_content = await file.read()
        text = extract_text_from_pdf(file_content)
        
        # Evaluate against rubric
        logger.info(f"Evaluating {file.filename} against rubric...")
        risk_assessment = rubric_evaluator.evaluate_contract(
            contract_text=text,
            rubric_content=rubric_content
        )
        
        return JSONResponse(content={
            "status": "success",
            "filename": file.filename,
            "risk_assessment": risk_assessment.to_dict()
        })
    except Exception as e:
        logger.error(f"Error in rubric evaluation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error evaluating rubric: {str(e)}")


@app.post("/api/parse-msa")
async def parse_msa(file: UploadFile = File(...)):
    """
    Parse an MSA PDF document and extract structured data according to the MSA schema.
    
    Returns:
        JSON object containing structured MSA data matching the predefined schema
    """
    if not file.filename or not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    text_length = 0
    try:
        # Extract text from PDF
        file_content = await file.read()
        text = extract_text_from_pdf(file_content)
        
        text_length = len(text)
        word_count = len(text.split())
        logger.info(f"Parsing MSA document: {file.filename} ({text_length} characters, {word_count} words)")
        
        # Warn if document is very large
        if text_length > 50000:
            logger.warning(f"Large document detected ({text_length} chars). Processing may take longer or timeout.")
        
        # Parse MSA using the parser
        msa_data = msa_parser.parse(text)
        
        return JSONResponse(content={
            "status": "success",
            "filename": file.filename,
            "text_length": text_length,
            "msa_data": msa_data
        })
    except ValueError as e:
        logger.error(f"Validation error in MSA parsing: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error parsing MSA: {str(e)}")
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error parsing MSA: {error_msg}")
        
        # Check for timeout errors
        error_lower = error_msg.lower()
        if any(keyword in error_lower for keyword in ["timeout", "504", "gateway", "timed out", "gateway time-out"]):
            size_info = f" ({text_length} characters)" if text_length > 0 else ""
            raise HTTPException(
                status_code=504,
                detail=f"LLM request timed out. The document may be too large{size_info}. "
                       f"Try processing a smaller document or contact support. Error: {error_msg[:300]}"
            )
        raise HTTPException(status_code=500, detail=f"Error parsing MSA: {str(e)[:500]}")


@app.post("/api/assess-risk")
async def assess_risk(msa_data: dict):
    """
    Assess compliance risk for an MSA by analyzing each clause in parallel.
    
    Takes the JSON output from /api/parse-msa and assesses risk for each clause
    using clause-specific prompts, then combines results.
    
    Returns:
        JSON object with overall compliance score and per-clause assessments
    """
    try:
        logger.info("=" * 80)
        logger.info("Risk Assessment Request Received")
        logger.info("=" * 80)
        logger.info(f"Received MSA data keys: {list(msa_data.keys()) if isinstance(msa_data, dict) else 'Not a dict'}")
        
        # Assess MSA risk (parallel processing)
        assessment_result = await risk_assessor.assess_msa(msa_data)
        
        # Convert to dict for JSON response
        result_dict = {
            "status": "success",
            "overall_compliance_score": assessment_result.overall_compliance_score,
            "overall_risk_level": assessment_result.overall_risk_level,
            "structure_completeness": assessment_result.structure_completeness,
            "missing_clauses_count": assessment_result.missing_clauses_count,
            "summary": assessment_result.summary,
            "clause_assessments": [
                {
                    "clause_name": assessment.clause_name,
                    "compliance_score": assessment.compliance_score,
                    "risk_level": assessment.risk_level,
                    "risk_factors": assessment.risk_factors,
                    "recommendations": assessment.recommendations,
                    "details": assessment.details
                }
                for assessment in assessment_result.clause_assessments
            ]
        }
        
        return JSONResponse(content=result_dict)
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error assessing MSA risk: {error_msg}")
        raise HTTPException(status_code=500, detail=f"Error assessing risk: {error_msg[:500]}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=6969)

