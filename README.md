# FinSolve RBAC Chatbot

## 🎯 Project Overview

The **FinSolve RBAC Chatbot** is an AI-powered conversational agent designed to provide secure, role-based access to organizational knowledge. It leverages Retrieval Augmented Generation (RAG) to deliver accurate, context-aware responses while ensuring that users can only access information aligned with their assigned roles and departmental permissions. This project includes a FastAPI backend API, a Streamlit frontend UI, a local SQLite database for user management, and integrates with Ollama for embeddings and the Gemini API for natural language generation.

---

## 📝 Table of Contents

* [🎯 Project Overview](#-project-overview)
* [✨ Key Features](#-key-features)
* [🚀 Technologies Used](#-technologies-used)
* [📂 Project Structure](#-project-structure)
* [⚙️ Setup and Installation](#%EF%B8%8F-setup-and-installation)
    * [Prerequisites](#prerequisites)
    * [Installation Steps](#installation-steps)
* [▶️ Running the Application](#%EF%B8%8F-running-the-application)
* [👥 Role Definitions and Access](#-role-definitions-and-access)
* [💡 Usage Examples](#-usage-examples)
    * [Logging In](#logging-in)
    * [Chatting with the Bot](#chatting-with-the-bot)
    * [Using the Admin Panel (as `admin` user)](#using-the-admin-panel-as-admin-user)
* [📐 Architecture Overview](#-architecture-overview)
* [⚠️ Current Limitations](#%EF%B8%8F-current-limitations)
* [🚀 Future Enhancements](#-future-enhancements)

---

## ✨ Key Features

* **Role-Based Access Control (RBAC):** Strict control over data access based on user roles and departments, ensuring sensitive information is only accessible to authorized personnel.
    * **Proactive Departmental Denial:** The system infers the user's query intent and proactively denies access if it targets a restricted department, providing a clear "no permission" message.
    * **Filtered Retrieval:** Semantic search queries to the vector database are dynamically filtered based on user permissions.
* **Conversational AI (RAG):** Answers natural language queries by retrieving relevant information from an extensive knowledge base.
* **Admin Panel:** A dedicated section for administrators to manage user accounts (Create, Read, Update, Delete) and assign roles/departments.
* **User Authentication:** Secure JWT (JSON Web Token) based login and session management.
* **Modular Architecture:** Clean separation of concerns for easy understanding, maintenance, and future expansion.
* **Data Ingestion Pipeline:** Automates the processing of raw organizational documents into a searchable vector store.
* **Responsive User Interface:** A user-friendly Streamlit frontend that adapts to different screen sizes.

## 🚀 Technologies Used

* **Python:** Core programming language.
* **FastAPI:** High-performance web framework for the backend API.
* **Streamlit:** Framework for building the interactive web user interface.
* **Ollama:** Local large language model runtime used for generating `nomic-embed-text` embeddings.
* **Gemini API:** Google's Generative AI API (`gemini-2.5-flash`) for natural language response generation.
* **ChromaDB:** Lightweight, embedded vector database for storing document embeddings and metadata.
* **SQLAlchemy:** Python SQL toolkit and Object Relational Mapper (ORM) for interacting with SQLite.
* **SQLite:** File-based relational database for user authentication and management.
* **`python-dotenv`:** For managing environment variables.
* **`python-jose`:** For JWT authentication.
* **`httpx`:** Asynchronous HTTP client for API calls.
* **`langchain` / `langchain-text-splitters`:** For robust text processing and chunking.
* **`pandas`:** For handling tabular data (e.g., CSV).

## 📂 Project Structure

.
├── data/                             # Raw organizational documents
│   ├── engineering/
│   ├── finance/
│   ├── general/
│   ├── hr/
│   └── marketing/
├── chroma_db/                        # Persistent storage for ChromaDB
├── finsolve_users.db                 # SQLite database for user data
├── src/
│   ├── init.py
│   ├── main.py                       # FastAPI application (main entry point)
│   ├── streamlit_app.py              # Streamlit frontend application
│   │
│   ├── core/                         # Core chatbot logic components
│   │   ├── init.py
│   │   ├── embedding.py              # Ollama embedding generation
│   │   ├── llm.py                    # Gemini API LLM interaction
│   │   ├── vector_store.py           # ChromaDB client & operations
│   │   ├── rbac.py                   # Role-Based Access Control definitions & filters
│   │   └── rag_chain.py              # Orchestrates the RAG flow & RBAC enforcement
│   │
│   ├── data_ingestion/               # Scripts for processing raw data
│   │   ├── init.py
│   │   ├── ingest.py                 # Main data ingestion script
│   │   ├── document_loaders.py       # Helpers for loading different file types
│   │   └── text_splitter.py          # Utility for text chunking
│   │
│   └── admin/                        # (Conceptual) Future Admin Panel related logic/schemas (currently integrated in main.py)
│       └── # ... (future admin-specific files)
│
├── .streamlit/                       # Streamlit configuration for theme
│   └── config.toml
├── .env                              # Environment variables
├── requirements.txt                  # Python dependencies
├── README.md                         # Project documentation (this file)
└── run.sh                            # Script to start both FastAPI and Streamlit


## ⚙️ Setup and Installation

Follow these steps to get the FinSolve RBAC Chatbot up and running on your local machine.

### Prerequisites

1.  **Python 3.9+:** Ensure you have Python installed.

2.  **Ollama:**
    * Download and install Ollama from [ollama.com](https://ollama.com/).
    * Once installed, open a terminal and run `ollama serve` to start the Ollama server. Keep this terminal open while the chatbot is running.
    * Pull the required models:
        ```bash
        ollama pull nomic-embed-text
        ```
        *(Note: While `nomic-embed-text` from Ollama is used for embeddings, the project utilizes the Gemini API for LLM generation.)*

3.  **Git:** For cloning the repository.

### Installation Steps

1.  **Clone the Repository:**
    ```bash
    git clone <repository_url_here>
    cd DS-RPC-01 # Or whatever your project folder is named
    ```

2.  **Create a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    # On Windows:
    venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    ```

3.  **Install Python Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set Up Environment Variables:**
    * Create a file named `.env` in the root directory of your project.
    * Add the following content to `.env`:
        ```dotenv
        # Ollama Host URL (Needed for nomic-embed-text embeddings)
        OLLAMA_HOST=http://localhost:11434

        # Secret key for JWT authentication (IMPORTANT: Change this to a strong, random string in production!)
        SECRET_KEY="your-super-secret-jwt-key-change-this-in-production"
        ALGORITHM="HS256"

        # Initial password for the 'admin' user created during database setup
        # If not set, it defaults to "adminpass"
        ADMIN_INITIAL_PASSWORD="adminpass"
        ```
    * **Note:** The Gemini API Key is automatically managed by the Canvas environment for `gemini-2.0-flash` (or `gemini-2.5-flash`), so you do **not** need to put it in your `.env` or in the `llm.py` code.

5.  **Initialize SQLite Database & Seed Users:**
    * This step creates the `finsolve_users.db` file and populates it with default users (including `admin`).
    * Run from the project root:
        ```bash
        python -u src/database.py
        ```
    * You should see output confirming user creation.

6.  **Run Data Ingestion:**
    * This processes your `data/` documents, generates embeddings, and loads them into ChromaDB. This will **clear** any existing data in your `finsolve_organizational_data` ChromaDB collection and rebuild it.
    * Run from the project root:
        ```bash
        python -u src/data_ingestion/ingest.py
        ```
    * Confirm successful ingestion in the terminal output.

7.  **Clear Python Cache (Good Practice):**
    ```bash
    # On Windows (PowerShell/CMD):
    for /d %i in ("__pycache__") do @rd /s /q "%i"
    # On macOS/Linux (Bash/Zsh):
    find . -name "__pycache__" -type d -exec rm -rf {} +
    ```

## ▶️ Running the Application

After completing the setup:

1.  **Ensure Ollama Server is Running:** (As mentioned in prerequisites)
    ```bash
    ollama serve
    ```
    (Keep this terminal open)

2.  **Start the FinSolve Chatbot Application:**
    * Open a **new terminal window** in your project root.
    * Activate your virtual environment.
    * Run the convenience script:
        ```bash
        ./run.sh
        ```
        This script will start both the FastAPI backend and the Streamlit frontend. Your web browser should automatically open to `http://localhost:8501`.

    *(Alternatively, you can run them manually in separate terminals:)*
    * *Terminal 1:* `uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload`
    * *Terminal 2 (new tab/window):* `streamlit run src/streamlit_app.py`

## 👥 Role Definitions and Access

The chatbot implements a strict RBAC model. Here are the predefined roles and their access permissions:

* **Admin:**
    * **Access:** Full access to all company data across all departments (`finance`, `marketing`, `hr`, `engineering`, `general`). Can also manage all user accounts.
    * **Login:** `username: admin`, `password: ADMIN_INITIAL_PASSWORD` (from your `.env`, defaults to `adminpass`).

* **C-Level Executives:**
    * **Access:** Full access to all company data across all departments (`finance`, `marketing`, `hr`, `engineering`, `general`).
    * **Login:** `username: ceo`, `password: ceopass`

* **Finance Team:**
    * **Access:** Financial reports, marketing expenses, equipment costs, reimbursements, etc. (i.e., data within the `finance` department).
    * **Login:** `username: finance_user`, `password: financepass`

* **Marketing Team:**
    * **Access:** Campaign performance data, customer feedback, and sales metrics (i.e., data within the `marketing` department).
    * **Login:** `username: marketing_user`, `password: marketingpass`

* **HR Team:**
    * **Access:** Employee data, attendance records, payroll, and performance reviews (i.e., data within the `hr` department).
    * **Login:** `username: hr_user`, `password: hrpass`

* **Engineering Department:**
    * **Access:** Technical architecture, development processes, and operational guidelines (i.e., data within the `engineering` department).
    * **Login:** `username: eng_user`, `password: engpass`

* **Employee Level:**
    * **Access:** Only general company information such as policies, events, and FAQs (i.e., data within the `general` department).
    * **Login:** `username: employee`, `password: employeepass`

## 💡 Usage Examples

### Logging In

1.  Open your browser to `http://localhost:8501`.

2.  Use any of the defined user credentials from the "Role Definitions and Access" section.

3.  For example, enter `username: finance_user`, `password: financepass`, and click "Login".

### Chatting with the Bot

Once logged in, you'll see the chat interface.

* **Authorized Query (e.g., as `finance_user`):**
    * Ask: "Generate a summary of our revenue streams."
    * Expected: An answer based on financial documents, with sources from the `finance` department.

* **Unauthorized Query (e.g., as `finance_user` trying to access marketing data):**
    * Ask: "What were the customer acquisition targets for Q1 2025?"
    * Expected: "Sorry, based on your 'Finance Team' role, you do not have permission to access information related to the Marketing department." (This demonstrates the proactive denial).

* **Query for Non-Existent Info (e.g., as any user):**
    * Ask: "What is the capital of Mars?"
    * Expected: "I couldn't find any relevant information for your query in our knowledge base. Please try rephrasing or check if the information exists."

### Using the Admin Panel (as `admin` user)

1.  Log in as `username: admin`, `password: ADMIN_INITIAL_PASSWORD`.

2.  In the sidebar, click "Go to Admin Panel".

3.  **Create User:** Use the "Create New User" form.

4.  **Manage Users:**
    * The table lists existing users.
    * Select a user (by checking the "Select" box) to enable the "Update User" form and "Delete User" button.
    * **Update User:** Change their role, department, or password.
    * **Delete User:** Remove a user (you cannot delete your own admin account).

5.  Click "Go to Chatbot" in the sidebar to return to the chat interface.

## 📐 Architecture Overview

The FinSolve RBAC Chatbot follows a modular, multi-layered architecture to ensure clear separation of concerns, scalability, and robust security.

* **Frontend (Streamlit App):** The user-facing web interface.

* **Backend (FastAPI App):** The central API server that handles all business logic, authentication, authorization, and orchestrates the RAG pipeline.

* **RBAC Module:** A core component within the backend that strictly enforces data access permissions based on predefined roles and departments. It applies filters during data retrieval and employs a proactive denial heuristic for queries targeting unauthorized departments.

* **Data & ML Services:**
    * **Ollama (Embeddings - `nomic-embed-text`):** Locally runs the embedding model to convert text into numerical vectors.
    * **Gemini API (LLM - `gemini-2.5-flash`):** The powerful AI model that generates natural language responses.
    * **ChromaDB (Vector Store):** Stores the embedded organizational data chunks along with their critical metadata (department, access level).
    * **SQLite (User Data):** A local database for secure user authentication and management.
    * **Organizational Data:** Your raw company documents.

* **Data Processing (Data Ingestion Script):** An offline script that prepares the raw organizational data by chunking, tagging with metadata, embedding, and loading into ChromaDB.

## ⚠️ Current Limitations

* **Password Hashing:** SHA256 is used for password hashing, which is suitable for demonstration. For production, stronger algorithms like bcrypt or Argon2 should be used.

* **Gemini API Key:** The API key is assumed to be injected by the Canvas environment. In a non-Canvas production environment, secure management (e.g., environment variables, secret management service) would be required.

* **Document Loaders:** Currently supports `.md` and `.csv`. Support for `.pdf` and `.docx` is present in `document_loaders.py` but commented out; external libraries might be needed for full functionality.

* **Chat History Persistence:** Chat history is not currently saved between user sessions or browser refreshes.

* **RBAC Rule Management in UI:** Role permissions (`ROLE_PERMISSIONS`) and department keywords (`DEPARTMENT_KEYWORDS`) are hardcoded in Python files. Dynamic management via the Admin UI is not implemented.

## 🚀 Future Enhancements

* **Advanced User Management:** Integrate with enterprise Identity Providers (IdPs) like Okta, Azure AD, or Auth0 for robust authentication.

* **Dynamic RBAC Rule Configuration:** Allow administrators to define and manage roles, permissions, and departmental keywords directly through the Admin UI, storing them persistently in the database.

* **Fine-Grained Access Levels:** Implement more granular `access_level` rules beyond simple department access (e.g., "confidential reports" vs. "general reports" within the Finance department).

* **Chat History Persistence:** Implement saving chat conversations to the SQLite database for user-specific history.

* **Enhanced Document Loaders:** Fully enable and test `.pdf` and `.docx` loading capabilities with appropriate parsing libraries.

* **Feedback Mechanism:** Allow users to provide feedback on chatbot responses.

* **Monitoring and Analytics:** Implement logging and dashboards for chatbot usage, performance, and common queries.

* **Multi-tenant Support:** Extend the architecture to support multiple distinct organizations if needed.