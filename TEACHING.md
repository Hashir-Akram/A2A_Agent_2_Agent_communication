# Teaching Guide: Build the A2A + MCP Travel Planner Step by Step

**Audience:** students who know basic Python. **Total time:** about 2 hours (7 steps, ~15 min each).
**Rule of the session:** after *every* step, run a test. Never add a file until the previous one works.

## The golden story to tell first (5 min, no code)

Draw this on the board and keep it visible all session:

```
User -> Orchestrator --A2A--> Agent --MCP--> Tool/API/DB
```

| Question | Answer |
|---|---|
| What is **MCP**? | How *one agent* talks to its **tools** (APIs, databases). |
| What is **A2A**? | How *one agent* talks to **another agent**. |
| Who thinks? | The LLM (OpenAI), inside the orchestrator and inside every agent. |

One-liner for students: **"MCP gives an agent hands. A2A lets agents talk to each other."**

We build **bottom-up**: tool → agent brain → A2A wrapper → more agents → orchestrator.
Students see something working in minute 15, not minute 90.

## The final folder structure (show this before coding)

```
a2a-travel/
|-- .venv/                  your virtual environment (not committed)
|-- .env                    secrets: OPENAI_API_KEY (not committed)
|-- requirements.txt
|-- run_agents.py           Step 5  - starts all agents
|-- orchestrator.py         Step 6  - the A2A client you chat with
|-- common/                 code SHARED by every agent
|   |-- __init__.py
|   |-- llm.py              Step 1  - OpenAI client
|   |-- agent_brain.py      Step 3  - LLM + MCP tool loop
|   `-- a2a_server.py       Step 4  - generic A2A server
|-- mcp_servers/            the TOOLS (MCP side)
|   |-- flights_mcp.py      Step 2
|   |-- hotel_mcp.py        Step 5  (creates hotels.db automatically)
|   `-- weather_mcp.py      Step 5
`-- agents/                 the A2A servers (one tiny file each)
    |-- __init__.py
    |-- flight_agent.py     Step 4  (port 8003)
    |-- hotel_agent.py      Step 5  (port 8002)
    `-- weather_agent.py    Step 5  (port 8001)
```

**Why these folders? (explain in one minute)**
- `common/`: logic written once and reused by every agent, so adding an agent never copies code.
- `mcp_servers/`: the **MCP side**. Only tools live here, with no LLM and no web server.
- `agents/`: the **A2A side**. Each file just says who the agent is and which MCP script it uses.
- Top level: the two things you *run* (`run_agents.py`, `orchestrator.py`).

Keeping MCP and A2A in separate folders makes the two protocols visible in the file layout.

---

## What we will build (the file map)

| Step | File(s) created | What students learn |
|---|---|---|
| 1 | `requirements.txt`, `.env`, `common/llm.py` | Setup + one LLM call |
| 2 | `mcp_servers/flights_mcp.py` | An MCP tool is a Python function |
| 3 | `common/agent_brain.py` | Agent = LLM + tool loop |
| 4 | `common/a2a_server.py`, `agents/flight_agent.py` | A2A: Agent Card + `message/send` |
| 5 | hotel + weather MCP servers and agents, `run_agents.py` | Same pattern, repeated |
| 6 | `orchestrator.py` | Agents become tools of the orchestrator |
| 7 | Edit the orchestrator | Memory + prompt rules (real bugs we hit) |

Final code for every file is in this repo. Students type the files themselves, and you use the repo as the answer key.

---

## Step 1 – Project setup (10 min)

**Concept:** nothing agentic yet, just get a working environment and prove the LLM answers.

```powershell
mkdir a2a-travel; cd a2a-travel
python -m venv .venv
.venv\Scripts\activate
```

Create the three folders now (empty is fine), so students *see* the architecture before writing any code:
```powershell
mkdir common, mcp_servers, agents
New-Item common\__init__.py, agents\__init__.py -ItemType File
```
`__init__.py` turns a folder into a Python package. Without it, `from common.llm import ...` fails with "No module named common".

Create `requirements.txt` (fastapi, uvicorn, httpx, openai, fastmcp, python-dotenv), then:
```powershell
pip install -r requirements.txt
```
Create `.env` (never commit this file): `OPENAI_API_KEY=sk-...` and `OPENAI_MODEL=gpt-4o-mini`.

Create `common/llm.py`:
- load `.env`, create one `AsyncOpenAI()` client, export `client` and `MODEL`.
- (Windows) the 3 lines that set stdout to UTF-8, so the ₹ symbol doesn't crash the console.

**Test it** (the "hello world"):
```powershell
python -c "import asyncio; from common.llm import client, MODEL; print(asyncio.run(client.chat.completions.create(model=MODEL, messages=[{'role':'user','content':'Say hi'}])).choices[0].message.content)"
```
**Pass:** a greeting prints. **Common failure:** `OPENAI_API_KEY` missing → check `.env` is in the project root.

---

## Step 2 – The first MCP tool (15 min)

**Concept:** a tool is just a function with a docstring. The docstring is how the LLM decides *when* to use it.

Create `mcp_servers/flights_mcp.py`:
- `mcp = FastMCP("flights")`, a small `FLIGHTS` list, one `@mcp.tool` function `search_flights(origin, destination)`, and `mcp.run()` under `if __name__ == "__main__"`.
- Start with fake data on purpose. Say: "Real APIs need keys. Swapping later changes one function."

**Test it** by acting as an MCP client, with no LLM involved:
```powershell
python -c "import asyncio; from fastmcp import Client
async def t():
    async with Client('mcp_servers/flights_mcp.py') as c:
        print([x.name for x in await c.list_tools()])
        print((await c.call_tool('search_flights', {'origin':'Mumbai','destination':'Goa'})).content[0].text)
asyncio.run(t())"
```
**Pass:** `['search_flights']` then a list of flights.
**Teaching moment:** `Client('file.py')` launches the server as a subprocess. That is MCP over *stdio*.

---

## Step 3 – Agent brain: LLM + tools (20 min)  ← the most important step

**Concept:** an agent is a loop. Write the 4 steps as comments first, and have students fill in the code.

Create `common/agent_brain.py` with `run_agent_with_mcp(system_prompt, user_text, mcp_script)`:
1. Open the MCP client, `list_tools()`, convert each to OpenAI's `{"type":"function", ...}` format.
2. Call the LLM with the messages + tools.
3. If `msg.tool_calls` → run each with `mcp.call_tool(...)`, append a `role: "tool"` message with the result.
4. Loop; when there are no tool calls, return `msg.content`. (Cap the loop at 5 rounds.)

**Test it**, still no A2A:
```powershell
python -c "import asyncio; from common.agent_brain import run_agent_with_mcp
print(asyncio.run(run_agent_with_mcp('You are a flight assistant.', 'Cheapest flight Mumbai to Goa?', 'mcp_servers/flights_mcp.py')))"
```
**Pass:** console shows `[MCP] search_flights(...)` and then a natural-language answer.
**Teaching moment:** ask students "who decided to call the tool?" → the LLM, not our code.

---

## Step 4 – Wrap the agent in A2A (20 min)

**Concept:** A2A needs only two things: an **Agent Card** (discovery) and **`message/send`** (do a task).

**Expect this question: "Is this where we create the agent?"** No. The agent was already built in Step 3
(LLM + tools). A2A does not create agents and has no `create_agent` like LangChain. It *exposes* an existing
agent so others can find and call it, which is why our function is named `expose_as_a2a_agent`.
Say: *"Step 3 builds the person. Step 4 gives them a phone number."*

Create `common/a2a_server.py` with `expose_as_a2a_agent(...)` returning a FastAPI app:
- `GET /.well-known/agent.json` → the card (name, description, url, skills).
- `POST /` → check `method == "message/send"`, pull text out of `params.message.parts`, call `run_agent_with_mcp`, return the JSON-RPC result with `parts: [{kind:"text", text: answer}]`.
- A `serve(app, port)` helper using uvicorn.

Create `agents/flight_agent.py` (~10 lines: name, description, skills, port 8003, system prompt, path to the MCP script).

**Run and test** (two terminals):
```powershell
python -m agents.flight_agent
```
```powershell
Invoke-RestMethod http://localhost:8003/.well-known/agent.json
$body = '{"jsonrpc":"2.0","id":"1","method":"message/send","params":{"message":{"role":"user","messageId":"m1","parts":[{"kind":"text","text":"Flights from Delhi to Goa?"}]}}}'
Invoke-RestMethod http://localhost:8003/ -Method Post -ContentType "application/json" -Body $body
```
**Pass:** the card prints, then a JSON reply with the flight answer.
**Teaching moment:** the agent is now just a web service. *Any* A2A client could call it, not only ours.

---

## Step 5 – Two more agents by copy-paste (15 min)

**Concept:** the pattern is the product. New agent = new MCP script + 10-line agent file.

1. `mcp_servers/hotel_mcp.py`: SQLite DB created and seeded on first use; `search_hotels(city, max_price_per_night)`. Port 8002 in `agents/hotel_agent.py`.
2. `mcp_servers/weather_mcp.py`: real Open-Meteo calls (geocode, then forecast). Port 8001 in `agents/weather_agent.py`.
3. `run_agents.py`: starts all three with `subprocess.Popen([sys.executable, "-m", "agents.xxx"])`.

**Test:** `python run_agents.py`, then call each agent's card URL (8001, 8002, 8003).
**Teaching moment (weather):** ask the weather agent about "Goa". The geocoder returns Genoa, Italy. This shows why tools need guardrails (country filter + alias), a real-world lesson.

---

## Step 6 – The Orchestrator (25 min)

**Concept:** the orchestrator treats **agents exactly like tools**. This is the trick that keeps the code small.

Create `orchestrator.py` in 4 functions, one at a time:
1. `discover_agents()`: GET each `/.well-known/agent.json`, store by name.
2. `agents_to_tools()`: each card becomes an OpenAI function (`ask_hotel_agent`, ...) with one `request` string parameter. The card's `description` becomes the tool description.
3. `send_a2a(url, text)`: POST the `message/send` JSON-RPC, return `result.parts[0].text`.
4. `plan_trip()` + `main()`: same loop as Step 3, except a "tool call" now means `send_a2a`. Use `asyncio.gather` so the 3 agents run **in parallel**.

**Run:** agents in terminal 1, `python orchestrator.py` in terminal 2.
Try: `Plan my Goa trip from Mumbai next week, hotels under 5000 per night`.
**Pass:** logs show three `[A2A] ->` lines, and agent terminals show `[MCP] ...` lines.

Point at the two terminals and narrate the path: **User → Orchestrator → (A2A) → Agent → (MCP) → Tool.** This is the payoff moment.

---

## Step 7 – Make it feel real: memory + prompt rules (15 min)

Do this **live as a debugging story**. Our first version failed in front of a real user.

1. **Bug: it keeps asking the same questions.** Run the first version with "10th Dec" → "Bangalore to Goa" → "yes".
   Cause: `plan_trip` built a new `messages` list every turn.
   Fix: keep one `history` list in `main()` and pass it in. (The LLM has no memory except what you send.)
2. **Bug: it over-asks.** The system prompt said "ask if details are missing". Rewrite it with rules: call the agents once origin and destination are known, assume defaults, ask at most once.
3. **Bug: it pretends to book.** "yes" made it say it booked a flight, but no agent has a booking tool. Add the rule: "you can only search and plan".

**Teaching moment:** most agent quality comes from the **system prompt and the tools you give**, not from fancy code.

---

## Wrap-up exercises (homework or a lab)

1. **Easy:** add a **Restaurant Agent** (`food_mcp.py`, port 8004). Add its URL to `AGENT_URLS` and `run_agents.py`. Nothing else should change. If it works, students understand the architecture.
2. **Medium:** replace the fake flights with a real API (e.g. Amadeus sandbox).
3. **Medium:** add a second tool to the hotel MCP (`get_hotel_details`). Does the agent use it automatically?
4. **Hard:** add a `book_hotel` tool that writes to SQLite. Discuss why you'd ask the user to confirm first.
5. **Hard:** move to the official `a2a-sdk` and compare the code size.

## Quick quiz for the end
1. Which protocol connects agent → database? (MCP)
2. Which connects orchestrator → agent? (A2A)
3. What URL does an A2A client read first to discover an agent? (`/.well-known/agent.json`)
4. Why did "yes" confuse the first orchestrator? (no conversation history)
5. How does the orchestrator know what the Hotel Agent can do? (its Agent Card description)

## Instructor tips
- **Pre-class:** have every student run Step 1's hello-world test before the session. Most delays come from API keys and venv issues.
- **Cost:** `gpt-4o-mini` keeps a whole class session to a few cents per student.
- **Run from the project root:** always run `python ...` commands from `a2a-travel/` (the folder containing `common/`), or imports break. Agents run as modules: `python -m agents.flight_agent`.
- **Windows:** always activate the venv in *each* new terminal. This is the #1 "module not found" cause.
- **Ports busy (`10048`):** an old agent is still running. Close that terminal or stop the old Python process.
- **Weather returns nothing for far-off dates:** Open-Meteo forecasts only about 16 days ahead. Use a date within two weeks for the demo.
- **Show, don't tell:** keep two terminals visible (agents + orchestrator) so students watch the A2A and MCP logs scroll.
- **Optional:** tag each step in git (`git tag step-1` ... `step-7`) so a student who falls behind can `git checkout step-N`.
