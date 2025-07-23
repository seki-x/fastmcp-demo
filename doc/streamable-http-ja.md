# Streamable HTTP完全ガイド

## Streamable HTTPとは？

**Streamable HTTP**は、リクエスト-レスポンスパターンとリアルタイムストリーミング機能を単一のHTTPエンドポイントで統合する現代的な通信プロトコルです。AIエージェントアーキテクチャ専用に設計され、[**Model Context Protocol（MCP）**](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports)の中核コンポーネントです。

### 主要特徴

- **単一エンドポイント**: すべての通信が1つのHTTPエンドポイントを通じて行われる
- **プロトコル非依存**: 同期（JSON）と非同期（SSE）両方のレスポンスをサポート
- **ステートフル セッション**: セッション管理を伴う永続接続を維持
- **双方向**: サーバーがクライアントに更新やリクエストをプッシュ可能
- **自動アップグレード**: クライアントの設定に基づいてJSONとストリーミングを自動切り替え

### コアコンセプト

```
クライアントリクエスト → 単一エンドポイント → サーバー判断
                                        ↓
                                 JSONレスポンス
                                   または
                                 SSEストリーム
```

サーバーは以下に基づいて**レスポンス形式を賢く選択**します：
- クライアントの`Accept`ヘッダー機能
- リクエストの性質（シンプル vs. 複雑）
- リアルタイム要件
- セッション状態

## なぜStreamable HTTPを使うのか？

### 1. **統一された通信**
従来のアプローチでは複数のエンドポイントが必要：
```
❌ 従来型:
/api/chat          (JSONレスポンス)
/api/stream        (SSEストリーミング)
/api/websocket     (WebSocket接続)
/api/poll          (ポーリングエンドポイント)

✅ Streamable HTTP:
/agent             (すべてを処理)
```

### 2. **AIエージェント最適化**
以下を必要とするAIワークロードに最適：
- **即座のレスポンス** - シンプルなクエリに対して
- **ストリーミングレスポンス** - 複雑な生成に対して
- **ツール呼び出し** - リアルタイムフィードバック付き
- **セッション永続化** - インタラクション間で

### 3. **インフラストラクチャの簡素化**
- **1つのエンドポイント** でセキュリティ、監視、スケーリングを管理
- **標準HTTP** - 既存インフラストラクチャで動作
- **セッション管理** がプロトコルに組み込まれている
- **自動フェイルオーバー** がレスポンスタイプ間で機能

### 4. **開発者体験**
```javascript
// 同じクライアントで両方のパターンを処理
const response = await fetch('/agent', {
  method: 'POST',
  headers: {
    'Accept': 'application/json, text/event-stream'
  },
  body: JSON.stringify(request)
});

// サーバーが判断: JSONまたはSSE
if (response.headers.get('content-type').includes('json')) {
  return await response.json();
} else {
  return handleSSEStream(response);
}
```

## Streamable HTTPの使い方

### サーバー実装（FastAPI + FastMCP）

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
    
    # リクエストを処理
    if data.get("method") == "chat":
        message = data["params"]["message"]
        
        # シンプルなリクエスト → JSONレスポンス
        if len(message) < 50 and "stream" not in accept_header:
            return {"response": f"素早い返答: {message}"}
        
        # 複雑なリクエスト → SSEストリーム
        if "text/event-stream" in accept_header:
            return StreamingResponse(
                generate_streaming_response(message),
                media_type="text/event-stream"
            )
    
    # デフォルトJSONレスポンス
    return {"result": "処理済み"}

async def generate_streaming_response(message: str):
    """複雑なレスポンス用のSSEストリーム生成"""
    yield f"data: {json.dumps({'type': 'start', 'message': '処理中...'})}\n\n"
    
    # 段階的更新でAI処理をシミュレート
    words = f"AIレスポンス: {message}".split()
    for word in words:
        await asyncio.sleep(0.1)  # 処理時間をシミュレート
        yield f"data: {json.dumps({'type': 'content', 'content': word + ' '})}\n\n"
    
    yield f"data: {json.dumps({'type': 'done'})}\n\n"
```

### クライアント実装

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
    
    // セッションIDを抽出
    this.sessionId = response.headers.get('Mcp-Session-Id') || this.sessionId;
    
    // レスポンスタイプを処理
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
      buffer = lines.pop(); // 不完全な行を保持
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = JSON.parse(line.slice(6));
          this.onStreamData(data); // 各チャンクを処理
        }
      }
    }
  }
}
```

### プロトコルフロー

```
1. クライアントリクエスト:
   POST /agent
   Accept: application/json, text/event-stream
   Body: {"method": "chat", "params": {"message": "こんにちは"}}

2. サーバー処理:
   - リクエストの複雑さを分析
   - クライアント機能をチェック
   - レスポンス形式を決定

3a. シンプルレスポンス (JSON):
   Content-Type: application/json
   {"response": "こんにちは！何かお手伝いできることはありますか？"}

3b. 複雑なレスポンス (SSE):
   Content-Type: text/event-stream
   data: {"type": "start"}
   data: {"type": "content", "content": "こんにちは！ "}
   data: {"type": "content", "content": "何か "}
   data: {"type": "content", "content": "お手伝い "}
   data: {"type": "done"}
```

## 包括的プロトコル比較

### 概要表

| 機能 | Streamable HTTP | Server-Sent Events | WebSocket | HTTPポーリング |
|---------|----------------|-------------------|-----------|--------------|
| **接続モデル** | ハイブリッド (JSON + SSE) | 単方向ストリーム | 双方向ソケット | リクエスト-レスポンス |
| **エンドポイント** | 単一 | 複数 | 単一 | 複数 |
| **リアルタイム** | ✅ 適応的 | ✅ プッシュベース | ✅ 全二重 | ❌ プルベース |
| **HTTP準拠** | ✅ 完全 | ✅ 完全 | ❌ アップグレード必要 | ✅ 完全 |
| **キャッシュ** | ✅ スマート | ❌ なし | ❌ なし | ✅ あり |
| **プロキシ対応** | ✅ 優秀 | ⚠️ 一部問題あり | ❌ 問題あり | ✅ 優秀 |
| **セッション管理** | ✅ 組み込み | ❌ 手動 | ✅ 接続ベース | ❌ 手動 |
| **スケーラビリティ** | ✅ 高 | ⚠️ 中 | ⚠️ 中 | ✅ 高 |
| **複雑さ** | 🟡 中 | 🟢 低 | 🔴 高 | 🟢 低 |

### 詳細比較

#### 1. **Streamable HTTP vs Server-Sent Events (SSE)**

**Streamable HTTPの利点:**
- **統一エンドポイント** - 別々のストリーミングエンドポイント不要
- **賢い切り替え** - シンプルなリクエストにはJSON、複雑なものにはSSE
- **セッション管理** - 組み込まれた状態追跡
- **後方互換性** - 非ストリーミングクライアントで動作

**SSEの利点:**
- **シンプルさ** - 分かりやすいストリーミング実装
- **直接制御** - 明示的なストリーミング動作
- **低オーバーヘッド** - プロトコル切り替えロジックなし

**使用例:**
```javascript
// SSE: 常にストリーミング
const eventSource = new EventSource('/events');
eventSource.onmessage = (event) => {
  console.log(event.data); // すべてのレスポンスがストリーム
};

// Streamable HTTP: 適応的
const client = new StreamableHTTPClient();
await client.send(simpleRequest);    // → JSONレスポンス
await client.send(complexRequest);   // → SSEストリーム
```

#### 2. **Streamable HTTP vs WebSocket**

**Streamable HTTPの利点:**
- **HTTP準拠** - すべてのHTTPインフラストラクチャで動作
- **キャッシュサポート** - 適切なレスポンスをキャッシュ可能
- **簡単なデプロイ** - 特別なサーバー設定不要
- **グレースフルデグラデーション** - 通常のHTTPにフォールバック

**WebSocketの利点:**
- **完全双方向** - 真の双方向リアルタイム通信
- **低レイテンシ** - メッセージごとのHTTPオーバーヘッドなし
- **カスタムプロトコル** - 任意のメッセージングパターン実装可能

**パフォーマンス比較:**
```
WebSocketメッセージ: ~2バイトオーバーヘッド
Streamable HTTP: ~100-200バイト (HTTPヘッダー)

WebSocket: 高頻度メッセージングに適している
Streamable HTTP: 時々ストリーミングするリクエスト-レスポンスに適している
```

#### 3. **Streamable HTTP vs HTTPポーリング**

**Streamable HTTPの利点:**
- **リアルタイム更新** - 即座のサーバープッシュ
- **効率的** - 無駄なリクエストなし
- **ステートフル** - セッションコンテキストを維持
- **適応的** - 必要に応じてモード切り替え

**HTTPポーリングの利点:**
- **汎用互換性** - どこでも動作
- **シンプルキャッシュ** - 標準HTTPキャッシュ
- **予測可能な負荷** - 制御されたリクエストレート

**リソース使用量:**
```
HTTPポーリング (1秒間隔):
- クライアントあたり3600リクエスト/時間
- 高いサーバー負荷
- モバイルでバッテリー消耗

Streamable HTTP:
- 1つの初期リクエスト + プッシュ更新
- 低いサーバー負荷
- バッテリー効率的
```

### プロトコル選択ガイド

#### **Streamable HTTP**を選ぶべき場合:
- ✅ AIエージェントや会話インターフェースを構築
- ✅ 素早いレスポンスとストリーミング両方が必要
- ✅ 統一エンドポイントアーキテクチャが欲しい
- ✅ セッション管理が必要
- ✅ MCPエコシステムで作業

#### **WebSocket**を選ぶべき場合:
- ✅ 高頻度双方向通信が必要
- ✅ リアルタイムゲームやコラボレーションツールを構築
- ✅ カスタムプロトコル要件
- ✅ 低レイテンシが重要

#### **Server-Sent Events**を選ぶべき場合:
- ✅ 単方向リアルタイム更新のみ
- ✅ シンプルなストリーミング要件
- ✅ 明示的なストリーミング制御が欲しい
- ✅ 既存SSEインフラストラクチャで作業

#### **HTTPポーリング**を選ぶべき場合:
- ✅ 最大互換性が必要
- ✅ まれな更新（30秒以上の間隔）
- ✅ シンプルなリクエスト-レスポンスパターン
- ✅ 強力なキャッシュ要件

## 実世界の例

### AIチャットアプリケーション
```typescript
// Streamable HTTPがここで優秀
class AIChatClient {
  async sendMessage(message: string) {
    // 短いメッセージ → JSONレスポンス
    if (message.length < 50) {
      const response = await this.client.send({
        method: 'chat',
        params: { message }
      });
      return response.content; // 即座のレスポンス
    }
    
    // 長い/複雑なメッセージ → SSEストリーム
    return this.client.sendStreaming({
      method: 'chat',
      params: { message }
    });
  }
}
```

### ライブダッシュボード
```typescript
// 従来のSSEアプローチ
const dashboard = new EventSource('/dashboard-stream');
dashboard.onmessage = (event) => {
  updateCharts(JSON.parse(event.data));
};

// Streamable HTTPアプローチ
const client = new StreamableHTTPClient();
// JSONで初期データを取得
const initialData = await client.send({ method: 'getDashboard' });
// SSEで更新を購読
const updates = await client.sendStreaming({ method: 'subscribeDashboard' });
```

### APIゲートウェイ統合
```yaml
# Streamable HTTP - 単一ルート
routes:
  - path: /agent
    service: ai-agent-service
    methods: [POST]
    
# 従来型 - 複数ルート
routes:
  - path: /api/chat
    service: chat-service
  - path: /api/stream
    service: streaming-service
  - path: /api/websocket
    service: websocket-service
```

## パフォーマンス考慮事項

### レイテンシ比較
```
初回レスポンス時間:
HTTPポーリング: ~500ms (次のポーリングを待機)
SSE: ~50ms (接続 + 最初のイベント)
WebSocket: ~100ms (ハンドシェイク + 最初のメッセージ)
Streamable HTTP: ~50ms (即座またはストリーム開始)

後続の更新:
HTTPポーリング: 500-1000ms
SSE: <10ms
WebSocket: <5ms
Streamable HTTP: <10ms (ストリーミング時)
```

### リソース使用量
```
接続あたりのメモリ:
HTTPポーリング: ~1KB (最小状態)
SSE: ~8KB (接続状態)
WebSocket: ~16KB (完全ソケット状態)
Streamable HTTP: ~12KB (セッション + 接続状態)

サーバー負荷 (1000同時クライアント):
HTTPポーリング (1秒): 1000 RPS
SSE: ~10 RPS (キープアライブ)
WebSocket: ~5 RPS (ping/pong)
Streamable HTTP: ~15 RPS (混合パターン)
```

### スケーラビリティパターン
```python
# Streamable HTTPスケーリング戦略
async def handle_request(request):
    # シンプルなリクエストをステートレスワーカーに
    if is_simple_request(request):
        return await stateless_handler(request)
    
    # 複雑なリクエストをストリーミングワーカーに
    else:
        return await streaming_handler(request)

# これにより可能になる:
# - シンプルなリクエスト用ステートレスワーカー (高スループット)
# - 複雑なリクエスト用ステートフルワーカー (豊富なインタラクション)
```

## セキュリティ考慮事項

### CORSと同一オリジンポリシー
```javascript
// Streamable HTTP - 標準CORS
fetch('/agent', {
  method: 'POST',
  headers: {
    'Accept': 'application/json, text/event-stream',
    'Authorization': 'Bearer token'
  }
}); // 標準CORSで動作

// WebSocket - 異なるCORS処理
const ws = new WebSocket('wss://api.example.com/ws', [], {
  headers: { 'Authorization': 'Bearer token' } // 動作しない可能性
});
```

### 認証
```python
# Streamable HTTP - 標準HTTP認証
@app.post("/agent")
async def agent(request: Request, user = Depends(get_current_user)):
    # 標準HTTP認証が動作
    session_id = f"user-{user.id}-{uuid4()}"
    
    if wants_streaming(request):
        return stream_with_auth(request, user)
    else:
        return json_with_auth(request, user)
```

### レート制限
```python
# Streamable HTTPで簡単なレート制限
from slowapi import Limiter

limiter = Limiter(key_func=get_session_id)

@app.post("/agent")
@limiter.limit("10/minute")  # セッションあたり
async def agent(request: Request):
    # レート制限が自然に動作
    pass
```

## 結論

**Streamable HTTP**は、特に現代のAIエージェントアーキテクチャに最適化されたAPI設計の進化を表しています。HTTPのシンプルさとストリーミングプロトコルのリアルタイム機能を組み合わせ、両方の開発者体験の利点を維持しています。

### 主要なポイント:

1. **統一アーキテクチャ** - 1つのエンドポイントですべての通信パターンを処理
2. **賢い適応** - リクエストの複雑さに基づいてプロトコルが切り替わる
3. **インフラストラクチャ対応** - 既存のHTTPインフラストラクチャで動作
4. **AI最適化** - 会話型およびエージェントベースのアプリケーションに最適
5. **将来性** - AIファーストアプリケーションの時代向けに設計

### Streamable HTTPを選ぶべき場合:

✅ **最適:** AIエージェント、チャットボット、会話インターフェース、MCPアプリケーション
✅ **適している:** 素早いレスポンスとリアルタイム更新の両方が必要なAPI
⚠️ **代替を検討:** 高頻度ゲーム、純粋なストリーミングアプリケーション、レガシーシステム

プロトコルは**同期と非同期通信の柔軟性**を**単一の保守可能なインターフェース**で必要とするシナリオで威力を発揮します。AIアプリケーションがより普及するにつれ、Streamable HTTPは応答性が高く、インテリジェントで、スケーラブルなAIエージェントサービスを構築するための基盤を提供します。
