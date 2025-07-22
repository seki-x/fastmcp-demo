# =============================================================================
# UPDATED SERVER CODE WITH REAL LLM SERVICE
# =============================================================================

from mcp.server.fastmcp import FastMCP
from llm_service import LLMService, LLMProvider, OPENAI_AVAILABLE, ANTHROPIC_AVAILABLE
import os
from typing import Optional
from dotenv import load_dotenv
load_dotenv()

# Initialize real LLM service
# Try OpenAI first, fallback to Anthropic, then local
def create_llm_service() -> LLMService:
    """Create LLM service with automatic provider detection"""
    
    # Try OpenAI first
    if OPENAI_AVAILABLE and os.getenv("OPENAI_API_KEY"):
        print("🤖 Using OpenAI GPT-4")
        return LLMService(
            provider=LLMProvider.OPENAI,
            model="google/gemini-2.0-flash-exp:free",  # or "gpt-3.5-turbo" for faster/cheaper
        )
    
    # Try Anthropic
    elif ANTHROPIC_AVAILABLE and os.getenv("ANTHROPIC_API_KEY"):
        print("🤖 Using Anthropic Claude")
        return LLMService(
            provider=LLMProvider.ANTHROPIC,
            model="claude-3-sonnet-20240229",
        )
    
    # Fallback to local/mock
    else:
        print("🤖 Using Local/Mock LLM (no API keys found)")
        return LLMService(provider=LLMProvider.LOCAL)

# Create the AI Agent Service with Real LLM
mcp = FastMCP("Real AI Agent")
llm_service = create_llm_service()

@mcp.tool()
async def greeting(name: str = "Friend") -> str:
    """A simple greeting tool"""
    return f"Hello, {name}! Nice to meet you. I'm your AI assistant powered by {llm_service.provider.value}!"

@mcp.tool()  
async def chat(message: str, session_id: Optional[str] = None) -> dict:
    """Main AI chat function with real LLM integration"""
    print(f"🤖 Processing with {llm_service.provider.value}: {message}")
    
    # Get available tools for LLM context
    available_tools = ["greeting", "get_capabilities"]
    
    # Call real LLM service
    llm_response = await llm_service.chat_completion(
        message=message,
        tools_available=available_tools,
        system_prompt="You are a helpful AI assistant integrated with FastMCP."
    )
    
    print(f"💭 LLM Response Type: {llm_response.type}")
    print(f"🔧 Model Used: {llm_response.model_used}")
    if llm_response.tokens_used:
        print(f"📊 Tokens Used: {llm_response.tokens_used}")
    
    if llm_response.type == "tool_call":
        # LLM wants to use a tool
        tool_name = llm_response.tool_name
        tool_args = llm_response.tool_args or {}
        
        print(f"🛠️  LLM wants to use tool: {tool_name} with args: {tool_args}")
        
        # Execute the tool
        if tool_name == "greeting":
            tool_result = await greeting(**tool_args)
        elif tool_name == "get_capabilities":
            tool_result = await get_capabilities()
        else:
            tool_result = f"Unknown tool: {tool_name}"
            
        return {
            "response": tool_result,
            "tool_used": tool_name,
            "reasoning": llm_response.reasoning,
            "model_used": llm_response.model_used,
            "tokens_used": llm_response.tokens_used,
            "session_id": session_id
        }
    
    # Regular text response
    return {
        "response": llm_response.content,
        "tool_used": None,
        "reasoning": llm_response.reasoning,
        "model_used": llm_response.model_used,
        "tokens_used": llm_response.tokens_used,
        "session_id": session_id
    }

@mcp.tool()
async def get_capabilities() -> dict:
    """Get AI agent capabilities"""
    return {
        "capabilities": ["chat", "greeting", "tool_execution"],
        "available_tools": ["greeting", "get_capabilities"],
        "llm_provider": llm_service.provider.value,
        "llm_model": llm_service.model,
        "protocol": "streamable-http",
        "version": "1.0.0"
    }

def run_real_server():
    """Run the AI agent server with real LLM"""
    print("🚀 Starting Real AI Agent Server with FastMCP...")
    print(f"🤖 LLM Provider: {llm_service.provider.value}")
    print("📡 Using Streamable HTTP transport")
    print("🌐 Server will run on: http://localhost:8000/mcp")
    
    mcp.run(
        transport="streamable-http"
    )

if __name__ == "__main__":
    run_real_server()


# =============================================================================
# SETUP INSTRUCTIONS
# =============================================================================

"""
SETUP INSTRUCTIONS:

1. Install dependencies:
   pip install mcp openai anthropic

2. Set up API keys (choose one):
   
   For OpenAI:
   export OPENAI_API_KEY="your-openai-api-key"
   
   For Anthropic:
   export ANTHROPIC_API_KEY="your-anthropic-api-key"
   
   Or create a .env file:
   OPENAI_API_KEY=your-openai-api-key
   ANTHROPIC_API_KEY=your-anthropic-api-key

3. Run the server:
   python real_llm_server.py

4. Test with the same client from the previous demo:
   python test_client.py

WHAT YOU GET:

✅ Real LLM integration (OpenAI GPT-4 or Anthropic Claude)
✅ Intelligent tool calling decisions from the LLM
✅ Token usage tracking
✅ Multiple provider support with fallbacks
✅ Production-ready error handling
✅ Conversation history support
✅ System prompt customization

The LLM will now make intelligent decisions about:
- When to use tools vs. direct responses
- How to respond contextually 
- Tool argument extraction from natural language
- Conversational flow management
"""