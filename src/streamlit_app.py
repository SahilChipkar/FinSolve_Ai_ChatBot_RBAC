# src/streamlit_app.py

import streamlit as st
import requests
import json
import time

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

def chat_api(query, token):
    """ Sends chat query to FastAPI backend with JWT for authentication. """
    url = f"{FASTAPI_BASE_URL}/chat"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.post(url, json={"query": query}, headers=headers)
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
            error_message += f"\nDetails: {error_detail}"
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
        return True # 204 No Content typically returns no JSON
    except requests.exceptions.RequestException as e:
        error_message = f"Error deleting user: {e}"
        try:
            error_detail = response.json().get("detail", "No details provided.")
            error_message += f"\nDetails: {error_detail}"
        except (requests.exceptions.JSONDecodeError, AttributeError):
            pass
        st.error(error_message)
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
    if "access_token" not in st.session_state: # Store JWT token
        st.session_state.access_token = ""
    if "current_page" not in st.session_state:
        st.session_state.current_page = "chat" # or "admin"
    if "selected_user_id" not in st.session_state:
        st.session_state.selected_user_id = None
    if "roles_list" not in st.session_state:
        st.session_state.roles_list = []
    if "departments_list" not in st.session_state:
        # These need to be consistent with src/core/rbac.py and src/data_ingestion/ingest.py
        st.session_state.departments_list = ["all", "finance", "marketing", "hr", "engineering", "general"]


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
                            st.session_state.username = username # Username is sent, not returned from token endpoint
                            st.session_state.access_token = token_data["access_token"]
                            
                            # --- FIX: Retrieve user details based on role to avoid unauthorized admin calls ---
                            # Only attempt to get user details via /admin/users if the user is 'admin'
                            if username == "admin":
                                try:
                                    response = requests.get(f"{FASTAPI_BASE_URL}/admin/users", headers={"Authorization": f"Bearer {st.session_state.access_token}"})
                                    response.raise_for_status()
                                    all_users = response.json()
                                    current_user_details = next((u for u in all_users if u['username'] == username), None)

                                    if current_user_details:
                                        st.session_state.user_role = current_user_details["role"]
                                        st.session_state.department = current_user_details["department"]
                                    else:
                                        st.error("Could not retrieve admin user details after login. Please try again.")
                                        st.session_state.logged_in = False # Force re-login
                                        st.rerun()

                                except requests.exceptions.RequestException as e:
                                    st.error(f"Failed to fetch admin user details after login: {e}. Please ensure FastAPI is running and admin endpoints are accessible.")
                                    st.session_state.logged_in = False
                                    st.rerun()
                            else:
                                # For non-admin users, we'll infer role/department locally for display
                                # This mapping should ideally come from a non-admin backend endpoint (e.g., /users/me)
                                MOCK_LOCAL_USER_ROLES = {
                                    "finance_user": {"role": "Finance Team", "department": "finance"},
                                    "marketing_user": {"role": "Marketing Team", "department": "marketing"},
                                    "hr_user": {"role": "HR Team", "department": "hr"},
                                    "eng_user": {"role": "Engineering Department", "department": "engineering"},
                                    "ceo": {"role": "C-Level Executives", "department": "all"},
                                    "employee": {"role": "Employee Level", "department": "general"}
                                }
                                user_details = MOCK_LOCAL_USER_ROLES.get(username, {"role": "Unknown", "department": "Unknown"})
                                st.session_state.user_role = user_details["role"]
                                st.session_state.department = user_details["department"]


                            st.success(f"Logged in as {st.session_state.username} ({st.session_state.user_role})")
                            st.session_state.messages = [
                                {"role": "Bot", "content": f"Hello {st.session_state.username}! How can I assist you today?"}
                            ]
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
            if st.button("Go to Admin Panel", key="go_to_admin_button"):
                st.session_state.current_page = "admin"
                st.rerun()

        if st.button("Clear Conversation", key="clear_chat_button"):
            st.session_state.messages = [
                {"role": "Bot", "content": f"Hello {st.session_state.username}! Your chat has been cleared. How can I help?"}
            ]
            st.rerun()

        if st.button("Logout", key="logout_button"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            init_session_state() # Re-initialize to clear all state
            st.rerun()

    # --- Main Chat Area ---
    st.title("💬 FinSolve Chat")

    # Display chat messages from history
    for message in st.session_state.messages:
        avatar = USER_AVATAR if message["role"] == "User" else BOT_AVATAR
        with st.chat_message(message["role"], avatar=avatar):
            st.write(message["content"])
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

    # Display suggested questions if chat is in its initial state
    if len(st.session_state.messages) <= 1:
        st.markdown("#### Suggested Questions:")
        role_questions = {
            "ceo": ["Summarize Q2 financial performance.", "What are the key risks identified by the finance and engineering departments?"],
            "finance team": ["What were the total expenses for the marketing department in Q1?", "Generate a summary of our revenue streams."],
            "marketing team": ["What is the marketing budget for the next quarter?", "List recent campaign performance metrics."],
            "hr team": ["Summarize the new employee onboarding policy.", "Are there any updates to the company's leave policy?"],
            "engineering department": ["What was the R&D spending last quarter?", "Provide an overview of the 'Project Phoenix' budget."],
            "employee level": ["What is the company policy on remote work?", "How do I submit an expense report?"]
        }
        
        # Get questions based on the lowercase user_role for consistency
        role_key = st.session_state.user_role.lower() 
        questions = role_questions.get(role_key, role_questions["employee level"]) # Default to employee questions

        cols = st.columns(len(questions))
        for i, q in enumerate(questions):
            with cols[i]:
                st.button(q, on_click=send_suggested_question, args=[q], key=f"suggestion_{i}", help=q, use_container_width=True)


    # Handle chat input from user (either typed or from a suggested question)
    prompt = st.chat_input("What would you like to know?") or st.session_state.get("suggested_question")

    if prompt:
        if "suggested_question" in st.session_state:
            del st.session_state["suggested_question"]
            
        st.session_state.messages.append({"role": "User", "content": prompt})
        with st.chat_message("User", avatar=USER_AVATAR):
            st.write(prompt)

        with st.chat_message("Bot", avatar=BOT_AVATAR):
            response_placeholder = st.empty()
            full_response_content = ""
            sources = []

            chat_response = chat_api(prompt, st.session_state.access_token)
            
            if chat_response:
                full_response_content = chat_response.get("response", "No response from bot.")
                sources = chat_response.get("sources", [])
                response_placeholder.write(full_response_content)
            else:
                full_response_content = "Sorry, I encountered an issue getting a response."
                response_placeholder.write(full_response_content)

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
        if st.button("Go to Chatbot", key="go_to_chat_button"):
            st.session_state.current_page = "chat"
            st.rerun()
        if st.button("Logout", key="admin_logout_button"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            init_session_state()
            st.rerun()
    
    st.header("⚙️ User Management")

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
                    st.session_state.selected_user_id = None
                    st.rerun()
            else:
                st.warning("Username and Password are required to create a user.")

    st.markdown("---")

    # List All Users and Management
    st.subheader("Manage Existing Users")
    users = get_all_users_api(st.session_state.access_token)

    if users:
        import pandas as pd
        users_df = pd.DataFrame(users)
        
        users_df['Select'] = False
        
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
            st.session_state.selected_user_id = selected_rows.iloc[0]['id']
            selected_username = selected_rows.iloc[0]['username']
            selected_role = selected_rows.iloc[0]['role']
            selected_department = selected_rows.iloc[0]['department']

            st.markdown(f"**Selected User: {selected_username} (ID: {st.session_state.selected_user_id})**")

            with st.form("update_user_form", clear_on_submit=False):
                st.write(f"Updating User: **{selected_username}**")
                update_role = st.selectbox("New Role", st.session_state.roles_list, index=st.session_state.roles_list.index(selected_role), key="update_role")
                update_department = st.selectbox("New Department Access", st.session_state.departments_list, index=st.session_state.departments_list.index(selected_department), key="update_department")
                update_password = st.text_input("New Password (leave blank to keep current)", type="password", key="update_password")
                
                update_submitted = st.form_submit_button("Update User")
                if update_submitted:
                    user_data_to_update = {}
                    if update_role != selected_role:
                        user_data_to_update["role"] = update_role
                    if update_department != selected_department:
                        user_data_to_update["department"] = update_department
                    if update_password:
                        user_data_to_update["password"] = update_password
                    
                    if user_data_to_update:
                        response = update_user_api(st.session_state.selected_user_id, user_data_to_update, st.session_state.access_token)
                        if response:
                            st.success(f"User '{response['username']}' updated successfully!")
                            st.session_state.selected_user_id = None
                            st.rerun()
                        else:
                            st.error("Failed to update user.")
                    else:
                        st.info("No changes detected to update.")
            
            if st.button(f"Delete User: {selected_username}", key="delete_user_button", help="Cannot delete yourself."):
                if selected_username == st.session_state.username:
                    st.error("You cannot delete your own admin account!")
                else:
                    if delete_user_api(st.session_state.selected_user_id, st.session_state.access_token):
                        st.success(f"User '{selected_username}' deleted successfully.")
                        st.session_state.selected_user_id = None
                        st.rerun()
                    else:
                        st.error("Failed to delete user.")
        else:
            st.info("Select a user from the table above to update or delete.")
            st.session_state.selected_user_id = None
    else:
        st.info("No users found in the database. Create one using the form above.")


# --- Main App Logic (Page Routing) ---
if not st.session_state.logged_in:
    display_login_page()
elif st.session_state.current_page == "chat":
    display_chat_page()
elif st.session_state.current_page == "admin":
    if st.session_state.user_role == "Admin":
        display_admin_page()
    else:
        st.error("Access Denied: You do not have administrator privileges.")
        st.session_state.current_page = "chat"
        st.rerun()
