# PDF Chat Server

A web application that allows you to upload PDF files and chat with them using Qwen3-32B via LangChain.

## Features

- 🎯 Drag and drop PDF upload
- 📄 PDF text extraction
- 🤖 Chat with PDFs using Qwen3-32B
- 📋 MSA (Master Service Agreement) structured parsing
- 🎨 Modern, responsive UI
- ⚡ Fast API with FastAPI

## Setup

1. Create and activate a virtual environment (recommended to avoid "externally managed environment" errors):
```bash
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# or on Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your OpenAI API key:
   ```bash
   OPENAI_API_KEY=sk-proj-your-api-key-here
   OPEN_AI_MODEL=gpt-4o
   OPENAI_TEMPERATURE=0
   ```
   
   Or set environment variables:
   - `OPENAI_API_KEY`: Your OpenAI API key (required)
   - `OPEN_AI_MODEL`: Model name (default: gpt-4o)
   - `OPENAI_TEMPERATURE`: Temperature setting (default: 0)

3. Run the server:
```bash
python app.py
```

Or using uvicorn directly:
```bash
uvicorn app:app --host 0.0.0.0 --port 6969 --reload
```

4. Open your browser and navigate to:
```
http://localhost:6969
```

## Usage

1. Drag and drop a PDF file onto the upload area, or click to browse
2. (Optional) Enter a custom query/question
3. Click "Process PDF" to extract text and get a response from the LLM
4. View the response in the response box

## API Endpoints

- `GET /` - Serve the web UI
- `POST /api/upload-pdf` - Upload and extract text from PDF
- `POST /api/chat` - Send text to LLM and get response
- `POST /api/process-pdf` - Upload PDF, extract text, and get LLM response in one call
- `POST /api/parse-msa` - Parse MSA PDF and extract structured data according to MSA schema

## MSA Parsing

The application includes a specialized parser for Master Service Agreements (MSAs) that extracts structured data according to a comprehensive schema.

### Using the MSA Parser

#### Via API

**Important:** Use `@` before the file path to indicate file upload:

```bash
curl -X POST "http://localhost:6969/api/parse-msa" \
  -F "file=@/path/to/your_msa.pdf"
```

**Note:** Very large documents (>50KB text) may timeout. If you encounter timeout errors, try:
- Using the Python script instead (see below)
- Processing smaller documents
- Splitting the document into sections

#### Via Python Script

```bash
python parse_msa.py path/to/msa.pdf --output msa_data.json
```

### MSA Schema

The parser extracts structured data including:
- **Basic Information**: MSA ID, version, dates, governing law
- **Parties**: Customer and provider details (legal names, addresses, contacts, signatories)
- **Services Scope**: Service categories, excluded services, service locations
- **Commercial Terms**: Rate cards, payment terms, discounts, surcharges, taxes
- **Intellectual Property**: Ownership models, license grants, pre-existing IP
- **Confidentiality**: NDA terms, confidentiality periods, exceptions
- **Data Protection**: DPA requirements, data location restrictions, applicable regulations
- **Compliance**: Regulatory compliance, import/export compliance, hazmat provisions
- **Liability & Indemnification**: Indemnification provisions, liability caps, exclusions
- **Warranties**: Service warranties, performance standards, SLAs
- **Termination**: Termination terms, causes, survival clauses
- **Dispute Resolution**: Escalation process, arbitration rules, venue
- **Insurance**: General liability, professional liability, cyber liability
- **General Provisions**: Assignment rights, notices, force majeure
- **Related Documents**: Superseded agreements, incorporated documents, exhibits
- **Execution Details**: Execution dates, signatory information

The output is a structured JSON object matching the schema definition.

## Deployment on Render

This project includes a build script (`build.sh`) and Render configuration (`render.yaml`) to handle Rust-based dependencies (like `pydantic`).

### Automatic Setup (using render.yaml)

If you're using `render.yaml`, the build script will run automatically. Make sure:
1. The `build.sh` file is executable (it should be committed to git)
2. Your Render service is configured to use the `render.yaml` file

### Manual Setup

If you're configuring Render manually:

1. **Set Build Command:**
   ```
   ./build.sh
   ```

2. **Set Start Command:**
   ```
   uvicorn app:app --host 0.0.0.0 --port $PORT
   ```

3. **Set Environment Variables:**
   - `CARGO_HOME` = `$HOME/.cargo`
   - `RUSTUP_HOME` = `$HOME/.rustup`
   - Plus your application variables (OPENAI_API_KEY, etc.)

The build script sets up a writable Cargo directory to avoid "Read-only file system" errors when building Rust-based Python packages.

## Project Structure

```
qwentest/
├── app.py              # FastAPI server with LangChain integration
├── msa_parser.py       # MSA parsing module with schema definition
├── parse_msa.py        # Command-line script for MSA parsing
├── static/
│   └── index.html      # Web UI with drag-and-drop
├── requirements.txt    # Python dependencies
├── build.sh           # Build script for Render deployment
├── render.yaml        # Render deployment configuration
├── .env               # Configuration (optional)
└── README.md          # This file
```

