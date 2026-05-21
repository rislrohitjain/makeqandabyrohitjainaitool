import os
import uuid
import shutil
import asyncio
import polars as pl
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.agents import AgentStateTracker
from app.pipeline import QAPipeline

app = FastAPI(
    title="Automated Rohit Jain's Question Paper & Answer Key API",
    description="REST API for the AI-driven Rohit Jain's assessment engine that automates the generation of structured question papers.",
    version="1.0.0"
)

# Enable CORS for mobile & web apps
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global in-memory job status store
JOBS_STATUS: Dict[str, Dict[str, Any]] = {}

# Ensure folders exist
STORAGE_DIR = "storage"
TEMP_DIR = os.path.join(STORAGE_DIR, "temp")
OUTPUTS_DIR = os.path.join(STORAGE_DIR, "outputs")
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)


def validate_api_inputs(mobile_number: str, exam_title: str, files: List[UploadFile]) -> List[str]:
    """
    Validates form fields and uploads according to client uploader rules:
    - Mobile number exactly 10 digits
    - Exam title <= 10 words
    - Maximum 5 files
    - Only PDF, DOCX, TXT allowed
    """
    errors = []
    
    # 1. Mobile validation
    if not mobile_number:
        errors.append("Mobile number is required.")
    elif not mobile_number.isdigit():
        errors.append("Mobile number must contain digits only.")
    elif len(mobile_number) != 10:
        errors.append("Mobile number must be exactly 10 digits.")

    # 2. Exam Title validation
    if not exam_title:
        errors.append("Exam Title is required.")
    else:
        word_count = len(exam_title.split())
        if word_count > 10:
            errors.append(f"Exam Title must be <= 10 words (currently {word_count} words).")

    # 3. File Upload validation
    if not files:
        errors.append("At least one document file must be uploaded.")
    elif len(files) > 5:
        errors.append("Maximum 5 files are allowed. Please remove extra files.")
    else:
        for f in files:
            ext = os.path.splitext(f.filename)[1].lower()
            if ext not in [".pdf", ".docx", ".txt"]:
                errors.append(f"Format not supported for file '{f.filename}'. Only PDF, DOCX, and TXT are allowed.")
                
    return errors


async def execute_generation_pipeline(
    session_id: str,
    temp_paths: List[str],
    exam_title: str,
    mobile_number: str,
    distractor_count: int,
    set_count: int,
    questions_per_set: int
):
    """
    Executes the pipeline inside the background task and updates the job status dict.
    """
    # 1. Initialize tracker in the status store
    JOBS_STATUS[session_id] = {
        "session_id": session_id,
        "status": "Processing",
        "progress": 0,
        "message": "🤖 Booting Q&A Robotic Synthesis Engine...",
        "subagent_states": {
            "Supervisor Orchestrator": "Idle",
            "Ingestion Quality Evaluator": "Idle",
            "Structural Chunking Planner": "Idle",
            "Item Gen Specialist A": "Idle",
            "Item Gen Specialist B": "Idle",
            "Item Gen Specialist C": "Idle",
            "Distractor Variation Designer": "Idle",
            "Deduplication Vector Analyzer": "Idle",
            "Format Verification Auditor": "Idle",
            "Package Cryptography Agent": "Idle"
        },
        "logs": [],
        "files": None,
        "result": None,
        "error": None
    }
    
    # Callback to feed the tracker updates directly to the status store
    def api_tracker_callback():
        if session_id not in JOBS_STATUS:
            return
        states = tracker.get_states()
        logs = tracker.get_logs()
        JOBS_STATUS[session_id]["subagent_states"] = states
        JOBS_STATUS[session_id]["logs"] = logs
        
        # Estimate overall progress (0-100%)
        completed_cores = sum(1 for state in states.values() if state == "Complete")
        JOBS_STATUS[session_id]["progress"] = int((completed_cores / len(states)) * 100)
        
        # Current active core status
        active_core = next((name for name, state in states.items() if state == "Processing"), None)
        if active_core:
            JOBS_STATUS[session_id]["message"] = f"🤖 Core active: {active_core}..."
        elif completed_cores == len(states):
            JOBS_STATUS[session_id]["message"] = "🏆 Robotic Convergence Achieved! Packaging complete."
        else:
            JOBS_STATUS[session_id]["message"] = "Orchestrating agent cores..."

    tracker = AgentStateTracker(on_update_callback=api_tracker_callback)
    
    try:
        pipeline = QAPipeline(tracker)
        df_result = await pipeline.execute(
            file_paths=temp_paths,
            exam_title=exam_title,
            mobile_number=mobile_number,
            session_id=session_id,
            distractor_count=distractor_count,
            set_count=set_count,
            questions_per_set=questions_per_set
        )
        
        # Read files generated inside output folder
        out_dir = f"storage/outputs/{mobile_number}/{session_id}"
        
        # Check files existence
        zip_exists = os.path.exists(os.path.join(out_dir, "output.zip"))
        xlsx_exists = os.path.exists(os.path.join(out_dir, "questions.xlsx"))
        
        files_info = {
            "zip_package": f"/api/download/{mobile_number}/{session_id}/output.zip" if zip_exists else None,
            "excel_sheet": f"/api/download/{mobile_number}/{session_id}/questions.xlsx" if xlsx_exists else None,
            "pdfs": {}
        }
        
        # Capture generated PDF set paths dynamically
        if "Set" in df_result.columns:
            unique_sets = df_result["Set"].unique().sort().to_list()
            for set_name in unique_sets:
                set_filename = f"{set_name.replace(' ', '_')}.pdf"
                if os.path.exists(os.path.join(out_dir, set_filename)):
                    files_info["pdfs"][set_name] = f"/api/download/{mobile_number}/{session_id}/{set_filename}"
        
        # Update the job status to complete
        JOBS_STATUS[session_id].update({
            "status": "Complete",
            "progress": 100,
            "message": "🏆 Robotic Convergence Achieved! All cores nominal.",
            "files": files_info,
            "result": {
                "total_questions": len(df_result),
                "questions": df_result.to_dicts()
            }
        })
        
        # Save a persistent status json in the output directory
        status_path = os.path.join(out_dir, "status.json")
        import json
        with open(status_path, "w") as sf:
            json.dump({
                "session_id": session_id,
                "status": "Complete",
                "message": "Robotic synthesis complete.",
                "files": files_info,
                "total_questions": len(df_result)
            }, sf, indent=4)
            
    except Exception as e:
        JOBS_STATUS[session_id].update({
            "status": "Failed",
            "message": f"❌ Core pipeline execution aborted: {str(e)}",
            "error": str(e)
        })
    finally:
        # Cleanup temporary uploaded files
        for p in temp_paths:
            try:
                os.remove(p)
            except Exception:
                pass


@app.post("/api/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_qa_bank_async(
    background_tasks: BackgroundTasks,
    mobile_number: str = Form(..., description="10-digit mobile number used as ZIP encryption PIN"),
    exam_title: str = Form(..., description="Running title appearing on exam paper headers"),
    distractor_count: int = Form(4, description="Number of distractor options (choices A, B, C...)"),
    set_count: int = Form(1, description="Number of distinct question sets to generate"),
    questions_per_set: int = Form(5, description="Number of questions per set"),
    files: List[UploadFile] = File(..., description="Allowed formats: PDF, DOCX, TXT (Max 5 files)")
):
    """
    Submits a robotic Q&A generation request. 
    Returns immediately with a `session_id`. Use this session ID to poll the `/api/status/{session_id}` endpoint.
    """
    # 1. Validate inputs
    errors = validate_api_inputs(mobile_number, exam_title, files)
    if errors:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error_code": "VALIDATION_FAILED",
                "message": "Robotic Validation Scan Failed",
                "errors": errors
            }
        )
        
    # 2. Setup isolated session
    session_id = str(uuid.uuid4())[:8]
    temp_paths = []
    
    # Save uploaded files to temp directory
    for f in files:
        safe_filename = f.filename.replace(" ", "_")
        temp_path = os.path.join(TEMP_DIR, f"{session_id}_{safe_filename}")
        save_upload_file(f, temp_path)
        temp_paths.append(temp_path)
        
    # 3. Add execution block as background task
    background_tasks.add_task(
        execute_generation_pipeline,
        session_id=session_id,
        temp_paths=temp_paths,
        exam_title=exam_title,
        mobile_number=mobile_number,
        distractor_count=distractor_count,
        set_count=set_count,
        questions_per_set=questions_per_set
    )
    
    return {
        "session_id": session_id,
        "status": "Accepted",
        "message": "Q&A generation started in the background.",
        "status_url": f"/api/status/{session_id}"
    }


@app.post("/api/generate-sync")
async def generate_qa_bank_sync(
    mobile_number: str = Form(...),
    exam_title: str = Form(...),
    distractor_count: int = Form(4),
    set_count: int = Form(1),
    questions_per_set: int = Form(5),
    files: List[UploadFile] = File(...)
):
    """
    Generates Q&A bank synchronously. Keeps the connection open until generation finishes.
    """
    errors = validate_api_inputs(mobile_number, exam_title, files)
    if errors:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error_code": "VALIDATION_FAILED",
                "message": "Robotic Validation Scan Failed",
                "errors": errors
            }
        )
        
    session_id = str(uuid.uuid4())[:8]
    temp_paths = []
    for f in files:
        safe_filename = f.filename.replace(" ", "_")
        temp_path = os.path.join(TEMP_DIR, f"{session_id}_{safe_filename}")
        save_upload_file(f, temp_path)
        temp_paths.append(temp_path)
        
    # Run pipeline synchronously in this thread
    await execute_generation_pipeline(
        session_id=session_id,
        temp_paths=temp_paths,
        exam_title=exam_title,
        mobile_number=mobile_number,
        distractor_count=distractor_count,
        set_count=set_count,
        questions_per_set=questions_per_set
    )
    
    job = JOBS_STATUS.get(session_id)
    if not job:
        raise HTTPException(status_code=500, detail="Failed to retrieve generation job.")
        
    if job["status"] == "Failed":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": job["message"], "error": job["error"]}
        )
        
    return {
        "session_id": session_id,
        "status": job["status"],
        "files": job["files"],
        "result": job["result"]
    }


@app.get("/api/status/{session_id}")
async def get_job_status(session_id: str):
    """
    Returns the real-time agent execution status, telemetry stream logs, and progress.
    Once progress reaches 100% and status is 'Complete', files info and results are included.
    """
    job = JOBS_STATUS.get(session_id)
    if not job:
        # Check if it was saved locally in a session directory
        # Search outputs folders for status.json
        for root, dirs, files in os.walk(OUTPUTS_DIR):
            if session_id in root and "status.json" in files:
                import json
                try:
                    with open(os.path.join(root, "status.json"), "r") as f:
                        saved_status = json.load(f)
                    return saved_status
                except Exception:
                    pass
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Generation session '{session_id}' not found."
        )
    return job


@app.get("/api/download/{mobile_number}/{session_id}/{filename}")
async def download_output_file(mobile_number: str, session_id: str, filename: str):
    """
    Serves generated ZIP packages, Excel files, and PDF papers.
    """
    file_path = os.path.join(OUTPUTS_DIR, mobile_number, session_id, filename)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requested file does not exist or has been deleted."
        )
        
    # Set custom user-friendly filenames for downloads
    download_name = filename
    if filename == "output.zip":
        download_name = f"Complete_Robotic_QA_Bank_Package_{mobile_number}.zip"
    elif filename == "questions.xlsx":
        download_name = f"Questions_&_Answers_Bank_{session_id}.xlsx"
        
    return FileResponse(
        path=file_path,
        filename=download_name,
        media_type="application/octet-stream"
    )


@app.get("/api/developer")
async def get_developer_profile():
    """
    Returns details of the developer, Rohit Jain.
    """
    return {
        "developer_name": "Rohit Jain",
        "designation": "Sr. Software Engineer",
        "qualifications": ["BCA", "MCA"],
        "specialties": [
            "AI Solutions Architect",
            "Full Stack Architect",
            "LLM Agentic Pipelines",
            "Enterprise Automation Solutions"
        ],
        "portfolio_url": "https://rohitjain-resume.vercel.app/",
        "contact_info": {
            "email": "engrohitjain5@gmail.com",
            "phone": "+91 89469 19241"
        }
    }


@app.get("/api/flowchart")
async def get_project_flowchart():
    """
    Returns the basic project execution flow steps.
    """
    return {
        "steps": [
            {
                "step_number": 1,
                "title": "Document Ingestion",
                "description": "Upload source files (PDF, DOCX, TXT) with validation checks."
            },
            {
                "step_number": 2,
                "title": "Contextual Text Chunking",
                "description": "Clean raw texts and split into semantic chunks."
            },
            {
                "step_number": 3,
                "title": "Multi-Agent Item Synthesis",
                "description": "Specialist subagents parallelly generate question stems, option alternatives, and correct keys."
            },
            {
                "step_number": 4,
                "title": "De-duplication & Vector Audit",
                "description": "Filters similar questions using Cosine Similarity."
            },
            {
                "step_number": 5,
                "title": "Secure Export Compilation",
                "description": "Renders custom PDF papers and compiles a password-secured ZIP package."
            }
        ]
    }
