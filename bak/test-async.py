# =============================================================================  
# CLIENT SIDE - test_client.py
# =============================================================================

import asyncio
import json
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession

class AIAgentClient:
    """Simple FastMCP client for testing"""
    
    def __init__(self, server_url: str = "http://localhost:8000/mcp"):
        self.server_url = server_url
        
    async def test_connection(self):
        """Test basic connection to server"""
        print("🔌 Testing connection...")
        
        try:
            async with streamablehttp_client(self.server_url) as (read, write):
                async with ClientSession(read, write) as session:
                    # Test initialization
                    result = await session.initialize()
                    print(f"✅ Connected! Server: {result}")
                    return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    async def test_capabilities(self):
        """Test getting server capabilities"""
        print("\n📋 Testing capabilities...")
        
        try:
            async with streamablehttp_client(self.server_url) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # Call get_capabilities tool
                    result = await session.call_tool("get_capabilities", {})
                    print(f"🛠️  Server capabilities: {json.dumps(result.content[0].text, indent=2)}")
                    return True
        except Exception as e:
            print(f"❌ Capabilities test failed: {e}")
            return False
    
    async def test_greeting_tool(self):
        """Test the greeting tool directly"""
        print("\n👋 Testing greeting tool...")
        
        try:
            async with streamablehttp_client(self.server_url) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # Test greeting tool
                    result = await session.call_tool("greeting", {"name": "Demo User"})
                    print(f"🎉 Greeting result: {result.content[0].text}")
                    return True
        except Exception as e:
            print(f"❌ Greeting test failed: {e}")
            return False
    
    async def test_chat_feature(self):
        """Test the main chat feature with LLM"""
        print("\n💬 Testing AI chat feature...")
        
        test_messages = [
            "Hello there!",
            "How's the weather today?", 
            "Tell me about artificial intelligence",
            "Hi, nice to meet you!"
        ]
        
        try:
            async with streamablehttp_client(self.server_url) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    for i, message in enumerate(test_messages, 1):
                        print(f"\n📤 Test {i}: '{message}'")
                        
                        # Call chat tool
                        result = await session.call_tool("chat", {
                            "message": message,
                            "session_id": f"test-session-{i}"
                        })
                        
                        # Parse response
                        response_data = json.loads(result.content[0].text)
                        print(f"🤖 AI Response: {response_data['response']}")
                        
                        if response_data.get('tool_used'):
                            print(f"🔧 Tool used: {response_data['tool_used']}")
                        
                        print(f"💭 AI Reasoning: {response_data['reasoning']}")
                    
                    return True
        except Exception as e:
            print(f"❌ Chat test failed: {e}")
            return False

async def run_tests():
    """Run all client tests"""
    print("🧪 Starting FastMCP AI Agent Tests")
    print("=" * 50)
    
    client = AIAgentClient()
    
    # Run tests sequentially
    tests = [
        ("Connection Test", client.test_connection),
        ("Capabilities Test", client.test_capabilities), 
        ("Greeting Tool Test", client.test_greeting_tool),
        ("AI Chat Feature Test", client.test_chat_feature)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n🔬 Running: {test_name}")
        try:
            success = await test_func()
            results[test_name] = "✅ PASSED" if success else "❌ FAILED"
        except Exception as e:
            print(f"💥 Unexpected error in {test_name}: {e}")
            results[test_name] = "💥 ERROR"
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    for test_name, result in results.items():
        print(f"{result} {test_name}")

if __name__ == "__main__":
    print("🚀 FastMCP AI Agent Client")
    print("Make sure the server is running on http://localhost:8000/mcp")
    print("Starting tests in 2 seconds...")
    
    asyncio.sleep(2)  # Give user time to see the message
    asyncio.run(run_tests())