# Resume AI Platform — Backend

Pure Python FastAPI Backend for Resume AI, ATS Scoring, and Career Management.

## Setup & Run

1. **Activate Virtual Environment:**
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

2. **Install Dependencies (if not already installed):**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run Development Server:**
   ```bash
   python run.py
   # OR
   uvicorn app.main:app --reload --port 8000
   ```

4. **Interactive API Documentation:**
   * Swagger UI: http://127.0.0.1:8000/docs
   * ReDoc: http://127.0.0.1:8000/redoc
