# =============================================================================
# INTERACTIVE MCP CHAT CLIENT - WORKING VERSION
# =============================================================================

import json
import time
import requests
from typing import Dict, Any, Optional

class WorkingMCPClient:
    """Working MCP client with correct initialization sequence"""
    
    def __init__(self, server_url: str = "http://localhost:8000/mcp"):
        self.server_url = server_url
        self.session_id = None
        self.request_id = 1
        self.initialized = False
        self.available_tools = []
        
    def _get_next_id(self) -> str:
        """Get next request ID"""
        request_id = f"req-{self.request_id}"
        self.request_id += 1
        return request_id
    
    def _make_request(self, method: str, params: Dict[str, Any] = None, is_notification: bool = False) -> Dict[str, Any]:
        """Make JSON-RPC request to FastMCP server"""
        
        payload = {
            "jsonrpc": "2.0",
            "method": method
        }
        
        # Notifications don't have ID
        if not is_notification:
            payload["id"] = self._get_next_id()
        
        if params is not None:
            payload["params"] = params
            
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "User-Agent": "WorkingMCP-Client/1.0"
        }
        
        # Add session ID if we have one
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
            
        try:
            response = requests.post(
                self.server_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            # Extract session ID from response headers
            new_session_id = response.headers.get("Mcp-Session-Id")
            if new_session_id:
                self.session_id = new_session_id
                
            response.raise_for_status()
            
            # Handle notifications (no response expected)
            if is_notification:
                return {"status": "notification_sent"}
            
            # Handle SSE response
            content_type = response.headers.get("Content-Type", "")
            if "text/event-stream" in content_type:
                return self._handle_sse_response(response)
            elif "application/json" in content_type:
                return response.json()
            else:
                return {"error": f"Unexpected content type: {content_type}"}
            
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    def _handle_sse_response(self, response) -> Dict[str, Any]:
        """Handle SSE response and extract JSON"""
        try:
            for line in response.iter_lines(decode_unicode=True):
                if line and line.startswith("data: "):
                    data = line[6:]
                    if data.strip():
                        try:
                            return json.loads(data)
                        except json.JSONDecodeError:
                            continue
            return {"error": "No valid JSON found in SSE stream"}
        except Exception as e:
            return {"error": f"SSE parsing error: {str(e)}"}
    
    def initialize(self) -> bool:
        """Initialize connection with complete MCP handshake"""
        print("🔌 Initializing MCP connection...")
        
        # Step 1: Send initialize request
        response = self._make_request("initialize", {
            "protocolVersion": "2025-03-26",
            "capabilities": {
                "experimental": {},
                "sampling": {}
            },
            "clientInfo": {
                "name": "interactive-mcp-client",
                "version": "1.0.0"
            }
        })
        
        if "result" not in response:
            print(f"❌ Initialize failed: {response.get('error', 'Unknown error')}")
            return False
        
        print(f"✅ Session ID: {self.session_id}")
        server_info = response["result"].get("serverInfo", {})
        print(f"📡 Server: {server_info.get('name', 'Unknown')} v{server_info.get('version', '?')}")
        
        # Step 2: Send initialized notification (CRITICAL!)
        print("📤 Sending initialized notification...")
        self._make_request("notifications/initialized", is_notification=True)
        
        # Step 3: Wait for server to complete initialization
        print("⏳ Waiting for server initialization...")
        time.sleep(2)
        
        # Step 4: Load available tools
        self._load_tools()
        
        self.initialized = True
        print("✅ MCP connection ready!")
        return True
    
    def _load_tools(self):
        """Load available tools from server"""
        response = self._make_request("tools/list", {})
        
        if "result" in response:
            self.available_tools = response["result"].get("tools", [])
            print(f"🔧 Loaded {len(self.available_tools)} tools")
        else:
            print(f"⚠️  Could not load tools: {response.get('error', 'Unknown error')}")
    
    def call_tool(self, tool_name: str, args: Dict[str, Any] = None) -> Any:
        """Call a tool on the server"""
        
        if not self.initialized:
            if not self.initialize():
                return {"error": "Failed to initialize"}
        
        if args is None:
            args = {}
            
        response = self._make_request("tools/call", {
            "name": tool_name,
            "arguments": args
        })
        
        if "result" in response:
            result = response["result"]
            
            # Handle MCP tool result format
            if isinstance(result, dict) and "content" in result:
                content = result["content"]
                if isinstance(content, list) and len(content) > 0:
                    first_content = content[0]
                    if isinstance(first_content, dict) and "text" in first_content:
                        return first_content["text"]
                    else:
                        return first_content
                else:
                    return content
            else:
                return result
        else:
            error = response.get("error", {})
            return {"error": error.get("message", "Unknown error")}

    def chat(self, message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Send a chat message"""
        
        args = {"message": message}
        if session_id:
            args["session_id"] = session_id
            
        result = self.call_tool("chat", args)
        
        if isinstance(result, dict) and "error" not in result:
            return result
        elif isinstance(result, str):
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                return {"response": result}
        else:
            return {"error": "Failed to get chat response", "details": result}
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get server capabilities"""
        result = self.call_tool("get_capabilities")
        
        if isinstance(result, str):
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                return {"response": result}
        elif isinstance(result, dict) and "error" not in result:
            return result
        else:
            return {"error": "Failed to get capabilities", "details": result}
    
    def greeting(self, name: str = "Friend") -> str:
        """Call the greeting tool"""
        result = self.call_tool("greeting", {"name": name})
        
        if isinstance(result, str):
            return result
        elif isinstance(result, dict) and "error" not in result:
            return str(result)
        else:
            return f"Error: {result}"

def interactive_chat():
    """Interactive chat mode with working MCP client"""
    print("🗣️  INTERACTIVE MCP CHAT")
    print("=" * 50)
    print("Commands:")
    print("  help    - Show this help")
    print("  tools   - List available tools")
    print("  caps    - Show server capabilities")
    print("  hello   - Test greeting tool")
    print("  quit    - Exit")
    print("  Or just type a message to chat with the AI!")
    print("=" * 50)
    
    client = WorkingMCPClient()
    
    # Initialize connection
    if not client.initialize():
        print("❌ Failed to connect to MCP server")
        print("Make sure the server is running: python real_llm_server.py")
        return
    
    print()
    session_id = f"interactive-{int(time.time())}"
    
    while True:
        try:
            user_input = input("\n💬 You: ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
                
            elif user_input.lower() == 'help':
                print("📋 Commands:")
                print("  help    - Show this help")
                print("  tools   - List available tools") 
                print("  caps    - Show server capabilities")
                print("  hello   - Test greeting tool")
                print("  quit    - Exit")
                print("  Or just type a message to chat!")
                continue
                
            elif user_input.lower() == 'tools':
                print("🔧 Available tools:")
                for tool in client.available_tools:
                    name = tool.get("name", "Unknown")
                    desc = tool.get("description", "No description")
                    print(f"   • {name}: {desc}")
                continue
                
            elif user_input.lower() == 'caps':
                print("🛠️  Getting server capabilities...")
                caps = client.get_capabilities()
                print(f"📋 Capabilities: {json.dumps(caps, indent=2)}")
                continue
                
            elif user_input.lower() in ['hello', 'hi']:
                print("👋 Testing greeting tool...")
                greeting = client.greeting("Interactive User")
                print(f"🤖 Greeting: {greeting}")
                continue
            
            # Regular chat message
            print("🤖 Thinking...")
            
            chat_response = client.chat(user_input, session_id)
            
            if "error" not in chat_response:
                response_text = chat_response.get("response", "No response")
                print(f"🤖 AI: {response_text}")
                
                # Show additional info if available
                tool_used = chat_response.get("tool_used")
                if tool_used:
                    print(f"   🔧 Used tool: {tool_used}")
                
                model_used = chat_response.get("model_used")
                if model_used:
                    print(f"   🧠 Model: {model_used}")
                    
                reasoning = chat_response.get("reasoning")
                if reasoning:
                    print(f"   💭 Reasoning: {reasoning}")
                    
                tokens = chat_response.get("tokens_used")
                if tokens:
                    print(f"   📊 Tokens: {tokens}")
                    
            else:
                print(f"❌ Error: {chat_response.get('error', 'Unknown error')}")
                details = chat_response.get('details')
                if details:
                    print(f"   Details: {details}")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Unexpected error: {e}")

def test_tools():
    """Test all available tools"""
    print("🧪 TESTING ALL TOOLS")
    print("=" * 50)
    
    client = WorkingMCPClient()
    
    if not client.initialize():
        print("❌ Failed to initialize")
        return
    
    print("\n1. Testing greeting tool...")
    greeting = client.greeting("Tool Tester")
    print(f"   Result: {greeting}")
    
    print("\n2. Testing capabilities...")
    caps = client.get_capabilities()
    print(f"   Result: {caps}")
    
    print("\n3. Testing chat...")
    chat_response = client.chat("Hello! This is a test message.")
    print(f"   Result: {chat_response}")
    
    print("\n✅ All tools tested!")

if __name__ == "__main__":
    print("🚀 WORKING MCP INTERACTIVE CLIENT")
    print("=" * 50)
    
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_tools()
    else:
        interactive_chat()
