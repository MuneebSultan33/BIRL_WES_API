import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from jose import JWTError, jwt

# Initialize the API
app = FastAPI(title="BIRL WES Pipeline API", description="Backend for Exome-Seq Processing (v0.1 Demo)")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- REAL AUTH SETUP ---
# NOTE: SECRET_KEY below is a placeholder for local/dev testing only.
# Before sharing this deployment with anyone else, replace it with a long
# random string stored as an environment variable (not hardcoded in code).
SECRET_KEY = "CHANGE_THIS_TO_A_LONG_RANDOM_STRING_BEFORE_SHARING"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Password is now stored as a real bcrypt hash, not plaintext.
# This hash corresponds to the password: "secretpassword"
fake_users_db = {
    "muneeb": {
        "username": "muneeb",
        "hashed_password": pwd_context.hash("secretpassword")
    }
}

jobs_db = {}

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

# MOCK PIPELINE — simulates timing only. Does NOT call FastQC/BWA-MEM/GATK yet.
# Real tool integration = Task 3 remaining work.
async def run_wes_pipeline_MOCK(job_id: str, user: str):
    """Simulates the hours-long WES computational pipeline."""
    jobs_db[job_id] = "Running Step 1: FastQC & Trimmomatic (MOCKED)..."
    await asyncio.sleep(10)

    jobs_db[job_id] = "Running Step 2: BWA-MEM Alignment & Picard Dedup (MOCKED)..."
    await asyncio.sleep(10)

    jobs_db[job_id] = "Running Step 3: GATK Mutect2 Somatic Variant Calling (MOCKED)..."
    await asyncio.sleep(10)

    jobs_db[job_id] = "Completed. Output: .maf file simulated."

# --- ENDPOINT 1: Token Generation (now issues a real signed JWT) ---
@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user_dict = fake_users_db.get(form_data.username)
    if not user_dict or not verify_password(form_data.password, user_dict["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect credentials")

    access_token = create_access_token(data={"sub": user_dict["username"]})
    return {"access_token": access_token, "token_type": "bearer"}

# --- ENDPOINT 2: Submit WES Job ---
@app.post("/run-wes-pipeline")
async def start_pipeline(background_tasks: BackgroundTasks, token: str = Depends(oauth2_scheme)):
    username = decode_token(token)
    job_id = str(uuid.uuid4())[:8]
    jobs_db[job_id] = "Queued"

    background_tasks.add_task(run_wes_pipeline_MOCK, job_id, username)

    return {"message": "Mock pipeline initiated in background", "job_id": job_id, "user": username}

# --- ENDPOINT 3: Check Job Status ---
@app.get("/job-status/{job_id}")
async def get_job_status(job_id: str, token: str = Depends(oauth2_scheme)):
    decode_token(token)
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job ID not found")

    return {"job_id": job_id, "current_status": jobs_db[job_id]}