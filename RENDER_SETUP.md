# Render Deployment Setup Guide

## The Problem
Render is trying to build `pydantic-core` from source, which requires Rust/Cargo. The build fails because Cargo tries to write to `/usr/local/cargo` which is read-only.

## Solution Steps

### Option 1: Use render.yaml (Recommended)
1. Make sure `render.yaml` is committed to your repository
2. In Render Dashboard, go to your service settings
3. Under "Build & Deploy", ensure "Auto-Deploy" is enabled
4. Render should automatically detect and use `render.yaml`

### Option 2: Manual Configuration
If `render.yaml` isn't working, configure manually:

1. **Python Version**: 
   - Go to Settings → Environment
   - Set `PYTHON_VERSION` = `3.12` (NOT 3.13 - no wheels available)

2. **Build Command**:
   ```
   ./build.sh
   ```

3. **Start Command**:
   ```
   uvicorn app:app --host 0.0.0.0 --port $PORT
   ```

4. **Environment Variables** (in Render Dashboard):
   - `CARGO_HOME` = `/tmp/cargo`
   - `RUSTUP_HOME` = `/tmp/rustup`
   - `PIP_PREFER_BINARY` = `1`

### Option 3: Alternative - Use Older Pydantic
If the above doesn't work, try using pydantic 2.4.x which has better wheel support:

Update `requirements.txt`:
```
pydantic==2.4.2
pydantic-core==2.10.1
```

## Troubleshooting

1. **Check Build Logs**: Look for "=== Starting build script ===" - if you don't see this, the build script isn't running
2. **Check Python Version**: Look for "Python version: 3.13" - if you see 3.13, that's the problem
3. **Verify Files**: Make sure `build.sh` is executable and committed to git

## Files to Commit
- `build.sh` (must be executable)
- `render.yaml`
- `runtime.txt`
- `requirements.txt`

