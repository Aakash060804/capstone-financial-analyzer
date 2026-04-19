"""
FastAPI backend — runs the financial analysis pipeline on demand.
Deploy on Railway: railway up
"""
import json, os, subprocess, time
from pathlib import Path
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

BASE    = Path(__file__).parent
OUTPUTS = BASE / "outputs"
OUTPUTS.mkdir(exist_ok=True)

app = FastAPI(title="FinAnalyzer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job tracker
jobs: dict[str, dict] = {}

STEP_MESSAGES = [
    "Fetching financial data from Screener.in…",
    "Building canonical statements…",
    "Computing ratios, DuPont & schedules…",
    "Running DCF valuation & Monte Carlo…",
    "Generating AI investment commentary…",
    "Exporting results…",
]


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

    if path.exists():
        return {"status": "cached", "company": slug}

    if jobs.get(slug, {}).get("status") == "running":
        return {"status": "running", "company": slug, **jobs[slug]}

    jobs[slug] = {"status": "running", "company": slug, "step": 0, "message": STEP_MESSAGES[0], "started_at": time.time()}
    background_tasks.add_task(run_pipeline, slug)
    return {"status": "started", "company": slug}


@app.get("/status/{company}")
def get_status(company: str):
    slug = company.upper()
    path = OUTPUTS / f"{slug}_financial_data.json"

    # File exists = done (most reliable signal)
    if path.exists():
        jobs.pop(slug, None)
        return {"status": "done", "company": slug}

    job = jobs.get(slug)
    if not job:
        return {"status": "not_started"}

    # Auto-timeout after 8 minutes
    elapsed = time.time() - job.get("started_at", time.time())
    if elapsed > 480 and job["status"] == "running":
        jobs[slug] = {**job, "status": "error", "message": "Pipeline timed out. Try again."}

    return jobs[slug]


def run_pipeline(company: str):
    def upd(step: int, msg: str = ""):
        jobs[company] = {
            **jobs.get(company, {}),
            "status": "running",
            "step": step,
            "message": msg or STEP_MESSAGES[min(step, len(STEP_MESSAGES) - 1)],
        }

    try:
        upd(0, "Fetching financial data from Screener.in…")
        result = subprocess.run(
            ["python", "main.py", "--company", company],
            cwd=BASE,
            capture_output=True,
            text=True,
            timeout=480,
            env={**os.environ},
        )

        # Parse stdout to advance step counter
        for line in (result.stdout or "").splitlines():
            if "[2/7]" in line or "[2.5/7]" in line:
                upd(1, "Building canonical statements & anomaly detection…")
            elif "[3/7]" in line or "[3.5/7]" in line:
                upd(2, "Computing ratios, DuPont & industry classification…")
            elif "[4/7]" in line:
                upd(4, "Generating AI investment commentary (parallel)…")
            elif "[5/7]" in line or "[5.5/7]" in line or "[2.7/7]" in line:
                upd(3, "Running DCF valuation, WACC & Monte Carlo simulation…")
            elif "[6/7]" in line:
                upd(5, "Building Excel workbook…")
            elif "[7/7]" in line:
                upd(5, "Exporting JSON — almost done…")

        if result.returncode == 0:
            jobs[company] = {"status": "done", "company": company, "step": 6}
        else:
            err = (result.stderr or result.stdout or "Unknown error")[-600:]
            jobs[company] = {"status": "error", "company": company, "message": err}

    except subprocess.TimeoutExpired:
        jobs[company] = {"status": "error", "company": company, "message": "Pipeline timed out after 8 minutes. Try again."}
    except Exception as e:
        jobs[company] = {"status": "error", "company": company, "message": str(e)}
