"""
Risk Assessment Module for MSA Clauses
Assesses compliance risk for each clause in parallel using clause-specific prompts.
"""

import json
import logging
import asyncio
import re
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ClauseRiskAssessment(BaseModel):
    """Risk assessment result for a single clause."""
    clause_name: str
    compliance_score: float  # 0-100, higher is better
    risk_level: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    risk_factors: List[str]
    recommendations: List[str]
    details: Dict[str, Any]


class RiskAssessmentResult(BaseModel):
    """Overall risk assessment result."""
    overall_compliance_score: float
    overall_risk_level: str
    clause_assessments: List[ClauseRiskAssessment]
    summary: str


# Clause-specific risk assessment prompts
CLAUSE_PROMPTS = {
    "commercial_terms": """You are an expert contract risk assessor specializing in commercial terms and pricing structures.

Analyze the commercial terms section of this MSA and assess compliance risk based on:
1. Payment terms (due days, late fees, interest rates)
2. Rate cards and pricing transparency
3. Volume discounts and pricing fairness
4. Expense reimbursement policies
5. Tax provisions and responsibilities
6. Fee structures and surcharges

RISK FACTORS TO CONSIDER:
- Payment terms > 60 days = HIGH RISK
- Missing late payment penalties = MEDIUM RISK
- Unclear pricing structures = MEDIUM-HIGH RISK
- Customer responsible for all taxes = MEDIUM RISK
- No volume discounts for large contracts = LOW-MEDIUM RISK
- High expense markups (>20%) = MEDIUM RISK
- Missing accepted payment methods = LOW RISK

Return a JSON object with:
{
    "compliance_score": <0-100>,
    "risk_level": "<LOW|MEDIUM|HIGH|CRITICAL>",
    "risk_factors": ["list of specific risk factors"],
    "recommendations": ["list of recommendations"],
    "details": {additional structured details}
}""",

    "liability_indemnification": """You are an expert contract risk assessor specializing in liability and indemnification clauses.

Analyze the liability and indemnification section and assess compliance risk based on:
1. Liability caps and limitations
2. Indemnification scope and mutual vs one-sided
3. Exclusions from liability limitations
4. Defense obligations
5. Notice requirements

RISK FACTORS TO CONSIDER:
- Liability cap < $1M or very low = HIGH RISK
- One-sided indemnification (only provider indemnifies) = HIGH RISK
- Missing exclusions for gross negligence/willful misconduct = CRITICAL RISK
- No defense obligations = MEDIUM RISK
- Unclear notice requirements = LOW-MEDIUM RISK
- Liability cap based on fees (good) vs fixed amount = LOWER RISK
- Missing IP infringement indemnification = HIGH RISK

Return a JSON object with:
{
    "compliance_score": <0-100>,
    "risk_level": "<LOW|MEDIUM|HIGH|CRITICAL>",
    "risk_factors": ["list of specific risk factors"],
    "recommendations": ["list of recommendations"],
    "details": {additional structured details}
}""",

    "intellectual_property": """You are an expert contract risk assessor specializing in intellectual property rights.

Analyze the intellectual property section and assess compliance risk based on:
1. IP ownership model (work for hire, customer owned, provider owned)
2. License grants and scope
3. Pre-existing IP handling
4. Deliverable ownership

RISK FACTORS TO CONSIDER:
- Provider retains ownership of deliverables = HIGH RISK
- Unclear IP ownership = HIGH RISK
- Missing license grants = HIGH RISK
- Pre-existing IP not properly addressed = MEDIUM RISK
- No perpetual license for deliverables = MEDIUM RISK
- Customer owns all IP (work for hire) = LOW RISK
- Clear license grants with proper scope = LOW RISK

Return a JSON object with:
{
    "compliance_score": <0-100>,
    "risk_level": "<LOW|MEDIUM|HIGH|CRITICAL>",
    "risk_factors": ["list of specific risk factors"],
    "recommendations": ["list of recommendations"],
    "details": {additional structured details}
}""",

    "data_protection": """You are an expert contract risk assessor specializing in data protection and privacy compliance.

Analyze the data protection section and assess compliance risk based on:
1. Applicable regulations (GDPR, CCPA, HIPAA, etc.)
2. Data processing agreements
3. Data location restrictions
4. Breach notification requirements
5. Data retention policies

RISK FACTORS TO CONSIDER:
- Missing GDPR compliance for EU data = CRITICAL RISK
- No breach notification period specified = HIGH RISK
- No data location restrictions = MEDIUM RISK
- Missing DPA requirement = HIGH RISK
- Breach notification > 72 hours = HIGH RISK
- No data retention policy = MEDIUM RISK
- Multiple regulations properly addressed = LOW RISK

Return a JSON object with:
{
    "compliance_score": <0-100>,
    "risk_level": "<LOW|MEDIUM|HIGH|CRITICAL>",
    "risk_factors": ["list of specific risk factors"],
    "recommendations": ["list of recommendations"],
    "details": {additional structured details}
}""",

    "compliance_requirements": """You are an expert contract risk assessor specializing in regulatory compliance.

Analyze the compliance requirements section and assess compliance risk based on:
1. Regulatory compliance (GDPR, HIPAA, SOX, PCI DSS, etc.)
2. Import/export compliance
3. Hazmat provisions
4. Industry-specific requirements

RISK FACTORS TO CONSIDER:
- Missing regulatory compliance requirements = HIGH RISK
- No export control compliance = MEDIUM-HIGH RISK
- Missing industry-specific compliance = HIGH RISK
- Hazmat provisions missing when needed = CRITICAL RISK
- Unclear compliance responsibilities = MEDIUM RISK
- Comprehensive compliance coverage = LOW RISK

Return a JSON object with:
{
    "compliance_score": <0-100>,
    "risk_level": "<LOW|MEDIUM|HIGH|CRITICAL>",
    "risk_factors": ["list of specific risk factors"],
    "recommendations": ["list of recommendations"],
    "details": {additional structured details}
}""",

    "warranties": """You are an expert contract risk assessor specializing in warranties and service level agreements.

Analyze the warranties section and assess compliance risk based on:
1. Service warranties and periods
2. Performance standards and SLAs
3. Availability SLAs
4. Response and resolution time SLAs
5. Warranty disclaimers

RISK FACTORS TO CONSIDER:
- Missing SLAs = HIGH RISK
- No availability SLA = HIGH RISK
- Response time SLA > 24 hours = MEDIUM RISK
- No warranty period specified = MEDIUM RISK
- Overly broad warranty disclaimers = MEDIUM RISK
- Comprehensive SLAs with clear metrics = LOW RISK
- No performance standards = HIGH RISK

Return a JSON object with:
{
    "compliance_score": <0-100>,
    "risk_level": "<LOW|MEDIUM|HIGH|CRITICAL>",
    "risk_factors": ["list of specific risk factors"],
    "recommendations": ["list of recommendations"],
    "details": {additional structured details}
}""",

    "termination": """You are an expert contract risk assessor specializing in termination provisions.

Analyze the termination section and assess compliance risk based on:
1. Termination for convenience rights
2. Notice periods
3. Cure periods
4. Termination for cause grounds
5. Survival clauses

RISK FACTORS TO CONSIDER:
- No termination for convenience = HIGH RISK
- Notice period < 30 days = MEDIUM RISK
- Cure period < 30 days = MEDIUM RISK
- Unclear termination grounds = MEDIUM RISK
- Missing survival clauses = HIGH RISK
- One-sided termination rights = HIGH RISK
- Clear mutual termination rights = LOW RISK

Return a JSON object with:
{
    "compliance_score": <0-100>,
    "risk_level": "<LOW|MEDIUM|HIGH|CRITICAL>",
    "risk_factors": ["list of specific risk factors"],
    "recommendations": ["list of recommendations"],
    "details": {additional structured details}
}""",

    "dispute_resolution": """You are an expert contract risk assessor specializing in dispute resolution mechanisms.

Analyze the dispute resolution section and assess compliance risk based on:
1. Dispute resolution method (litigation, arbitration, mediation)
2. Arbitration rules (AAA, JAMS, ICC, etc.)
3. Venue and jurisdiction
4. Escalation process
5. Attorneys fees provisions

RISK FACTORS TO CONSIDER:
- Litigation in unfavorable jurisdiction = HIGH RISK
- No escalation process = MEDIUM RISK
- Unclear arbitration rules = MEDIUM RISK
- "Each party bears own fees" = MEDIUM RISK
- No venue specified = HIGH RISK
- Arbitration with clear rules = LOW-MEDIUM RISK
- Prevailing party gets fees = LOW RISK

Return a JSON object with:
{
    "compliance_score": <0-100>,
    "risk_level": "<LOW|MEDIUM|HIGH|CRITICAL>",
    "risk_factors": ["list of specific risk factors"],
    "recommendations": ["list of recommendations"],
    "details": {additional structured details}
}""",

    "confidentiality": """You are an expert contract risk assessor specializing in confidentiality and non-disclosure provisions.

Analyze the confidentiality section and assess compliance risk based on:
1. Mutual vs one-sided NDA
2. Confidentiality period
3. Exceptions to confidentiality
4. Return/destruction requirements

RISK FACTORS TO CONSIDER:
- One-sided confidentiality = HIGH RISK
- No confidentiality period specified = MEDIUM RISK
- Confidentiality period < 2 years = MEDIUM RISK
- Missing standard exceptions = MEDIUM RISK
- No return/destruction requirements = MEDIUM RISK
- Mutual NDA with proper exceptions = LOW RISK

Return a JSON object with:
{
    "compliance_score": <0-100>,
    "risk_level": "<LOW|MEDIUM|HIGH|CRITICAL>",
    "risk_factors": ["list of specific risk factors"],
    "recommendations": ["list of recommendations"],
    "details": {additional structured details}
}""",

    "insurance": """You are an expert contract risk assessor specializing in insurance requirements.

Analyze the insurance section and assess compliance risk based on:
1. General liability insurance
2. Professional liability/E&O insurance
3. Cyber liability insurance
4. Workers compensation
5. Coverage amounts

RISK FACTORS TO CONSIDER:
- Missing general liability = HIGH RISK
- Missing professional liability = HIGH RISK
- Coverage < $1M = MEDIUM RISK
- Missing cyber liability = MEDIUM-HIGH RISK
- No workers comp = HIGH RISK
- Comprehensive coverage with adequate amounts = LOW RISK

Return a JSON object with:
{
    "compliance_score": <0-100>,
    "risk_level": "<LOW|MEDIUM|HIGH|CRITICAL>",
    "risk_factors": ["list of specific risk factors"],
    "recommendations": ["list of recommendations"],
    "details": {additional structured details}
}""",
}


class RiskAssessor:
    """Risk assessor for MSA clauses."""
    
    def __init__(self, llm: ChatOpenAI):
        """
        Initialize the Risk Assessor.
        
        Args:
            llm: LangChain LLM instance for risk assessment
        """
        self.llm = llm
        self.clause_prompts = CLAUSE_PROMPTS
    
    def _extract_clauses(self, msa_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract individual clauses from MSA data."""
        clauses = {}
        
        # Extract top-level clauses
        clause_mapping = {
            "commercial_terms": "commercial_terms",
            "liability_indemnification": "liability_indemnification",
            "intellectual_property": "intellectual_property",
            "data_protection": "data_protection",
            "compliance_requirements": "compliance_requirements",
            "warranties": "warranties",
            "termination": "termination",
            "dispute_resolution": "dispute_resolution",
            "confidentiality": "confidentiality",
            "insurance": "insurance",
        }
        
        # Handle both wrapped and unwrapped formats
        # First try to get MASTER_SERVICE_AGREEMENT, if not found, use msa_data directly
        if "MASTER_SERVICE_AGREEMENT" in msa_data:
            msa_content = msa_data["MASTER_SERVICE_AGREEMENT"]
            # Handle double-wrapping (in case it's nested)
            if isinstance(msa_content, dict) and "MASTER_SERVICE_AGREEMENT" in msa_content:
                logger.info("Detected double-wrapping, extracting inner MASTER_SERVICE_AGREEMENT")
                msa_content = msa_content["MASTER_SERVICE_AGREEMENT"]
        else:
            msa_content = msa_data
        
        # Debug logging
        logger.info(f"MSA content type: {type(msa_content)}")
        if isinstance(msa_content, dict):
            all_keys = list(msa_content.keys())
            logger.info(f"MSA content has {len(all_keys)} keys. First 15 keys: {all_keys[:15]}")
            # Check if any of our target clauses exist
            clause_keys_found = [k for k in clause_mapping.values() if k in msa_content]
            logger.info(f"Found {len(clause_keys_found)} target clause keys: {clause_keys_found[:10]}")
        else:
            logger.error(f"MSA content is not a dict: {type(msa_content)}")
            return clauses
        
        for clause_key, clause_path in clause_mapping.items():
            # Check if clause exists in the structure (even if null)
            if clause_path in msa_content:
                clause_data = msa_content.get(clause_path)
                # Include clause even if null - we'll assess it as missing
                clauses[clause_key] = clause_data if clause_data is not None else {}
                has_data = clause_data is not None and clause_data != {}
                logger.info(f"✓ Found clause '{clause_key}' ({clause_path}): {'has data' if has_data else 'null/empty'}")
            else:
                logger.warning(f"✗ Clause '{clause_key}' ({clause_path}) NOT found in MSA content")
        
        if len(clauses) == 0:
            logger.error("=" * 80)
            logger.error("WARNING: No clauses extracted! Available keys in MSA content:")
            if isinstance(msa_content, dict):
                for key in list(msa_content.keys())[:20]:
                    value_type = type(msa_content[key]).__name__
                    logger.error(f"  - {key}: {value_type}")
            logger.error("=" * 80)
        
        logger.info(f"Extracted {len(clauses)} clauses: {list(clauses.keys())}")
        return clauses
    
    async def _assess_clause(self, clause_name: str, clause_data: Dict[str, Any]) -> ClauseRiskAssessment:
        """Assess risk for a single clause."""
        prompt_template = self.clause_prompts.get(clause_name)
        
        if not prompt_template:
            logger.warning(f"No prompt template found for clause: {clause_name}")
            return ClauseRiskAssessment(
                clause_name=clause_name,
                compliance_score=50.0,
                risk_level="MEDIUM",
                risk_factors=["No assessment prompt available"],
                recommendations=["Review clause manually"],
                details={}
            )
        
        # Handle null/empty clause data
        if not clause_data or clause_data == {}:
            logger.info(f"Clause {clause_name} is null or empty - assessing as missing")
            return ClauseRiskAssessment(
                clause_name=clause_name,
                compliance_score=0.0,
                risk_level="HIGH",
                risk_factors=[f"{clause_name.replace('_', ' ').title()} clause is missing or not specified in the MSA"],
                recommendations=[f"Add {clause_name.replace('_', ' ').title()} clause to the MSA"],
                details={"status": "missing"}
            )
        
        # Create the assessment prompt
        clause_json = json.dumps(clause_data, indent=2)
        prompt = f"""{prompt_template}

CLAUSE DATA (JSON):
{clause_json}

Analyze this clause and provide your risk assessment in JSON format as specified above."""
        
        try:
            # Invoke LLM
            response = self.llm.invoke(prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Extract JSON from response
            json_match = None
            # Try to find JSON block
            json_block_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', response_text, re.DOTALL)
            if json_block_match:
                json_str = json_block_match.group(1)
            else:
                # Look for JSON object directly
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    raise ValueError("No JSON found in LLM response")
            
            assessment_data = json.loads(json_str)
            
            return ClauseRiskAssessment(
                clause_name=clause_name,
                compliance_score=float(assessment_data.get("compliance_score", 50.0)),
                risk_level=assessment_data.get("risk_level", "MEDIUM"),
                risk_factors=assessment_data.get("risk_factors", []),
                recommendations=assessment_data.get("recommendations", []),
                details=assessment_data.get("details", {})
            )
            
        except Exception as e:
            logger.error(f"Error assessing clause {clause_name}: {str(e)}")
            return ClauseRiskAssessment(
                clause_name=clause_name,
                compliance_score=50.0,
                risk_level="MEDIUM",
                risk_factors=[f"Assessment error: {str(e)}"],
                recommendations=["Review clause manually"],
                details={"error": str(e)}
            )
    
    async def assess_msa(self, msa_data: Dict[str, Any]) -> RiskAssessmentResult:
        """
        Assess risk for all clauses in an MSA in parallel.
        
        Args:
            msa_data: Parsed MSA data from /api/parse-msa endpoint
            
        Returns:
            RiskAssessmentResult with overall score and per-clause assessments
        """
        logger.info("=" * 80)
        logger.info("Starting MSA Risk Assessment")
        logger.info("=" * 80)
        
        # Extract clauses
        clauses = self._extract_clauses(msa_data)
        logger.info(f"Found {len(clauses)} clauses to assess: {list(clauses.keys())}")
        
        # Assess all clauses in parallel
        assessment_tasks = [
            self._assess_clause(clause_name, clause_data)
            for clause_name, clause_data in clauses.items()
        ]
        
        logger.info(f"Assessing {len(assessment_tasks)} clauses in parallel...")
        clause_assessments = await asyncio.gather(*assessment_tasks)
        
        # Calculate overall compliance score (weighted average)
        if clause_assessments:
            total_score = sum(assessment.compliance_score for assessment in clause_assessments)
            overall_score = total_score / len(clause_assessments)
        else:
            overall_score = 50.0
        
        # Determine overall risk level
        risk_scores = {"CRITICAL": 0, "HIGH": 25, "MEDIUM": 50, "LOW": 75}
        max_risk = max(
            (risk_scores.get(assessment.risk_level, 50) for assessment in clause_assessments),
            default=50
        )
        
        if max_risk <= 25:
            overall_risk = "CRITICAL" if max_risk == 0 else "HIGH"
        elif overall_score >= 75:
            overall_risk = "LOW"
        elif overall_score >= 50:
            overall_risk = "MEDIUM"
        else:
            overall_risk = "HIGH"
        
        # Generate summary
        summary = f"Overall Compliance Score: {overall_score:.1f}/100 ({overall_risk} Risk)\n\n"
        summary += f"Assessed {len(clause_assessments)} clauses:\n"
        for assessment in clause_assessments:
            summary += f"- {assessment.clause_name}: {assessment.compliance_score:.1f}/100 ({assessment.risk_level})\n"
        
        logger.info("=" * 80)
        logger.info(f"Risk Assessment Complete - Overall Score: {overall_score:.1f}/100 ({overall_risk})")
        logger.info("=" * 80)
        
        return RiskAssessmentResult(
            overall_compliance_score=overall_score,
            overall_risk_level=overall_risk,
            clause_assessments=clause_assessments,
            summary=summary
        )

