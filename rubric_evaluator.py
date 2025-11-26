"""
Rubric-based Contract Evaluation System
Evaluates contracts against predefined rubric questions and calculates risk scores
"""

import re
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from langchain_openai import ChatOpenAI
from pydantic_settings import BaseSettings
import logging

logger = logging.getLogger(__name__)


class RubricSettings(BaseSettings):
    OPENAI_API_KEY: str
    OPEN_AI_MODEL: str = "Qwen3-32B"
    OPENAI_TEMPERATURE: float = 0
    INFERENCE_SERVER_URL: str = "https://llm-api.annotet.com"

    class Config:
        env_file = ".env"


@dataclass
class RubricQuestion:
    """Represents a rubric question"""
    category: str
    category_number: int
    question_number: int
    question: str
    guidance: str  # The "A:" answer guidance
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class QuestionAnswer:
    """Answer to a rubric question"""
    question: RubricQuestion
    answer: str
    score: float  # 1-5 scale
    reasoning: str
    risk_level: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    
    def to_dict(self) -> Dict:
        return {
            "category": self.question.category,
            "category_number": self.question.category_number,
            "question_number": self.question.question_number,
            "question": self.question.question,
            "answer": self.answer,
            "score": self.score,
            "reasoning": self.reasoning,
            "risk_level": self.risk_level
        }


@dataclass
class CategoryScore:
    """Score for a category"""
    category: str
    category_number: int
    average_score: float
    questions: List[QuestionAnswer]
    risk_level: str
    
    def to_dict(self) -> Dict:
        return {
            "category": self.category,
            "category_number": self.category_number,
            "average_score": self.average_score,
            "risk_level": self.risk_level,
            "questions": [q.to_dict() for q in self.questions]
        }


@dataclass
class RiskAssessment:
    """Overall risk assessment"""
    overall_score: float  # 1-5 scale
    overall_risk_level: str
    category_scores: List[CategoryScore]
    total_questions: int
    answered_questions: int
    critical_risks: List[str]  # List of critical risk areas
    
    def to_dict(self) -> Dict:
        return {
            "overall_score": self.overall_score,
            "overall_risk_level": self.overall_risk_level,
            "total_questions": self.total_questions,
            "answered_questions": self.answered_questions,
            "critical_risks": self.critical_risks,
            "category_scores": [cs.to_dict() for cs in self.category_scores]
        }


class RubricParser:
    """Parse evaluation rubric from text file"""
    
    # Emoji to category mapping
    EMOJI_CATEGORIES = {
        "🟥": "LIABILITY STRUCTURE",
        "🟧": "INDEMNIFICATION",
        "🟨": "IP OWNERSHIP",
        "🟩": "CONFIDENTIALITY & DATA HANDLING",
        "🟦": "INSURANCE",
        "🟫": "OPERATIONAL PERFORMANCE",
        "⬛": "TERMINATION & SURVIVAL",
        "⬜": "COMMERCIAL RESTRICTIONS"
    }
    
    @staticmethod
    def parse_rubric(rubric_content: str) -> List[RubricQuestion]:
        """Parse rubric questions from text content"""
        questions = []
        lines = rubric_content.split('\n')
        
        current_category = None
        current_category_number = 0
        current_question_number = 0
        current_question = None
        current_guidance = None
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Check for category header (emoji + number)
            for emoji, category_name in RubricParser.EMOJI_CATEGORIES.items():
                if line.startswith(emoji):
                    # Save previous question if exists
                    if current_question and current_guidance:
                        questions.append(RubricQuestion(
                            category=current_category,
                            category_number=current_category_number,
                            question_number=current_question_number,
                            question=current_question,
                            guidance=current_guidance
                        ))
                    
                    # Extract category number
                    match = re.search(r'(\d+)\.', line)
                    if match:
                        current_category_number = int(match.group(1))
                    else:
                        current_category_number += 1
                    
                    current_category = category_name
                    current_question_number = 0
                    current_question = None
                    current_guidance = None
                    break
            
            # Check for Q1:, Q2:, etc.
            if re.match(r'^Q\d+:', line):
                # Save previous question if exists
                if current_question and current_guidance:
                    questions.append(RubricQuestion(
                        category=current_category,
                        category_number=current_category_number,
                        question_number=current_question_number,
                        question=current_question,
                        guidance=current_guidance
                    ))
                
                # Extract question number and text
                match = re.match(r'Q(\d+):\s*(.+)', line)
                if match:
                    current_question_number = int(match.group(1))
                    current_question = match.group(2).strip()
                    current_guidance = None
            
            # Check for A: guidance
            elif line.startswith('A:') and current_question:
                current_guidance = line[2:].strip()
            
            i += 1
        
        # Save last question
        if current_question and current_guidance:
            questions.append(RubricQuestion(
                category=current_category,
                category_number=current_category_number,
                question_number=current_question_number,
                question=current_question,
                guidance=current_guidance
            ))
        
        return questions


class RubricEvaluator:
    """Evaluate contracts against rubric questions"""
    
    def __init__(self, settings: Optional[RubricSettings] = None):
        self.settings = settings or RubricSettings()
        self.llm = ChatOpenAI(
            model=self.settings.OPEN_AI_MODEL,
            temperature=self.settings.OPENAI_TEMPERATURE,
            openai_api_key=self.settings.OPENAI_API_KEY,
            openai_api_base=self.settings.INFERENCE_SERVER_URL,
            timeout=300,
            max_retries=2
        )
        self.parser = RubricParser()
    
    def _create_evaluation_prompt(self, question: RubricQuestion, contract_text: str) -> str:
        """Create prompt for evaluating a single question"""
        return f"""You are evaluating a contract against a specific rubric question. Analyze the contract text and answer the question.

RUBRIC QUESTION:
{question.question}

GUIDANCE FOR EVALUATION:
{question.guidance}

CONTRACT TEXT:
{contract_text[:15000]}  # Limit to avoid token limits

Please provide:
1. A direct answer to the question based on what you find (or don't find) in the contract
2. A score from 1-5 where:
   - 5 = Excellent/Comprehensive: Fully addresses the concern, very favorable to client
   - 4 = Good: Addresses most concerns, generally favorable
   - 3 = Acceptable: Basic coverage, neutral or mixed
   - 2 = Poor: Missing important elements, unfavorable to client
   - 1 = Critical: Major gaps or very unfavorable terms
3. Brief reasoning for your score
4. Risk level: LOW, MEDIUM, HIGH, or CRITICAL

Format your response as JSON:
{{
    "answer": "<your answer>",
    "score": <1-5>,
    "reasoning": "<brief explanation>",
    "risk_level": "<LOW|MEDIUM|HIGH|CRITICAL>"
}}"""
    
    def _parse_llm_response(self, response_text: str) -> Dict:
        """Parse LLM response to extract answer, score, reasoning"""
        try:
            # Try to extract JSON
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                import json
                result = json.loads(json_match.group())
                return {
                    "answer": result.get("answer", response_text),
                    "score": float(result.get("score", 3.0)),
                    "reasoning": result.get("reasoning", ""),
                    "risk_level": result.get("risk_level", "MEDIUM")
                }
        except Exception as e:
            logger.warning(f"Could not parse JSON from LLM response: {e}")
        
        # Fallback: try to extract score from text
        score_match = re.search(r'score["\']?\s*[:=]\s*([1-5])', response_text, re.IGNORECASE)
        score = float(score_match.group(1)) if score_match else 3.0
        
        # Extract risk level
        risk_match = re.search(r'risk[_\s]*level["\']?\s*[:=]\s*([A-Z]+)', response_text, re.IGNORECASE)
        risk_level = risk_match.group(1) if risk_match else "MEDIUM"
        
        return {
            "answer": response_text[:500],  # Limit answer length
            "score": score,
            "reasoning": response_text,
            "risk_level": risk_level
        }
    
    def evaluate_question(self, question: RubricQuestion, contract_text: str) -> QuestionAnswer:
        """Evaluate a single rubric question against contract text"""
        prompt = self._create_evaluation_prompt(question, contract_text)
        
        try:
            response = self.llm.invoke(prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            parsed = self._parse_llm_response(response_text)
            
            return QuestionAnswer(
                question=question,
                answer=parsed["answer"],
                score=parsed["score"],
                reasoning=parsed["reasoning"],
                risk_level=parsed["risk_level"]
            )
        except Exception as e:
            logger.error(f"Error evaluating question {question.category} Q{question.question_number}: {str(e)}")
            # Return default answer on error
            return QuestionAnswer(
                question=question,
                answer=f"Error evaluating: {str(e)}",
                score=3.0,
                reasoning="Could not evaluate due to error",
                risk_level="MEDIUM"
            )
    
    def _calculate_risk_level(self, score: float) -> str:
        """Calculate risk level from score"""
        if score >= 4.5:
            return "LOW"
        elif score >= 3.5:
            return "MEDIUM"
        elif score >= 2.5:
            return "HIGH"
        else:
            return "CRITICAL"
    
    def evaluate_contract(
        self,
        contract_text: str,
        rubric_content: str,
        max_questions: Optional[int] = None
    ) -> RiskAssessment:
        """
        Evaluate a contract against the rubric
        
        Args:
            contract_text: The contract text to evaluate
            rubric_content: Content of the evaluation rubric
            max_questions: Optional limit on number of questions to evaluate (for testing)
        
        Returns:
            RiskAssessment with scores and risk levels
        """
        # Parse rubric questions
        questions = self.parser.parse_rubric(rubric_content)
        
        if max_questions:
            questions = questions[:max_questions]
        
        logger.info(f"Evaluating contract against {len(questions)} rubric questions")
        
        # Evaluate each question
        question_answers = []
        for i, question in enumerate(questions, 1):
            logger.info(f"Evaluating question {i}/{len(questions)}: {question.category} Q{question.question_number}")
            answer = self.evaluate_question(question, contract_text)
            question_answers.append(answer)
        
        # Group by category
        category_groups = {}
        for qa in question_answers:
            category = qa.question.category
            if category not in category_groups:
                category_groups[category] = []
            category_groups[category].append(qa)
        
        # Calculate category scores
        category_scores = []
        for category, qas in sorted(category_groups.items(), key=lambda x: x[1][0].question.category_number):
            avg_score = sum(qa.score for qa in qas) / len(qas)
            risk_level = self._calculate_risk_level(avg_score)
            
            category_scores.append(CategoryScore(
                category=category,
                category_number=qas[0].question.category_number,
                average_score=avg_score,
                questions=qas,
                risk_level=risk_level
            ))
        
        # Calculate overall score
        overall_score = sum(qa.score for qa in question_answers) / len(question_answers) if question_answers else 0.0
        overall_risk_level = self._calculate_risk_level(overall_score)
        
        # Identify critical risks (categories with HIGH or CRITICAL risk)
        critical_risks = [
            cs.category for cs in category_scores
            if cs.risk_level in ["HIGH", "CRITICAL"]
        ]
        
        return RiskAssessment(
            overall_score=overall_score,
            overall_risk_level=overall_risk_level,
            category_scores=category_scores,
            total_questions=len(questions),
            answered_questions=len(question_answers),
            critical_risks=critical_risks
        )

