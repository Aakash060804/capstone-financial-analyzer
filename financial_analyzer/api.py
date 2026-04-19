"""
FastAPI backend — runs the financial analysis pipeline on demand.
Deploy on Railway: railway up
"""
import json, os, subprocess, uuid
from pathlib import Path
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

BASE = Path(__file__).parent
OUTPUTS = BASE / "outputs"
OUTPUTS.mkdir(exist_ok=True)

app = FastAPI(title="FinAnalyzer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job tracker: company -> status dict
jobs: dict[str, dict] = {}


@app.get("/")
def root():
    return {"status": "ok", "message": "FinAnalyzer API is running"}


@app.get("/data/{company}")
def get_data(company: str):
    path = OUTPUTS / f"{company.upper()}_financial_data.json"
    if path.exists():
        return JSONResponse(content=json.loads(path.read_text()))
    return JSONResponse(status_code=404, content={"error": "not_found"})


@app.post("/analyze/{company}")
def analyze(company: str, background_tasks: BackgroundTasks):
    slug = company.upper()
    path = OUTPUTS / f"{slug}_financial_data.json"

    # Already cached — return immediately
    if path.exists():
        return {"status": "cached", "company": slug}

    # Already running
    if jobs.get(slug, {}).get("status") == "running":
        return {"status": "running", "company": slug}

    # Start pipeline in background
    jobs[slug] = {"status": "running", "company": slug, "message": "Pipeline started…", "started_at": time.time(), "step": 0}
    background_tasks.add_task(run_pipeline, slug)
    return {"status": "started", "company": slug}


@app.get("/status/{company}")
def get_status(company: str):
    slug = company.upper()
    path = OUTPUTS / f"{slug}_financial_data.json"
    if path.exists():
        jobs.pop(slug, None)
        return {"status": "done", "company": slug}

    job = jobs.get(slug)
    if not job:
        return {"status": "not_started"}

    # Auto-timeout after 2 minutes
    elapsed = time.time() - job.get("started_at", time.time())
    if elapsed > 120 and job["status"] == "running":
        jobs[slug] = {**job, "status": "error", "message": "Pipeline timed out. Try again."}

    return jobs[slug]


def run_pipeline(company: str):
    try:
        jobs[company]["message"] = "Scraping data from Screener.in…"
        result = subprocess.run(
            ["python", "main.py", "--company", company, "--fast"],
            cwd=BASE,
            capture_output=True,
            text=True,
            timeout=120,   # hard 2-min cap; --fast should finish in ~30s
            env={**os.environ},
        )
        if result.returncode == 0:
            jobs[company] = {"status": "done", "company": company}
        else:
            err = result.stderr[-800:] if result.stderr else result.stdout[-800:]
            jobs[company] = {"status": "error", "company": company, "error": err}
    except subprocess.TimeoutExpired:
        jobs[company] = {"status": "error", "company": company, "error": "Pipeline timed out after 8 minutes"}
    except Exception as e:
        jobs[company] = {"status": "error", "company": company, "error": str(e)}
