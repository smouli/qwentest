#!/usr/bin/env python3
"""
Command-line utility for evaluating Q&A pairs
"""

import argparse
import sys
import os
from pathlib import Path

# Try to import evaluator, provide helpful error if it fails
try:
    from evaluator import Evaluator, EvaluatorSettings
except ImportError as e:
    print("Error: Could not import required modules.", file=sys.stderr)
    print("Please make sure you have activated the virtual environment:", file=sys.stderr)
    print("  source venv/bin/activate", file=sys.stderr)
    print("Or install dependencies:", file=sys.stderr)
    print("  pip install -r requirements.txt", file=sys.stderr)
    print(f"\nOriginal error: {e}", file=sys.stderr)
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Evaluate generated Q&A pairs against ground truth"
    )
    parser.add_argument(
        "ground_truth",
        type=str,
        help="Path to ground truth markdown file"
    )
    parser.add_argument(
        "generated",
        type=str,
        help="Path to generated Q&A markdown file"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Path to save evaluation report (default: print to stdout)"
    )
    parser.add_argument(
        "--llm-weight",
        type=float,
        default=0.7,
        help="Weight for LLM score (default: 0.7)"
    )
    parser.add_argument(
        "--keyword-weight",
        type=float,
        default=0.3,
        help="Weight for keyword score (default: 0.3)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON instead of human-readable report"
    )
    
    args = parser.parse_args()
    
    # Validate weights
    if abs(args.llm_weight + args.keyword_weight - 1.0) > 0.01:
        print("Warning: LLM weight and keyword weight should sum to 1.0", file=sys.stderr)
        print(f"Current weights: LLM={args.llm_weight}, Keyword={args.keyword_weight}", file=sys.stderr)
    
    # Read files
    try:
        gt_path = Path(args.ground_truth)
        gen_path = Path(args.generated)
        
        if not gt_path.exists():
            print(f"Error: Ground truth file not found: {args.ground_truth}", file=sys.stderr)
            sys.exit(1)
        
        if not gen_path.exists():
            print(f"Error: Generated file not found: {args.generated}", file=sys.stderr)
            sys.exit(1)
        
        gt_content = gt_path.read_text(encoding='utf-8')
        gen_content = gen_path.read_text(encoding='utf-8')
        
    except Exception as e:
        print(f"Error reading files: {str(e)}", file=sys.stderr)
        sys.exit(1)
    
    # Initialize evaluator
    evaluator = Evaluator(EvaluatorSettings())
    
    # Run evaluation
    print("Running evaluation...", file=sys.stderr)
    try:
        results = evaluator.evaluate_document(
            ground_truth_content=gt_content,
            generated_content=gen_content,
            llm_weight=args.llm_weight,
            keyword_weight=args.keyword_weight
        )
    except Exception as e:
        print(f"Error during evaluation: {str(e)}", file=sys.stderr)
        sys.exit(1)
    
    # Output results
    if args.json:
        import json
        output = json.dumps(results, indent=2)
    else:
        output = evaluator.generate_report(results)
    
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(output, encoding='utf-8')
        print(f"Results saved to {output_path}", file=sys.stderr)
    else:
        print(output)
    
    # Print summary to stderr
    print("\n" + "=" * 80, file=sys.stderr)
    print("SUMMARY", file=sys.stderr)
    print("=" * 80, file=sys.stderr)
    print(f"Match Rate: {results['match_rate']:.2%}", file=sys.stderr)
    print(f"Average Combined Score: {results['average_combined_score']:.3f}", file=sys.stderr)
    print(f"Average LLM Score: {results['average_llm_score']:.3f}", file=sys.stderr)
    print(f"Average Keyword Score: {results['average_keyword_score']:.3f}", file=sys.stderr)
    print("=" * 80, file=sys.stderr)


if __name__ == "__main__":
    main()

