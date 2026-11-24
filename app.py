
import streamlit as st
import asyncio
import os
from pathlib import Path
from collections import Counter

from langchain_core.messages import HumanMessage

from backend.repository_manager import RepositoryManager
from backend.retriever import index_repository, get_collection_stats
from backend.graph import build_graph
from utils.code_parser import get_all_repository_files


# ==================================================
# PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="RepoGuide",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded"
)

BASE_DIR = Path(__file__).resolve().parent


# ==================================================
# LOAD ENVIRONMENT VARIABLES
# ==================================================

# Load from .env file for local development
from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

# For Streamlit Cloud, use st.secrets
try:
    if "GOOGLE_API_KEY" in st.secrets:
        os.environ["GOOGLE_API_KEY"] = st.secrets["GOOGLE_API_KEY"]
except Exception:
    # st.secrets not available (running locally without secrets.toml)
    pass

# Verify API key is available
if not os.getenv("GOOGLE_API_KEY"):
    st.error("""
    ⚠️ **GOOGLE_API_KEY not found!**
    
    **For local development:**
    - Create a `.env` file in the project root
    - Add: `GOOGLE_API_KEY=your_api_key_here`
    
    **For Streamlit Cloud:**
    - Go to app settings
    - Click "Secrets" in the sidebar
    - Add:
    ```
    GOOGLE_API_KEY = "your_api_key_here"
    ```
    
    Get your free API key at: https://ai.google.dev/
    """)
    st.stop()


# ==================================================
# INITIALIZE REPOSITORY MANAGER
# ==================================================

@st.cache_resource
def get_repo_manager():
    return RepositoryManager(BASE_DIR)


repo_manager = get_repo_manager()


# ==================================================
# SESSION STATE
# ==================================================

if "current_repo_id" not in st.session_state:
    st.session_state.current_repo_id = None

if "current_repo_path" not in st.session_state:
    st.session_state.current_repo_path = None

if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent_messages" not in st.session_state:
    st.session_state.agent_messages = []

if "agent" not in st.session_state:
    st.session_state.agent = None

if "indexing_status" not in st.session_state:
    st.session_state.indexing_status = None


# ==================================================
# CUSTOM STYLING
# ==================================================

st.markdown("""
<style>
    .main-title {
        font-size: 2.5rem;
        font-weight: 750;
    }

    .subtitle {
        color: #888888;
        font-size: 1rem;
    }

    div[data-testid="stMetric"] {
        background-color: rgba(128,128,128,0.08);
        padding: 15px;
        border-radius: 10px;
    }
    
    .repo-connected {
        color: #28a745;
        font-weight: bold;
    }
    
    .repo-not-connected {
        color: #dc3545;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


# ==================================================
# HEADER
# ==================================================

st.markdown(
    '<div class="main-title">RepoGuide</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Your Agentic Codebase Intelligence Assistant'
    '</div>',
    unsafe_allow_html=True
)

st.divider()


# ==================================================
# SIDEBAR
# ==================================================

st.sidebar.title("RepoGuide")

st.sidebar.subheader("Connected Repository")

if st.session_state.current_repo_id:
    repo_info = repo_manager.get_repository(st.session_state.current_repo_id)
    if repo_info:
        st.sidebar.markdown(
            f'<div class="repo-connected">✓ {Path(repo_info["path"]).name}</div>',
            unsafe_allow_html=True
        )
        st.sidebar.caption(f"Type: {repo_info['type']}")
        st.sidebar.caption(f"Path: {repo_info['path']}")
        
        # Show indexing status
        stats = get_collection_stats(st.session_state.current_repo_id)
        if stats['exists'] and stats['count'] > 0:
            st.sidebar.caption(f"✓ Indexed: {stats['count']} chunks")
        else:
            st.sidebar.caption("⚠ Not indexed yet")
    else:
        st.sidebar.markdown(
            '<div class="repo-not-connected">✗ No repository</div>',
            unsafe_allow_html=True
        )
else:
    st.sidebar.markdown(
        '<div class="repo-not-connected">✗ No repository</div>',
        unsafe_allow_html=True
    )

if st.sidebar.button("Switch Repository", use_container_width=True):
    st.session_state.current_repo_id = None
    st.session_state.current_repo_path = None
    st.session_state.messages = []
    st.session_state.agent_messages = []
    st.session_state.agent = None
    st.session_state.indexing_status = None
    st.rerun()

st.sidebar.divider()

if st.sidebar.button("Clear Chat", use_container_width=True):
    st.session_state.messages = []
    st.session_state.agent_messages = []
    st.rerun()

st.sidebar.divider()

st.sidebar.caption(
    "Powered by LangGraph, Gemini 3.8 Flash, MCP, "
    "ChromaDB and Sentence Transformers."
)


# ==================================================
# REPOSITORY CONNECTION SCREEN
# ==================================================

if not st.session_state.current_repo_id:
    
    st.header("Connect to a Repository")
    
    st.info("Select a repository to get started. You can connect to a GitHub repository or use a local folder.")
    
    tab1, tab2, tab3 = st.tabs(["GitHub Repository", "Local Folder", "Existing Repositories"])
    
    with tab1:
        st.subheader("Clone from GitHub")
        
        github_url = st.text_input(
            "GitHub Repository URL",
            placeholder="https://github.com/username/repository",
            help="Enter a public GitHub repository URL"
        )
        
        if st.button("Clone Repository", type="primary"):
            if github_url:
                with st.spinner("Cloning repository..."):
                    result = repo_manager.clone_github_repo(github_url)
                    
                    if result['success']:
                        st.success(result['message'])
                        st.session_state.current_repo_id = result['repo_id']
                        st.session_state.current_repo_path = result['path']
                        st.rerun()
                    else:
                        st.error(result['message'])
            else:
                st.warning("Please enter a GitHub URL")
    
    with tab2:
        st.subheader("Use Local Folder")
        
        local_path = st.text_input(
            "Local Folder Path",
            placeholder="/path/to/your/repository",
            help="Enter the full path to a local directory"
        )
        
        # Sample repo option
        sample_repo_path = BASE_DIR / "sample_repo"
        if sample_repo_path.exists():
            if st.checkbox("Use sample_repo (test repository)"):
                local_path = str(sample_repo_path)
        
        if st.button("Connect to Local Folder", type="primary"):
            if local_path:
                with st.spinner("Connecting to repository..."):
                    result = repo_manager.register_local_repo(local_path)
                    
                    if result['success']:
                        st.success(result['message'])
                        st.session_state.current_repo_id = result['repo_id']
                        st.session_state.current_repo_path = result['path']
                        st.rerun()
                    else:
                        st.error(result['message'])
            else:
                st.warning("Please enter a local folder path")
    
    with tab3:
        st.subheader("Previously Connected Repositories")
        
        repos = repo_manager.list_repositories()
        
        if repos:
            for repo_id, repo_info in repos.items():
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.text(f"{Path(repo_info['path']).name}")
                    st.caption(f"{repo_info['type']} - {repo_info['path']}")
                    
                    # Show if indexed
                    if repo_info.get('indexed', False):
                        st.caption("✓ Indexed")
                    else:
                        st.caption("⚠ Not indexed")
                
                with col2:
                    if st.button("Connect", key=f"connect_{repo_id}"):
                        # Verify path still exists
                        repo_path = Path(repo_info['path'])
                        if repo_path.exists():
                            st.session_state.current_repo_id = repo_id
                            st.session_state.current_repo_path = repo_info['path']
                            st.rerun()
                        else:
                            st.error(f"Repository path no longer exists: {repo_info['path']}")
                
                with col3:
                    if st.button("Delete", key=f"delete_{repo_id}"):
                        repo_manager.delete_repository(repo_id)
                        st.rerun()
                
                st.divider()
        else:
            st.info("No repositories connected yet")
    
    st.stop()


# ==================================================
# REPOSITORY OVERVIEW
# ==================================================

st.header("Repository Overview")

# Show cloud storage warning
if "streamlit.io" in os.getenv("HOSTNAME", "") or os.getenv("STREAMLIT_SHARING_MODE"):
    st.info("""
    ℹ️ **Streamlit Cloud Notice**: Indexed data is stored temporarily. 
    If the app restarts, you'll need to re-index your repository. 
    For persistent storage, consider running locally.
    """)

repo_path = Path(st.session_state.current_repo_path)

if repo_path.exists():

    files = get_all_repository_files(str(repo_path))

    extensions = Counter(
        Path(path).suffix.lower() or "No extension"
        for path in files
    )

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Files", len(files))
    col2.metric("File Types", len(extensions))
    col3.metric("Repository Status", "Connected")

    with st.expander("Explore Repository Structure"):
        for file_path in sorted(files)[:100]:  # Limit display
            st.text(str(Path(file_path).relative_to(repo_path)))
        
        if len(files) > 100:
            st.caption(f"... and {len(files) - 100} more files")

    with st.expander("File Type Distribution"):
        st.bar_chart(dict(extensions))

else:
    st.warning("Repository path not found.")


# ==================================================
# KNOWLEDGE BASE STATUS & INDEXING
# ==================================================

st.divider()

col_header1, col_header2 = st.columns([3, 1])

with col_header1:
    st.header("Knowledge Base")

with col_header2:
    if st.button("🔄 Refresh Stats", use_container_width=True):
        st.rerun()

# Get indexing stats
stats = get_collection_stats(st.session_state.current_repo_id)

col1, col2, col3 = st.columns([2, 2, 1])

col1.metric(
    "Indexing Status",
    "Indexed" if stats['exists'] and stats['count'] > 0 else "Not Indexed"
)

col2.metric(
    "Stored Chunks",
    stats['count']
)

with col3:
    # Show appropriate button based on indexing status
    if stats['exists'] and stats['count'] > 0:
        if st.button("Re-index", use_container_width=True):
            st.session_state.indexing_status = "indexing"
            st.rerun()
    else:
        if st.button("Index Repository", type="primary", use_container_width=True):
            st.session_state.indexing_status = "indexing"
            st.rerun()

# Handle indexing
if st.session_state.indexing_status == "indexing":
    status_placeholder = st.empty()
    
    with status_placeholder:
        with st.spinner("Indexing repository... This may take a few minutes."):
            result = index_repository(
                st.session_state.current_repo_path,
                st.session_state.current_repo_id
            )
    
    if result['success']:
        repo_manager.mark_indexed(st.session_state.current_repo_id, True)
        st.session_state.indexing_status = None
        # Reset agent to pick up new index
        st.session_state.agent = None
        
        # Show success and auto-rerun after brief display
        with status_placeholder:
            st.success(f"✓ Repository indexed successfully! {result['chunk_count']} chunks created from {result['document_count']} documents.")
        
        # Immediate rerun to show chat interface
        st.rerun()
    else:
        st.session_state.indexing_status = None
        st.error(f"✗ Indexing failed: {result.get('error', 'Unknown error')}")
        st.stop()


# ==================================================
# AI CHAT INTERFACE
# ==================================================

st.divider()

st.header("Chat with your Codebase")

# Only enable chat if repository is indexed
if not stats['exists'] or stats['count'] == 0:
    st.warning("⚠️ Please index the repository before chatting. Click 'Index Repository' above.")
    st.stop()

st.caption(
    "Ask questions, explore files, understand code "
    "and investigate repository architecture."
)


# Load agent
@st.cache_resource(show_spinner="Initializing RepoGuide AI Agent...")
def load_agent(repo_id, repo_path):
    return asyncio.run(build_graph(repo_id, repo_path))


# Display previous conversations
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# Chat input
prompt = st.chat_input(
    "Ask RepoGuide anything about your repository..."
)


if prompt:

    # Display user message
    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    with st.chat_message("user"):
        st.markdown(prompt)

    # Invoke LangGraph agent
    with st.chat_message("assistant"):

        try:

            with st.spinner("RepoGuide is analyzing your repository..."):

                # Load agent if not already loaded
                if st.session_state.agent is None:
                    st.session_state.agent = load_agent(
                        st.session_state.current_repo_id,
                        st.session_state.current_repo_path
                    )

                agent = st.session_state.agent

                updated_messages = (
                    st.session_state.agent_messages
                    + [HumanMessage(content=prompt)]
                )

                result = asyncio.run(
                    agent.ainvoke(
                        {"messages": updated_messages},
                        config={"recursion_limit": 10}
                    )
                )

                st.session_state.agent_messages = result["messages"]

                response = result["messages"][-1].content

                if isinstance(response, list):
                    response = "\n".join(
                        str(item) for item in response
                    )

                response = str(response)

            st.markdown(response)

            st.session_state.messages.append({
                "role": "assistant",
                "content": response
            })

        except Exception as error:

            error_message = (
                f"Something went wrong while processing your question:\n\n"
                f"`{str(error)}`"
            )

            st.error(error_message)

            # Do not retain a failed turn in agent history.
            st.session_state.messages.pop()

            st.info(
                "Try a more specific question or check if you're hitting API limits."
            )
