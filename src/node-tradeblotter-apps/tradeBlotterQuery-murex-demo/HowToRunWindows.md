```markdown
# Local Setup and Run Guide (Windows)

This guide explains how to set up and run all three services on Windows:

- Python API: `tradeQueryApi`
- Python MCP HTTP wrapper: `mcp_http_server`
- Node.js desktop/web frontend

---

## 0. Summary of Terminals // if you are ready otherwise read below

You should end up with three running terminals:

1. **tradeQueryApi**
    - Python venv active
    - Command: `python.exe .\main.py`
    - Port: `8000`
2. **mcp_http_server**
    - Python venv active
    - Command: `uvicorn mcp_http_server:app --port 7001`
    - Port: `7001`
3. **Node.js desktop/web app**
    - Command: `node --env-file=../.env server.js`
    - Port: `5173` (as printed by the app)

## 1. Create and Prepare the Python Virtual Environment

From the project root (where `requirements.txt` lives):

```bash
# Create virtual environment (if not yet created)
python -m venv .venv

# Activate venv (PowerShell)
.\.venv\Scripts\Activate.ps1

# or in cmd.exe
.\.venv\Scripts\activate.bat

# Install Python dependencies
pip install -r requirements.txt
```

Make sure you see `(.venv)` at the start of your prompt, indicating the environment is active.

---

## 2. Create the `.env` Configuration File

In the project root, create a file named `.env` with the following content:

```env
# Local debugging
MCP_HTTP_BASE_URL=http://localhost:7001
TRADE_API_BASE_URL=http://localhost:8000
```

This file will be used by both the Python services and the Node.js frontend.

---

## 3. Start `tradeQueryApi` (Python)

1. Open a **new terminal** in the project root.
2. Activate the virtual environment:

```bash
..\..\..\..\ .venv\Scripts\Activate.ps1
```

(Adjust the relative path so it correctly points to your `.venv`. From the `tradeQueryApi` folder, the idea is to move up to the root where `.venv` lives and activate it.)
3. Change directory to the `tradeQueryApi` folder.
4. Run the API:

```bash
python.exe .\main.py
```


If everything is correct, you should see output similar to:

```text
INFO:     Started server process 
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```


---

## 4. Start `mcp_http_server` (Python MCP Wrapper)

`mcp_http_server.py` wraps the MCP server behind an HTTP interface.

1. Open another **new terminal**.
2. Activate the same virtual environment from the project root:

```bash
..\..\..\..\ .venv\Scripts\Activate.ps1
```

(Again, adjust the relative path according to where your `mcp` folder sits.)
3. Change directory to:

```text
${workspaceFolder}/src/node-tradeblotter-apps/tradeBlotterQuery-murex-demo/mcp
```

4. Start the MCP HTTP server:

```bash
uvicorn mcp_http_server:app --port 7001
```


If all is good, you should see:

```text
INFO:     Started server process 
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:7001 (Press CTRL+C to quit)
```


---

## 5. Install Node.js Dependencies for the Desktop/Web App

1. Open another **new terminal**.
2. Go to the desktop/web frontend folder (for example):

```bash
cd path\to\desktopApp
```

3. Install Node.js dependencies:

```bash
npm install
```


This reads `package.json` in `desktopApp` and installs all required packages into `node_modules`.

---

## 6. Start the Node.js Desktop/Web Frontend

From the same `desktopApp` folder:

```bash
node --env-file=../.env server.js
```

Notes:

- This uses Node’s native `--env-file` flag (Node 20+) to load the `.env` file from the parent directory.
- Ensure the relative path `../.env` is correct based on where `server.js` is located.

If everything worked, you should see something like:

```text
Desktop app running on http://localhost:5173
```

Open that URL in your browser to access the frontend.

---


```

