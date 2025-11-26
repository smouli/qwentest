#!/usr/bin/env python3
"""
Script to generate Q&A pairs from a PDF file using the API
"""

import argparse
import sys
import requests
from pathlib import Path

def generate_qa_from_pdf(pdf_path: str, output_path: str, server_url: str = "http://localhost:6969"):
    """
    Generate Q&A pairs from a PDF file
    
    Args:
        pdf_path: Path to the PDF file
        output_path: Path to save the generated Q&A markdown
        server_url: URL of the FastAPI server
    """
    pdf_file = Path(pdf_path)
    
    if not pdf_file.exists():
        print(f"Error: PDF file not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Uploading PDF: {pdf_path}", file=sys.stderr)
    print(f"Server URL: {server_url}", file=sys.stderr)
    
    # Prepare the file upload
    with open(pdf_file, 'rb') as f:
        files = {'file': (pdf_file.name, f, 'application/pdf')}
        
        try:
            # Make request to process-pdf endpoint
            response = requests.post(
                f"{server_url}/api/process-pdf",
                files=files,
                timeout=600  # 10 minutes timeout
            )
            
            if response.status_code != 200:
                print(f"Error: Server returned status {response.status_code}", file=sys.stderr)
                print(f"Response: {response.text}", file=sys.stderr)
                sys.exit(1)
            
            data = response.json()
            
            if data.get('status') != 'success':
                print(f"Error: {data.get('detail', 'Unknown error')}", file=sys.stderr)
                sys.exit(1)
            
            # Extract the Q&A response
            qa_content = data.get('response', '')
            
            # Save to output file
            output_file = Path(output_path)
            output_file.write_text(qa_content, encoding='utf-8')
            
            print(f"\nSuccess! Generated Q&A pairs saved to: {output_path}", file=sys.stderr)
            print(f"Total chunks processed: {data.get('chunks_processed', 1)}", file=sys.stderr)
            print(f"Response length: {len(qa_content)} characters", file=sys.stderr)
            
        except requests.exceptions.ConnectionError:
            print(f"Error: Could not connect to server at {server_url}", file=sys.stderr)
            print("Make sure the server is running:", file=sys.stderr)
            print("  python app.py", file=sys.stderr)
            sys.exit(1)
        except requests.exceptions.Timeout:
            print("Error: Request timed out. The PDF may be too large.", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error: {str(e)}", file=sys.stderr)
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Generate Q&A pairs from a PDF file"
    )
    parser.add_argument(
        "pdf_path",
        type=str,
        help="Path to the PDF file"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="generated_qa.md",
        help="Output file path (default: generated_qa.md)"
    )
    parser.add_argument(
        "--server",
        "-s",
        type=str,
        default="http://localhost:6969",
        help="Server URL (default: http://localhost:6969)"
    )
    
    args = parser.parse_args()
    
    generate_qa_from_pdf(args.pdf_path, args.output, args.server)


if __name__ == "__main__":
    main()

