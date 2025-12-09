# Risk Assessment System Architecture

## Overview

The Risk Assessment System analyzes MSA (Master Service Agreement) documents by breaking them into clauses and assessing compliance risk for each clause in parallel using clause-specific prompts.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (index.html)                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Mode Selection:                                          │  │
│  │  • Parse MSA → Extract structured JSON                    │  │
│  │  • Assess Risk → Analyze compliance risk                   │  │
│  └──────────────────────────────────────────────────────────┘  │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        │ HTTP POST
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (app.py)                      │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  /api/parse-msa                                          │   │
│  │  • Upload PDF                                            │   │
│  │  • Extract text                                          │   │
│  │  • Parse into structured JSON                            │   │
│  │  • Return: {"msa_data": {...}}                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                        │                                         │
│                        │ JSON Output                             │
│                        ▼                                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  /api/assess-risk                                        │   │
│  │  • Receives MSA JSON                                     │   │
│  │  • Orchestrator Agent                                    │   │
│  └──────────────────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        │ Parallel Processing
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│              Risk Assessor (risk_assessor.py)                   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Clause Extraction                                        │   │
│  │  • Extract 10 clauses from MSA JSON                      │   │
│  │  • Map to clause-specific prompts                        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                        │                                         │
│                        │ Parallel Execution                      │
│                        ▼                                         │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐      │
│  │ Clause 1 │ Clause 2 │ Clause 3 │ Clause 4 │ ...      │      │
│  │ Prompt   │ Prompt   │ Prompt   │ Prompt   │          │      │
│  └────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬─────┘      │
│       │          │          │          │          │             │
│       │          │          │          │          │             │
│       ▼          ▼          ▼          ▼          ▼             │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐      │
│  │ LLM      │ LLM      │ LLM      │ LLM      │ LLM      │      │
│  │ Call     │ Call     │ Call     │ Call     │ Call     │      │
│  └────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬─────┘      │
│       │          │          │          │          │             │
│       │          │          │          │          │             │
│       ▼          ▼          ▼          ▼          ▼             │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐      │
│  │ Risk     │ Risk     │ Risk     │ Risk     │ Risk     │      │
│  │ Score    │ Score    │ Score    │ Score    │ Score    │      │
│  │ Factors  │ Factors  │ Factors  │ Factors  │ Factors  │      │
│  └────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬─────┘      │
│       │          │          │          │          │             │
│       └──────────┴──────────┴──────────┴──────────┘             │
│                        │                                         │
│                        │ Aggregate Results                       │
│                        ▼                                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Result Aggregation                                      │   │
│  │  • Calculate overall compliance score                    │   │
│  │  • Determine overall risk level                          │   │
│  │  • Generate summary                                      │   │
│  └──────────────────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        │ Structured Response
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Response Format                               │
│  {                                                               │
│    "overall_compliance_score": 75.5,                            │
│    "overall_risk_level": "MEDIUM",                              │
│    "summary": "...",                                             │
│    "clause_assessments": [                                       │
│      {                                                           │
│        "clause_name": "commercial_terms",                       │
│        "compliance_score": 80.0,                                │
│        "risk_level": "LOW",                                      │
│        "risk_factors": [...],                                    │
│        "recommendations": [...],                                 │
│        "details": {...}                                          │
│      },                                                          │
│      ...                                                         │
│    ]                                                             │
│  }                                                               │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Frontend (`static/index.html`)
- **Mode Selection**: Choose between parsing MSA or assessing risk
- **MSA JSON Input**: Textarea for pasting parsed MSA JSON
- **Risk Assessment Display**: Visual dashboard showing:
  - Overall compliance score (0-100)
  - Overall risk level (LOW/MEDIUM/HIGH/CRITICAL)
  - Per-clause scores and risk levels
  - Risk factors and recommendations

### 2. Backend API (`app.py`)
- **`/api/parse-msa`**: Parses PDF into structured MSA JSON
- **`/api/assess-risk`**: Orchestrates parallel risk assessment

### 3. Risk Assessor (`risk_assessor.py`)
- **Clause Extraction**: Identifies and extracts clauses from MSA JSON
- **Parallel Processing**: Uses `asyncio.gather()` to process all clauses simultaneously
- **Clause-Specific Prompts**: Each clause has a specialized prompt with:
  - Domain expertise (e.g., "commercial terms expert")
  - Risk factors to consider
  - Scoring criteria
  - Expected output format

### 4. LLM Integration
- Uses OpenAI GPT-4o for risk assessment
- Each clause assessment is independent
- Returns structured JSON with:
  - Compliance score (0-100)
  - Risk level
  - Risk factors
  - Recommendations
  - Additional details

## Clause Types Assessed

1. **commercial_terms** - Payment terms, pricing, discounts, taxes
2. **liability_indemnification** - Liability caps, indemnification scope
3. **intellectual_property** - IP ownership, licenses, pre-existing IP
4. **data_protection** - GDPR, breach notification, data retention
5. **compliance_requirements** - Regulatory compliance, import/export
6. **warranties** - Service warranties, SLAs, performance standards
7. **termination** - Termination rights, notice periods, survival clauses
8. **dispute_resolution** - Arbitration, litigation, venue, fees
9. **confidentiality** - NDA terms, confidentiality periods
10. **insurance** - Coverage requirements, amounts

## Data Flow

1. **User uploads PDF** → `/api/parse-msa`
2. **MSA Parser extracts structured data** → Returns JSON
3. **User pastes JSON** → `/api/assess-risk`
4. **Risk Assessor extracts clauses** → Identifies 10 clause types
5. **Parallel LLM calls** → Each clause assessed simultaneously
6. **Results aggregated** → Overall score calculated
7. **Response returned** → Frontend displays results

## Performance

- **Parallel Processing**: All clause assessments run simultaneously
- **Typical Time**: ~10-30 seconds for 10 clauses (depends on LLM response time)
- **Scalability**: Can handle any number of clauses (currently 10)

## Risk Scoring

- **Compliance Score**: 0-100 (higher is better)
- **Risk Levels**:
  - **LOW**: Score ≥ 75, minimal risk factors
  - **MEDIUM**: Score 50-74, some risk factors
  - **HIGH**: Score 25-49, significant risk factors
  - **CRITICAL**: Score < 25 or critical risk factors present

## Example Usage

```bash
# 1. Parse MSA
curl -X POST "http://localhost:6969/api/parse-msa" \
  -F "file=@msa.pdf"

# 2. Assess Risk (using parsed JSON)
curl -X POST "http://localhost:6969/api/assess-risk" \
  -H "Content-Type: application/json" \
  -d '{"MASTER_SERVICE_AGREEMENT": {...}}'
```

## Frontend Workflow

1. Select "Parse MSA" mode
2. Upload PDF → Get structured JSON
3. Copy JSON output
4. Select "Assess Risk" mode
5. Paste JSON → Click "Assess Risk"
6. View results:
   - Overall compliance score
   - Per-clause breakdown
   - Risk factors
   - Recommendations

