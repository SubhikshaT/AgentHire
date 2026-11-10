# Windows setup (VS Code, PowerShell)

No Docker, no paid services. Tested commands are the same as in the README; this page adds install
notes and troubleshooting.

## 1. Install the tools
| Tool | Where | Notes |
|---|---|---|
| Python 3.11 | python.org/downloads | Tick "Add python.exe to PATH". `py -3.11 --version` should work |
| Node.js LTS | nodejs.org | `node -v`, `npm -v` |
| PostgreSQL 16 or 17 | postgresql.org/download/windows (EDB installer) | Remember the `postgres` password. Add `C:\Program Files\PostgreSQL\16\bin` to PATH for `psql` |
| Git | git-scm.com | |
| VS Code | code.visualstudio.com | Python + ESLint extensions are helpful |
| Ollama (optional) | ollama.com/download | Needed only for AI question generation / answer evaluation |

### pgvector on Windows
Option A – prebuilt: some EDB installs offer pgvector in **Application Stack Builder** (Database Server → extensions). If listed, install it.

Option B – build from source (needs "Visual Studio Build Tools" with C++):
```bat
REM Run in "x64 Native Tools Command Prompt for VS" as Administrator
set "PGROOT=C:\Program Files\PostgreSQL\16"
git clone --branch v0.8.0 https://github.com/pgvector/pgvector.git
cd pgvector
nmake /F Makefile.win
nmake /F Makefile.win install
```
Then in psql: `CREATE EXTENSION IF NOT EXISTS vector;`

**If pgvector will not install:** set `VECTOR_BACKEND=python` in `backend\.env` *before* running
`alembic upgrade head`. Embeddings are then stored as float arrays and similarity is computed in Python.
Everything works the same (both modes are tested). To switch later, drop and recreate the database.

## 2. Create the databases
```powershell
psql -U postgres -c "CREATE DATABASE agenthire;"
psql -U postgres -c "CREATE DATABASE agenthire_test;"
# only if pgvector is installed:
psql -U postgres -d agenthire -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql -U postgres -d agenthire_test -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

## 3. Backend
```powershell
cd AgentHire\backend
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt          # includes CPU-only PyTorch (~200 MB)
python -m spacy download en_core_web_sm
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"   # paste into SECRET_KEY
notepad .env                              # set your postgres password in both URLs, choose LLM_PROVIDER
alembic upgrade head
python ..\scripts\seed_demo_data.py       # optional demo data (~1 minute; downloads the embedding model once)
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## 4. Frontend (second terminal)
```powershell
cd AgentHire\frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```
Open http://localhost:3000. Demo logins: `demo.recruiter@example.com` / `DemoPass123` and `aarav.raman@example.com` / `DemoPass123`.

## 5. Optional: local AI with Ollama
```powershell
ollama pull qwen2.5:7b        # ~4.7 GB, needs about 8 GB free RAM
# low-RAM laptops:  ollama pull llama3.2:3b  and set OLLAMA_MODEL=llama3.2:3b
```
In `backend\.env`: `LLM_PROVIDER=ollama`, `OLLAMA_MODEL=qwen2.5:7b`. Restart the backend.
Settings → AI provider shows whether it is reachable.

Gemini instead: `LLM_PROVIDER=gemini`, `GEMINI_API_KEY=...`, `GEMINI_MODEL=<a current Gemini model id>`.

## Troubleshooting
| Problem | Fix |
|---|---|
| `Activate.ps1 cannot be loaded` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `pip install` fails on torch | Use Python 3.11 64-bit. Re-run `pip install -r requirements.txt` (it uses the PyTorch CPU index) |
| `npm install` errors | Delete the `node_modules` folder (keep `package-lock.json`), run `npm cache verify`, then `npm install` |
| `connection refused` to PostgreSQL | Start the "postgresql-x64-16" service (services.msc); check port 5432 and the password in `.env` |
| `extension "vector" is not available` | Install pgvector (above) or set `VECTOR_BACKEND=python` |
| `SECRET_KEY is still the placeholder value` | Generate a secret (see step 3) |
| Port 8000 or 3000 in use | `netstat -ano | findstr :8000` then `taskkill /PID <pid> /F`, or use another port (`BACKEND_URL` in `frontend\.env.local`) |
| Frontend shows "Cannot reach the backend" | Backend not running, or `BACKEND_URL` wrong |
| Embedding model download fails | Needs internet once (Hugging Face). After that it is cached in `%USERPROFILE%\.cache\huggingface` |
| spaCy model missing | `python -m spacy download en_core_web_sm` (parsing still works without it, names are detected by rules) |
| Ollama "not reachable" | Run `ollama serve`; check `http://localhost:11434` in a browser; model pulled with the exact name in `.env` |
| Ollama out of memory / very slow | Use `llama3.2:3b`; close other apps; raise `LLM_TIMEOUT_SECONDS` |
| Resume "No text found" | It is a scanned image PDF; OCR is not supported. Export a text PDF or DOCX |
| E2E tests get 429 | Start the backend with `$env:RATE_LIMIT_ENABLED="false"` while running Playwright |
