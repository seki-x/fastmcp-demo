# =============================================================================
# REAL LLM SERVICE IMPLEMENTATION
# =============================================================================

import asyncio
import json
import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

# Provider-specific imports
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️  OpenAI not installed. Run: pip install openai")

try:
    from anthropic import AsyncAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("⚠️  Anthropic not installed. Run: pip install anthropic")

class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"  # For future local model support

@dataclass
class LLMResponse:
    """Structured LLM response"""
    type: str  # "text" or "tool_call"
    content: Optional[str] = None
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    reasoning: Optional[str] = None
    model_used: Optional[str] = None
    tokens_used: Optional[int] = None

class LLMService:
    """Production-ready LLM service with multiple provider support"""
    
    def __init__(self, 
                 provider: LLMProvider = LLMProvider.OPENAI,
                 model: Optional[str] = None,
                 api_key: Optional[str] = None):
        
        self.provider = provider
        self.model = model or self._get_default_model(provider)
        self.api_key = api_key or self._get_api_key(provider)
        
        # Initialize clients
        self.openai_client = None
        self.anthropic_client = None
        
        self._initialize_clients()
    
    def _get_default_model(self, provider: LLMProvider) -> str:
        """Get default model for each provider"""
        defaults = {
            LLMProvider.OPENAI: "gpt-4",
            LLMProvider.ANTHROPIC: "claude-3-sonnet-20240229",
            LLMProvider.LOCAL: "llama2"  # Example
        }
        return defaults.get(provider, "gpt-4")
    
    def _get_api_key(self, provider: LLMProvider) -> Optional[str]:
        """Get API key from environment variables"""
        env_vars = {
            LLMProvider.OPENAI: "OPENAI_API_KEY",
            LLMProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
            LLMProvider.LOCAL: None
        }
        
        env_var = env_vars.get(provider)
        if env_var:
            key = os.getenv(env_var)
            if not key:
                print(f"⚠️  Warning: {env_var} not found in environment variables")
            return key
        return None
    
    def _initialize_clients(self):
        """Initialize API clients based on provider"""
        if self.provider == LLMProvider.OPENAI and OPENAI_AVAILABLE and self.api_key:
            self.openai_client = AsyncOpenAI(
                api_key=self.api_key, base_url="https://openrouter.ai/api/v1"
            )
            print(f"✅ OpenAI client initialized with model: {self.model}")
        
        elif self.provider == LLMProvider.ANTHROPIC and ANTHROPIC_AVAILABLE and self.api_key:
            self.anthropic_client = AsyncAnthropic(api_key=self.api_key)
            print(f"✅ Anthropic client initialized with model: {self.model}")
        
        else:
            print(f"❌ Could not initialize {self.provider.value} client")
            print("   Check API key and package installation")

    async def chat_completion(self, 
                            message: str, 
                            tools_available: List[str] = None,
                            system_prompt: Optional[str] = None,
                            conversation_history: List[Dict] = None) -> LLMResponse:
        """
        Get chat completion from LLM with tool calling support
        
        Args:
            message: User message
            tools_available: List of available tool names
            system_prompt: Optional system prompt
            conversation_history: Previous conversation messages
        
        Returns:
            LLMResponse object
        """
        
        if self.provider == LLMProvider.OPENAI:
            return await self._openai_completion(
                message, tools_available, system_prompt, conversation_history
            )
        elif self.provider == LLMProvider.ANTHROPIC:
            return await self._anthropic_completion(
                message, tools_available, system_prompt, conversation_history
            )
        elif self.provider == LLMProvider.LOCAL:
            return await self._local_completion(
                message, tools_available, system_prompt, conversation_history
            )
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    async def _openai_completion(self, 
                               message: str, 
                               tools_available: List[str] = None,
                               system_prompt: Optional[str] = None,
                               conversation_history: List[Dict] = None) -> LLMResponse:
        """OpenAI completion with function calling"""
        
        if not self.openai_client:
            raise RuntimeError("OpenAI client not initialized")
        
        # Build messages
        messages = []
        
        # System prompt
        system_content = system_prompt or self._get_default_system_prompt(tools_available)
        messages.append({"role": "system", "content": system_content})
        
        # Conversation history
        if conversation_history:
            messages.extend(conversation_history[-10:])  # Last 10 messages
        
        # Current message
        messages.append({"role": "user", "content": message})
        
        # Prepare tools for OpenAI function calling
        tools = self._prepare_openai_tools(tools_available) if tools_available else None
        
        try:
            completion = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto" if tools else None,
                temperature=0.7,
                max_tokens=1000
            )
            
            response_message = completion.choices[0].message
            
            # Check if LLM wants to call a function
            if response_message.tool_calls:
                tool_call = response_message.tool_calls[0]
                function_name = tool_call.function.name
                
                try:
                    function_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    function_args = {}
                
                return LLMResponse(
                    type="tool_call",
                    tool_name=function_name,
                    tool_args=function_args,
                    reasoning=f"I need to use the {function_name} function to help with this request.",
                    model_used=self.model,
                    tokens_used=completion.usage.total_tokens if completion.usage else None
                )
            
            # Regular text response
            return LLMResponse(
                type="text",
                content=response_message.content,
                reasoning="Providing a direct conversational response.",
                model_used=self.model,
                tokens_used=completion.usage.total_tokens if completion.usage else None
            )
            
        except Exception as e:
            print(f"❌ OpenAI API error: {e}")
            return LLMResponse(
                type="text",
                content=f"I apologize, but I encountered an error processing your request. Please try again.",
                reasoning=f"API error: {str(e)}"
            )

    async def _anthropic_completion(self, 
                                  message: str, 
                                  tools_available: List[str] = None,
                                  system_prompt: Optional[str] = None,
                                  conversation_history: List[Dict] = None) -> LLMResponse:
        """Anthropic completion with tool use"""
        
        if not self.anthropic_client:
            raise RuntimeError("Anthropic client not initialized")
        
        # Build messages for Anthropic
        messages = []
        
        # Conversation history
        if conversation_history:
            messages.extend(conversation_history[-10:])
        
        # Current message
        messages.append({"role": "user", "content": message})
        
        # System prompt
        system_content = system_prompt or self._get_default_system_prompt(tools_available)
        
        # Prepare tools for Anthropic
        tools = self._prepare_anthropic_tools(tools_available) if tools_available else None
        
        try:
            response = await self.anthropic_client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.7,
                system=system_content,
                messages=messages,
                tools=tools if tools else []
            )
            
            # Process response
            for content_block in response.content:
                if content_block.type == "tool_use":
                    return LLMResponse(
                        type="tool_call",
                        tool_name=content_block.name,
                        tool_args=content_block.input,
                        reasoning=f"I should use the {content_block.name} tool to help with this request.",
                        model_used=self.model,
                        tokens_used=response.usage.input_tokens + response.usage.output_tokens if response.usage else None
                    )
                
                elif content_block.type == "text":
                    return LLMResponse(
                        type="text",
                        content=content_block.text,
                        reasoning="Providing a direct conversational response.",
                        model_used=self.model,
                        tokens_used=response.usage.input_tokens + response.usage.output_tokens if response.usage else None
                    )
            
            # Fallback
            return LLMResponse(
                type="text",
                content="I received your message but couldn't generate a proper response.",
                reasoning="Unexpected response format from Anthropic API."
            )
            
        except Exception as e:
            print(f"❌ Anthropic API error: {e}")
            return LLMResponse(
                type="text",
                content="I apologize, but I encountered an error processing your request. Please try again.",
                reasoning=f"API error: {str(e)}"
            )

    async def _local_completion(self, 
                              message: str, 
                              tools_available: List[str] = None,
                              system_prompt: Optional[str] = None,
                              conversation_history: List[Dict] = None) -> LLMResponse:
        """Local model completion (placeholder for Ollama, etc.)"""
        
        # This is a placeholder for local model integration
        # You could integrate with Ollama, transformers, or other local solutions
        
        print("🔧 Local model completion not implemented yet")
        print("   You can integrate with Ollama, transformers, or other local models here")
        
        # Simple rule-based response for demo
        if tools_available and any(tool in message.lower() for tool in ["hello", "hi", "greeting"]):
            return LLMResponse(
                type="tool_call",
                tool_name="greeting",
                tool_args={"name": "User"},
                reasoning="Detected greeting intent, using greeting tool.",
                model_used="local-demo"
            )
        
        return LLMResponse(
            type="text",
            content=f"Local model response to: '{message}'",
            reasoning="Local model processing.",
            model_used="local-demo"
        )

    def _get_default_system_prompt(self, tools_available: List[str] = None) -> str:
        """Generate default system prompt"""
        
        base_prompt = """You are a helpful AI assistant. You should be conversational, friendly, and helpful.

When responding to users:
1. Be concise but informative
2. Use tools when they would be helpful
3. Explain your reasoning when using tools
4. Be natural in conversation"""

        if tools_available:
            tools_text = ", ".join(tools_available)
            base_prompt += f"""

Available tools: {tools_text}

Use tools when appropriate to enhance your response. For example:
- Use 'greeting' for hellos, introductions, or welcome messages
- Consider which tool would best help the user with their request"""

        return base_prompt

    def _prepare_openai_tools(self, tools_available: List[str]) -> List[Dict]:
        """Prepare tools in OpenAI function calling format"""
        
        # Define tool schemas for OpenAI
        tool_schemas = {
            "greeting": {
                "type": "function",
                "function": {
                    "name": "greeting",
                    "description": "Generate a personalized greeting message",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Name of the person to greet"
                            }
                        },
                        "required": ["name"]
                    }
                }
            },
            "get_capabilities": {
                "type": "function", 
                "function": {
                    "name": "get_capabilities",
                    "description": "Get the AI agent's capabilities and available tools",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
            # Add more tool schemas as needed
        }
        
        return [tool_schemas.get(tool) for tool in tools_available if tool in tool_schemas]

    def _prepare_anthropic_tools(self, tools_available: List[str]) -> List[Dict]:
        """Prepare tools in Anthropic tool use format"""
        
        # Define tool schemas for Anthropic
        tool_schemas = {
            "greeting": {
                "name": "greeting",
                "description": "Generate a personalized greeting message",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name of the person to greet"
                        }
                    },
                    "required": ["name"]
                }
            },
            "get_capabilities": {
                "name": "get_capabilities",
                "description": "Get the AI agent's capabilities and available tools",
                "input_schema": {
                    "type": "object", 
                    "properties": {},
                    "required": []
                }
            }
            # Add more tool schemas as needed
        }
        
        return [tool_schemas.get(tool) for tool in tools_available if tool in tool_schemas]

