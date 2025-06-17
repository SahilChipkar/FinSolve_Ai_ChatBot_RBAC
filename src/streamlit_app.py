# src/streamlit_app.py

import streamlit as st
import requests
import json
import time
from datetime import datetime

# --- Configuration ---
FASTAPI_BASE_URL = "http://localhost:8000"

st.set_page_config(
    page_title="FinSolve RBAC Chatbot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- SVG Icons ---
USER_AVATAR = "👤"
BOT_AVATAR = "🤖"
ADMIN_AVATAR = "⚙️" # Gear icon for admin

# --- Custom CSS for a Polished UI ---
st.markdown("""
<style>
    /* General Body and Main Container */
    /* Theme colors now primarily handled by .streamlit/config.toml */

    /* Main content area */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        padding-left: 5rem;
        padding-right: 5rem;
    }

    /* Sidebar Styling */
    /* Handled by .streamlit/config.toml for background, and custom for borders/text */
    .st-emotion-cache-16txtl3 { /* Specific Streamlit internal class for sidebar */
        border-right: 1px solid #3a3a5a;
    }
    .st-emotion-cache-16txtl3 h1, .st-emotion-cache-16txtl3 h2, .st-emotion-cache-16txtl3 .st-emotion-cache-1q8dd3i {
        color: #f0f2f6; /* Ensures text in sidebar is light */
    }
    .st-emotion-cache-16txtl3 .st-emotion-cache-1v0mbdj { /* Separator in sidebar */
        border-top-color: #3a3a5a;
    }

    /* Chat Message Styling */
    .st-emotion-cache-1c7y2kd { /* This targets the chat message bubble itself */
        border-radius: 0.75rem;
        border: 1px solid transparent;
        padding: 1rem;
    }
    [data-testid="chat-message-container-User"] .st-emotion-cache-1c7y2kd {
        background-color: #253961; /* User message bubble color (cool blue) */
    }
    [data-testid="chat-message-container-Bot"] .st-emotion-cache-1c7y2kd {
        background-color: #2c2c4d; /* Bot message bubble color (darker purple) */
        border-color: #4a4a6a;
    }
    .stChatMessage .st-emotion-cache-4oy321 { /* Avatar background */
        background-color: transparent;
    }

    /* Source Info Styling */
    .source-info {
        font-size: 0.8rem;
        color: #a0a0c0; /* Lighter grey for source info */
        margin-top: 0.75rem;
        padding-top: 0.5rem;
        border-top: 1px dashed #4a4a6a; /* Darker dashed line */
    }

    /* Login Form Container */
    .login-container {
        background-color: #2a2a4a;
        padding: 2rem 3rem;
        border-radius: 1rem;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        border: 1px solid rgba(255, 255, 255, 0.18);
    }
    
    /* Buttons and Inputs */
    .stButton>button {
        background-color: #6a0578; /* Purple-ish button */
        color: white;
        border-radius: 0.5rem;
        border: none;
        padding: 0.75rem 1.5rem;
    }
    .stButton>button:hover {
        background-color: #8a079a;
    }
    .stTextInput>div>div>input {
        background-color: #3a3a5a;
        color: #f0f2f6;
        border-radius: 0.5rem;
        border: 1px solid #5a5a7a;
    }
    .stTextArea>div>div>textarea { /* For admin panel text area */
        background-color: #3a3a5a;
        color: #f0f2f6;
        border-radius: 0.5rem;
        border: 1px solid #5a5a7a;
    }
    .stSelectbox>div>div>div { /* For admin panel selectbox */
        background-color: #3a3a5a;
        color: #f0f2f6;
        border-radius: 0.5rem;
        border: 1px solid #5a5a7a;
    }
    .stSelectbox>div>div>div>div[data-testid="stSelectboxDropdown"] {
        background-color: #3a3a5a;
        color: #f0f2f6;
    }


    /* Suggested Questions Buttons */
    .stButton.suggested-question-button button {
        background-color: #3a3a5a;
        border: 1px solid #5a5a7a;
        font-weight: 400;
        text-align: left;
        display: block;
        width: 100%;
        margin-bottom: 0.5rem;
    }
    .stButton.suggested-question-button button:hover {
        background-color: #4a4a6a;
        border-color: #6a0578;
    }

    /* Table styling for admin panel */
    .dataframe {
        width: 100%;
        border-collapse: collapse;
        margin: 20px 0;
        font-size: 0.9em;
        min-width: 400px;
        box-shadow: 0 0 20px rgba(0, 0, 0, 0.15);
        border-radius: 8px;
        overflow: hidden; /* Ensures rounded corners on table */
    }
    .dataframe thead tr {
        background-color: #6a0578; /* Header background */
        color: #ffffff;
        text-align: left;
    }
    .dataframe th, .dataframe td {
        padding: 12px 15px;
        border: 1px solid #3a3a5a; /* Darker border for cells */
    }
    .dataframe tbody tr {
        border-bottom: 1px solid #3a3a5a;
        background-color: #2a2a4a; /* Row background */
        color: #f0f2f6; /* Row text color */
    }
    .dataframe tbody tr:nth-of-type(even) {
        background-color: #1f1f3d; /* Alternate row color */
    }
    .dataframe tbody tr:last-of-type {
        border-bottom: 2px solid #6a0578;
    }
    .dataframe tbody tr.active-row {
        font-weight: bold;
        color: #e0e0e0;
    }

    /* Chat Session List in Sidebar */
    .st-emotion-cache-16txtl3 .stButton button { /* Target all buttons in the sidebar */
        background-color: #3a3a5a; /* Default background for sidebar buttons */
        color: #f0f2f6;
        border-radius: 0.5rem;
        border: 1px solid #5a5a7a;
        padding: 0.5rem 0.75rem;
        margin-bottom: 0.3rem; /* Small space between all sidebar buttons */
        width: 100%; /* Ensure all sidebar buttons take full width */
        text-align: center; /* Default text alignment */
    }

    /* Styling for the main session button (title) */
    .st-emotion-cache-16txtl3 .stButton button[key^="select_session_btn_"] {
        background-color: #3a3a5a;
        border: 1px solid #5a5a7a;
        text-align: left; /* Align text to left for chat titles */
        padding: 8px 10px; /* Padding to match chat-session-row */
        height: auto; /* Allow button height to adjust to content */
    }
    .st-emotion-cache-16txtl3 .stButton button[key^="select_session_btn_"].active {
        background-color: #6a0578; /* Active session highlight */
        font-weight: bold;
    }
    .st-emotion-cache-16txtl3 .stButton button[key^="select_session_btn_"]:hover {
        background-color: #4a4a6a;
    }

    /* Styling for the ellipsis button */
    .st-emotion-cache-16txtl3 .stButton button[key^="toggle_actions_btn_"] {
        background: none !important; /* Transparent background */
        border: none !important; /* No border */
        color: #f0f2f6 !important;
        font-size: 1.2em !important;
        opacity: 0.7;
        padding: 0 !important; /* No padding to make it compact */
        width: auto !important; /* Allow width to be content-based */
        height: auto !important;
        display: flex;
        justify-content: center;
        align-items: center;
        line-height: 1;
        margin-bottom: 0 !important; /* No margin below ellipsis */
    }
    .st-emotion-cache-16txtl3 .stButton button[key^="toggle_actions_btn_"]:hover {
        opacity: 1;
    }

    /* Styles for the rename/delete buttons when they appear */
    .session-control-buttons .stButton > button {
        background-color: #4a4a6a !important; /* Darker background */
        border: 1px solid #5a5a7a !important;
        color: #f0f2f6 !important;
        border-radius: 0.5rem !important;
        margin-top: 5px !important;
        padding: 0.5rem 0.75rem !important;
        font-size: 0.85em !important;
        width: 100% !important; /* Take full width of their column */
    }
    .session-control-buttons .stButton > button:hover {
        background-color: #5a5a7a !important;
    }
    /* Adjust column padding for these buttons if necessary, though direct button styling is preferred */
    .session-control-buttons div[data-testid="stColumn"] {
        padding-left: 0.25rem !important;
        padding-right: 0.25rem !important;
    }
</style>
""", unsafe_allow_html=True)


# --- API Functions ---

def login_user_api(username, password):
    """ Authenticates the user via the FastAPI backend and gets JWT. """
    url = f"{FASTAPI_BASE_URL}/token"
    try:
        response = requests.post(url, data={"username": username, "password": password})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        error_message = f"Login API Error: {e}"
        try:
            error_detail = response.json().get("detail", "No details provided.")
            error_message += f"\nDetails: {error_detail}"
        except (requests.exceptions.JSONDecodeError, AttributeError):
            pass
        st.error(error_message)
        return None

def chat_api(query, token, session_id=None): # MODIFIED: Added session_id parameter
    """ Sends chat query to FastAPI backend with JWT for authentication. """
    url = f"{FASTAPI_BASE_URL}/chat"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"query": query, "session_id": session_id} # Include session_id in payload
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        error_message = f"Chat API Error: {e}"
        try:
            error_detail = response.json().get("detail", "No details provided.")
            error_message += f"\nDetails: {error_detail}"
        except (requests.exceptions.JSONDecodeError, AttributeError):
            pass
        st.error(error_message)
        return None

# --- NEW: Chat Session API Functions ---
def create_chat_session_api(token, title="New Chat"):
    """ Creates a new chat session on the backend. """
    url = f"{FASTAPI_BASE_URL}/chat_sessions"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        response = requests.post(url, json={"title": title}, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error creating chat session: {e}")
        return None

def get_user_chat_sessions_api(token):
    """ Fetches all chat sessions for the current user. """
    url = f"{FASTAPI_BASE_URL}/chat_sessions"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching chat sessions: {e}")
        return []

def get_session_messages_api(session_id, token):
    """ Fetches messages for a specific chat session. """
    url = f"{FASTAPI_BASE_URL}/chat_sessions/{session_id}/messages"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching session messages: {e}")
        return []

def update_session_title_api(session_id, new_title, token):
    """ Updates the title of a specific chat session. """
    url = f"{FASTAPI_BASE_URL}/chat_sessions/{session_id}/title"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        response = requests.put(url, json={"title": new_title}, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error updating session title: {e}")
        return None

def delete_chat_session_api(session_id, token):
    """ Deletes a specific chat session and its messages. """
    url = f"{FASTAPI_BASE_URL}/chat_sessions/{session_id}"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.delete(url, headers=headers)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"Error deleting chat session: {e}")
        return False

# --- Admin API Functions (from previous version, remain unchanged) ---
def get_all_users_api(token):
    """ Fetches all users from the admin endpoint. """
    url = f"{FASTAPI_BASE_URL}/admin/users"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching users: {e}")
        return None

def create_user_api(user_data, token):
    """ Creates a new user via the admin endpoint. """
    url = f"{FASTAPI_BASE_URL}/admin/users"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        response = requests.post(url, json=user_data, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        error_message = f"Error creating user: {e}"
        try:
            error_detail = response.json().get("detail", "No details provided.")
            error_message += f"\nDetails: {error_detail}"
        except (requests.exceptions.JSONDecodeError, AttributeError):
            pass
        st.error(error_message)
        return None

def update_user_api(user_id, user_data, token):
    """ Updates an existing user via the admin endpoint. """
    url = f"{FASTAPI_BASE_URL}/admin/users/{user_id}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        response = requests.put(url, json=user_data, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        error_message = f"Error updating user: {e}"
        try:
            error_detail = response.json().get("detail", "No details provided.")
            error_message += f"\nDetails: {e}"
        except (requests.exceptions.JSONDecodeError, AttributeError):
            pass
        st.error(error_message)
        return None

def delete_user_api(user_id, token):
    """ Deletes a user via the admin endpoint. """
    url = f"{FASTAPI_BASE_URL}/admin/users/{user_id}"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.delete(url, headers=headers)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"Error deleting user: {e}")
        return False

def get_available_roles_api(token):
    """ Fetches available roles from the admin endpoint. """
    url = f"{FASTAPI_BASE_URL}/admin/roles"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching roles: {e}")
        return []

# --- Session State Initialization ---
def init_session_state():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "username" not in st.session_state:
        st.session_state.username = ""
    if "user_role" not in st.session_state:
        st.session_state.user_role = ""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "department" not in st.session_state:
        st.session_state.department = ""
    if "access_token" not in st.session_state:
        st.session_state.access_token = ""
    if "current_page" not in st.session_state:
        st.session_state.current_page = "chat"
    if "selected_user_id" not in st.session_state:
        st.session_state.selected_user_id = None
    if "roles_list" not in st.session_state:
        st.session_state.roles_list = []
    if "departments_list" not in st.session_state:
        st.session_state.departments_list = ["all", "finance", "marketing", "hr", "engineering", "general"]
    
    # --- NEW: Chat Session State Variables ---
    if "chat_sessions" not in st.session_state:
        st.session_state.chat_sessions = [] # List of {id, title, created_at}
    if "current_session_id" not in st.session_state:
        st.session_state.current_session_id = None
    if "current_session_title" not in st.session_state:
        st.session_state.current_session_title = "New Chat" # Default title for new conversation
    if "session_messages_loaded" not in st.session_state:
        st.session_state.session_messages_loaded = False # Flag to load messages only once per session switch
    if "show_rename_input" not in st.session_state: # To control rename form visibility
        st.session_state.show_rename_input = None
    if "show_session_actions_id" not in st.session_state: # NEW: To show rename/delete for a specific session
        st.session_state.show_session_actions_id = None
    if "confirm_delete_id" not in st.session_state: # To manage delete confirmation
        st.session_state.confirm_delete_id = None


init_session_state()

# --- Login UI ---
def display_login_page():
    st.title("Welcome to FinSolve RBAC Chatbot")
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.container():
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            st.header("Login")
            
            with st.form("login_form"):
                username = st.text_input("Username", key="login_username")
                password = st.text_input("Password", type="password", key="login_password")
                submitted = st.form_submit_button("Login")

                if submitted:
                    if not username or not password:
                        st.warning("Please enter both username and password.")
                    else:
                        token_data = login_user_api(username, password)
                        if token_data:
                            st.session_state.logged_in = True
                            st.session_state.username = username
                            st.session_state.access_token = token_data["access_token"]
                            
                            # Directly set user details from login API response (assuming FastAPI is updated)
                            st.session_state.user_role = token_data.get("role", "")
                            st.session_state.department = token_data.get("department", "")
                            st.session_state.user_id = token_data.get("user_id") # Assuming user_id is also returned

                            # --- Load chat sessions on login ---
                            st.session_state.chat_sessions = get_user_chat_sessions_api(st.session_state.access_token)
                            if st.session_state.chat_sessions:
                                # Auto-select the most recent session if available
                                st.session_state.current_session_id = st.session_state.chat_sessions[0]["id"]
                                st.session_state.current_session_title = st.session_state.chat_sessions[0]["title"]
                                st.session_state.session_messages_loaded = False # Ensure messages for this session are loaded
                            else:
                                # If no sessions exist, create a new one automatically
                                new_session = create_chat_session_api(st.session_state.access_token, "New Chat")
                                if new_session:
                                    st.session_state.chat_sessions = [new_session]
                                    st.session_state.current_session_id = new_session["id"]
                                    st.session_state.current_session_title = new_session["title"]
                                    st.session_state.messages = [] # Initialize messages for new chat
                                    st.session_state.session_messages_loaded = False # Ensure messages for this session are loaded
                                else:
                                    st.error("Failed to create initial chat session.")
                                    st.session_state.logged_in = False
                                    st.rerun()
                                    
                            st.success(f"Logged in as {st.session_state.username} ({st.session_state.user_role})")
                            st.rerun()
                        # Error is handled by login_user_api directly
            
            st.markdown('</div>', unsafe_allow_html=True)
            
    # Display mock user credentials for easy testing
    with st.expander("Show Test User Credentials"):
        st.markdown("""
        - **admin** / `adminpass` (or your .env password)
        - **finance_user** / `financepass`
        - **marketing_user** / `marketingpass`
        - **hr_user** / `hrpass`
        - **eng_user** / `engpass`
        - **ceo** / `ceopass`
        - **employee** / `employeepass`
        """)

# --- Main Chat UI ---
def display_chat_page():
    # --- Sidebar ---
    with st.sidebar:
        st.title("User Profile")
        st.write(f"**Username:** {st.session_state.username}")
        st.write(f"**Role:** {st.session_state.user_role.capitalize()}")
        st.write(f"**Department:** {st.session_state.department.capitalize()}")
        
        st.markdown("---")
        
        # Navigation between chat and admin panel
        if st.session_state.user_role == "Admin":
            if st.button("Go to Admin Panel", key="go_to_admin_button", use_container_width=True):
                st.session_state.current_page = "admin"
                st.rerun()

        st.markdown("---")
        st.subheader("Chats")

        # --- New Chat Button ---
        if st.button("➕ New Chat", key="new_chat_button", use_container_width=True):
            new_session = create_chat_session_api(st.session_state.access_token)
            if new_session:
                st.session_state.chat_sessions = get_user_chat_sessions_api(st.session_state.access_token) # Refresh list
                st.session_state.current_session_id = new_session["id"]
                st.session_state.current_session_title = new_session["title"]
                st.session_state.messages = [] # Clear current messages for new chat
                st.session_state.session_messages_loaded = False
                st.session_state.show_session_actions_id = None # Hide any active rename/delete buttons
                st.rerun()

        # Display list of chat sessions
        if st.session_state.chat_sessions:
            for session in st.session_state.chat_sessions:
                is_active = (session["id"] == st.session_state.current_session_id)
                
                # Use st.container to group the row and potential action buttons below it
                with st.container():
                    # Create a horizontal layout for the session title and ellipsis button
                    col1, col2 = st.columns([0.8, 0.2]) # Adjust width ratios as needed

                    with col1:
                        # Session Title Button (selects the chat)
                        st.button(
                            session["title"],
                            key=f"select_session_btn_{session['id']}",
                            on_click=lambda s_id=session["id"], s_title=session["title"]: set_current_session(s_id, s_title),
                            use_container_width=True,
                            help="Click to select this chat session",
                        )
                        # Custom CSS to apply active state and correct styling to this specific button
                        st.markdown(f"""
                            <style>
                                div[data-testid="stSidebar"] div[data-testid="stButton"] button[key="select_session_btn_{session['id']}"] {{
                                    background-color: {'#6a0578' if is_active else '#3a3a5a'} !important;
                                    color: {'white' if is_active else '#f0f2f6'} !important;
                                    font-weight: {'bold' if is_active else 'normal'} !important;
                                    text-align: left !important;
                                    padding: 8px 10px !important;
                                    border-radius: 0.5rem !important;
                                    border: 1px solid {'#6a0578' if is_active else '#5a5a7a'} !important;
                                }}
                                div[data-testid="stSidebar"] div[data-testid="stButton"] button[key="select_session_btn_{session['id']}"]:hover {{
                                    background-color: {'#8a079a' if is_active else '#4a4a6a'} !important;
                                }}
                            </style>
                        """, unsafe_allow_html=True)

                    with col2:
                        # Ellipsis Button (toggles rename/delete options)
                        st.button(
                            "...",
                            key=f"toggle_actions_btn_{session['id']}",
                            on_click=lambda s_id=session["id"]: toggle_session_actions(s_id),
                            help="More options (rename, delete)",
                            use_container_width=True,
                        )
                        # Custom CSS for the ellipsis button
                        st.markdown(f"""
                            <style>
                                div[data-testid="stSidebar"] div[data-testid="stButton"] button[key="toggle_actions_btn_{session['id']}"] {{
                                    background: none !important;
                                    border: none !important;
                                    color: #f0f2f6 !important;
                                    font-size: 1.2em !important;
                                    opacity: 0.7;
                                    padding: 0 !important;
                                    width: auto !important;
                                    height: auto !important;
                                    display: flex;
                                    justify-content: center;
                                    align-items: center;
                                    line-height: 1;
                                    margin-bottom: 0 !important; /* No margin below ellipsis */
                                }}
                                div[data-testid="stSidebar"] div[data-testid="stButton"] button[key="toggle_actions_btn_{session['id']}"]:hover {{
                                    opacity: 1;
                                    color: #FF4B4B !important; /* Red for delete hover */
                                }}
                            </style>
                        """, unsafe_allow_html=True)


                    # Streamlit buttons for actual actions (Rename/Delete), shown conditionally
                    # These will appear BELOW the session row when `show_session_actions_id` matches
                    if st.session_state.show_session_actions_id == session["id"]:
                        with st.container(): # Group these buttons for styling
                            st.markdown('<div class="session-control-buttons">', unsafe_allow_html=True)
                            col_rename, col_delete = st.columns(2)
                            with col_rename:
                                st.button(
                                    "✏️ Rename", 
                                    key=f"rename_session_direct_{session['id']}", 
                                    on_click=lambda s_id=session["id"]: set_rename_input_visible(s_id),
                                    use_container_width=True
                                )
                            with col_delete:
                                st.button(
                                    "🗑️ Delete", 
                                    key=f"delete_session_direct_{session['id']}", 
                                    on_click=lambda s_id=session["id"]: confirm_delete_session(s_id),
                                    use_container_width=True
                                )
                            st.markdown('</div>', unsafe_allow_html=True)
                            st.markdown("---", help="Separator after actions") # Visual separator


        else:
            st.info("No chat sessions yet. Click '➕ New Chat' to start one!")

        st.markdown("---")
        if st.button("Logout", key="logout_button", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            init_session_state() # Re-initialize to clear all state
            st.rerun()

    # Callback function for session selection
    def set_current_session(session_id, session_title):
        if st.session_state.current_session_id != session_id:
            st.session_state.current_session_id = session_id
            st.session_state.current_session_title = session_title
            st.session_state.session_messages_loaded = False # Mark for reloading messages
            st.session_state.messages = [] # Clear messages to show loading
            st.session_state.show_rename_input = None # Hide rename input when switching sessions
            st.session_state.show_session_actions_id = None # Hide any action buttons when switching
            st.session_state.confirm_delete_id = None # Clear delete confirmation
            # st.rerun() is called automatically after a button click outside an input widget

    # Callback to toggle show/hide action buttons for a session
    def toggle_session_actions(session_id):
        if st.session_state.show_session_actions_id == session_id:
            st.session_state.show_session_actions_id = None # Hide actions
        else:
            st.session_state.show_session_actions_id = session_id # Show actions
        st.session_state.show_rename_input = None # Hide rename form if another session's actions are shown
        st.session_state.confirm_delete_id = None # Hide delete confirmation if another session's actions are shown


    # Callback to show rename input
    def set_rename_input_visible(session_id):
        st.session_state.show_rename_input = session_id
        st.session_state.show_session_actions_id = None # Hide the "..." actions after selecting rename

    # Callback for delete confirmation
    def confirm_delete_session(session_id):
        if st.session_state.current_session_id == session_id:
            st.session_state.confirm_delete_id = session_id
        else:
            st.error("Please select the chat you wish to delete.")
        st.session_state.show_session_actions_id = None # Hide the "..." actions after selecting delete


    # --- Main Chat Area ---
    st.title("💬 FinSolve Chat")

    # --- Session Title and Rename/Delete Confirmation Inputs ---
    if st.session_state.current_session_id:
        st.subheader(st.session_state.current_session_title)
        
        # Confirmation for delete
        if "confirm_delete_id" in st.session_state and st.session_state.confirm_delete_id == st.session_state.current_session_id:
             st.warning(f"Are you sure you want to delete '{st.session_state.current_session_title}'?")
             col_confirm_del, col_cancel_del = st.columns(2)
             with col_confirm_del:
                 if st.button("Yes, Delete", key="do_delete_session", use_container_width=True):
                     if delete_chat_session_api(st.session_state.current_session_id, st.session_state.access_token):
                         st.success("Chat session deleted.")
                         # Reset session state after deletion
                         st.session_state.current_session_id = None
                         st.session_state.messages = []
                         st.session_state.session_messages_loaded = False
                         st.session_state.chat_sessions = get_user_chat_sessions_api(st.session_state.access_token)
                         if st.session_state.chat_sessions:
                             st.session_state.current_session_id = st.session_state.chat_sessions[0]["id"]
                             st.session_state.current_session_title = st.session_state.chat_sessions[0]["title"]
                         st.session_state.confirm_delete_id = None # Clear confirmation state
                         st.rerun()
                     else:
                         st.error("Failed to delete chat session.")
                         st.session_state.confirm_delete_id = None # Clear confirmation state
                         st.rerun() # Rerun to remove confirm buttons
             with col_cancel_del:
                 if st.button("Cancel", key="cancel_delete_session", use_container_width=True):
                     st.session_state.confirm_delete_id = None # Clear confirmation state
                     st.rerun() # Rerun to remove confirm buttons

        # Form for renaming
        elif "show_rename_input" in st.session_state and st.session_state.show_rename_input == st.session_state.current_session_id:
            with st.form(key=f"rename_form_{st.session_state.current_session_id}", clear_on_submit=True):
                new_title = st.text_input("New Chat Title", value=st.session_state.current_session_title, key=f"rename_input_{st.session_state.current_session_id}")
                submit_rename = st.form_submit_button("Save Title")
                if submit_rename:
                    if new_title and new_title != st.session_state.current_session_title:
                        updated_session = update_session_title_api(st.session_state.current_session_id, new_title, st.session_state.access_token)
                        if updated_session:
                            st.success("Chat title updated!")
                            st.session_state.current_session_title = updated_session["title"]
                            st.session_state.chat_sessions = get_user_chat_sessions_api(st.session_state.access_token) # Refresh list
                            del st.session_state.show_rename_input
                            st.rerun()
                        else:
                            st.error("Failed to update chat title.")
                    else:
                        st.info("Title is unchanged or empty.")
                        del st.session_state.show_rename_input
                        st.rerun()
    else:
        st.info("Start a new chat or select an existing one from the sidebar.")


    # Load messages for the current session only once
    if st.session_state.current_session_id and not st.session_state.session_messages_loaded:
        with st.spinner("Loading chat history..."): # NEW: Loading indicator for history
            history_messages = get_session_messages_api(st.session_state.current_session_id, st.session_state.access_token)
            st.session_state.messages = [] # Clear existing messages
            if history_messages:
                for msg in history_messages:
                    st.session_state.messages.append({"role": msg["sender"].capitalize(), "content": msg["message_text"]})
            # Add initial welcome message if session is truly new or empty
            if not st.session_state.messages:
                st.session_state.messages.append({"role": "Bot", "content": f"Hello {st.session_state.username}! How can I assist you today?"})
            st.session_state.session_messages_loaded = True # Mark as loaded


    # Display chat messages from history
    for message in st.session_state.messages:
        avatar = USER_AVATAR if message["role"] == "User" else BOT_AVATAR
        with st.chat_message(message["role"], avatar=avatar):
            st.write(message["content"])
            # Sources are currently only available for newly generated messages
            if "sources" in message and message["sources"]:
                source_display = "**Source(s):**\n"
                unique_sources = {f"{s.get('source_file')}-{s.get('department')}": s for s in message["sources"]}.values()
                for s in unique_sources:
                    dept = f" (Dept: {s['department'].capitalize()})" if s.get('department') else ""
                    source_display += f"- *{s.get('source_file', 'Unknown')}*{dept}\n"
                st.markdown(f'<div class="source-info">{source_display}</div>', unsafe_allow_html=True)

    # Function to handle sending a suggested question
    def send_suggested_question(question):
        st.session_state.suggested_question = question

    # Display suggested questions if chat is in its initial state for the current session
    if st.session_state.current_session_id and len(st.session_state.messages) == 1 and st.session_state.messages[0]["content"].startswith("Hello"):
        st.markdown("#### Suggested Questions:")
        role_questions = {
            "ceo": ["Summarize Q2 financial performance.", "What are the key risks identified by the finance and engineering departments?"],
            "finance team": ["What were the total expenses for the marketing department in Q1?", "Generate a summary of our revenue streams."],
            "marketing team": ["What is the marketing budget for the next quarter?", "List recent campaign performance metrics."],
            "hr team": ["Summarize the new employee onboarding policy.", "Are there any updates to the company's leave policy?"],
            "engineering department": ["What was the R&D spending last quarter?", "Provide an overview of the 'Project Phoenix' budget."],
            "employee level": ["What is the company policy on remote work?", "How do I submit an expense report?"]
        }
        
        role_key = st.session_state.user_role.lower() 
        questions = role_questions.get(role_key, role_questions["employee level"]) # Default to employee questions

        cols = st.columns(len(questions))
        for i, q in enumerate(questions):
            with cols[i]:
                st.button(q, on_click=send_suggested_question, args=[q], key=f"suggestion_{st.session_state.current_session_id}_{i}", help=q, use_container_width=True)


    # Handle chat input from user (either typed or from a suggested question)
    prompt = st.chat_input("What would you like to know?", key="chat_input_main", disabled=not st.session_state.current_session_id)
    if "suggested_question" in st.session_state and st.session_state.suggested_question:
        prompt = st.session_state.suggested_question
        del st.session_state["suggested_question"] # Consume the suggested question

    if prompt and st.session_state.current_session_id: # Ensure there's an active session
        st.session_state.messages.append({"role": "User", "content": prompt})
        with st.chat_message("User", avatar=USER_AVATAR):
            st.write(prompt)

        with st.chat_message("Bot", avatar=BOT_AVATAR):
            with st.spinner("Thinking..."):
                chat_response = chat_api(prompt, st.session_state.access_token, st.session_state.current_session_id)
            
            full_response_content = ""
            sources = []

            if chat_response:
                full_response_content = chat_response.get("response", "No response from bot.")
                sources = chat_response.get("sources", [])
                # Ensure the session_id from response matches current_session_id for consistency
                # In normal flow, it should always match, but good for debugging.
                if chat_response.get("session_id") and chat_response["session_id"] != st.session_state.current_session_id:
                    st.warning("Session ID mismatch detected. Reloading sessions.")
                    st.session_state.chat_sessions = get_user_chat_sessions_api(st.session_state.access_token)
                    # Try to set to the returned session_id if it's new, otherwise stick to current
                    found_session = next((s for s in st.session_state.chat_sessions if s["id"] == chat_response["session_id"]), None)
                    if found_session:
                        st.session_state.current_session_id = found_session["id"]
                        st.session_state.current_session_title = found_session["title"]
                    else: # Fallback if returned ID is not in current list (shouldn't happen with proper backend)
                        st.session_state.current_session_id = chat_response["session_id"]
                        st.session_state.current_session_title = "New Chat" # Or some derived title if you implement auto-titling
                    
                    st.session_state.session_messages_loaded = False # Force reload messages for the new session
                    st.rerun()


                st.write(full_response_content)
            else:
                full_response_content = "Sorry, I encountered an issue getting a response."
                st.write(full_response_content)

        st.session_state.messages.append({
            "role": "Bot",
            "content": full_response_content,
            "sources": sources
        })
        
        st.rerun()

# --- Admin Panel UI ---
def display_admin_page():
    # --- Admin Sidebar ---
    with st.sidebar:
        st.title("Admin Panel")
        st.write(f"Logged in as: **{st.session_state.username}** (Admin)")
        st.markdown("---")
        if st.button("Go to Chatbot", key="go_to_chat_button", use_container_width=True):
            st.session_state.current_page = "chat"
            st.rerun()
        if st.button("Logout", key="admin_logout_button", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            init_session_state()
            st.rerun()
    
    st.header("⚙️ User Management")

    # Only attempt to fetch data and render forms if the user is confirmed as Admin
    # This acts as an additional safeguard against unauthorized backend calls
    if st.session_state.user_role == "Admin" and st.session_state.access_token:
        # Fetch available roles once
        if not st.session_state.roles_list:
            st.session_state.roles_list = get_available_roles_api(st.session_state.access_token)
            if "Admin" not in st.session_state.roles_list:
                 st.session_state.roles_list.append("Admin")
            st.session_state.roles_list.sort()


        # Create New User Form
        st.subheader("Create New User")
        with st.form("create_user_form", clear_on_submit=True):
            new_username = st.text_input("Username", key="new_username")
            new_password = st.text_input("Password", type="password", key="new_password")
            new_role = st.selectbox("Role", st.session_state.roles_list, key="new_role")
            
            default_department = "general"
            if new_role == "Admin" or new_role == "C-Level Executives":
                default_department = "all"
            elif "finance" in new_role.lower():
                default_department = "finance"
            elif "marketing" in new_role.lower():
                default_department = "marketing"
            elif "hr" in new_role.lower():
                default_department = "hr"
            elif "engineering" in new_role.lower():
                default_department = "engineering"

            new_department = st.selectbox("Department Access", st.session_state.departments_list, index=st.session_state.departments_list.index(default_department) if default_department in st.session_state.departments_list else 0, key="new_department")

            create_submitted = st.form_submit_button("Create User")
            if create_submitted:
                if new_username and new_password:
                    user_data = {
                        "username": new_username,
                        "password": new_password,
                        "role": new_role,
                        "department": new_department
                    }
                    response = create_user_api(user_data, st.session_state.access_token)
                    if response:
                        st.success(f"User '{response['username']}' created successfully!")
                        st.session_state.selected_user_id = None # Clear selection after create
                        st.rerun() # Rerun to update the user list table
                else:
                    st.warning("Username and Password are required to create a user.")

        st.markdown("---")

        # List All Users and Management
        st.subheader("Manage Existing Users")
        users = get_all_users_api(st.session_state.access_token) # This call is now inside the robust guard

        if users:
            import pandas as pd
            users_df = pd.DataFrame(users)
            
            # Add a 'Select' column for checkboxes
            users_df['Select'] = False
            
            # Use st.data_editor for an editable table
            edited_df = st.data_editor(users_df, 
                                       column_order=['Select', 'id', 'username', 'role', 'department'],
                                       column_config={"id": st.column_config.NumberColumn("ID", disabled=True),
                                                      "username": st.column_config.TextColumn("Username", disabled=True),
                                                      "role": st.column_config.SelectboxColumn("Role", options=st.session_state.roles_list, required=True),
                                                      "department": st.column_config.SelectboxColumn("Department", options=st.session_state.departments_list, required=True),
                                                      "Select": st.column_config.CheckboxColumn("Select", help="Select user for update/delete")},
                                       hide_index=True,
                                       key="users_data_editor")

            selected_rows = edited_df[edited_df['Select']]
            
            if len(selected_rows) > 0:
                # Only allow one user to be selected for update/delete at a time
                if len(selected_rows) > 1:
                    st.warning("Please select only one user for update or delete.")
                    st.session_state.selected_user_id = None
                else:
                    st.session_state.selected_user_id = selected_rows.iloc[0]['id']
                    selected_username = selected_rows.iloc[0]['username']
                    selected_role = selected_rows.iloc[0]['role']
                    selected_department = selected_rows.iloc[0]['department']

                    st.markdown(f"**Selected User: {selected_username} (ID: {st.session_state.selected_user_id})**")

                    with st.form("update_user_form", clear_on_submit=False):
                        st.write(f"Updating User: **{selected_username}**")
                        # Pre-fill with current values
                        update_role = st.selectbox("New Role", st.session_state.roles_list, index=st.session_state.roles_list.index(selected_role) if selected_role in st.session_state.roles_list else 0, key="update_role")
                        update_department = st.selectbox("New Department Access", st.session_state.departments_list, index=st.session_state.departments_list.index(selected_department) if selected_department in st.session_state.departments_list else 0, key="update_department")
                        update_password = st.text_input("New Password (leave blank to keep current)", type="password", key="update_password")
                        
                        update_submitted = st.form_submit_button("Update User")
                        if update_submitted:
                            user_data_to_update = {}
                            # Only add to payload if value has changed or password is provided
                            if update_role != selected_role:
                                user_data_to_update["role"] = update_role
                            if update_department != selected_department:
                                user_data_to_update["department"] = update_department
                            if update_password: # Only include password if user typed something
                                user_data_to_update["password"] = update_password
                            
                            if user_data_to_update: # Only send API call if there are changes
                                response = update_user_api(user_id=st.session_state.selected_user_id, user_data=user_data_to_update, token=st.session_state.access_token)
                                if response:
                                    st.success(f"User '{response['username']}' updated successfully!")
                                    st.session_state.selected_user_id = None # Clear selection after update
                                    st.rerun() # Rerun to update the user list table
                                else:
                                    st.error("Failed to update user.")
                            else:
                                st.info("No changes detected to update.")
                    
                    # Delete User Button
                    if st.button(f"Delete User: {selected_username}", key="delete_user_button", help="Cannot delete yourself."):
                        if selected_username == st.session_state.username:
                            st.error("You cannot delete your own admin account!")
                        else:
                            if delete_user_api(st.session_state.selected_user_id, st.session_state.access_token):
                                st.success(f"User '{selected_username}' deleted successfully.")
                                st.session_state.selected_user_id = None # Clear selection after delete
                                st.rerun() # Rerun to update the user list table
                            else:
                                st.error("Failed to delete user.")
            else:
                st.info("Select a user from the table above to update or delete.")
                st.session_state.selected_user_id = None # Ensure no user is selected if no row is checked
        else:
            st.info("No users found in the database. Create one using the form above.")
    else: # If not admin or no token, display a warning
        st.warning("You must be logged in as an Admin to access User Management.")


# --- Main App Logic (Page Routing) ---
if not st.session_state.logged_in:
    display_login_page()
elif st.session_state.current_page == "chat":
    display_chat_page()
elif st.session_state.current_page == "admin":
    # This outer check ensures that only "Admin" roles can even *enter* the admin display function.
    if st.session_state.user_role == "Admin":
        display_admin_page()
    else:
        st.error("Access Denied: You do not have administrator privileges.")
        st.session_state.current_page = "chat" # Redirect non-admins to chat page
        st.rerun()
