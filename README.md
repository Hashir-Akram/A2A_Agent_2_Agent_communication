# A2A + MCP Travel Planner (4 Agents, Simple Version)

A small, readable project that shows how **A2A** (agent ↔ agent) and **MCP** (agent ↔ tools) work together.

```
User ─► Orchestrator ──A2A──► Weather Agent ──MCP──► Weather API (Open-Meteo, real)
        (A2A client)   ├────► Hotel Agent   ──MCP──► Hotel DB (SQLite)
                       └────► Flight Agent  ──MCP──► Flights API (sample data)
```

## The two protocols in one sentence each

| Protocol | Connects | Used for |
|----------|----------|----------|
| **A2A**  | Orchestrator → Agents | "Hey Weather Agent, please do this task" |
| **MCP**  | Agent → Tools/APIs/DB | "Weather Agent, here are the tools you can call" |

OpenAI (the LLM) is the *brain* inside the Orchestrator and inside each agent.

## Project layout

```
common/
  llm.py            OpenAI client (reads .env)
  agent_brain.py    LLM + MCP tool loop used by every agent
  a2a_server.py     Generic A2A server (agent card + message/send)
mcp_servers/        The TOOLS (one MCP server per agent)
  weather_mcp.py    real weather via Open-Meteo (no key needed)
  hotel_mcp.py      SQLite database (auto-created and seeded)
  flights_mcp.py    sample flight data (swap for a real API later)
agents/             The 3 A2A servers (ports 8001-8003), ~10 lines each
orchestrator.py     The A2A client + LLM planner (you chat with this)
run_agents.py       Starts the 3 agents
```

## Setup (Windows, venv)

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # then put your OPENAI_API_KEY inside .env
```

## Run

Terminal 1 (agents):
```powershell
.venv\Scripts\activate
python run_agents.py
```

Terminal 2 (orchestrator):
```powershell
.venv\Scripts\activate
python orchestrator.py
```

Try: `Plan my Goa trip from Mumbai, hotel budget Rs 5000 per night, for 3 days`

You will see the flow in the logs: `[A2A] -> ask_hotel_agent ...` in the orchestrator, then `[MCP] search_hotels(...)` in the agent terminal.

---

## How the flow is implemented (read this, don't just copy)

### Step 1 – Build the tools (MCP) — `mcp_servers/*.py`
A tool is a normal Python function with `@mcp.tool`. FastMCP turns its name, docstring and type hints into a schema the LLM understands.
```python
@mcp.tool
def search_flights(origin: str, destination: str) -> str:
    """Search flights between two cities, cheapest first."""
```
The **docstring matters**: it is how the LLM decides *when* to use the tool.

### Step 2 – Give an agent its brain — `common/agent_brain.py`
The loop every agent runs:
1. Connect to its MCP server and `list_tools()`.
2. Send the user text + tools to OpenAI.
3. If OpenAI answers with a `tool_call` → run it with `mcp.call_tool()` → send the result back.
4. When OpenAI replies with plain text → that is the answer.

### Step 3 – Expose the agent over A2A — `common/a2a_server.py`
An A2A agent needs just two endpoints:
- `GET /.well-known/agent.json` – the **Agent Card** (name, description, skills). This is how others *discover* it.
- `POST /` with JSON-RPC `message/send` – how others *give it a task*.

Each file in `agents/` only supplies: name, description, system prompt and which MCP script to use.

### Step 4 – The Orchestrator (A2A client) — `orchestrator.py`
1. **Discover**: fetch each agent's card.
2. **Convert to tools**: each agent becomes one OpenAI tool (`ask_weather_agent`, `ask_hotel_agent`, `ask_flight_agent`) with the card's description.
3. **Plan**: the LLM decides which agents to call; for a trip it calls all three at once.
4. **Delegate**: we POST a `message/send` to each agent (in parallel).
5. **Answer**: the LLM merges the three replies into one trip plan.

The nice trick: *the orchestrator treats agents exactly like tools*. That is why the code stays small.

### A2A message format used
```json
{"jsonrpc":"2.0","id":"1","method":"message/send",
 "params":{"message":{"role":"user","messageId":"abc",
   "parts":[{"kind":"text","text":"Weather in Goa for 3 days?"}]}}}
```
Reply: `result.parts[0].text`.

## Extend it
- **Add a 4th specialist** (e.g. Restaurant Agent): create `mcp_servers/food_mcp.py`, copy `agents/hotel_agent.py` with a new port, add the port to `run_agents.py` and `AGENT_URLS` in `orchestrator.py`. Nothing else changes.
- **Real flights**: replace the body of `search_flights` with an Amadeus/Skyscanner call.
- **Different model**: set `OPENAI_MODEL` in `.env`.

## Simplifications (on purpose)
- Minimal hand-written A2A (no streaming, no long-running task states, no auth). The official `a2a-sdk` adds these; the concepts above stay the same.
- Each request starts the agent's MCP server as a subprocess — simple, a bit slow. A production system would keep it running.
- Flight data is sample data.
