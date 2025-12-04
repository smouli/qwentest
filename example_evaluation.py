#!/usr/bin/env python3
"""
Example script demonstrating how to use the evaluation pipeline
"""

from evaluator import Evaluator, EvaluatorSettings
from pathlib import Path

def main():
    # Initialize evaluator
    print("Initializing evaluator...")
    evaluator = Evaluator(EvaluatorSettings())
    
    # Example: Read ground truth and generated content
    # In practice, you would load these from files or API responses
    
    ground_truth_content = """## SECTION 1.1 — AFFILIATE

Q1: What is the definition of "Affiliate" in this Agreement?
A1: "Affiliate" means, with respect to any entity, any other entity, directly or indirectly, Controlling, Controlled by or under common Control with such entity, and, for purposes hereof North Star Capital, Ltd. and its Affiliates shall be deemed to be Affiliates of BLUESTONE ADVISORS L.P.

Q2: Are North Star Capital, Ltd. and its Affiliates considered Affiliates of BLUESTONE ADVISORS L.P.?
A2: Yes, North Star Capital, Ltd. and its Affiliates are specifically deemed to be Affiliates of BLUESTONE ADVISORS L.P. for purposes of this Agreement.
"""

    generated_content = """## SECTION 1.1 — AFFILIATE

Q1: What is the definition of "Affiliate" in this Agreement?
A1: An Affiliate refers to any entity that directly or indirectly Controls, is Controlled by, or is under common Control with another entity. Additionally, North Star Capital, Ltd. and its Affiliates are specifically considered Affiliates of BLUESTONE ADVISORS L.P. under this Agreement.

Q2: Are North Star Capital, Ltd. and its Affiliates considered Affiliates of BLUESTONE ADVISORS L.P.?
A2: Yes, North Star Capital, Ltd. and its Affiliates are deemed to be Affiliates of BLUESTONE ADVISORS L.P. for purposes of this Agreement.
"""

    print("\nRunning evaluation...")
    print("=" * 80)
    
    # Evaluate the document
    results = evaluator.evaluate_document(
        ground_truth_content=ground_truth_content,
        generated_content=generated_content,
        llm_weight=0.7,
        keyword_weight=0.3
    )
    
    # Print summary
    print("\nEVALUATION SUMMARY")
    print("=" * 80)
    print(f"Total Ground Truth Pairs: {results['total_ground_truth_pairs']}")
    print(f"Total Generated Pairs: {results['total_generated_pairs']}")
    print(f"Matched Pairs: {results['matched_pairs']}")
    print(f"Match Rate: {results['match_rate']:.2%}")
    print(f"\nAverage Scores:")
    print(f"  LLM Score: {results['average_llm_score']:.3f}")
    print(f"  Keyword Score: {results['average_keyword_score']:.3f}")
    print(f"  Combined Score: {results['average_combined_score']:.3f}")
    
    # Print detailed results for each pair
    print("\n" + "=" * 80)
    print("DETAILED RESULTS")
    print("=" * 80)
    
    for idx, result in enumerate(results['results'], 1):
        print(f"\n--- Pair {idx} ---")
        print(f"Question: {result['question']}")
        print(f"\nGround Truth:")
        print(f"  {result['ground_truth_answer']}")
        print(f"\nGenerated:")
        print(f"  {result['generated_answer']}")
        print(f"\nScores:")
        print(f"  LLM: {result['llm_score']:.3f}")
        print(f"  Keyword: {result['keyword_score']:.3f}")
        print(f"  Combined: {result['combined_score']:.3f}")
        print(f"\nLLM Judgment:")
        print(f"  {result['llm_judgment']}")
        print(f"\nKeywords:")
        print(f"  Matched ({len(result['matched_keywords'])}): {', '.join(result['matched_keywords'][:10])}")
        if result['missing_keywords']:
            print(f"  Missing ({len(result['missing_keywords'])}): {', '.join(result['missing_keywords'][:10])}")
    
    # Generate and save report
    print("\n" + "=" * 80)
    print("Generating full report...")
    report = evaluator.generate_report(results, output_path='example_evaluation_report.txt')
    print("Report saved to: example_evaluation_report.txt")
    
    print("\n" + "=" * 80)
    print("Example evaluation complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()


