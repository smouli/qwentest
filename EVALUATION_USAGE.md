# Evaluation Pipeline Usage Guide

This evaluation pipeline provides both LLM-as-judge semantic matching and deterministic keyword-based scoring for Q&A pairs.

## Features

1. **LLM Judge**: Uses an LLM to evaluate semantic similarity between answers
2. **Keyword Scoring**: Deterministic keyword-based scoring using Jaccard similarity
3. **Combined Scoring**: Weighted combination of both methods
4. **Detailed Reports**: Comprehensive evaluation reports with reasoning

## Components

### 1. Evaluator Module (`evaluator.py`)

Main evaluation classes:
- `Evaluator`: Main evaluation pipeline
- `LLMJudge`: LLM-based semantic evaluation
- `KeywordScorer`: Deterministic keyword-based scoring
- `QAParser`: Parses Q&A pairs from markdown format

### 2. API Endpoints

#### POST `/api/evaluate`
Evaluate Q&A pairs from JSON content.

**Request Body:**
```json
{
  "ground_truth_content": "## SECTION 1.1\nQ1: Question?\nA1: Answer...",
  "generated_content": "## SECTION 1.1\nQ1: Question?\nA1: Generated answer...",
  "llm_weight": 0.7,
  "keyword_weight": 0.3
}
```

**Response:**
```json
{
  "status": "success",
  "evaluation": {
    "total_ground_truth_pairs": 10,
    "total_generated_pairs": 10,
    "matched_pairs": 9,
    "match_rate": 0.9,
    "average_llm_score": 0.85,
    "average_keyword_score": 0.78,
    "average_combined_score": 0.83,
    "results": [...]
  }
}
```

#### POST `/api/evaluate-file`
Evaluate Q&A pairs from uploaded files.

**Form Data:**
- `ground_truth_file`: Markdown file with ground truth Q&A pairs
- `generated_file`: Markdown file with generated Q&A pairs
- `llm_weight`: (optional, default: 0.7)
- `keyword_weight`: (optional, default: 0.3)

### 3. Command-Line Utility (`evaluate_document.py`)

Evaluate documents from the command line:

```bash
python evaluate_document.py ground_truth.md generated.md --output report.txt
```

**Options:**
- `--output, -o`: Save report to file (default: print to stdout)
- `--llm-weight`: Weight for LLM score (default: 0.7)
- `--keyword-weight`: Weight for keyword score (default: 0.3)
- `--json`: Output results as JSON

## Usage Examples

### Example 1: Command-Line Evaluation

```bash
# Basic evaluation
python evaluate_document.py BLUESTONE_Inter_Intel_MSA_QA.md generated_qa.md

# Save report to file
python evaluate_document.py BLUESTONE_Inter_Intel_MSA_QA.md generated_qa.md -o evaluation_report.txt

# Output JSON results
python evaluate_document.py BLUESTONE_Inter_Intel_MSA_QA.md generated_qa.md --json -o results.json

# Custom weights (more emphasis on keywords)
python evaluate_document.py BLUESTONE_Inter_Intel_MSA_QA.md generated_qa.md --llm-weight 0.5 --keyword-weight 0.5
```

### Example 2: Python API Usage

```python
from evaluator import Evaluator, EvaluatorSettings

# Initialize evaluator
evaluator = Evaluator(EvaluatorSettings())

# Read ground truth and generated content
with open('ground_truth.md', 'r') as f:
    gt_content = f.read()

with open('generated.md', 'r') as f:
    gen_content = f.read()

# Evaluate
results = evaluator.evaluate_document(
    ground_truth_content=gt_content,
    generated_content=gen_content,
    llm_weight=0.7,
    keyword_weight=0.3
)

# Generate report
report = evaluator.generate_report(results, output_path='report.txt')
print(f"Match Rate: {results['match_rate']:.2%}")
print(f"Average Score: {results['average_combined_score']:.3f}")
```

### Example 3: Evaluate Single Q&A Pair

```python
from evaluator import Evaluator, EvaluatorSettings

evaluator = Evaluator(EvaluatorSettings())

result = evaluator.evaluate_qa_pair(
    question="What is the definition of Affiliate?",
    ground_truth_answer="Affiliate means any entity Controlling or Controlled by...",
    generated_answer="An Affiliate is an entity that controls or is controlled...",
    llm_weight=0.7,
    keyword_weight=0.3
)

print(f"Combined Score: {result.combined_score:.3f}")
print(f"LLM Score: {result.llm_score:.3f}")
print(f"Keyword Score: {result.keyword_score:.3f}")
print(f"Matched Keywords: {result.matched_keywords}")
```

## Scoring Methodology

### LLM Score (0.0 - 1.0)
- **1.0**: Perfect match, all information present and correct
- **0.8-0.9**: Very good match, minor details missing
- **0.6-0.7**: Good match, some important details missing
- **0.4-0.5**: Partial match, core meaning somewhat preserved
- **0.2-0.3**: Poor match, only basic similarity
- **0.0-0.1**: No meaningful match

### Keyword Score (0.0 - 1.0)
Based on Jaccard similarity of keyword sets:
- Extracts meaningful keywords (length >= 4, excludes stopwords)
- Calculates intersection / union of keyword sets
- Provides deterministic, reproducible scoring

### Combined Score
Weighted average: `(llm_weight × llm_score) + (keyword_weight × keyword_score)`

Default weights: 70% LLM, 30% Keywords

## Q&A Format

The parser expects markdown format:

```markdown
## SECTION 1.1 — TITLE

Q1: What is the question?
A1: This is the answer.

Q2: Another question?
A2: Another answer.

---

## SECTION 1.2 — ANOTHER TITLE

Q1: Question here?
A1: Answer here.
```

## Output Format

### Evaluation Results Dictionary

```python
{
    "total_ground_truth_pairs": int,
    "total_generated_pairs": int,
    "matched_pairs": int,
    "match_rate": float,  # 0.0 to 1.0
    "average_llm_score": float,
    "average_keyword_score": float,
    "average_combined_score": float,
    "results": [
        {
            "question": str,
            "ground_truth_answer": str,
            "generated_answer": str,
            "llm_score": float,
            "keyword_score": float,
            "combined_score": float,
            "llm_judgment": str,
            "matched_keywords": List[str],
            "missing_keywords": List[str],
            "section": str
        },
        ...
    ],
    "unmatched_ground_truth": int,
    "unmatched_generated": int
}
```

## Tips

1. **Weight Tuning**: Adjust `llm_weight` and `keyword_weight` based on your needs:
   - Higher LLM weight: Better semantic understanding, but slower and less deterministic
   - Higher keyword weight: Faster, deterministic, but may miss semantic nuances

2. **Matching Threshold**: The system uses a 0.3 similarity threshold to match questions. You can modify this in the `evaluate_document` method if needed.

3. **Performance**: LLM evaluation can be slow for large documents. Consider:
   - Processing in batches
   - Using lower LLM weight for faster evaluation
   - Caching results

4. **Accuracy**: For best results:
   - Ensure consistent Q&A formatting
   - Use clear section headers
   - Match question numbering between ground truth and generated content

## Troubleshooting

**Issue**: Low match rate
- **Solution**: Check if question formats match between ground truth and generated content

**Issue**: LLM evaluation errors
- **Solution**: Check API key and server URL in settings

**Issue**: Keyword scores seem too low
- **Solution**: This is normal - keyword scoring is strict. Focus on combined score or adjust weights.

