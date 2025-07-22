# FastMCP AI Agent Demo

A simple AI agent service built with FastMCP using Streamable HTTP protocol.

## Features

- 🤖 **AI Chat** - Intelligent conversation with LLM integration
- 🔧 **Tool Calling** - AI can use tools like greeting and capabilities
- 🌊 **Streamable HTTP** - Real-time communication protocol
- 💬 **Interactive Mode** - Live chat with the AI agent

## Quick Start

### 1. Install Dependencies

```bash
pip install mcp[cli] openai requests
```

Or 

```bash
uv sync
```

### 2. Set Up API Key (Optional)

For real LLM integration, set one of:

*See https://openrouter.ai/models for free models.*
Please change the model at llm_service.py (see arguments of AsyncOpenAI)

```bash
# For OpenAI
export OPENAI_API_KEY="your-openai-api-key"
```

*Note: Without API keys, it uses a local mock LLM*

### 3. Start the Server

```bash
python server.py
```

You should see:
```
🚀 Starting Real AI Agent Server with FastMCP...
🤖 LLM Provider: openai (or local)
📡 Using Streamable HTTP transport
🌐 Server will run on: http://localhost:8000/mcp
```

### 4. Run the Interactive Client

In a new terminal:

```bash
python test.py
```

## Usage

### Interactive Commands

- **Type any message** - Chat with the AI
- **`hello`** - Test the greeting tool
- **`tools`** - List available tools
- **`caps`** - Show server capabilities
- **`help`** - Show all commands
- **`quit`** - Exit

### Example Chat

```
💬 You: Hello there!
🤖 AI: Hello! Nice to meet you. I'm your AI assistant powered by openai!
   🔧 Used tool: greeting
   🧠 Model: gpt-4

💬 You: What can you do?
🤖 AI: I can chat, use greeting tools, analyze capabilities, and more!
   🔧 Used tool: get_capabilities
```

## Available Tools

- **`greeting`** - Generates personalized greetings
- **`chat`** - Main AI conversation with LLM integration
- **`get_capabilities`** - Shows AI agent capabilities

## Architecture

- **Server** (`server.py`) - FastMCP server with AI agent tools
- **Client** (`test.py`) - Interactive MCP client with complete initialization
- **Protocol** - Streamable HTTP with proper MCP handshake
- **LLM Integration** - Supports OpenAI, Anthropic, or local mock

## Troubleshooting

### Server won't start
- Check if port 8000 is available
- Make sure FastMCP is installed: `pip install mcp`

### Client can't connect
- Ensure server is running first
- Check server logs for errors
- Verify URL: `http://localhost:8000/mcp`

### Tools not working
- Wait for server initialization to complete
- Check server logs for validation errors
- Ensure proper MCP handshake (client handles this automatically)

## Technical Details

- **FastMCP** - Python framework for MCP servers
- **Streamable HTTP** - Single endpoint for all communications
- **Session Management** - Persistent sessions with proper initialization
- **Tool Calling** - LLM intelligently decides when to use tools
- **Real-time** - Server-Sent Events for live responses

## Files

- `server.py` - FastMCP AI agent server
- `test.py` - Interactive MCP client
- `README.md` - This documentation

Built with ❤️ using FastMCP and Streamable HTTP protocol.
