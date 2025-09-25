MCP Gmail Server Reference (Node & Python)
=========================================

Purpose
- Minimal reference for a Gmail MCP server that exposes a JSON-RPC endpoint compatible with the Voice Agent’s `mcp` tool.
- Implements a small set of tools: list_messages, get_message, create_draft, send_message.

Protocol
- Transport: HTTP JSON-RPC 2.0 over a single endpoint, e.g. `POST /rpc`
- Auth from Agent: Bearer token in `Authorization: Bearer <token>` (server verifies or maps to user)
- OAuth to Gmail: The MCP server itself owns OAuth 2.0 flow and securely stores user tokens

Methods
- tools/list (optional): returns available tool names and schemas
- tools/call: executes a tool
  - params: { name: string, arguments: object }
- resources/read (optional): read a resource by URI (not required for Gmail basic flows)

Suggested tool names
- gmail.list_messages: { query?: string, max?: number }
- gmail.get_message: { id: string, format?: "full"|"metadata"|"raw" }
- gmail.create_draft: { to: string, subject: string, body: string }
- gmail.send_message: { to: string, subject: string, body: string }

Security Notes
- Keep OAuth client secrets and refresh tokens on the MCP server only.
- Use per-user mapping for the incoming Bearer token (pairing) or embed user ID in the token.
- Rate-limit and audit log; mask PII where possible.

--------------------------------------------
Node.js (Express) Skeleton
--------------------------------------------

Prereqs
- Packages: express, body-parser (or built-in), googleapis, jsonwebtoken (optional), dotenv, uuid

Example `server.js`
```js
import express from 'express';
import { google } from 'googleapis';

const app = express();
app.use(express.json({ limit: '1mb' }));

// In production, replace with persistent store (DB/Redis)
const users = new Map(); // key: bearer token -> { oauthTokens, gmailClient }

function getOAuth2Client() {
  // Load from env or config file
  const clientId = process.env.GOOGLE_CLIENT_ID;
  const clientSecret = process.env.GOOGLE_CLIENT_SECRET;
  const redirectUri = process.env.GOOGLE_REDIRECT_URI; // e.g. http://localhost:9101/oauth2/callback
  return new google.auth.OAuth2(clientId, clientSecret, redirectUri);
}

async function ensureGmailClient(bearer) {
  let u = users.get(bearer);
  if (!u) {
    // In real apps, look up user by bearer, load stored tokens
    // For reference, throw if not paired
    throw new Error('Unauthorized or not paired');
  }
  const oauth2Client = getOAuth2Client();
  oauth2Client.setCredentials(u.oauthTokens);
  const gmail = google.gmail({ version: 'v1', auth: oauth2Client });
  u.gmailClient = gmail;
  return u;
}

function buildRfc822({ to, subject, body }) {
  const headers = [
    `To: ${to}`,
    `Subject: ${subject}`,
    'MIME-Version: 1.0',
    'Content-Type: text/plain; charset=UTF-8',
  ];
  const msg = headers.join('\r\n') + '\r\n\r\n' + body;
  return Buffer.from(msg).toString('base64').replace(/\+/g, '-').replace(/\//g, '_'); // URL-safe base64
}

app.post('/rpc', async (req, res) => {
  try {
    const auth = req.headers['authorization'] || '';
    const token = auth.startsWith('Bearer ')
      ? auth.slice('Bearer '.length)
      : null;
    if (!token) return res.status(401).json({ error: 'Unauthorized' });

    const { jsonrpc, id, method, params } = req.body || {};
    if (jsonrpc !== '2.0') return res.status(400).json({ error: 'Invalid JSON-RPC' });

    if (method === 'tools/list') {
      return res.json({ jsonrpc: '2.0', id, result: [
        { name: 'gmail.list_messages' },
        { name: 'gmail.get_message' },
        { name: 'gmail.create_draft' },
        { name: 'gmail.send_message' },
      ]});
    }

    const user = await ensureGmailClient(token);
    const gmail = user.gmailClient;

    if (method === 'tools/call') {
      const { name, arguments: args = {} } = params || {};
      switch (name) {
        case 'gmail.list_messages': {
          const q = args.query || 'is:unread newer_than:7d';
          const max = args.max || 10;
          const out = await gmail.users.messages.list({ userId: 'me', q, maxResults: max });
          return res.json({ jsonrpc: '2.0', id, result: out.data });
        }
        case 'gmail.get_message': {
          const msgId = args.id;
          const format = args.format || 'full';
          const out = await gmail.users.messages.get({ userId: 'me', id: msgId, format });
          return res.json({ jsonrpc: '2.0', id, result: out.data });
        }
        case 'gmail.create_draft': {
          const raw = buildRfc822({ to: args.to, subject: args.subject, body: args.body });
          const out = await gmail.users.drafts.create({ userId: 'me', requestBody: { message: { raw } } });
          return res.json({ jsonrpc: '2.0', id, result: out.data });
        }
        case 'gmail.send_message': {
          const raw = buildRfc822({ to: args.to, subject: args.subject, body: args.body });
          const out = await gmail.users.messages.send({ userId: 'me', requestBody: { raw } });
          return res.json({ jsonrpc: '2.0', id, result: out.data });
        }
        default:
          return res.json({ jsonrpc: '2.0', id, error: { code: -32601, message: 'Unknown tool' } });
      }
    }

    // optional
    if (method === 'resources/read') {
      return res.json({ jsonrpc: '2.0', id, result: { ok: true } });
    }

    return res.json({ jsonrpc: '2.0', id, error: { code: -32601, message: 'Unknown method' } });
  } catch (e) {
    console.error(e);
    return res.status(500).json({ jsonrpc: '2.0', id: req.body?.id ?? null, error: { code: -32000, message: String(e) } });
  }
});

app.listen(process.env.PORT || 9101, () => {
  console.log('Gmail MCP server listening');
});
```

Notes
- Add OAuth pairing routes (`/oauth2/start`, `/oauth2/callback`) to obtain and store tokens per user.
- Map the incoming Bearer token to a stored user record; load `oauthTokens` and refresh automatically.

--------------------------------------------
Python (FastAPI) Skeleton
--------------------------------------------

Prereqs
- Packages: fastapi, uvicorn, google-api-python-client, google-auth-oauthlib, pydantic

Example `server.py`
```python
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import os
import base64

app = FastAPI()

# In production, replace with persistent user store
USERS = {}  # key: bearer token -> { 'tokens': {...} }

class JsonRpcRequest(BaseModel):
    jsonrpc: str
    id: int | str | None
    method: str
    params: dict | None = None

def get_gmail(credentials_dict):
    creds = Credentials(**credentials_dict)
    gmail = build('gmail', 'v1', credentials=creds)
    return gmail

def build_rfc822(to: str, subject: str, body: str) -> str:
    msg = f"To: {to}\r\nSubject: {subject}\r\nMIME-Version: 1.0\r\nContent-Type: text/plain; charset=UTF-8\r\n\r\n{body}"
    b64 = base64.urlsafe_b64encode(msg.encode('utf-8')).decode('utf-8')
    return b64

@app.post('/rpc')
async def rpc(req: Request, payload: JsonRpcRequest):
    auth = req.headers.get('authorization') or ''
    token = auth[7:] if auth.startswith('Bearer ') else None
    if not token or token not in USERS:
        raise HTTPException(status_code=401, detail='Unauthorized')

    if payload.jsonrpc != '2.0':
        raise HTTPException(status_code=400, detail='Invalid JSON-RPC')

    try:
        if payload.method == 'tools/list':
            return { 'jsonrpc': '2.0', 'id': payload.id, 'result': [
                { 'name': 'gmail.list_messages' },
                { 'name': 'gmail.get_message' },
                { 'name': 'gmail.create_draft' },
                { 'name': 'gmail.send_message' },
            ] }

        user = USERS[token]
        gmail = get_gmail(user['tokens'])
        p = payload.params or {}

        if payload.method == 'tools/call':
            name = p.get('name')
            args = p.get('arguments') or {}
            if name == 'gmail.list_messages':
                q = args.get('query', 'is:unread newer_than:7d')
                max_results = int(args.get('max', 10))
                out = gmail.users().messages().list(userId='me', q=q, maxResults=max_results).execute()
                return { 'jsonrpc': '2.0', 'id': payload.id, 'result': out }
            if name == 'gmail.get_message':
                mid = args['id']
                fmt = args.get('format', 'full')
                out = gmail.users().messages().get(userId='me', id=mid, format=fmt).execute()
                return { 'jsonrpc': '2.0', 'id': payload.id, 'result': out }
            if name == 'gmail.create_draft':
                raw = build_rfc822(args['to'], args['subject'], args['body'])
                out = gmail.users().drafts().create(userId='me', body={'message': {'raw': raw}}).execute()
                return { 'jsonrpc': '2.0', 'id': payload.id, 'result': out }
            if name == 'gmail.send_message':
                raw = build_rfc822(args['to'], args['subject'], args['body'])
                out = gmail.users().messages().send(userId='me', body={'raw': raw}).execute()
                return { 'jsonrpc': '2.0', 'id': payload.id, 'result': out }
            return { 'jsonrpc': '2.0', 'id': payload.id, 'error': { 'code': -32601, 'message': 'Unknown tool' } }

        if payload.method == 'resources/read':
            return { 'jsonrpc': '2.0', 'id': payload.id, 'result': { 'ok': True } }

        return { 'jsonrpc': '2.0', 'id': payload.id, 'error': { 'code': -32601, 'message': 'Unknown method' } }

    except Exception as e:
        return { 'jsonrpc': '2.0', 'id': payload.id, 'error': { 'code': -32000, 'message': str(e) } }
```

Notes
- Add OAuth routes (e.g., `/oauth/start`, `/oauth/callback`) using `google_auth_oauthlib.flow.Flow` to acquire and store tokens per user.
- On each call, refresh tokens automatically (the Google library handles refresh using refresh_token/client_secrets if present).

--------------------------------------------
Testing the Server
--------------------------------------------

1) Pair a user (out of scope here): store `{ 'tokens': { ... } }` into USERS or a DB, and issue a Bearer token for the Agent.

2) Call list_messages
```bash
curl -X POST http://localhost:9101/rpc \
  -H 'Authorization: Bearer TEST_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc":"2.0",
    "id":1,
    "method":"tools/call",
    "params":{"name":"gmail.list_messages","arguments":{"query":"is:unread","max":5}}
  }'
```

3) Call send_message (confirm on Agent side before invoking)
```bash
curl -X POST http://localhost:9101/rpc \
  -H 'Authorization: Bearer TEST_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc":"2.0",
    "id":2,
    "method":"tools/call",
    "params":{"name":"gmail.send_message","arguments":{"to":"me@example.com","subject":"Hi","body":"Hello"}}
  }'
```

--------------------------------------------
Production Considerations
--------------------------------------------
- Persist users and tokens with encryption; rotate keys.
- Enforce scopes and per-tool ACLs; add allow/deny lists.
- Add rate limiting, request tracing, structured logging with PII minimization.
- Support tools/list with full JSON schemas to enable richer tool-calling in the Agent.
