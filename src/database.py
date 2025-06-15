# src/database.py

import os
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import hashlib # For password hashing

# Define the path for the SQLite database file
# It will be created in your project root
DATABASE_FILE = "finsolve_users.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DATABASE_FILE}"

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

    def __repr__(self):
        return f"<User(username='{self.username}', role='{self.role}')>"

# --- Database Engine and Session ---
# create_engine: Creates a SQLAlchemy engine. `check_same_thread=False` is needed for SQLite
# with FastAPI because FastAPI uses multiple threads for requests, and SQLite by default
# doesn't allow cross-thread database access.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# SessionLocal: Each instance of SessionLocal is a database session.
# The `autocommit=False` and `autoflush=False` settings are standard.
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
    """Hashes a password using SHA256."""
    # In a production application, use a stronger hashing algorithm like bcrypt
    # from passlib.hash import bcrypt
    # return bcrypt.hash(password)
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

# --- Initial Database Setup (for first run) ---
def create_db_and_tables():
    """
    Creates all defined tables in the database if they don't already exist.
    Also, seeds initial admin user if no users exist.
    """
    Base.metadata.create_all(bind=engine)
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
