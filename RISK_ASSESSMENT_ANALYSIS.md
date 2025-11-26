# Risk Assessment Analysis: Current Implementation

## Current Ground Truth Status

**There is NO ground truth for risk assessment currently.**

The system operates purely on **LLM-as-judge** methodology:

1. **No reference answers**: There are no "correct" answers or expected scores stored
2. **No expert evaluations**: No human expert evaluations to compare against
3. **No calibration data**: No historical data to calibrate scores
4. **Pure LLM evaluation**: The LLM acts as the sole evaluator

## How Risk Assessment Currently Works

### Step 1: Question Evaluation
For each of the 32 rubric questions:

1. **Prompt Creation** (`_create_evaluation_prompt`):
   - Takes the rubric question and guidance
   - Includes contract text (up to 15,000 chars)
   - Asks LLM to:
     - Answer the question
     - Score 1-5 (with criteria)
     - Provide reasoning
     - Assign risk level (LOW/MEDIUM/HIGH/CRITICAL)

2. **LLM Response**:
   - LLM analyzes contract text
   - Returns JSON with: `answer`, `score`, `reasoning`, `risk_level`
   - If JSON parsing fails, falls back to regex extraction

3. **Score Assignment**:
   - Score range: 1.0 to 5.0 (float)
   - Default on error: 3.0 (neutral)

### Step 2: Score Aggregation

1. **Category Scores**:
   - Average all question scores within each category
   - Calculate category risk level deterministically:
     - ≥4.5 → LOW
     - 3.5-4.4 → MEDIUM
     - 2.5-3.4 → HIGH
     - <2.5 → CRITICAL

2. **Overall Score**:
   - Average all 32 question scores
   - Calculate overall risk level using same thresholds

3. **Critical Risk Identification**:
   - Flag categories with HIGH or CRITICAL risk levels

## Current Limitations

### 1. No Validation
- No way to verify if LLM scores are accurate
- No comparison against expert evaluations
- No inter-rater reliability checks

### 2. LLM Variability
- Different LLM runs may produce different scores
- No consistency guarantees
- Temperature=0 helps but doesn't eliminate variability

### 3. No Calibration
- Scores are not calibrated against real-world outcomes
- No historical data to learn from
- No feedback loop to improve scoring

### 4. Subjective Scoring Criteria
- "Favorable to client" is subjective
- LLM may interpret criteria differently each time
- No standardized reference points

## Potential Improvements

### Option 1: Add Ground Truth Dataset
Create a dataset with:
- Contract examples
- Expert evaluations (scores for each question)
- Expected risk levels
- Use this to:
  - Validate LLM scores
  - Calibrate scoring
  - Measure accuracy

### Option 2: Multi-Judge Evaluation
- Use multiple LLM calls and average scores
- Or use different models and compare
- Reduces single-judge bias

### Option 3: Keyword-Based Validation
- Extract key terms/phrases that indicate risk
- Use deterministic keyword matching as baseline
- Compare LLM scores against keyword scores
- Flag discrepancies for review

### Option 4: Expert Review System
- Allow experts to review and correct LLM scores
- Build training dataset over time
- Fine-tune prompts based on expert feedback

### Option 5: Confidence Scoring
- Add confidence intervals to scores
- Flag low-confidence evaluations
- Request human review for uncertain cases

## Current Scoring Criteria (from prompt)

```
- 5 = Excellent/Comprehensive: Fully addresses the concern, very favorable to client
- 4 = Good: Addresses most concerns, generally favorable
- 3 = Acceptable: Basic coverage, neutral or mixed
- 2 = Poor: Missing important elements, unfavorable to client
- 1 = Critical: Major gaps or very unfavorable terms
```

## Risk Level Mapping

```
Score Range    → Risk Level
≥ 4.5         → LOW
3.5 - 4.4     → MEDIUM
2.5 - 3.4     → HIGH
< 2.5         → CRITICAL
```

## Recommendations

1. **Short-term**: Document the current approach and its limitations
2. **Medium-term**: Collect expert evaluations for a sample of contracts to create ground truth
3. **Long-term**: Implement hybrid evaluation (LLM + keywords + expert review)

