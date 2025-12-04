#!/usr/bin/env python3
"""
Script to parse an MSA PDF file and extract structured data.
"""

import argparse
import sys
import requests
import json
from pathlib import Path

def parse_msa_pdf(pdf_path: str, output_path: str = None, server_url: str = "http://localhost:6969"):
    """
    Parse an MSA PDF file and extract structured data.
    
    Args:
        pdf_path: Path to the PDF file
        output_path: Optional path to save the JSON output (default: {pdf_name}_msa.json)
        server_url: URL of the FastAPI server
    """
    pdf_file = Path(pdf_path)
    
    if not pdf_file.exists():
        print(f"Error: PDF file not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Parsing MSA PDF: {pdf_path}", file=sys.stderr)
    print(f"Server URL: {server_url}", file=sys.stderr)
    
    # Prepare the file upload
    with open(pdf_file, 'rb') as f:
        files = {'file': (pdf_file.name, f, 'application/pdf')}
        
        try:
            # Make request to parse-msa endpoint
            print("Sending request to server...", file=sys.stderr)
            response = requests.post(
                f"{server_url}/api/parse-msa",
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
            
            # Extract the MSA data
            msa_data = data.get('msa_data', {})
            
            # Determine output path
            if output_path is None:
                output_path = pdf_file.stem + "_msa.json"
            
            # Save to output file
            output_file = Path(output_path)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(msa_data, f, indent=2, ensure_ascii=False)
            
            print(f"\n✅ Success! MSA data saved to: {output_path}", file=sys.stderr)
            print(f"Filename: {data.get('filename', 'N/A')}", file=sys.stderr)
            print(f"\nExtracted fields:", file=sys.stderr)
            print(f"  - MSA ID: {msa_data.get('msa_id', 'N/A')}", file=sys.stderr)
            print(f"  - Effective Date: {msa_data.get('effective_date', 'N/A')}", file=sys.stderr)
            print(f"  - Customer: {msa_data.get('customer', {}).get('legal_name', 'N/A')}", file=sys.stderr)
            print(f"  - Provider: {msa_data.get('provider', {}).get('legal_name', 'N/A')}", file=sys.stderr)
            
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
        description="Parse an MSA PDF file and extract structured data"
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
        default=None,
        help="Output JSON file path (default: {pdf_name}_msa.json)"
    )
    parser.add_argument(
        "--server",
        "-s",
        type=str,
        default="http://localhost:6969",
        help="Server URL (default: http://localhost:6969)"
    )
    
    args = parser.parse_args()
    
    parse_msa_pdf(args.pdf_path, args.output, args.server)


if __name__ == "__main__":
    main()

