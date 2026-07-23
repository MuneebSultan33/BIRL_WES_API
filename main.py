import asyncio
import uuid
from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

# Initialize the API
app = FastAPI(title="BIRL WES Pipeline API", description="Backend for Exome-Seq Processing (v0.1 Demo)")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# NOTE: Demo-only auth. Plaintext password, in-memory store, token = username.
# Not real OAuth2/JWT security yet. TODO before production use.
fake_users_db = {
    "muneeb": {"username": "muneeb", "hashed_password": "secretpassword"}
}

# This dictionary will act as our temporary server memory to track running pipelines
jobs_db = {}

# MOCK PIPELINE — simulates timing only. Does NOT call FastQC/BWA-MEM/GATK yet.
# Real tool integration = Task 3 remaining work.
async def run_wes_pipeline_MOCK(job_id: str, user: str):
    """Simulates the hours-long WES computational pipeline."""
    jobs_db[job_id] = "Running Step 1: FastQC & Trimmomatic (MOCKED)..."
    await asyncio.sleep(10) # Pauses for 10 seconds to simulate heavy processing
    
    jobs_db[job_id] = "Running Step 2: BWA-MEM Alignment & Picard Dedup (MOCKED)..."
    await asyncio.sleep(10)
    
    jobs_db[job_id] = "Running Step 3: GATK Mutect2 Somatic Variant Calling (MOCKED)..."
    await asyncio.sleep(10)
    
    jobs_db[job_id] = "Completed. Output: .maf file simulated."

# --- ENDPOINT 1: Token Generation ---
@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user_dict = fake_users_db.get(form_data.username)
    if not user_dict or form_data.password != user_dict["hashed_password"]:
        raise HTTPException(status_code=401, detail="Incorrect credentials")
    return {"access_token": user_dict["username"], "token_type": "bearer"}

# --- ENDPOINT 2: Submit WES Job ---
@app.post("/run-wes-pipeline")
async def start_pipeline(background_tasks: BackgroundTasks, token: str = Depends(oauth2_scheme)):
    # Generate a unique tracking ID for this specific run
    job_id = str(uuid.uuid4())[:8] 
    jobs_db[job_id] = "Queued"
    
    # Hand the heavy WES function to the background so the API doesn't freeze
    background_tasks.add_task(run_wes_pipeline_MOCK, job_id, token)
    
    return {"message": "Mock pipeline initiated in background", "job_id": job_id, "user": token}

# --- ENDPOINT 3: Check Job Status ---
@app.get("/job-status/{job_id}")
async def get_job_status(job_id: str, token: str = Depends(oauth2_scheme)):
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job ID not found")
    
    return {"job_id": job_id, "current_status": jobs_db[job_id]}