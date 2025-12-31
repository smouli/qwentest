"""
Risk Assessment Module for MSA Clauses
Assesses compliance risk for each clause in parallel using clause-specific prompts.
"""

import json
import logging
import asyncio
import re
from typing import Dict, Any, List, Tuple
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
    structure_completeness: float  # % of expected clauses that are present (0-100)
    missing_clauses_count: int  # Number of clauses that are missing/null
    clause_assessments: List[ClauseRiskAssessment]
    summary: str


# Clause-specific risk assessment prompts - Framework-based approach
# Focuses on 3 core MSA areas: SLAs, Payment Terms, and Termination
CLAUSE_PROMPTS = {
    "service_level_agreements": """You are an expert contract risk assessor specializing in Service Level Agreements (SLAs) and deliverable quality standards.

CONTEXT: An MSA establishes the commercial norms for work output and service expectations. SLAs define the quality, performance, and delivery standards for deliverables and services.

Analyze the Service Level Agreements section of this MSA and assess compliance risk based on:

1. DELIVERABLE QUALITY STANDARDS:
   - Work output expectations and specifications
   - Performance standards and metrics
   - Service quality guarantees
   - Warranty periods for deliverables

2. SERVICE PERFORMANCE METRICS:
   - Availability SLAs (uptime guarantees)
   - Response time SLAs (time to respond to issues)
   - Resolution time SLAs (time to fix problems)
   - Performance benchmarks

3. PENALTIES FOR NON-DELIVERY:
   - Penalties defined if services are not delivered as expected
   - Service credits or refunds for SLA breaches
   - Escalation procedures for repeated failures
   - Remedies for non-performance (repair, correction, replacement, refund, re-performance)
   - Early termination rights and trigger conditions (breach, unresolved non-performance, data-processing violation, non-payment)
   - Post-termination obligations (returning confidential information, deleting data, ceasing use)
   - Liability scope and carve-outs (caps, exclusions, exceptions for fraud, gross negligence, security/privacy breaches, IP infringement, regulatory penalties)
   - Consequences for late payment (suspension of service, termination rights, cure periods, interest, collections)

RISK FACTORS TO CONSIDER:
- Missing SLAs entirely = HIGH RISK (no performance guarantees)
- No availability SLA = HIGH RISK (downtime risk)
- Response time SLA > 24 hours = MEDIUM RISK (slow support)
- No penalties for non-delivery = HIGH RISK (no enforcement mechanism)
- Unclear work output expectations = MEDIUM-HIGH RISK (disputes)
- No warranty period for deliverables = MEDIUM RISK (quality risk)
- Comprehensive SLAs with clear metrics and penalties = LOW RISK

Return a JSON object with:
{
    "compliance_score": <0-100>,
    "risk_level": "<LOW|MEDIUM|HIGH|CRITICAL>",
    "risk_factors": ["list of specific risk factors"],
    "recommendations": ["list of recommendations"],
    "details": {
        "sla_metrics": {details about SLAs found},
        "penalties": {details about penalties},
        "work_output_expectations": {details about deliverables}
    }
}""",

    "payment_terms": """You are an expert contract risk assessor specializing in payment terms and commercial structures.

CONTEXT: Payment terms govern the financial relationship and establish commercial norms for invoicing, payment, and financial obligations.

Analyze the Payment Terms section of this MSA and assess compliance risk based on:

1. INVOICING AND PAYMENT STRUCTURE:
   - Invoicing frequency (weekly, bi-weekly, monthly, etc.)
   - Payment due dates (days after invoice)
   - Acceptable payment methods (wire transfer, ACH, check, credit card, etc.)
   - Payment terms clarity and enforceability

2. LATE PAYMENT PROVISIONS:
   - Late payment penalties (interest rates, fees)
   - Grace periods before penalties apply
   - Remedies for non-payment (suspension of services, termination)
   - Dispute resolution for payment issues

3. COMMERCIAL TERMS:
   - Rate cards and pricing transparency
   - Volume discounts and pricing fairness
   - Expense reimbursement policies and markups
   - Tax provisions and responsibilities
   - Fee structures and surcharges

RISK FACTORS TO CONSIDER:
- Payment terms > 60 days = HIGH RISK (cash flow impact)
- Missing late payment penalties = MEDIUM RISK (no enforcement)
- Missing acceptable payment methods = MEDIUM RISK (payment uncertainty)
- Unclear invoicing frequency = MEDIUM RISK (billing disputes)
- Customer responsible for all taxes = MEDIUM RISK (cost burden)
- High expense markups (>20%) = MEDIUM RISK (cost escalation)
- No remedies for non-payment = HIGH RISK (payment risk)
- Clear payment terms with penalties = LOW RISK

Return a JSON object with:
{
    "compliance_score": <0-100>,
    "risk_level": "<LOW|MEDIUM|HIGH|CRITICAL>",
    "risk_factors": ["list of specific risk factors"],
    "recommendations": ["list of recommendations"],
    "details": {
        "invoicing_frequency": {details},
        "payment_due_days": {details},
        "accepted_payment_methods": {details},
        "late_payment_penalties": {details},
        "commercial_terms": {additional commercial details}
    }
}""",

    "termination_breach": """You are an expert contract risk assessor specializing in termination clauses and breach of contract provisions.

CONTEXT: Termination clauses define breach of contract requirements and establish how parties can exit the relationship when expectations are not met.

Analyze the Termination and Breach of Contract section of this MSA and assess compliance risk based on:

1. TERMINATION FOR BREACH:
   - Grounds for termination for cause (material breach, non-payment, etc.)
   - Cure periods (time allowed to fix breaches before termination)
   - Notice requirements for breach and termination
   - What constitutes a material breach

2. TERMINATION FOR CONVENIENCE:
   - Rights to terminate without cause
   - Notice periods for convenience termination
   - Mutual vs one-sided termination rights
   - Exit flexibility and fairness

3. POST-TERMINATION OBLIGATIONS:
   - Survival clauses (what survives after termination)
   - Payment obligations after termination
   - Return of materials and data
   - Transition assistance requirements

RISK FACTORS TO CONSIDER:
- No termination for convenience = HIGH RISK (locked into contract)
- Cure period < 30 days = MEDIUM RISK (insufficient time to fix)
- Unclear breach grounds = MEDIUM RISK (disputes)
- Missing survival clauses = HIGH RISK (lose protections after exit)
- One-sided termination rights = HIGH RISK (unfair)
- No notice requirements = MEDIUM RISK (surprise termination)
- Clear mutual termination with proper notice = LOW RISK

Return a JSON object with:
{
    "compliance_score": <0-100>,
    "risk_level": "<LOW|MEDIUM|HIGH|CRITICAL>",
    "risk_factors": ["list of specific risk factors"],
    "recommendations": ["list of recommendations"],
    "details": {
        "termination_for_breach": {details about breach termination},
        "termination_for_convenience": {details about convenience termination},
        "cure_periods": {details},
        "survival_clauses": {details}
    }
}""",

    "indemnification": """You are an expert contract risk assessor specializing in indemnification clauses and third-party protection.

CONTEXT: Indemnification clauses protect parties against third-party claims, intellectual property disputes, negligence, and regulatory impacts (fines, penalties, or legal actions resulting from non-compliance with laws/regulations such as GDPR, HIPAA, SOX, etc.).

Analyze the Indemnification section of this MSA and assess compliance risk based on:

1. INDEMNIFICATION SCOPE:
   - Third-party claims protection
   - Intellectual property infringement disputes
   - Negligence and misconduct claims
   - Regulatory impacts (fines, penalties from non-compliance with GDPR, HIPAA, SOX, PCI DSS, etc.)

2. INDEMNIFICATION STRUCTURE:
   - Mutual vs one-sided indemnification
   - What each party indemnifies the other for
   - Defense obligations (who defends against claims)
   - Notice requirements for indemnification claims

3. EXCLUSIONS AND LIMITATIONS:
   - What's excluded from indemnification
   - Limitations on indemnification scope
   - Time limits for indemnification claims

RISK FACTORS TO CONSIDER:
- One-sided indemnification (only provider indemnifies) = HIGH RISK (unfair burden)
- Missing IP infringement indemnification = HIGH RISK (IP risk)
- No indemnification for regulatory impacts = HIGH RISK (compliance risk)
- Missing indemnification for third-party claims = HIGH RISK (liability exposure)
- No defense obligations = MEDIUM RISK (unclear process)
- Unclear notice requirements = MEDIUM RISK (claim disputes)
- Comprehensive mutual indemnification = LOW RISK

Return a JSON object with:
{
    "compliance_score": <0-100>,
    "risk_level": "<LOW|MEDIUM|HIGH|CRITICAL>",
    "risk_factors": ["list of specific risk factors"],
    "recommendations": ["list of recommendations"],
    "details": {
        "indemnification_scope": {what's covered},
        "mutual_indemnification": {true/false},
        "regulatory_impacts_covered": {yes/no and details},
        "ip_indemnification": {details},
        "third_party_claims": {details}
    }
}""",

    "liability_insurance": """You are an expert contract risk assessor specializing in liability limitations and insurance requirements.

CONTEXT: Liability and insurance clauses protect against various risks including confidentiality breaches, data breaches, service failures, IP infringement, negligence, and other contractual breaches.

Analyze the Liability and Insurance section of this MSA and assess compliance risk based on:

1. LIABILITY LIMITATIONS:
   - Liability caps and maximum exposure limits
   - Exclusions from liability limitations (gross negligence, willful misconduct, etc.)
   - Types of damages covered/excluded (direct, indirect, consequential)
   - Liability allocation between parties

2. INSURANCE REQUIREMENTS:
   - General liability insurance (coverage amounts)
   - Professional liability/E&O insurance (errors and omissions)
   - Cyber liability insurance (data breaches, security incidents)
   - Workers compensation insurance
   - Additional insurance requirements

3. PROTECTION AGAINST BREACHES:
   - Protection against confidentiality breaches
   - Protection against data protection breaches
   - Protection against service delivery failures
   - Protection against IP infringement
   - Protection against regulatory violations

RISK FACTORS TO CONSIDER:
- Liability cap < $1M = HIGH RISK (insufficient protection)
- Missing exclusions for gross negligence = CRITICAL RISK (unlimited exposure)
- Missing general liability insurance = HIGH RISK (no basic protection)
- Missing professional liability = HIGH RISK (no E&O protection)
- Missing cyber liability = MEDIUM-HIGH RISK (data breach risk)
- Coverage < $1M = MEDIUM RISK (insufficient coverage)
- No protection against confidentiality breaches = HIGH RISK
- Comprehensive liability limits with adequate insurance = LOW RISK

Return a JSON object with:
{
    "compliance_score": <0-100>,
    "risk_level": "<LOW|MEDIUM|HIGH|CRITICAL>",
    "risk_factors": ["list of specific risk factors"],
    "recommendations": ["list of recommendations"],
    "details": {
        "liability_cap": {details},
        "liability_exclusions": {what's excluded},
        "insurance_coverage": {details about insurance},
        "breach_protections": {what breaches are covered}
    }
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
        clauses: Dict[str, Any] = {}
        
        # Extract top-level clauses
        # Map framework-based clause names to MSA schema field names
        # Framework focuses on 3 core areas: SLAs, Payment Terms, and Termination
        clause_mapping = {
            "service_level_agreements": "warranties",  # SLAs are in warranties section
            "payment_terms": "commercial_terms",  # Payment terms are in commercial_terms section
            "termination_breach": "termination",  # Termination for breach is in termination section
            "indemnification": "liability_indemnification",  # Indemnification is in liability_indemnification section
            "liability_insurance": "insurance",  # Liability and insurance are in insurance section
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
            # Extract response text - ensure it's a string
            if hasattr(response, 'content'):
                response_text = str(response.content)
            else:
                response_text = str(response)
            
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
            
            compliance_score = float(assessment_data.get("compliance_score", 50.0))
            
            # Ensure present clauses never score exactly 0.0
            # 0.0 is reserved exclusively for missing clauses
            # If a clause has data but scores 0.0, it means it's critically poor but still present
            if clause_data and clause_data != {} and compliance_score == 0.0:
                compliance_score = 5.0  # Minimum score for present but critically poor clauses
                logger.warning(f"Clause {clause_name} scored 0.0 but has data - adjusting to 5.0 to distinguish from missing")
            
            return ClauseRiskAssessment(
                clause_name=clause_name,
                compliance_score=compliance_score,
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
    
    def _calculate_structure_completeness(self, clause_assessments: List[ClauseRiskAssessment], total_expected_clauses: int) -> Tuple[float, int]:
        """
        Calculate structure completeness metrics.
        
        Args:
            clause_assessments: List of clause assessments
            total_expected_clauses: Total number of clauses expected in the MSA
            
        Returns:
            Tuple of (structure_completeness_score, missing_clauses_count)
            - structure_completeness_score: % of expected clauses that are present (0-100)
            - missing_clauses_count: Number of clauses that are missing/null
        """
        # Count missing clauses (score = 0.0 and marked as missing in details)
        missing_count = sum(
            1 for assessment in clause_assessments 
            if assessment.compliance_score == 0.0 and assessment.details.get("status") == "missing"
        )
        
        present_count = len(clause_assessments) - missing_count
        
        # Completeness = % of expected clauses that are present
        if total_expected_clauses > 0:
            completeness = (present_count / total_expected_clauses) * 100
        else:
            completeness = 100.0 if present_count > 0 else 0.0
        
        return completeness, missing_count
    
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
        
        # Calculate structure completeness metrics
        # Total expected clauses = number of clause types we're assessing
        total_expected_clauses = len(self.clause_prompts)  # Should be 5 based on framework
        structure_completeness, missing_clauses_count = self._calculate_structure_completeness(
            clause_assessments, 
            total_expected_clauses
        )
        
        # Calculate overall compliance score (average of clause scores)
        if clause_assessments:
            total_score = sum(assessment.compliance_score for assessment in clause_assessments)
            compliance_score = total_score / len(clause_assessments)
        else:
            compliance_score = 50.0
        
        # Enhanced overall score: combine compliance and structure completeness
        # Weight: 60% compliance quality, 40% structure completeness
        # This ensures MSAs with missing clauses score lower than those with all clauses present
        overall_score = (0.6 * compliance_score) + (0.4 * structure_completeness)
        
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
        
        # Generate summary with structure metrics
        summary = f"Overall Compliance Score: {overall_score:.1f}/100 ({overall_risk} Risk)\n"
        summary += f"Structure Completeness: {structure_completeness:.1f}% ({missing_clauses_count} missing clauses)\n"
        summary += f"Compliance Quality: {compliance_score:.1f}/100\n\n"
        summary += f"Assessed {len(clause_assessments)} clauses:\n"
        for assessment in clause_assessments:
            status_indicator = " [MISSING]" if assessment.compliance_score == 0.0 and assessment.details.get("status") == "missing" else ""
            summary += f"- {assessment.clause_name}: {assessment.compliance_score:.1f}/100 ({assessment.risk_level}){status_indicator}\n"
        
        logger.info("=" * 80)
        logger.info(f"Risk Assessment Complete - Overall Score: {overall_score:.1f}/100 ({overall_risk})")
        logger.info(f"Structure Completeness: {structure_completeness:.1f}% ({missing_clauses_count} missing)")
        logger.info(f"Compliance Quality: {compliance_score:.1f}/100")
        logger.info("=" * 80)
        
        return RiskAssessmentResult(
            overall_compliance_score=overall_score,
            overall_risk_level=overall_risk,
            structure_completeness=structure_completeness,
            missing_clauses_count=missing_clauses_count,
            clause_assessments=clause_assessments,
            summary=summary
        )

