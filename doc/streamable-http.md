# Complete Guide to Streamable HTTP

## What is Streamable HTTP?

**Streamable HTTP** is a modern communication protocol that unifies request-response patterns with real-time streaming capabilities in a single HTTP endpoint. It was designed specifically for AI agent architectures and is a core component of the  **Model Context Protocol（MCP）** | [Transport](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports).

### Key Characteristics

- **Single Endpoint**: All communications flow through one HTTP endpoint
- **Protocol Agnostic**: Supports both synchronous (JSON) and asynchronous (SSE) responses
- **Stateful Sessions**: Maintains persistent connections with session management
- **Bidirectional**: Servers can push updates and requests back to clients
- **Self-Upgrading**: Automatically switches between JSON and streaming based on client preferences

### Core Concept

```
Client Request → Single Endpoint → Server Decision
                                      ↓
                               JSON Response
                                 OR
                               SSE Stream
```

The server **intelligently chooses** the response format based on:
- Client's `Accept` header capabilities
- Nature of the request (simple vs. complex)
- Real-time requirements
- Session state

## Why Use Streamable HTTP?

### 1. **Unified Communication**
Traditional approaches require multiple endpoints:
```
❌ Traditional:
/api/chat          (JSON responses)
/api/stream        (SSE streaming)
/api/websocket     (WebSocket connection)
/api/poll          (Polling endpoint)

✅ Streamable HTTP:
/agent             (Handles everything)
```

### 2. **AI Agent Optimization**
Perfect for AI workloads that need:
- **Instant responses** for simple queries
- **Streaming responses** for complex generation
- **Tool calling** with real-time feedback
- **Session persistence** across interactions

### 3. **Infrastructure Simplicity**
- **One endpoint** to secure, monitor, and scale
- **Standard HTTP** - works with existing infrastructure
- **Session management** built into the protocol
- **Automatic failover** between response types

### 4. **Developer Experience**
```javascript
// Same client handles both patterns
const response = await fetch('/agent', {
  method: 'POST',
  headers: {
    'Accept': 'application/json, text/event-stream'
  },
  body: JSON.stringify(request)
});

// Server decides: JSON or SSE
if (response.headers.get('content-type').includes('json')) {
  return await response.json();
} else {
  return handleSSEStream(response);
}
```

## How to Use Streamable HTTP

### Server Implementation (FastAPI + FastMCP)

```python
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import json
import asyncio

app = FastAPI()

@app.post("/agent")
async def streamable_endpoint(request: Request):
    data = await request.json()
    accept_header = request.headers.get("accept", "")
    session_id = request.headers.get("mcp-session-id")
    
    # Process the request
    if data.get("method") == "chat":
        message = data["params"]["message"]
        
        # Simple request → JSON response
        if len(message) < 50 and "stream" not in accept_header:
            return {"response": f"Quick reply to: {message}"}
        
        # Complex request → SSE stream
        if "text/event-stream" in accept_header:
            return StreamingResponse(
                generate_streaming_response(message),
                media_type="text/event-stream"
            )
    
    # Default JSON response
    return {"result": "processed"}

async def generate_streaming_response(message: str):
    """Generate SSE stream for complex responses"""
    yield f"data: {json.dumps({'type': 'start', 'message': 'Processing...'})}\n\n"
    
    # Simulate AI processing with incremental updates
    words = f"AI response to: {message}".split()
    for word in words:
        await asyncio.sleep(0.1)  # Simulate processing time
        yield f"data: {json.dumps({'type': 'content', 'content': word + ' '})}\n\n"
    
    yield f"data: {json.dumps({'type': 'done'})}\n\n"
```

### Client Implementation

```javascript
class StreamableHTTPClient {
  async sendRequest(data, preferStreaming = false) {
    const headers = {
      'Content-Type': 'application/json',
      'Accept': preferStreaming 
        ? 'application/json, text/event-stream'
        : 'application/json'
    };
    
    if (this.sessionId) {
      headers['Mcp-Session-Id'] = this.sessionId;
    }
    
    const response = await fetch('/agent', {
      method: 'POST',
      headers,
      body: JSON.stringify(data)
    });
    
    // Extract session ID
    this.sessionId = response.headers.get('Mcp-Session-Id') || this.sessionId;
    
    // Handle response type
    const contentType = response.headers.get('content-type');
    
    if (contentType.includes('text/event-stream')) {
      return this.handleSSEStream(response);
    } else {
      return response.json();
    }
  }
  
  async handleSSEStream(response) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop(); // Keep incomplete line
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = JSON.parse(line.slice(6));
          this.onStreamData(data); // Handle each chunk
        }
      }
    }
  }
}
```

### Protocol Flow

```
1. Client Request:
   POST /agent
   Accept: application/json, text/event-stream
   Body: {"method": "chat", "params": {"message": "Hello"}}

2. Server Processing:
   - Analyzes request complexity
   - Checks client capabilities
   - Decides response format

3a. Simple Response (JSON):
   Content-Type: application/json
   {"response": "Hello! How can I help?"}

3b. Complex Response (SSE):
   Content-Type: text/event-stream
   data: {"type": "start"}
   data: {"type": "content", "content": "Hello! "}
   data: {"type": "content", "content": "How "}
   data: {"type": "content", "content": "can "}
   data: {"type": "done"}
```

## Comprehensive Protocol Comparison

### Overview Table

| Feature | Streamable HTTP | Server-Sent Events | WebSocket | HTTP Polling |
|---------|----------------|-------------------|-----------|--------------|
| **Connection Model** | Hybrid (JSON + SSE) | Unidirectional Stream | Bidirectional Socket | Request-Response |
| **Endpoints** | Single | Multiple | Single | Multiple |
| **Real-time** | ✅ Adaptive | ✅ Push-based | ✅ Full-duplex | ❌ Pull-based |
| **HTTP Compliance** | ✅ Full | ✅ Full | ❌ Upgrade required | ✅ Full |
| **Caching** | ✅ Smart | ❌ No | ❌ No | ✅ Yes |
| **Proxy Friendly** | ✅ Excellent | ⚠️ Some issues | ❌ Problematic | ✅ Excellent |
| **Session Management** | ✅ Built-in | ❌ Manual | ✅ Connection-based | ❌ Manual |
| **Scalability** | ✅ High | ⚠️ Medium | ⚠️ Medium | ✅ High |
| **Complexity** | 🟡 Medium | 🟢 Low | 🔴 High | 🟢 Low |

### Detailed Comparison

#### 1. **Streamable HTTP vs Server-Sent Events (SSE)**

**Streamable HTTP Advantages:**
- **Unified endpoint** - No need for separate streaming endpoints
- **Intelligent switching** - Uses JSON for simple requests, SSE for complex
- **Session management** - Built-in state tracking
- **Backward compatibility** - Works with non-streaming clients

**SSE Advantages:**
- **Simplicity** - Straightforward streaming implementation
- **Direct control** - Explicit streaming behavior
- **Lower overhead** - No protocol switching logic

**Use Cases:**
```javascript
// SSE: Always streaming
const eventSource = new EventSource('/events');
eventSource.onmessage = (event) => {
  console.log(event.data); // Every response is streamed
};

// Streamable HTTP: Adaptive
const client = new StreamableHTTPClient();
await client.send(simpleRequest);    // → JSON response
await client.send(complexRequest);   // → SSE stream
```

#### 2. **Streamable HTTP vs WebSocket**

**Streamable HTTP Advantages:**
- **HTTP compliance** - Works with all HTTP infrastructure
- **Caching support** - Can cache appropriate responses
- **Simpler deployment** - No special server configuration
- **Graceful degradation** - Falls back to regular HTTP

**WebSocket Advantages:**
- **Full bidirectional** - True two-way real-time communication
- **Lower latency** - No HTTP overhead per message
- **Custom protocols** - Can implement any messaging pattern

**Performance Comparison:**
```
WebSocket Message: ~2 bytes overhead
Streamable HTTP: ~100-200 bytes (HTTP headers)

WebSocket: Better for high-frequency messaging
Streamable HTTP: Better for request-response with occasional streaming
```

#### 3. **Streamable HTTP vs HTTP Polling**

**Streamable HTTP Advantages:**
- **Real-time updates** - Immediate server push
- **Efficient** - No wasted requests
- **Stateful** - Maintains session context
- **Adaptive** - Switches modes as needed

**HTTP Polling Advantages:**
- **Universal compatibility** - Works everywhere
- **Simple caching** - Standard HTTP caching
- **Predictable load** - Controlled request rate

**Resource Usage:**
```
HTTP Polling (1s intervals):
- 3600 requests/hour per client
- High server load
- Battery drain on mobile

Streamable HTTP:
- 1 initial request + pushed updates
- Low server load
- Battery efficient
```

### Protocol Selection Guide

#### Choose **Streamable HTTP** when:
- ✅ Building AI agents or conversational interfaces
- ✅ Need both quick responses and streaming
- ✅ Want unified endpoint architecture
- ✅ Require session management
- ✅ Working with MCP ecosystem

#### Choose **WebSocket** when:
- ✅ Need high-frequency bidirectional communication
- ✅ Building real-time games or collaboration tools
- ✅ Custom protocol requirements
- ✅ Low-latency is critical

#### Choose **Server-Sent Events** when:
- ✅ One-way real-time updates only
- ✅ Simple streaming requirements
- ✅ Want explicit streaming control
- ✅ Working with existing SSE infrastructure

#### Choose **HTTP Polling** when:
- ✅ Maximum compatibility required
- ✅ Infrequent updates (>30s intervals)
- ✅ Simple request-response pattern
- ✅ Strong caching requirements

## Real-World Examples

### AI Chat Application
```typescript
// Streamable HTTP excels here
class AIChatClient {
  async sendMessage(message: string) {
    // Short messages → JSON response
    if (message.length < 50) {
      const response = await this.client.send({
        method: 'chat',
        params: { message }
      });
      return response.content; // Immediate response
    }
    
    // Long/complex messages → SSE stream
    return this.client.sendStreaming({
      method: 'chat',
      params: { message }
    });
  }
}
```

### Live Dashboard
```typescript
// Traditional SSE approach
const dashboard = new EventSource('/dashboard-stream');
dashboard.onmessage = (event) => {
  updateCharts(JSON.parse(event.data));
};

// Streamable HTTP approach
const client = new StreamableHTTPClient();
// Get initial data via JSON
const initialData = await client.send({ method: 'getDashboard' });
// Subscribe to updates via SSE
const updates = await client.sendStreaming({ method: 'subscribeDashboard' });
```

### API Gateway Integration
```yaml
# Streamable HTTP - Single route
routes:
  - path: /agent
    service: ai-agent-service
    methods: [POST]
    
# Traditional - Multiple routes
routes:
  - path: /api/chat
    service: chat-service
  - path: /api/stream
    service: streaming-service
  - path: /api/websocket
    service: websocket-service
```

## Performance Considerations

### Latency Comparison
```
First Response Time:
HTTP Polling: ~500ms (waiting for next poll)
SSE: ~50ms (connection + first event)
WebSocket: ~100ms (handshake + first message)
Streamable HTTP: ~50ms (immediate or stream start)

Subsequent Updates:
HTTP Polling: 500-1000ms
SSE: <10ms
WebSocket: <5ms
Streamable HTTP: <10ms (when streaming)
```

### Resource Usage
```
Memory per Connection:
HTTP Polling: ~1KB (minimal state)
SSE: ~8KB (connection state)
WebSocket: ~16KB (full socket state)
Streamable HTTP: ~12KB (session + connection state)

Server Load (1000 concurrent clients):
HTTP Polling (1s): 1000 RPS
SSE: ~10 RPS (keepalive)
WebSocket: ~5 RPS (ping/pong)
Streamable HTTP: ~15 RPS (mixed pattern)
```

### Scalability Patterns
```python
# Streamable HTTP scaling strategy
async def handle_request(request):
    # Route simple requests to stateless workers
    if is_simple_request(request):
        return await stateless_handler(request)
    
    # Route complex requests to streaming workers
    else:
        return await streaming_handler(request)

# This allows:
# - Stateless workers for simple requests (high throughput)
# - Stateful workers for complex requests (rich interactions)
```

## Security Considerations

### CORS and Same-Origin Policy
```javascript
// Streamable HTTP - Standard CORS
fetch('/agent', {
  method: 'POST',
  headers: {
    'Accept': 'application/json, text/event-stream',
    'Authorization': 'Bearer token'
  }
}); // Works with standard CORS

// WebSocket - Different CORS handling
const ws = new WebSocket('wss://api.example.com/ws', [], {
  headers: { 'Authorization': 'Bearer token' } // May not work
});
```

### Authentication
```python
# Streamable HTTP - Standard HTTP auth
@app.post("/agent")
async def agent(request: Request, user = Depends(get_current_user)):
    # Standard HTTP authentication works
    session_id = f"user-{user.id}-{uuid4()}"
    
    if wants_streaming(request):
        return stream_with_auth(request, user)
    else:
        return json_with_auth(request, user)
```

### Rate Limiting
```python
# Easy rate limiting with Streamable HTTP
from slowapi import Limiter

limiter = Limiter(key_func=get_session_id)

@app.post("/agent")
@limiter.limit("10/minute")  # Per session
async def agent(request: Request):
    # Rate limiting works naturally
    pass
```

## Conclusion

**Streamable HTTP** represents an evolution in API design, specifically optimized for modern AI agent architectures. It combines the simplicity of HTTP with the real-time capabilities of streaming protocols, while maintaining the developer experience benefits of both.

### Key Takeaways:

1. **Unified Architecture** - One endpoint handles all communication patterns
2. **Intelligent Adaptation** - Protocol switches based on request complexity
3. **Infrastructure Friendly** - Works with existing HTTP infrastructure
4. **AI-Optimized** - Perfect for conversational and agent-based applications
5. **Future-Proof** - Designed for the era of AI-first applications

### When to Choose Streamable HTTP:

✅ **Perfect for:** AI agents, chatbots, conversational interfaces, MCP applications
✅ **Good for:** APIs that need both quick responses and real-time updates
⚠️ **Consider alternatives for:** High-frequency gaming, pure streaming applications, legacy systems

The protocol shines in scenarios where you need the **flexibility of both synchronous and asynchronous communication** in a **single, maintainable interface**. As AI applications become more prevalent, Streamable HTTP provides the foundation for building responsive, intelligent, and scalable AI agent services.
