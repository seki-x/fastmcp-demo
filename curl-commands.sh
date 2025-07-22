# initial connection
curl -v -L -X POST http://localhost:8000/mcp/ \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -d '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {"experimental": {}, "sampling": {}}, "clientInfo": {"name": "curl-test", "version": "1.0"}}}'

# list tools
curl -v -L -X POST http://localhost:8000/mcp \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -H "Mcp-Session-Id: 9323f955c8b34b35a4c39b553af0ead3" \
    -d '{"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}'
