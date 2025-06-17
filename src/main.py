# src/main.py

import os
import sys
import logging
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import JWTError, jwt
from dotenv import load_dotenv
from sqlalchemy import desc # NEW: For ordering chat messages by timestamp

# Load environment variables
load_dotenv()

# Add the project root to sys.path to resolve 'src' imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import database utilities and models
from src.database import get_db, User, ChatMessage, ChatSession, create_db_and_tables, verify_password, get_password_hash # MODIFIED: Import ChatSession
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

class UserResponse(BaseModel):
    username: str
    role: str
    department: str
    id: int

class ChatRequest(BaseModel):
    query: str
    session_id: Optional[int] = None # MODIFIED: Optional session_id for chat messages

class ChatResponse(BaseModel):
    response: str
    sources: List[Dict[str, Any]]
    session_id: int # NEW: Return the session ID with the chat response

class MessageResponse(BaseModel):
    sender: str
    message_text: str
    timestamp: datetime
    id: int
    session_id: int # NEW: Include session_id in message response

class ChatSessionResponse(BaseModel): # NEW: Pydantic model for chat sessions
    id: int
    user_id: int
    title: str
    created_at: datetime

class ChatSessionCreate(BaseModel): # NEW: Pydantic model for creating a session
    title: Optional[str] = "New Chat"

class ChatSessionUpdate(BaseModel): # NEW: Pydantic model for updating a session
    title: str

class UserCreate(BaseModel):
    username: str
    password: str
    role: str
    department: str

class UserUpdate(BaseModel):
    role: str | None = None
    department: str | None = None
    password: str | None = None # For changing password


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

# authenticate_user function now uses verify_password from src.database
def authenticate_user(username: str, password: str, db: Session):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        logger.warning(f"Authentication failed: User '{username}' not found.")
        return False
    # Use the bcrypt verify function
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
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    logger.info(f"User '{user.username}' logged in successfully and received JWT.")
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/chat", response_model=ChatResponse, summary="Chat with the FinSolve Bot")
async def chat_with_bot(request: ChatRequest, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Handles chatbot queries with role-based access control. Requires JWT authentication.
    Saves chat history to the database.
    """
    logger.info(f"Chat request from user '{current_user.username}' (ID: {current_user.id}, Role: '{current_user.role}'). Query: '{request.query}'")

    # --- NEW: Handle chat sessions ---
    session_id = request.session_id
    if session_id is None:
        # If no session_id is provided, create a new session
        new_session = ChatSession(user_id=current_user.id, title="New Chat")
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        session_id = new_session.id
        logger.info(f"Created new chat session for user {current_user.username}: ID {session_id}")
    else:
        # Validate that the session belongs to the current user
        session_exists = db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id
        ).first()
        if not session_exists:
            logger.warning(f"User {current_user.username} attempted to use unauthorized session ID: {session_id}")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized session ID.")


    try:
        # Save user message to database
        user_message = ChatMessage(
            user_id=current_user.id,
            session_id=session_id, # MODIFIED: Link to session
            sender="user",
            message_text=request.query,
            timestamp=datetime.utcnow()
        )
        db.add(user_message)
        db.commit()
        db.refresh(user_message)
        logger.info(f"User message saved (Session ID: {session_id}): {user_message.id}")

        response_text, sources = await rag_chain_instance.retrieve_and_generate(
            user_query=request.query,
            user_role=current_user.role
        )
        logger.info(f"Chat response generated for user '{current_user.username}'.")

        # Save bot response to database
        bot_message = ChatMessage(
            user_id=current_user.id,
            session_id=session_id, # MODIFIED: Link to session
            sender="bot",
            message_text=response_text,
            timestamp=datetime.utcnow()
        )
        db.add(bot_message)
        db.commit()
        db.refresh(bot_message)
        logger.info(f"Bot message saved (Session ID: {session_id}): {bot_message.id}")

        return ChatResponse(response=response_text, sources=sources, session_id=session_id) # MODIFIED: Return session_id
    except Exception as e:
        db.rollback() # Rollback any partial transactions if an error occurs
        logger.exception(f"Error processing chat request for user '{current_user.username}' in session {session_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal server error occurred during chat processing.")

# --- NEW: Chat Session Management Endpoints ---

@app.post("/chat_sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED, summary="Create a new chat session")
async def create_chat_session(
    session_data: ChatSessionCreate,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Creates a new, empty chat session for the current user.
    """
    logger.info(f"User '{current_user.username}' requesting to create a new chat session with title: '{session_data.title}'")
    new_session = ChatSession(
        user_id=current_user.id,
        title=session_data.title,
        created_at=datetime.utcnow()
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    logger.info(f"New chat session created: ID {new_session.id}, Title: '{new_session.title}' for user '{current_user.username}'.")
    return ChatSessionResponse(
        id=new_session.id,
        user_id=new_session.user_id,
        title=new_session.title,
        created_at=new_session.created_at
    )

@app.get("/chat_sessions", response_model=List[ChatSessionResponse], summary="List all chat sessions for current user")
async def get_user_chat_sessions(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves all chat sessions for the authenticated user, ordered by creation time.
    """
    logger.info(f"User '{current_user.username}' requesting list of chat sessions.")
    sessions = db.query(ChatSession).filter(ChatSession.user_id == current_user.id).order_by(desc(ChatSession.created_at)).all() # Ordered by newest first
    
    response_sessions = [
        ChatSessionResponse(
            id=s.id,
            user_id=s.user_id,
            title=s.title,
            created_at=s.created_at
        ) for s in sessions
    ]
    logger.info(f"Retrieved {len(response_sessions)} chat sessions for user '{current_user.username}'.")
    return response_sessions

@app.get("/chat_sessions/{session_id}/messages", response_model=List[MessageResponse], summary="Retrieve messages for a specific chat session")
async def get_session_messages(
    session_id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves all messages for a specific chat session belonging to the current user.
    """
    logger.info(f"User '{current_user.username}' requesting messages for session ID: {session_id}.")
    # Ensure the session belongs to the current user for security
    session_exists = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    if not session_exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found or unauthorized.")

    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.timestamp).all()
    
    response_messages = [
        MessageResponse(
            id=msg.id,
            session_id=msg.session_id,
            sender=msg.sender,
            message_text=msg.message_text,
            timestamp=msg.timestamp
        ) for msg in messages
    ]
    logger.info(f"Retrieved {len(response_messages)} messages for session ID {session_id}.")
    return response_messages

@app.put("/chat_sessions/{session_id}/title", response_model=ChatSessionResponse, summary="Update title of a chat session")
async def update_chat_session_title(
    session_id: int,
    session_update: ChatSessionUpdate,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Updates the title of a specific chat session belonging to the current user.
    """
    logger.info(f"User '{current_user.username}' attempting to update title for session ID: {session_id} to '{session_update.title}'.")
    db_session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()

    if not db_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found or unauthorized.")

    db_session.title = session_update.title
    db.commit()
    db.refresh(db_session)
    logger.info(f"Chat session ID {session_id} title updated to '{db_session.title}'.")
    return ChatSessionResponse(
        id=db_session.id,
        user_id=db_session.user_id,
        title=db_session.title,
        created_at=db_session.created_at
    )

@app.delete("/chat_sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a chat session (and all its messages)")
async def delete_chat_session(
    session_id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Deletes a chat session and all its associated messages.
    """
    logger.info(f"User '{current_user.username}' attempting to delete session ID: {session_id}.")
    db_session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()

    if not db_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found or unauthorized.")

    db.delete(db_session)
    db.commit()
    logger.info(f"Chat session ID {session_id} and its messages deleted by user '{current_user.username}'.")
    return {"message": "Chat session deleted successfully."}

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
    # This part iterates ROLE_PERMISSIONS to get all valid departments from either 'department' key or '$or' clause
    valid_departments = set()
    for role_def in ROLE_PERMISSIONS.values():
        if isinstance(role_def, dict):
            if 'department' in role_def:
                valid_departments.add(role_def['department'])
            elif '$or' in role_def:
                for or_condition in role_def['$or']:
                    if isinstance(or_condition, dict) and 'department' in or_condition:
                        valid_departments.add(or_condition['department'])
    valid_departments.add("all") # Add "all" for Admin
    
    if user_data.department not in valid_departments:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid department: {user_data.department}. Must be one of {list(valid_departments)}.")


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
        # Department validation (basic)
        valid_departments = set()
        for role_def in ROLE_PERMISSIONS.values():
            if isinstance(role_def, dict):
                if 'department' in role_def:
                    valid_departments.add(role_def['department'])
                elif '$or' in role_def:
                    for or_condition in role_def['$or']:
                        if isinstance(or_condition, dict) and 'department' in or_condition:
                            valid_departments.add(or_condition['department'])
        valid_departments.add("all") # Add "all" for Admin
        
        if user_update.department not in valid_departments:
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
