# PDF Chat Server

A web application that allows you to upload PDF files and chat with them using Qwen3-32B via LangChain.

## Features

- 🎯 Drag and drop PDF upload
- 📄 PDF text extraction
- 🤖 Chat with PDFs using Qwen3-32B
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

2. (Optional) Update configuration in `.env` file or environment variables:
   - `OPENAI_API_KEY`: Your API key
   - `OPEN_AI_MODEL`: Model name (default: Qwen3-32B)
   - `OPENAI_TEMPERATURE`: Temperature setting (default: 0)
   - `INFERENCE_SERVER_URL`: Your inference server URL

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

## Project Structure

```
qwentest/
├── app.py              # FastAPI server with LangChain integration
├── static/
│   └── index.html      # Web UI with drag-and-drop
├── requirements.txt    # Python dependencies
├── .env               # Configuration (optional)
└── README.md          # This file
```

