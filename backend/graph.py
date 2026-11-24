
import os
import sys

from pathlib import Path
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage
from langchain_core.tools import tool

from langchain_mcp_adapters.client import MultiServerMCPClient

from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition

from backend.retriever import search_repository


# --------------------------------------------------
# 1. PROJECT CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[1]

load_dotenv(BASE_DIR / ".env")


# --------------------------------------------------
# 2. GOOGLE GENERATIVE AI LLM - Lazy initialization with Fallbacks
# --------------------------------------------------

_llm = None

def get_llm():
    """Get or initialize the Google Generative AI LLM with fallback models."""
    global _llm
    
    if _llm is None:
        google_api_key = os.getenv("GOOGLE_API_KEY")
        groq_api_key = os.getenv("GROQ_API_KEY")
        
        if not google_api_key and not groq_api_key:
            raise ValueError(
                "Neither GOOGLE_API_KEY nor GROQ_API_KEY found. "
                "Please set at least one in .env file (local) or Streamlit secrets (cloud)."
            )
        
        # Primary models - Gemini (with fallbacks)
        fallback_chain = []
        
        if google_api_key:
            # Primary model - latest Gemini Flash
            primary_llm = ChatGoogleGenerativeAI(
                model="gemini-3.8-flash",
                temperature=0,
                api_key=google_api_key,
                max_retries=2  # Retry more aggressively for 503 spikes
            )
            
            # Fallback model 1 - Gemini 4 Hydrogen
            backup_llm_1 = ChatGoogleGenerativeAI(
                model="gemini-4-hydrogen",
                temperature=0,
                api_key=google_api_key,
                max_retries=2
            )
            
            # Fallback model 2 - Gemini 3.5 Flash Lite
            backup_llm_2 = ChatGoogleGenerativeAI(
                model="gemini-3.5-flash-lite",
                temperature=0,
                api_key=google_api_key,
                max_retries=2
            )
            
            fallback_chain = [primary_llm, backup_llm_1, backup_llm_2]
        
        # Ultimate fallback - Groq (most reliable)
        if groq_api_key:
            groq_llm = ChatGroq(
                model="openai/gpt-oss-120b",
                temperature=0,
                api_key=groq_api_key,
                max_retries=3
            )
            fallback_chain.append(groq_llm)
        
        # Build the fallback chain
        if len(fallback_chain) == 1:
            _llm = fallback_chain[0]
        else:
            _llm = fallback_chain[0].with_fallbacks(fallback_chain[1:])
    
    return _llm

# --------------------------------------------------
# 3. CREATE DYNAMIC RAG TOOL
# --------------------------------------------------

def create_rag_tool(repo_id: str):
    """Create a RAG search tool for a specific repository."""
    
    @tool
    def rag_search(query: str) -> str:
        """Search repository knowledge base using semantic similarity."""

        try:
            # Pass repo_id to search_repository
            results = search_repository(query, repo_id, k=2)

            if not results:
                return "No relevant documents found."

            output = []

            for index, document in enumerate(results, start=1):
                source = document.metadata.get("source", "Unknown")
                # Reduced from 1500 to 800 characters per chunk
                content = document.page_content[:800]

                output.append(
                    f"Result {index}\n"
                    f"Source: {source}\n"
                    f"Content:\n{content}"
                )

            return "\n\n".join(output)

        except Exception as error:
            return f"RAG search failed: {str(error)}"
    
    return rag_search


# --------------------------------------------------
# 4. CONNECT TO MCP SERVER
# --------------------------------------------------

def wrap_mcp_tool(tool):
    """Wrap MCP tool to ensure it always returns a non-empty string."""
    
    # Get the original function - handle different tool types
    if hasattr(tool, 'func'):
        original_func = tool.func
    #async
    elif hasattr(tool, 'coroutine'):
        original_func = tool.coroutine
    elif callable(tool):
        original_func = tool
    else:
        # Can't wrap this tool, return as-is
        return tool
    
    # Check if it's already async
    import inspect
    is_async = inspect.iscoroutinefunction(original_func)
    
    if is_async:
        async def wrapped_func(*args, **kwargs):
            try:
                result = await original_func(*args, **kwargs)
                
                # Handle None or empty results
                if result is None:
                    return "Tool executed successfully but returned no data."
                
                # Convert to string if not already
                if not isinstance(result, str):
                    import json
                    result_str = json.dumps(result, indent=2, ensure_ascii=False)
                    
                    # Ensure non-empty
                    if not result_str or result_str.strip() in ['[]', '{}', 'null']:
                        return "Tool executed successfully but returned no data."
                    
                    return result_str
                
                # Ensure non-empty string
                if not result or not result.strip():
                    return "Tool executed successfully but returned no data."
                
                return result
                
            except Exception as e:
                return f"Tool execution failed: {str(e)}"
    else:
        def wrapped_func(*args, **kwargs):
            try:
                result = original_func(*args, **kwargs)
                
                # Handle None or empty results
                if result is None:
                    return "Tool executed successfully but returned no data."
                
                # Convert to string if not already
                if not isinstance(result, str):
                    import json
                    result_str = json.dumps(result, indent=2, ensure_ascii=False)
                    
                    # Ensure non-empty
                    if not result_str or result_str.strip() in ['[]', '{}', 'null']:
                        return "Tool executed successfully but returned no data."
                    
                    return result_str
                
                # Ensure non-empty string
                if not result or not result.strip():
                    return "Tool executed successfully but returned no data."
                
                return result
                
            except Exception as e:
                return f"Tool execution failed: {str(e)}"
    
    # Preserve tool metadata
    if hasattr(original_func, '__name__'):
        wrapped_func.__name__ = original_func.__name__
    if hasattr(original_func, '__doc__'):
        wrapped_func.__doc__ = original_func.__doc__
    
    # Update the tool's function reference
    if hasattr(tool, 'func'):
        tool.func = wrapped_func
    elif hasattr(tool, 'coroutine'):
        tool.coroutine = wrapped_func
    
    return tool


async def get_mcp_tools(repo_path: str):
    """Get MCP tools configured for a specific repository."""

    client = MultiServerMCPClient({

        "repoguide": {
            "transport": "stdio",
            "command": sys.executable,
            "args": ["-m", "mcp_server.server"],
            "cwd": str(BASE_DIR),
            "env": {
                **os.environ.copy(),
                "REPOGUIDE_REPO_PATH": repo_path  # Pass repo path via env
            }
        }

    })

    tools = await client.get_tools()
    
    # Wrap all MCP tools to ensure non-empty string responses
    wrapped_tools = [wrap_mcp_tool(tool) for tool in tools]

    return wrapped_tools


# --------------------------------------------------
# 5. CREATE LANGGRAPH AGENT
# --------------------------------------------------

async def build_graph(repo_id: str, repo_path: str):
    """
    Build LangGraph agent for a specific repository.
    
    Args:
        repo_id: Unique repository identifier
        repo_path: Path to the repository
    """

    # Get LLM instance (lazy initialization)
    llm = get_llm()

    mcp_tools = await get_mcp_tools(repo_path)

    # Create RAG tool for this repository
    rag_tool = create_rag_tool(repo_id)

    # Combine RAG and MCP tools
    tools = [rag_tool] + mcp_tools

    # Give tools to the LLM
    llm_with_tools = llm.bind_tools(tools)

    system_prompt = """
    You are RepoGuide, an intelligent codebase
    analysis assistant.

    Your job is to help developers understand
    software repositories by actively analyzing
    the codebase using available tools.

    You have access to the following tools:

    1. rag_search:
       Retrieves semantically relevant code
       and documentation from the vector database.
       USE THIS FIRST for most questions about the repository.

    2. MCP repository tools:
       - list_files: Shows all files in the repository
       - count_files: Counts files by type
       - get_file_structure: Shows directory structure
       - read_file: Reads specific file contents
       - search_code: Searches for keywords in code

    CRITICAL INSTRUCTIONS:

    - You MUST use tools to answer questions. Never give generic responses.
    - For questions about "what is this repository about", "summarize", 
      "what files", "what models", etc., ALWAYS use rag_search and/or 
      list_files first to gather actual information.
    - If asked about notebooks (.ipynb files), use rag_search to find
      content from those notebooks.
    - If asked about specific files, use read_file to get the content.
    - If asked to search for something, use search_code.
    - For questions about ML models, algorithms, or implementations,
      use rag_search to find relevant documentation and code.
    - NEVER say "I'm ready to help" or "let me know what you'd like"
      without first attempting to use tools to answer.
    - If you don't find information with one tool, try another tool.
    - Be specific and provide actual information from the repository,
      not generic responses.
    - Keep responses concise to stay within token limits.
    - If tools return no data, explicitly state that and suggest
      what the user might try instead.
    """

    # --------------------------------------------------
    # AGENT NODE
    # --------------------------------------------------

    async def agent_node(state: MessagesState):
        # Limit conversation history to last 6 messages (Gemini has 1M+ token context)
        recent_messages = state["messages"][-6:]
        
        messages = [
            SystemMessage(content=system_prompt)
        ] + recent_messages

        try:
            response = await llm_with_tools.ainvoke(messages)
            
            return {
                "messages": [response]
            }
        except Exception as e:
            error_msg = str(e)
            
            # Provide helpful error messages
            if "context" in error_msg.lower():
                error_response = (
                    "I encountered a context length error. "
                    "Please try:\n"
                    "1. Asking a more specific question\n"
                    "2. Focusing on a specific file or topic\n"
                    "3. Breaking your question into smaller parts"
                )
            elif "400" in error_msg:
                error_response = (
                    "I encountered an API error. This might be due to:\n"
                    "1. Invalid tool response format\n"
                    "2. Missing required parameters\n"
                    "Please try rephrasing your question or ask about a specific file."
                )
            elif "rate_limit" in error_msg.lower() or "429" in error_msg:
                error_response = (
                    "Rate limit exceeded. The system automatically tried backup models. "
                    "Please wait a moment and try again."
                )
            elif "503" in error_msg or "unavailable" in error_msg.lower():
                error_response = (
                    "The model service is temporarily overloaded. "
                    "The system automatically tried backup models. "
                    "Please wait a moment and try again."
                )
            else:
                error_response = f"An error occurred: {error_msg}"
            
            # Return error as a message
            from langchain_core.messages import AIMessage
            return {
                "messages": [AIMessage(content=error_response)]
            }

    # --------------------------------------------------
    # BUILD GRAPH
    # --------------------------------------------------

    workflow = StateGraph(MessagesState)

    workflow.add_node("agent", agent_node)

    workflow.add_node(
        "tools",
        ToolNode(tools)
    )

    workflow.add_edge(START, "agent")

    # Decide whether to execute tools or finish
    workflow.add_conditional_edges(
        "agent",
        tools_condition,
        {
            "tools": "tools",
            END: END
        }
    )

    # Return tool results to the agent
    workflow.add_edge("tools", "agent")

    return workflow.compile()
