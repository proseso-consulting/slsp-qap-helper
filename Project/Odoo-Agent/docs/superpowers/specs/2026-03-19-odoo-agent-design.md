# Odoo Agent Service — Design Spec

**Date:** 2026-03-19
**Project:** Odoo-Agent
**Status:** Approved

---

## Overview

An external webhook-based agent service deployed on **Google Cloud Run** that powers multiple AI agents inside **Odoo 19 Online Discuss**. Since Odoo Online (SaaS) does not support custom Python modules, the service runs externally and communicates with Odoo via XML-RPC.

Each agent appears in Odoo Discuss as a named bot with its own avatar. Users send messages in the agent's dedicated channel and receive AI-generated replies that can read and act on live Odoo data.

---

## Constraints

- **Odoo Online (SaaS)** — no custom Python modules, no Odoo.sh
- **No extra user licenses** — agents use `res.partner` records; one shared internal service user posts messages on behalf of all agents
- **One service, multiple agents** — a single Cloud Run deployment hosts all agents
- **Works within existing infrastructure** — reuses Cloud Run, Cloud Build, and the existing `google-drive-mcp-server` patterns

---

## Architecture

```
User types in Odoo Discuss (agent channel)
        ↓
Odoo Automated Action — webhook on mail.message create
(filtered: author_id != agent_partner_id, prevents loop)
        ↓
POST /{WEBHOOK_SECRET}/webhook  ← secret in URL path (same pattern as google-drive-mcp-server)
        ↓
Cloud Run Agent Service — returns 200 immediately, processes in background (FastAPI BackgroundTasks)
  ├── Look up agent config from ai.agent by channel_id
  ├── Cooldown check: skip if agent posted in the last 10s
  ├── Fetch conversation history from mail.message (comment type only)
  ├── Call Gemini API with tools + history (loop max 10 iterations)
  │     └── Gemini calls Odoo tools as needed (function calling)
  └── Post reply to Odoo Discuss with author_id = agent partner
```

**Runtime dependencies:**

| Dependency | Purpose |
|---|---|
| Odoo XML-RPC | Read/write Odoo data, post replies, fetch history |
| Google Gemini API | LLM + function calling (models with function calling support required) |
| Google Drive MCP server (optional) | Charts, Google Sheets, Drive file creation |

---

## Components

### Cloud Run Agent Service (Python)

```
agent-service/
├── main.py           # FastAPI app — POST /{WEBHOOK_SECRET}/webhook
├── agent.py          # Orchestration — cooldown, history, Gemini loop, post reply
├── odoo.py           # Odoo XML-RPC client with retry/backoff and per-call timeout
├── gemini.py         # Gemini API client + function calling setup
├── tools/
│   ├── odoo_tools.py     # 35 Odoo Connect tools re-implemented as direct XML-RPC calls
│   └── output_tools.py   # create_chart, create_excel, create_google_sheet, attach_file
├── config.py         # Env vars loader
└── Dockerfile / cloudbuild.yaml
```

**Cloud Run settings:**
- `min-instances: 1` — prevents container recycling mid-background-task (critical for async processing)
- `concurrency: 80` — handles multiple channels simultaneously

### Odoo Setup (one-time configuration)

| Item | Detail |
|---|---|
| Service user | One dedicated internal Odoo user (e.g. `agent-service@proseso-ventures.odoo.com`) used for all API calls |
| `res.partner` per agent | Separate partner record per agent — name + avatar appear in Discuss |
| Discuss channel per agent | One private channel per agent; channel `id` is the lookup key for agent config |
| Automated Action per channel | Fires webhook on `mail.message` create; domain filter excludes agent partner's own messages |
| `ai.agent` record per agent | Stores system prompt + model; linked to channel via `partner_id` ← verified writable via XML-RPC on `proseso-ventures.odoo.com` |

**Note on posting as agent partner:** `mail.channel.message_post` accepts `author_id` as a kwarg. Whether Odoo Online permits overriding `author_id` for a non-owner partner depends on the service account's access rights. This must be verified in the target instance before building. **Fallback:** if the override is denied, post as the service user and prefix the message body with the agent name in bold (e.g. `<b>FinanceBot:</b> ...`).

**Note on `odoo_authenticate`:** Authentication is handled internally by `odoo.py` at startup — not exposed as a Gemini tool.

### Agent Configuration (stored in Odoo `ai.agent`)

Model and behavior are configured per agent via the `system_prompt` field:

```
[MODEL: gemini-2.5-pro]

You are a helpful finance assistant for Proseso Ventures.
You have full access to Odoo data and can read, create, and update records.
Always ask for confirmation before deleting anything.
```

The service reads `system_prompt` from Odoo, extracts `[MODEL: ...]`, and uses the remainder as the system prompt sent to Gemini. Any valid Google AI model name supported by the Gemini API can be used — not limited to Odoo's built-in selection. Model must support function calling (e.g. `gemini-2.5-pro`, `gemini-2.5-flash`).

### Channel-to-Agent Mapping

The Automated Action webhook does **not** include `agent_partner_id` in the payload (it is not a `mail.message` field). Instead, the service looks up agent config by `channel_id`:

1. Webhook payload includes `channel_id` (from `res_id` on `mail.message`)
2. Service queries `ai.agent` where channel matches (via a stored mapping — see below)
3. Returns agent's `partner_id`, `system_prompt`, and model name

**Mapping storage:** A `mail.channel` custom description or a config JSON stored in Google Secret Manager keyed by `channel_id`. Secret Manager is preferred: no Odoo schema changes needed, no SaaS limitations.

---

## Tools Available to Gemini

### Odoo Tools (`odoo_tools.py`) — Static, XML-RPC direct

| Category | Tools |
|---|---|
| Search & Read | `odoo_search`, `odoo_read`, `odoo_read_group`, `odoo_count`, `odoo_get_fields`, `odoo_get_views`, `odoo_get_menus`, `odoo_get_metadata`, `odoo_search_models`, `odoo_default_get` |
| Write | `odoo_create`, `odoo_write`, `odoo_delete`, `odoo_copy`, `odoo_name_create`, `odoo_create_guided`, `odoo_execute_batch` |
| Actions | `odoo_call`, `odoo_run_server_action`, `odoo_trigger_cron`, `odoo_check_access` |
| Messaging | `odoo_send_message` |
| Files | `odoo_upload_attachment`, `odoo_download_attachment`, `odoo_get_report` |
| Lookup | `odoo_name_search`, `odoo_name_search_batch`, `odoo_list_companies` |

**Security guardrails:**
- `odoo_delete` and `odoo_run_server_action` require explicit user confirmation text in the conversation before `agent.py` will execute them — not delegated to Gemini alone
- Denylist of protected models: `ir.rule`, `ir.model.access`, `res.users`, `ir.config_parameter` — these cannot be modified via agent tools
- All tool calls are logged with the originating message for audit

### Output Tools (`output_tools.py`) — Dynamic MCP client for Google Drive server

At service startup, the agent service connects to `google-drive-mcp-server` via **SSE transport** using the `mcp` Python client library, calls `tools/list`, and registers discovered tools as Gemini function calling tools. New tools added to the Google Drive MCP server are picked up on next service restart.

**Startup behavior if MCP server unreachable:** Fail-open — service starts without output tools, logs a warning. Agents still function with Odoo tools only.

| Tool | Output | Attachment mechanism |
|---|---|---|
| `create_chart` | PNG image | Generate with `matplotlib` → upload to `ir.attachment` → link to reply `mail.message` via `attachment_ids` |
| `create_excel` | `.xlsx` file | Generate with `openpyxl` → upload to `ir.attachment` → link to reply `mail.message` via `attachment_ids` |
| `create_google_sheet` | Google Sheet link | Call Google Drive MCP server → post link URL in reply body |
| `attach_file` | Any file | Upload to `ir.attachment` → link to reply `mail.message` via `attachment_ids` |

**File attachment sequence for Discuss:**
1. Upload binary → `ir.attachment.create` with `res_model='mail.channel'`, `res_id=channel_id`
2. Call `mail.channel.message_post` with `attachment_ids=[attachment_id]`
3. Attachment appears inline in Discuss (images) or as download link (other files)

---

## Data Flow — Single Message

1. User sends message in agent's Discuss channel
2. Odoo Automated Action fires:
   - Trigger: `mail.message` on create
   - Domain filter: `[('author_id', '!=', agent_partner_id), ('res_id', '=', channel_id), ('message_type', '=', 'comment')]`
   - Action: HTTP POST to `https://agent-service.run.app/{WEBHOOK_SECRET}/webhook`
   - Payload: `{ channel_id, message_id, body, author_name }`
3. Service validates URL secret — 401 if mismatch
4. Service returns `200 OK` immediately; spawns `BackgroundTask` for processing
5. **Cooldown check:** fetch last message in channel from Odoo — if sender is agent partner AND timestamp < `DEBOUNCE_SECONDS` ago → skip. This is a cooldown (not a true debounce): first message in a rapid burst is processed; subsequent messages within the window are dropped. This is the intended behavior for v1.
6. Look up agent config: query Secret Manager for channel-to-agent mapping by `channel_id` → get `agent_partner_id`, `ai_agent_id`
7. Fetch agent config from `ai.agent` record → parse `[MODEL: ...]` → extract system prompt
8. Fetch conversation history from `mail.message`:
   - Filter: `res_id = channel_id`, `message_type = 'comment'`, exclude system/notification partners
   - Limit: `HISTORY_LIMIT` messages, capped by `HISTORY_MAX_CHARS` (approximate token budget)
   - Build `[{role: "user"/"model", content: "..."}]` for Gemini
9. Call Gemini: model name, system prompt, history, full tool set
10. **Function calling loop** (max `MAX_TOOL_ITERATIONS` = 10):
    - Gemini requests tool call → check denylist + confirmation requirements → execute XML-RPC or MCP call → return result to Gemini
    - Repeat until Gemini returns final text response
11. Post reply via `mail.channel.message_post` with `author_id = agent_partner_id` and `attachment_ids` if files were generated
12. Message appears in Discuss as the agent bot

---

## Concurrency

- **Multiple channels simultaneously:** Cloud Run auto-scales; each webhook is independent — handled natively
- **Same-channel rapid messages:** Cooldown check (Step 5) drops messages within `DEBOUNCE_SECONDS` of the last agent reply. First message is processed; subsequent rapid messages are dropped in v1.
- **Future:** Cloud Tasks FIFO queue per channel for strict sequential processing without message dropping

---

## Error Handling

| Failure | Response |
|---|---|
| URL secret mismatch | 401, log, ignore |
| Odoo unreachable at webhook receipt | 503 — Odoo retries webhook |
| Odoo unreachable during processing | Post: *"I'm having trouble connecting to Odoo right now. Try again in a moment."* |
| Odoo XML-RPC rate limit (429) | Retry with exponential backoff (3 attempts, max 30s total) in `odoo.py` |
| XML-RPC call timeout | Per-call timeout of `XML_RPC_TIMEOUT` seconds (default: 30). Return timeout error to Gemini — it adapts or explains |
| Agent config not found | Post: *"This channel is not configured for an agent. Contact admin."* |
| Gemini API error | Post: *"I'm having trouble responding right now. Try again in a moment."* |
| Tool call on denylisted model | Return error to Gemini: *"That operation is not permitted."* |
| Destructive tool without confirmation | Return to Gemini: *"Ask the user to confirm before proceeding."* |
| Tool call loop exceeded | Hard cap at `MAX_TOOL_ITERATIONS` — Gemini responds with available info |
| Cooldown triggered | 200, silent skip — no reply posted |
| MCP server unreachable at startup | Fail-open — start without output tools, log warning |
| `author_id` override rejected by Odoo | Fall back to posting as service user with agent name prefixed in body |

**Key principle:** The agent never goes silent. Every failure posts a human-readable message back to Discuss.

---

## Testing

| Type | What | Method |
|---|---|---|
| Unit | Each Odoo tool function | Mock XML-RPC responses, assert correct payload |
| Unit | Cooldown logic | Simulate timestamps, assert skip/process correctly |
| Unit | History filtering | Assert log notes and system messages excluded |
| Integration | Webhook → Odoo → Gemini → reply | Real `proseso-ventures.odoo.com` `#agent-test` channel |
| Integration | Verify `author_id` override works | Post message, check `author_id` in Discuss |
| Manual E2E | Full conversation | Send messages, verify replies, verify Odoo data changes |
| Manual E2E | File output | Ask for a chart, Excel file, Google Sheet |
| Tool calling | Destructive tool confirmation | Ask agent to delete a record — verify it asks for confirmation |
| Security | Prompt injection | Embed Odoo commands in a record's notes — verify agent does not execute |
| Error paths | Bad secret, Gemini down, rate limit | Assert graceful replies, no silent failures |

**Dev setup:** Dedicated `#agent-test` Discuss channel with a test agent (`[MODEL: gemini-2.5-flash]` for low cost during testing). Production channels are separate and unaffected.

---

## Deployment

Follows the same Cloud Build + Cloud Run pattern as `google-drive-mcp-server` and `Odoo-AP-Worker`:

- Push to `main` → Cloud Build → Docker image → Cloud Run deploy
- Secrets via Google Secret Manager
- Region: `asia-southeast1` (consistent with existing services)
- `min-instances: 1` required to prevent container recycling mid-background-task

---

## Environment Variables

| Variable | Description |
|---|---|
| `ODOO_URL` | `https://proseso-ventures.odoo.com` |
| `ODOO_DB` | `proseso-ventures` |
| `ODOO_USER` | Service account email |
| `ODOO_API_KEY` | Odoo API key (Secret Manager, rotate quarterly) |
| `GEMINI_API_KEY` | Google AI Studio API key (Secret Manager) |
| `WEBHOOK_SECRET` | Shared secret in URL path for webhook validation |
| `GOOGLE_DRIVE_MCP_URL` | URL of the Google Drive MCP server |
| `GOOGLE_DRIVE_MCP_SECRET` | Auth secret for Google Drive MCP server |
| `DEFAULT_GEMINI_MODEL` | Fallback model if not in system prompt (must support function calling) |
| `MAX_TOOL_ITERATIONS` | Max Gemini tool call iterations per response (default: 10) |
| `DEBOUNCE_SECONDS` | Cooldown window in seconds (default: 10) |
| `HISTORY_LIMIT` | Max messages to include in history (default: 20) |
| `HISTORY_MAX_CHARS` | Max total characters of history (default: 50000) |
| `XML_RPC_TIMEOUT` | Per-call XML-RPC timeout in seconds (default: 30) |

**Minimum Odoo permission scope for service account:** Read/write access to `mail.channel`, `mail.message`, `ir.attachment`, `ai.agent`, and all business models the agents need to access. No access to `ir.rule`, `ir.model.access`, `res.users`, `ir.config_parameter`.
