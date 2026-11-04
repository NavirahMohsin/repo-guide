# RepoGuide - Intelligent Codebase Analysis Assistant

RepoGuide is an AI-powered assistant that helps developers understand software repositories through natural language conversations. It combines RAG (Retrieval Augmented Generation), MCP (Model Context Protocol), and LangGraph to provide intelligent codebase analysis.

## Features

- 🔗 **Dynamic Repository Selection**: Connect to GitHub repos or local folders
- 🧠 **Semantic Search**: RAG-powered code understanding using ChromaDB and Sentence Transformers
- 🔧 **MCP Tools**: File browsing, code search, and structure analysis
- 💬 **AI Chat**: Ask questions about your codebase in natural language
- 📊 **Repository Insights**: File statistics, type distribution, and structure visualization
- 🔄 **Multi-Repository Support**: Switch between different repositories with isolated indexes

## Tech Stack

- **Frontend**: Streamlit
- **LLM**: Groq (openai/gpt-oss-120b)
- **Framework**: LangGraph + LangChain
- **Vector DB**: ChromaDB
- **Embeddings**: Sentence Transformers (all-MiniLM-L6-v2)
- **Tools**: MCP (Model Context Protocol)

## Local Development

### Prerequisites

- Python 3.9+
- Groq API key (free tier available)

### Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd RepoGuide
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file:
```bash
GROQ_API_KEY=your_groq_api_key_here
```

5. Run the app:
```bash
streamlit run app.py
```

## Streamlit Cloud Deployment

### Step 1: Prepare Repository

Ensure these files are in your repository:
- ✅ `app.py` - Main application
- ✅ `requirements.txt` - Python dependencies
- ✅ `packages.txt` - System packages (git)
- ✅ `.streamlit/config.toml` - Streamlit configuration
- ✅ `.gitignore` - Excludes data folders and secrets

### Step 2: Deploy to Streamlit Cloud

1. Push your code to GitHub:
```bash
git add .
git commit -m "Prepare for Streamlit Cloud deployment"
git push origin main
```

2. Go to [share.streamlit.io](https://share.streamlit.io)

3. Click "New app"

4. Configure:
   - **Repository**: Your GitHub repo
   - **Branch**: main
   - **Main file path**: app.py

5. Click "Advanced settings" and add secrets:
```toml
GROQ_API_KEY = "your_groq_api_key_here"
```

6. Click "Deploy"

### Step 3: Post-Deployment

After deployment:
- The app will start without a default repository
- Users must connect to a repository first
- GitHub cloning works on Streamlit Cloud
- Local folder connections require accessible paths

### Important Notes for Streamlit Cloud

1. **Persistent Storage**: Streamlit Cloud has ephemeral storage. Cloned repos and indexes may be lost on app restart.

2. **Memory Limits**: Free tier has 1GB RAM. Large repositories may fail to index.

3. **GitHub Rate Limits**: Unauthenticated clones may hit rate limits. Consider adding GitHub token for private repos.

4. **Groq API Limits**: Free tier has usage limits. Monitor your usage.

## Usage

### 1. Connect to Repository

Choose one of three options:
- **GitHub**: Clone a public repository
- **Local Folder**: Use an existing local directory
- **Existing**: Reconnect to previously used repositories

### 2. Index Repository

Click "Index Repository" to:
- Load and parse files (PDF, notebooks, code)
- Split into chunks (500 tokens with 50 overlap)
- Generate embeddings
- Store in ChromaDB

### 3. Chat with Your Codebase

Ask questions like:
- "What is this repository about?"
- "Summarize the main Python files"
- "What ML models are implemented?"
- "Show me the repository structure"
- "Search for 'authentication' in the code"

## Architecture

```
┌─────────────┐
│  Streamlit  │
│     UI      │
└──────┬──────┘
       │
       ├─► Repository Manager (GitHub/Local)
       │
       ├─► RAG Pipeline
       │   ├─► Document Loader (PDF, .ipynb, code)
       │   ├─► Text Splitter (500 token chunks)
       │   ├─► Embeddings (Sentence Transformers)
       │   └─► ChromaDB (per-repo collections)
       │
       └─► LangGraph Agent
           ├─► Groq LLM (8K context)
           ├─► RAG Tool (semantic search)
           └─► MCP Tools (file operations)
```

## Configuration

### Groq Context Optimization

To stay within Groq's 8K token limit:
- Retrieved chunks: 2 (max)
- Characters per chunk: 800
- Conversation history: Last 4 messages
- Document chunk size: 500 tokens
- MCP file reads: 3000 char limit
- Search results: 20 max

### Supported File Types

- **Code**: .py, .js, .jsx, .ts, .tsx, .java, .c, .cpp, .h
- **Web**: .html, .css
- **Config**: .json, .yaml, .yml, .toml, .ini, .sql
- **Docs**: .md, .txt
- **Special**: .pdf, .ipynb

### Ignored Directories

- .git
- venv, .venv
- node_modules
- __pycache__
- dist, build
- .next
- .ipynb_checkpoints

## Troubleshooting

### Error 413: Context Length Exceeded

**Solution**: Groq's 8K token limit exceeded
- Ask more specific questions
- Focus on individual files
- Break down complex queries

### Error 400: Invalid Tool Response

**Solution**: Tool returned empty data
- Ensure repository is properly indexed
- Check that files exist in the repository
- Try re-indexing the repository

### Indexing Takes Too Long

**Solution**: Large repository
- Consider indexing only specific subdirectories
- Reduce chunk size in `backend/ingestion.py`
- Use a smaller test repository

### Chat Not Loading After Indexing

**Solution**: Fixed in latest version
- Refresh the page
- Check "Knowledge Base" section shows indexed status
- Click "Refresh Stats" button

## Contributing

Contributions welcome! Areas for improvement:
- Private GitHub repository support
- Custom embedding models
- Advanced search filters
- Export conversation history
- Repository comparison features

## License

MIT License - See LICENSE file for details

## Support

For issues or questions:
1. Check existing GitHub issues
2. Create a new issue with detailed description
3. Include error messages and reproduction steps

## Credits

Built with:
- [Streamlit](https://streamlit.io/)
- [LangChain](https://langchain.com/)
- [LangGraph](https://github.com/langchain-ai/langgraph)
- [Groq](https://groq.com/)
- [ChromaDB](https://www.trychroma.com/)
- [Sentence Transformers](https://www.sbert.net/)
