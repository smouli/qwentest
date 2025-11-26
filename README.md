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
├── static/
│   └── index.html      # Web UI with drag-and-drop
├── requirements.txt    # Python dependencies
├── build.sh           # Build script for Render deployment
├── render.yaml        # Render deployment configuration
├── .env               # Configuration (optional)
└── README.md          # This file
```

