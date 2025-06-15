# src/main.py

import os
import sys
import logging
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Dict, Any, List
from sqlalchemy.orm import Session # Import Session for database operations
from datetime import datetime, timedelta
from jose import JWTError, jwt
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to sys.path to resolve 'src' imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import database utilities and models
from src.database import get_db, User, create_db_and_tables, get_password_hash # Import hashing function
from src.core.rag_chain import RAGChain
from src.core.rbac import ROLE_PERMISSIONS # To get role names for validation

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- FastAPI App Initialization ---
app = FastAPI(
    title="FinSolve Chatbot API",
    description="RAG-based Chatbot with Role-Based Access Control for FinSolve Technologies.",
    version="1.0.0"
)

# Configure CORS
origins = [
    "http://localhost",
    "http://localhost:8501", # Default Streamlit port
    "http://127.0.0.1:8501",
    # Add other production origins here if deployed
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- JWT Configuration ---
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = 30

if not SECRET_KEY:
    logger.error("SECRET_KEY environment variable is not set. JWT will not work correctly.")
    raise ValueError("SECRET_KEY environment variable is not set. Please set it in your .env file.")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- Pydantic Models ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None

class UserResponse(BaseModel): # Renamed from 'User' to avoid conflict with SQLAlchemy model
    username: str
    role: str
    department: str
    id: int # Add ID for user management

class UserCreate(BaseModel):
    username: str
    password: str
    role: str
    department: str

class UserUpdate(BaseModel):
    role: str | None = None
    department: str | None = None
    password: str | None = None # For changing password

class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    response: str
    sources: List[Dict[str, Any]]

# --- JWT Helper Functions ---
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Function to verify password against stored hash (from database)
def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Use the same hashing function used during user creation/update
    return get_password_hash(plain_password) == hashed_password

def authenticate_user(username: str, password: str, db: Session):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        logger.warning(f"Authentication failed: User '{username}' not found.")
        return False
    if not verify_password(password, user.hashed_password):
        logger.warning(f"Authentication failed: Incorrect password for user '{username}'.")
        return False
    return user

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    # Retrieve user from DB based on token username
    user = db.query(User).filter(User.username == token_data.username).first()
    if user is None:
        raise credentials_exception
    
    return UserResponse(id=user.id, username=user.username, role=user.role, department=user.department)

async def get_current_admin_user(current_user: UserResponse = Depends(get_current_user)):
    """Dependency to ensure the current user has 'Admin' role."""
    if current_user.role != "Admin":
        logger.warning(f"Unauthorized access attempt by user '{current_user.username}' (role: '{current_user.role}') to admin route.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have sufficient permissions to perform this action. Admin role required."
        )
    return current_user

# --- Global RAGChain instance ---
rag_chain_instance = RAGChain()

# --- FastAPI Event Handlers ---
@app.on_event("startup")
async def startup_event():
    logger.info("FastAPI application starting up...")
    # Ensure database and tables are created, and seed initial users if necessary
    try:
        create_db_and_tables() # This ensures DB is ready and seeded
        logger.info("Database tables checked/created and initial users seeded.")
    except Exception as e:
        logger.exception(f"Error during database initialization at startup: {e}")
        # In production, this might be a critical error requiring app halt.
        # For demo, we'll log and continue if possible.

    # Initialize ChromaDB client and log document count
    try:
        doc_count = await rag_chain_instance.vector_store.count_documents()
        logger.info(f"ChromaDB collection initialized. Contains {doc_count} documents.")
    except Exception as e:
        logger.exception(f"Error during ChromaDB initialization at startup: {e}")

@app.get("/", summary="Root endpoint for API health check")
async def read_root():
    logger.info("Root endpoint accessed.")
    return {"message": "Welcome to FinSolve Chatbot API"}

@app.post("/token", response_model=Token, summary="Obtain JWT access token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires # Use user.username from DB object
    )
    logger.info(f"User '{user.username}' logged in successfully and received JWT.")
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/chat", response_model=ChatResponse, summary="Chat with the FinSolve Bot")
async def chat_with_bot(request: ChatRequest, current_user: UserResponse = Depends(get_current_user)):
    """
    Handles chatbot queries with role-based access control. Requires JWT authentication.
    """
    logger.info(f"Chat request from user '{current_user.username}' (Role: '{current_user.role}'). Query: '{request.query}'")

    try:
        response_text, sources = await rag_chain_instance.retrieve_and_generate(
            user_query=request.query,
            user_role=current_user.role
        )
        logger.info(f"Chat response generated for user '{current_user.username}'.")
        return ChatResponse(response=response_text, sources=sources)
    except Exception as e:
        logger.exception(f"Error processing chat request for user '{current_user.username}': {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal server error occurred during chat processing.")

# --- Admin Endpoints (Requires 'Admin' Role) ---

@app.get("/admin/users", response_model=List[UserResponse], summary="List all users (Admin only)")
async def get_all_users(current_user: UserResponse = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    """Retrieves all users from the database."""
    logger.info(f"Admin user '{current_user.username}' requested list of all users.")
    users = db.query(User).all()
    return [UserResponse(id=u.id, username=u.username, role=u.role, department=u.department) for u in users]

@app.post("/admin/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Create a new user (Admin only)")
async def create_user(user_data: UserCreate, current_user: UserResponse = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    """Creates a new user in the database."""
    logger.info(f"Admin user '{current_user.username}' attempting to create new user: {user_data.username}")
    
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered.")

    # Validate role and department against predefined roles in RBAC
    if user_data.role not in ROLE_PERMISSIONS and user_data.role != "Admin":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid role: {user_data.role}. Must be one of {list(ROLE_PERMISSIONS.keys())} or 'Admin'.")
    
    # Department validation (basic)
    if user_data.department not in [dept for r in ROLE_PERMISSIONS.values() for dept in (r['department'] if 'department' in r else (o['department'] for o in r['$or'])) if isinstance(r, dict) and '$or' in r or isinstance(r, dict) and 'department' in r] and user_data.department != "all":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid department: {user_data.department}.")


    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        username=user_data.username,
        hashed_password=hashed_password,
        role=user_data.role,
        department=user_data.department
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    logger.info(f"Admin user '{current_user.username}' successfully created new user: {db_user.username}.")
    return UserResponse(id=db_user.id, username=db_user.username, role=db_user.role, department=db_user.department)

@app.put("/admin/users/{user_id}", response_model=UserResponse, summary="Update an existing user (Admin only)")
async def update_user(user_id: int, user_update: UserUpdate, current_user: UserResponse = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    """Updates an existing user's role, department, or password."""
    logger.info(f"Admin user '{current_user.username}' attempting to update user with ID: {user_id}")
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if user_update.role:
        if user_update.role not in ROLE_PERMISSIONS and user_update.role != "Admin":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid role: {user_update.role}.")
        db_user.role = user_update.role
    
    if user_update.department:
        # Department validation (basic) - can be enhanced
        if user_update.department not in [dept for r in ROLE_PERMISSIONS.values() for dept in (r['department'] if 'department' in r else (o['department'] for o in r['$or'])) if isinstance(r, dict) and '$or' in r or isinstance(r, dict) and 'department' in r] and user_update.department != "all":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid department: {user_update.department}.")
        db_user.department = user_update.department

    if user_update.password:
        db_user.hashed_password = get_password_hash(user_update.password)
    
    db.commit()
    db.refresh(db_user)
    logger.info(f"Admin user '{current_user.username}' successfully updated user: {db_user.username}.")
    return UserResponse(id=db_user.id, username=db_user.username, role=db_user.role, department=db_user.department)

@app.delete("/admin/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a user (Admin only)")
async def delete_user(user_id: int, current_user: UserResponse = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    """Deletes a user from the database."""
    logger.info(f"Admin user '{current_user.username}' attempting to delete user with ID: {user_id}")
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    # Prevent admin from deleting themselves (or other critical admins if multiple)
    if db_user.username == current_user.username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="An admin cannot delete their own account.")

    db.delete(db_user)
    db.commit()
    logger.info(f"Admin user '{current_user.username}' successfully deleted user: {db_user.username}.")
    return {"message": "User deleted successfully."}

@app.get("/admin/roles", response_model=List[str], summary="List all available roles (Admin only)")
async def get_available_roles(current_user: UserResponse = Depends(get_current_admin_user)):
    """Lists all roles defined in the RBAC configuration."""
    roles = list(ROLE_PERMISSIONS.keys())
    roles.append("Admin") # Add the Admin role itself
    logger.info(f"Admin user '{current_user.username}' requested list of available roles.")
    return sorted(roles)

# --- Run the FastAPI application ---
# To run this, save the file and then from your terminal in the project root:
# uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
# (The --reload flag is useful for development)

if __name__ == "__main__":
    import uvicorn
    # This block will create/check DB and seed users when main.py is run directly
    create_db_and_tables() 
    uvicorn.run(app, host="0.0.0.0", port=8000)
