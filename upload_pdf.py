#!/usr/bin/env python3
"""
Direct PDF upload script - uploads a PDF file directly to the server without UI.
"""
import requests
import sys
import os
from pathlib import Path

def upload_pdf(file_path: str, server_url: str = "http://localhost:6969", query: str = None):
    """
    Upload a PDF file directly to the server.
    
    Args:
        file_path: Path to the PDF file
        server_url: Server URL (default: http://localhost:6969)
        query: Optional custom query/prompt (uses default contract parsing if None)
    """
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return False
    
    if not file_path.lower().endswith('.pdf'):
        print(f"Error: File must be a PDF: {file_path}")
        return False
    
    print(f"Uploading PDF: {file_path}")
    print(f"Server: {server_url}")
    print(f"File size: {os.path.getsize(file_path) / 1024:.2f} KB")
    print("-" * 50)
    
    try:
        # Prepare the file for upload
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, 'application/pdf')}
            data = {}
            if query:
                data['query'] = query
            
            # Upload and process
            print("Sending request to server...")
            response = requests.post(
                f"{server_url}/api/process-pdf",
                files=files,
                data=data,
                timeout=600  # 10 minutes timeout for large files
            )
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ Success!")
            print(f"Filename: {result.get('filename', 'N/A')}")
            print(f"Query: {result.get('query', 'N/A')[:100]}...")
            print(f"\n📄 Response:\n")
            print(result.get('response', 'No response'))
            
            # Optionally save response to file
            output_file = Path(file_path).stem + "_response.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(result.get('response', ''))
            print(f"\n💾 Response saved to: {output_file}")
            return True
        else:
            print(f"\n❌ Error: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Details: {error_data.get('detail', 'Unknown error')}")
            except:
                print(f"Response: {response.text[:500]}")
            return False
            
    except requests.exceptions.Timeout:
        print("\n❌ Error: Request timed out. The document may be too large.")
        print("Try increasing the timeout or processing the document in chunks.")
        return False
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Error: Could not connect to server at {server_url}")
        print("Make sure the server is running: python app.py")
        return False
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False


if __name__ == "__main__":
    # Default file path
    default_file = "/Users/sanatmouli/Desktop/BLUESTONE & Inter Intel MSA PE 20190528.pdf"
    
    # Get file path from command line or use default
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = default_file
    
    # Optional: custom query from command line
    query = None
    if len(sys.argv) > 2:
        query = sys.argv[2]
    
    # Optional: server URL from command line
    server_url = "http://localhost:6969"
    if len(sys.argv) > 3:
        server_url = sys.argv[3]
    
    success = upload_pdf(file_path, server_url, query)
    sys.exit(0 if success else 1)


