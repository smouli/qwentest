"""
Evaluation Pipeline for Q&A Pair Matching
Uses LLM as judge and keyword-based deterministic scoring
"""

import re
import json
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
from langchain_openai import ChatOpenAI
from pydantic_settings import BaseSettings
import logging

logger = logging.getLogger(__name__)


class EvaluatorSettings(BaseSettings):
    OPENAI_API_KEY: str
    OPEN_AI_MODEL: str = "gpt-4o"  # Using OpenAI's GPT-4o model
    OPENAI_TEMPERATURE: float = 0

    class Config:
        env_file = ".env"


@dataclass
class QAPair:
    """Represents a Q&A pair"""
    question: str
    answer: str
    section: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class EvaluationResult:
    """Result of evaluating a single Q&A pair"""
    question: str
    ground_truth_answer: str
    generated_answer: str
    llm_score: float  # 0.0 to 1.0
    keyword_score: float  # 0.0 to 1.0
    combined_score: float  # Weighted average
    llm_judgment: str  # LLM's reasoning
    matched_keywords: List[str]
    missing_keywords: List[str]
    section: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


class QAParser:
    """Parse Q&A pairs from markdown format"""
    
    @staticmethod
    def parse_markdown(content: str) -> List[QAPair]:
        """Parse Q&A pairs from markdown content"""
        qa_pairs = []
        current_section = None
        
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Check for section header
            if line.startswith('## SECTION'):
                current_section = line.replace('##', '').strip()
                i += 1
                continue
            
            # Check for Q1:, Q2:, etc.
            if re.match(r'^Q\d+:', line):
                question = line.split(':', 1)[1].strip()
                i += 1
                
                # Look for corresponding answer
                if i < len(lines) and re.match(r'^A\d+:', lines[i].strip()):
                    answer = lines[i].split(':', 1)[1].strip()
                    qa_pairs.append(QAPair(
                        question=question,
                        answer=answer,
                        section=current_section
                    ))
            
            i += 1
        
        return qa_pairs
    
    @staticmethod
    def parse_llm_output(content: str) -> List[QAPair]:
        """Parse Q&A pairs from LLM output (similar format)"""
        return QAParser.parse_markdown(content)


class KeywordScorer:
    """Deterministic keyword-based scoring"""
    
    @staticmethod
    def extract_keywords(text: str, min_length: int = 4) -> set:
        """Extract meaningful keywords from text"""
        # Remove common stopwords and extract significant words
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'should', 'could', 'may', 'might', 'must', 'can', 'this',
            'that', 'these', 'those', 'it', 'its', 'they', 'them', 'their',
            'there', 'then', 'than', 'when', 'where', 'what', 'which', 'who',
            'whom', 'whose', 'why', 'how', 'all', 'each', 'every', 'some', 'any',
            'no', 'not', 'only', 'just', 'also', 'more', 'most', 'other', 'such',
            'same', 'very', 'much', 'many', 'few', 'little', 'own', 'shall'
        }
        
        # Normalize and extract words
        text_lower = text.lower()
        # Remove punctuation and split
        words = re.findall(r'\b[a-z]+\b', text_lower)
        
        # Filter by length and stopwords
        keywords = {w for w in words if len(w) >= min_length and w not in stopwords}
        
        return keywords
    
    @staticmethod
    def score_by_keywords(answer1: str, answer2: str) -> Tuple[float, List[str], List[str]]:
        """
        Score similarity based on keyword overlap
        Returns: (score, matched_keywords, missing_keywords)
        """
        keywords1 = KeywordScorer.extract_keywords(answer1)
        keywords2 = KeywordScorer.extract_keywords(answer2)
        
        if not keywords1 and not keywords2:
            return 1.0, [], []
        
        if not keywords1 or not keywords2:
            return 0.0, [], list(keywords1 | keywords2)
        
        # Calculate Jaccard similarity
        intersection = keywords1 & keywords2
        union = keywords1 | keywords2
        
        score = len(intersection) / len(union) if union else 0.0
        
        matched = list(intersection)
        missing = list(keywords1 - keywords2)
        
        return score, matched, missing


class LLMJudge:
    """LLM-based judge for semantic answer matching"""
    
    def __init__(self, settings: EvaluatorSettings):
        self.llm = ChatOpenAI(
            model=settings.OPEN_AI_MODEL,
            temperature=settings.OPENAI_TEMPERATURE,
            openai_api_key=settings.OPENAI_API_KEY,
            timeout=300,
            max_retries=2
        )
        self.judge_prompt_template = """You are an expert evaluator comparing two answers to the same question.

Question: {question}

Ground Truth Answer: {ground_truth}

Generated Answer: {generated}

Evaluate how well the generated answer matches the ground truth answer. Consider:
1. Semantic similarity (do they convey the same meaning?)
2. Completeness (does the generated answer cover all key points?)
3. Accuracy (are the facts correct?)
4. Clarity and precision

Provide your evaluation in the following JSON format:
{{
    "score": <float between 0.0 and 1.0>,
    "reasoning": "<brief explanation of your scoring>",
    "key_points_matched": <list of key points that match>,
    "key_points_missing": <list of important points from ground truth that are missing>,
    "key_points_incorrect": <list of points in generated answer that contradict ground truth>
}}

Score Guidelines:
- 1.0: Perfect match, all information present and correct
- 0.8-0.9: Very good match, minor details missing or slightly different wording
- 0.6-0.7: Good match, some important details missing but core meaning preserved
- 0.4-0.5: Partial match, core meaning somewhat preserved but significant gaps
- 0.2-0.3: Poor match, only basic similarity
- 0.0-0.1: No meaningful match

Return ONLY valid JSON, no additional text."""
    
    def evaluate(self, question: str, ground_truth: str, generated: str) -> Tuple[float, str]:
        """
        Use LLM to evaluate answer similarity
        Returns: (score, judgment_text)
        """
        prompt = self.judge_prompt_template.format(
            question=question,
            ground_truth=ground_truth,
            generated=generated
        )
        
        try:
            response = self.llm.invoke(prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                score = float(result.get('score', 0.0))
                reasoning = result.get('reasoning', '')
                
                # Build comprehensive judgment text
                judgment = f"Score: {score:.2f}\nReasoning: {reasoning}\n"
                
                if result.get('key_points_matched'):
                    judgment += f"Matched Points: {', '.join(result['key_points_matched'])}\n"
                if result.get('key_points_missing'):
                    judgment += f"Missing Points: {', '.join(result['key_points_missing'])}\n"
                if result.get('key_points_incorrect'):
                    judgment += f"Incorrect Points: {', '.join(result['key_points_incorrect'])}\n"
                
                return score, judgment.strip()
            else:
                # Fallback: try to extract score from text
                score_match = re.search(r'score["\']?\s*[:=]\s*([0-9.]+)', response_text, re.IGNORECASE)
                if score_match:
                    score = float(score_match.group(1))
                    return score, response_text
                else:
                    logger.warning("Could not parse LLM response, defaulting to 0.5")
                    return 0.5, response_text
                    
        except Exception as e:
            logger.error(f"Error in LLM evaluation: {str(e)}")
            return 0.5, f"Error during LLM evaluation: {str(e)}"


class Evaluator:
    """Main evaluation pipeline"""
    
    def __init__(self, settings: Optional[EvaluatorSettings] = None):
        self.settings = settings or EvaluatorSettings()
        self.llm_judge = LLMJudge(self.settings)
        self.keyword_scorer = KeywordScorer()
        self.parser = QAParser()
    
    def evaluate_qa_pair(
        self,
        question: str,
        ground_truth_answer: str,
        generated_answer: str,
        section: Optional[str] = None,
        llm_weight: float = 0.7,
        keyword_weight: float = 0.3
    ) -> EvaluationResult:
        """
        Evaluate a single Q&A pair
        
        Args:
            question: The question
            ground_truth_answer: Expected answer
            generated_answer: Answer to evaluate
            section: Optional section identifier
            llm_weight: Weight for LLM score (default 0.7)
            keyword_weight: Weight for keyword score (default 0.3)
        
        Returns:
            EvaluationResult with scores and analysis
        """
        # Get LLM judgment
        llm_score, llm_judgment = self.llm_judge.evaluate(
            question, ground_truth_answer, generated_answer
        )
        
        # Get keyword score
        keyword_score, matched_keywords, missing_keywords = self.keyword_scorer.score_by_keywords(
            ground_truth_answer, generated_answer
        )
        
        # Calculate combined score
        combined_score = (llm_weight * llm_score) + (keyword_weight * keyword_score)
        
        return EvaluationResult(
            question=question,
            ground_truth_answer=ground_truth_answer,
            generated_answer=generated_answer,
            llm_score=llm_score,
            keyword_score=keyword_score,
            combined_score=combined_score,
            llm_judgment=llm_judgment,
            matched_keywords=matched_keywords,
            missing_keywords=missing_keywords,
            section=section
        )
    
    def evaluate_document(
        self,
        ground_truth_content: str,
        generated_content: str,
        llm_weight: float = 0.7,
        keyword_weight: float = 0.3
    ) -> Dict:
        """
        Evaluate an entire document's Q&A pairs
        
        Returns:
            Dictionary with evaluation results and summary statistics
        """
        # Parse Q&A pairs
        ground_truth_pairs = self.parser.parse_markdown(ground_truth_content)
        generated_pairs = self.parser.parse_llm_output(generated_content)
        
        logger.info(f"Found {len(ground_truth_pairs)} ground truth pairs and {len(generated_pairs)} generated pairs")
        
        # Match pairs by question similarity
        results = []
        matched_ground_truth = set()
        
        for gen_pair in generated_pairs:
            best_match = None
            best_similarity = 0.0
            
            # Find best matching ground truth question
            for idx, gt_pair in enumerate(ground_truth_pairs):
                if idx in matched_ground_truth:
                    continue
                
                # Simple similarity based on keyword overlap
                gen_keywords = self.keyword_scorer.extract_keywords(gen_pair.question)
                gt_keywords = self.keyword_scorer.extract_keywords(gt_pair.question)
                
                if gen_keywords and gt_keywords:
                    intersection = gen_keywords & gt_keywords
                    union = gen_keywords | gt_keywords
                    similarity = len(intersection) / len(union) if union else 0.0
                else:
                    # Fallback to string similarity
                    similarity = 0.5 if gen_pair.question.lower() in gt_pair.question.lower() or gt_pair.question.lower() in gen_pair.question.lower() else 0.0
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = gt_pair
            
            if best_match and best_similarity > 0.3:  # Threshold for matching
                # Evaluate the matched pair
                result = self.evaluate_qa_pair(
                    question=best_match.question,
                    ground_truth_answer=best_match.answer,
                    generated_answer=gen_pair.answer,
                    section=best_match.section,
                    llm_weight=llm_weight,
                    keyword_weight=keyword_weight
                )
                results.append(result)
                matched_ground_truth.add(ground_truth_pairs.index(best_match))
        
        # Calculate summary statistics
        if results:
            avg_llm_score = sum(r.llm_score for r in results) / len(results)
            avg_keyword_score = sum(r.keyword_score for r in results) / len(results)
            avg_combined_score = sum(r.combined_score for r in results) / len(results)
        else:
            avg_llm_score = avg_keyword_score = avg_combined_score = 0.0
        
        return {
            "total_ground_truth_pairs": len(ground_truth_pairs),
            "total_generated_pairs": len(generated_pairs),
            "matched_pairs": len(results),
            "match_rate": len(results) / len(ground_truth_pairs) if ground_truth_pairs else 0.0,
            "average_llm_score": avg_llm_score,
            "average_keyword_score": avg_keyword_score,
            "average_combined_score": avg_combined_score,
            "results": [r.to_dict() for r in results],
            "unmatched_ground_truth": len(ground_truth_pairs) - len(matched_ground_truth),
            "unmatched_generated": len(generated_pairs) - len(results)
        }
    
    def generate_report(self, evaluation_results: Dict, output_path: Optional[str] = None) -> str:
        """Generate a human-readable evaluation report"""
        report_lines = [
            "=" * 80,
            "EVALUATION REPORT",
            "=" * 80,
            "",
            f"Total Ground Truth Q&A Pairs: {evaluation_results['total_ground_truth_pairs']}",
            f"Total Generated Q&A Pairs: {evaluation_results['total_generated_pairs']}",
            f"Matched Pairs: {evaluation_results['matched_pairs']}",
            f"Match Rate: {evaluation_results['match_rate']:.2%}",
            "",
            "SCORES:",
            f"  Average LLM Score: {evaluation_results['average_llm_score']:.3f}",
            f"  Average Keyword Score: {evaluation_results['average_keyword_score']:.3f}",
            f"  Average Combined Score: {evaluation_results['average_combined_score']:.3f}",
            "",
            "=" * 80,
            "DETAILED RESULTS",
            "=" * 80,
            ""
        ]
        
        for idx, result in enumerate(evaluation_results['results'], 1):
            report_lines.extend([
                f"\n--- Pair {idx} ---",
                f"Section: {result.get('section', 'N/A')}",
                f"Question: {result['question']}",
                "",
                "Ground Truth Answer:",
                result['ground_truth_answer'],
                "",
                "Generated Answer:",
                result['generated_answer'],
                "",
                f"LLM Score: {result['llm_score']:.3f}",
                f"Keyword Score: {result['keyword_score']:.3f}",
                f"Combined Score: {result['combined_score']:.3f}",
                "",
                "LLM Judgment:",
                result['llm_judgment'],
                "",
                f"Matched Keywords ({len(result['matched_keywords'])}): {', '.join(result['matched_keywords'][:10])}",
                f"Missing Keywords ({len(result['missing_keywords'])}): {', '.join(result['missing_keywords'][:10])}",
                ""
            ])
        
        report = "\n".join(report_lines)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)
            logger.info(f"Report saved to {output_path}")
        
        return report

