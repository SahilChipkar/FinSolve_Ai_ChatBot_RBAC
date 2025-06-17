# src/database.py

import os
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from passlib.context import CryptContext
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables for ADMIN_INITIAL_PASSWORD
load_dotenv()

# Define the path for the SQLite database file
DATABASE_FILE = "finsolve_users.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DATABASE_FILE}"

# Initialize CryptContext for password hashing (using bcrypt algorithm)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# SQLAlchemy Base for declarative models
Base = declarative_base()

# --- Database Models ---
class User(Base):
    """
    SQLAlchemy model for storing user information.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String) # Store hashed password
    role = Column(String, default="Employee Level") # e.g., "Finance Team", "Admin", "Employee Level"
    department = Column(String, default="general") # e.g., "finance", "marketing", "hr", "engineering", "general", "all"

    # Define relationships
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan") # NEW
    # Note: ChatMessage relationship removed from User, as messages now link to sessions, not directly to users

    def __repr__(self):
        return f"<User(username='{self.username}', role='{self.role}')>"

class ChatSession(Base): # NEW: ChatSession Model
    """
    SQLAlchemy model for storing individual chat sessions/conversations.
    """
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String, default="New Chat") # Title of the chat session, like "Q1 Finance Report"
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan") # NEW

    def __repr__(self):
        return f"<ChatSession(id={self.id}, user_id={self.user_id}, title='{self.title}')>"

class ChatMessage(Base):
    """
    SQLAlchemy model for storing chat history messages.
    Each message now belongs to a specific ChatSession.
    """
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id")) # MODIFIED: Link to ChatSession
    user_id = Column(Integer, ForeignKey("users.id")) # Keep user_id for direct filtering if needed, though session_id provides user context

    sender = Column(String) # 'user' or 'bot'
    message_text = Column(Text) # The content of the message
    timestamp = Column(DateTime, default=datetime.utcnow) # When the message was sent

    # Define relationship to ChatSession
    session = relationship("ChatSession", back_populates="messages") # NEW
    # No direct relationship to User here, as it's handled via session


    def __repr__(self):
        return f"<ChatMessage(session_id={self.session_id}, sender='{self.sender}', timestamp='{self.timestamp}')>"


# --- Database Engine and Session ---
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- Dependency to get DB session for FastAPI ---
def get_db():
    """
    Dependency function to provide a database session.
    It yields a session and ensures it's closed after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Password Hashing Function ---
def get_password_hash(password: str) -> str:
    """Hashes a password using bcrypt."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password using bcrypt."""
    return pwd_context.verify(plain_password, hashed_password)

# --- Initial Database Setup (for first run) ---
def create_db_and_tables():
    """
    Creates all defined tables in the database if they don't already exist.
    Also, seeds initial admin user if no users exist.
    """
    # Use checkfirst=True to only create tables that don't exist
    Base.metadata.create_all(bind=engine, checkfirst=True)

    db = SessionLocal()
    try:
        # Check if an admin user already exists
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            # Create a default admin user
            admin_password = os.getenv("ADMIN_INITIAL_PASSWORD", "adminpass") # Get from .env if set
            admin_user = User(
                username="admin",
                hashed_password=get_password_hash(admin_password),
                role="Admin",
                department="all" # Admin has access to all departments
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            print(f"Default admin user '{admin_user.username}' created.")
        else:
            print("Admin user already exists.")

        # Add other initial mock users if they don't exist
        initial_users_data = {
            "finance_user": {"pass": "financepass", "role": "Finance Team", "department": "finance"},
            "marketing_user": {"pass": "marketingpass", "role": "Marketing Team", "department": "marketing"},
            "hr_user": {"pass": "hrpass", "role": "HR Team", "department": "hr"},
            "eng_user": {"pass": "engpass", "role": "Engineering Department", "department": "engineering"},
            "ceo": {"pass": "ceopass", "role": "C-Level Executives", "department": "all"},
            "employee": {"pass": "employeepass", "role": "Employee Level", "department": "general"}
        }

        for username, data in initial_users_data.items():
            if not db.query(User).filter(User.username == username).first():
                user = User(
                    username=username,
                    hashed_password=get_password_hash(data["pass"]),
                    role=data["role"],
                    department=data["department"]
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                print(f"Default user '{username}' created.")
            else:
                print(f"User '{username}' already exists.")

    except Exception as e:
        db.rollback()
        print(f"Error seeding initial users: {e}")
    finally:
        db.close()


# Example usage (for testing purposes)
if __name__ == "__main__":
    print("--- Initializing database and seeding users ---")
    create_db_and_tables()
    print("Database setup complete.")

    # You can manually inspect the 'finsolve_users.db' file using a SQLite browser.
    # To test user retrieval:
    db = SessionLocal()
    try:
        users = db.query(User).all()
        print("\nExisting Users:")
        for user in users:
            print(f"- ID: {user.id}, Username: {user.username}, Role: {user.role}, Department: {user.department}")
    finally:
        db.close()
