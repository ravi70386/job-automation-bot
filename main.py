import os
import shutil
import logging
from typing import Optional
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Depends, HTTPException, status, Request, Form, UploadFile, File, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from jose import JWTError, jwt
from crontab import CronTab
import bcrypt

# Import the bot script
from resume_update import run_update

# --- Logging Configuration ---
LOGS_DIR = "logs"
os.makedirs(LOGS_DIR, exist_ok=True)
app_log_file = os.path.join(LOGS_DIR, f"app_{datetime.now().strftime('%Y-%m-%d')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(app_log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("JobBotApp")

# --- Configuration ---
DATABASE_URL = "sqlite:///./bot.db"
SECRET_KEY = os.getenv("SECRET_KEY", "job-automation-bot-secret-key-123")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

# --- Database Setup ---
logger.info("Initializing database...")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

Base.metadata.create_all(bind=engine)

# --- Security ---
def get_password_hash(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    pwd_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(pwd_bytes, hashed_bytes)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure Admin User
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == "admin").first():
            logger.info("Creating default admin user...")
            admin_user = User(username="admin", hashed_password=get_password_hash("admin123"))
            db.add(admin_user)
            db.commit()
    except Exception as e:
        logger.error(f"Error creating admin user: {str(e)}")
    finally:
        db.close()
    yield

# --- App Setup ---
app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")
# Disable cache to avoid unhashable key errors in experimental Python 3.14
templates.env.cache = None

RESUMES_DIR = "resumes"
os.makedirs(RESUMES_DIR, exist_ok=True)

# --- Auth Helper ---
async def get_current_user_from_cookie(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token: return None
    try:
        payload = jwt.decode(token.replace("Bearer ", ""), SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None: return None
        return db.query(User).filter(User.username == username).first()
    except JWTError: 
        logger.warning(f"Invalid JWT token attempt from {request.client.host}")
        return None

# --- UI Routes ---

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = None):
    return templates.TemplateResponse(request, "login.html", {"error": error, "hide_nav": True})

@app.post("/login")
async def login(request: Request, response: RedirectResponse, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    logger.info(f"Login attempt for user: {username} from {request.client.host}")
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        logger.warning(f"Failed login attempt for {username} from {request.client.host}")
        return RedirectResponse(url="/login?error=Invalid credentials", status_code=status.HTTP_303_SEE_OTHER)
    
    access_token = create_access_token(data={"sub": user.username})
    redirect = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    redirect.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    logger.info(f"User {username} logged in successfully")
    return redirect

@app.get("/logout")
async def logout(request: Request):
    logger.info(f"User logging out from {request.client.host}")
    response = RedirectResponse(url="/login")
    response.delete_cookie("access_token")
    return response

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, user: User = Depends(get_current_user_from_cookie)):
    if not user: return RedirectResponse(url="/login")
    
    resumes = sorted([f for f in os.listdir(RESUMES_DIR) if f.lower().endswith(".pdf")])
    logs = sorted(os.listdir(LOGS_DIR), reverse=True)[:10]
    
    # Round Robin detection
    up_next = "None"
    if resumes:
        POINTER_FILE = ".resume_pointer"
        idx = 0
        if os.path.exists(POINTER_FILE):
            try:
                with open(POINTER_FILE, "r") as f:
                    idx = int(f.read().strip())
            except: pass
        up_next = resumes[idx % len(resumes)]

    next_run = "Not Set"
    try:
        cron = CronTab(user=True)
        job = next(cron.find_comment('job-automation-bot'), None)
        if job:
            next_run = str(job.slices)
    except Exception as e:
        logger.error(f"Error reading crontab: {str(e)}")

    return templates.TemplateResponse(request, "dashboard.html", {
        "active_page": "dashboard", 
        "resume_count": len(resumes), 
        "recent_logs": logs,
        "next_run": next_run,
        "up_next": up_next
    })

@app.get("/cron_ui", response_class=HTMLResponse)
async def cron_ui(request: Request, user: User = Depends(get_current_user_from_cookie)):
    if not user: return RedirectResponse(url="/login")
    
    current_schedule = "0 0 * * *"
    try:
        cron = CronTab(user=True)
        job = next(cron.find_comment('job-automation-bot'), None)
        if job: current_schedule = str(job.slices)
    except Exception as e:
        logger.error(f"Error reading crontab: {str(e)}")
    
    return templates.TemplateResponse(request, "cron.html", {
        "active_page": "cron", 
        "current_schedule": current_schedule
    })

@app.post("/cron/update")
async def update_cron(schedule: str = Form(...), user: User = Depends(get_current_user_from_cookie)):
    if not user: raise HTTPException(status_code=401)
    try:
        logger.info(f"Updating cron schedule to: {schedule} by user {user.username}")
        cron = CronTab(user=True)
        cron.remove_all(comment='job-automation-bot')
        script_path = os.path.abspath("resume_update.py")
        venv_python = os.path.join(os.getcwd(), "venv/bin/python")
        if not os.path.exists(venv_python): venv_python = "python3"
        
        job = cron.new(command=f"cd {os.getcwd()} && {venv_python} {script_path}", comment='job-automation-bot')
        job.setall(schedule)
        cron.write()
        logger.info("Cron schedule updated successfully")
    except Exception as e:
        logger.error(f"Failed to update cron: {str(e)}")
    return RedirectResponse(url="/cron_ui", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/resumes_ui", response_class=HTMLResponse)
async def resumes_ui(request: Request, user: User = Depends(get_current_user_from_cookie)):
    if not user: return RedirectResponse(url="/login")
    resumes = sorted(os.listdir(RESUMES_DIR))
    return templates.TemplateResponse(request, "resumes.html", {"active_page": "resumes", "resumes": resumes})

@app.get("/logs_ui", response_class=HTMLResponse)
async def logs_ui(request: Request, user: User = Depends(get_current_user_from_cookie)):
    if not user: return RedirectResponse(url="/login")
    logs = sorted(os.listdir(LOGS_DIR), reverse=True)
    return templates.TemplateResponse(request, "logs.html", {"active_page": "logs", "logs": logs})

# --- Action Routes ---

@app.post("/resumes/upload")
async def upload_resume(file: UploadFile = File(...), user: User = Depends(get_current_user_from_cookie)):
    if not user: raise HTTPException(status_code=401)
    if file.filename.endswith(".pdf"):
        logger.info(f"Uploading resume: {file.filename} by user {user.username}")
        with open(os.path.join(RESUMES_DIR, file.filename), "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"Resume {file.filename} uploaded successfully")
    else:
        logger.warning(f"Attempted to upload invalid file: {file.filename}")
    return RedirectResponse(url="/resumes_ui", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/resumes/delete/{filename}")
async def delete_resume(filename: str, user: User = Depends(get_current_user_from_cookie)):
    if not user: raise HTTPException(status_code=401)
    logger.info(f"Deleting resume: {filename} by user {user.username}")
    file_path = os.path.join(RESUMES_DIR, filename)
    if os.path.exists(file_path): 
        os.remove(file_path)
        logger.info(f"Resume {filename} deleted successfully")
    else:
        logger.error(f"Attempted to delete non-existent resume: {filename}")
    return RedirectResponse(url="/resumes_ui", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/trigger")
async def trigger_bot(background_tasks: BackgroundTasks, user: User = Depends(get_current_user_from_cookie)):
    if not user: raise HTTPException(status_code=401)
    logger.info(f"Manual bot trigger initiated by user {user.username}")
    background_tasks.add_task(run_update)
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/logs/{filename}")
async def view_log(filename: str, user: User = Depends(get_current_user_from_cookie)):
    if not user: raise HTTPException(status_code=401)
    logger.info(f"Viewing log file: {filename} by user {user.username}")
    file_path = os.path.join(LOGS_DIR, filename)
    if os.path.exists(file_path): 
        return FileResponse(file_path)
    logger.error(f"Log file not found: {filename}")
    raise HTTPException(status_code=404)

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting JobBot Management Server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
