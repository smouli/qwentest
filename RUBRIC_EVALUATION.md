# Rubric-Based Contract Evaluation

The application now automatically evaluates uploaded PDF contracts against a comprehensive rubric and returns risk scores.

## How It Works

When you upload a PDF through `/api/process-pdf`, the system will:

1. **Extract text** from the PDF
2. **Generate Q&A pairs** using the contract parsing prompt
3. **Automatically evaluate** the contract against 8 risk categories (32 questions total)
4. **Calculate risk scores** for each category and overall
5. **Return risk assessment** along with the Q&A pairs

## Risk Categories

The rubric evaluates contracts across 8 categories:

1. **🟥 LIABILITY STRUCTURE** (1-5)
   - Liability caps, carve-outs, damage classifications

2. **🟧 INDEMNIFICATION** (1-5)
   - Indemnification scope, IP protection, regulatory claims

3. **🟨 IP OWNERSHIP** (1-5)
   - Work product ownership, pre-existing IP, assignment mechanisms

4. **🟩 CONFIDENTIALITY & DATA HANDLING** (1-5)
   - Confidentiality obligations, data security, GDPR compliance

5. **🟦 INSURANCE** (1-5)
   - Insurance requirements, coverage limits, additional insured status

6. **🟫 OPERATIONAL PERFORMANCE** (1-5)
   - SLAs, acceptance criteria, subcontractor restrictions

7. **⬛ TERMINATION & SURVIVAL** (1-5)
   - Termination rights, survival clauses, data return obligations

8. **⬜ COMMERCIAL RESTRICTIONS** (1-5)
   - Non-solicitation, publicity restrictions, assignment rights

## Scoring System

Each question is scored on a **1-5 scale**:
- **5** = Excellent/Comprehensive: Fully addresses the concern, very favorable to client
- **4** = Good: Addresses most concerns, generally favorable
- **3** = Acceptable: Basic coverage, neutral or mixed
- **2** = Poor: Missing important elements, unfavorable to client
- **1** = Critical: Major gaps or very unfavorable terms

### Risk Levels

- **LOW** (score ≥ 4.5): Low risk, favorable terms
- **MEDIUM** (score 3.5-4.4): Moderate risk, acceptable terms
- **HIGH** (score 2.5-3.4): High risk, unfavorable terms
- **CRITICAL** (score < 2.5): Critical risk, major concerns

## API Response Format

When you upload a PDF, the response includes a `risk_assessment` object:

```json
{
  "filename": "contract.pdf",
  "response": "...Q&A pairs...",
  "risk_assessment": {
    "overall_score": 3.8,
    "overall_risk_level": "MEDIUM",
    "total_questions": 32,
    "answered_questions": 32,
    "critical_risks": ["LIABILITY STRUCTURE", "INDEMNIFICATION"],
    "category_scores": [
      {
        "category": "LIABILITY STRUCTURE",
        "category_number": 1,
        "average_score": 2.5,
        "risk_level": "HIGH",
        "questions": [
          {
            "question": "Does the contract include a liability cap...",
            "answer": "Yes, the contract includes...",
            "score": 2.5,
            "reasoning": "...",
            "risk_level": "HIGH"
          },
          ...
        ]
      },
      ...
    ]
  }
}
```

## API Endpoints

### 1. Process PDF with Automatic Rubric Evaluation

```bash
POST /api/process-pdf
Content-Type: multipart/form-data

file: <PDF file>
evaluate_rubric: true (default)
```

**Response**: Includes Q&A pairs AND risk assessment

### 2. Evaluate Rubric Only

```bash
POST /api/evaluate-rubric
Content-Type: multipart/form-data

file: <PDF file>
```

**Response**: Only risk assessment (no Q&A pairs)

### 3. Process PDF without Rubric Evaluation

```bash
POST /api/process-pdf
Content-Type: multipart/form-data

file: <PDF file>
evaluate_rubric: false
```

**Response**: Only Q&A pairs (no risk assessment)

## Example Usage

### Python

```python
import requests

# Upload PDF and get risk assessment
with open('contract.pdf', 'rb') as f:
    files = {'file': f}
    data = {'evaluate_rubric': 'true'}
    response = requests.post('http://localhost:6969/api/process-pdf', files=files, data=data)
    
result = response.json()
risk_assessment = result['risk_assessment']

print(f"Overall Score: {risk_assessment['overall_score']:.2f}")
print(f"Risk Level: {risk_assessment['overall_risk_level']}")
print(f"Critical Risks: {', '.join(risk_assessment['critical_risks'])}")

# Print category scores
for category in risk_assessment['category_scores']:
    print(f"\n{category['category']}: {category['average_score']:.2f} ({category['risk_level']})")
```

### cURL

```bash
# Upload PDF with rubric evaluation
curl -X POST "http://localhost:6969/api/process-pdf" \
  -F "file=@contract.pdf" \
  -F "evaluate_rubric=true"

# Evaluate rubric only
curl -X POST "http://localhost:6969/api/evaluate-rubric" \
  -F "file=@contract.pdf"
```

## Understanding the Scores

### Overall Score Interpretation

- **4.5-5.0**: Excellent contract, very favorable to client
- **3.5-4.4**: Good contract, generally acceptable
- **2.5-3.4**: Poor contract, needs review and negotiation
- **1.0-2.4**: Critical issues, significant risk

### Critical Risks

Categories with HIGH or CRITICAL risk levels are flagged in the `critical_risks` array. These areas require immediate attention and may need contract amendments.

## Customization

The rubric questions are defined in `evaluation_rubric.txt`. You can modify this file to:
- Add new questions
- Change evaluation criteria
- Adjust category focus

After modifying the rubric file, restart the server to load the new rubric.

## Performance Notes

- Rubric evaluation adds processing time (approximately 30-60 seconds per question)
- For 32 questions, expect 15-30 minutes total evaluation time
- The system processes questions sequentially to avoid overwhelming the LLM API
- Consider using `evaluate_rubric=false` for faster Q&A generation if risk assessment isn't needed

## Troubleshooting

**Issue**: Rubric evaluation not running
- **Solution**: Check that `evaluation_rubric.txt` exists in the project root

**Issue**: Evaluation taking too long
- **Solution**: This is normal for 32 questions. Consider evaluating specific categories only by modifying the rubric file.

**Issue**: Low scores across all categories
- **Solution**: This may indicate the contract has significant gaps. Review the detailed answers and reasoning for each question.


