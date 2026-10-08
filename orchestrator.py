"""
Orchestrator = the A2A *client* (the green box in the diagram).

Flow:
    1. DISCOVER : read each agent's Agent Card.
    2. TOOLS    : turn every agent into one LLM tool ("ask_weather_agent", ...).
    3. PLAN     : the LLM decides which agents to call (it can call several).
    4. DELEGATE : send each request to the agent via A2A (JSON-RPC message/send).
    5. ANSWER   : the LLM combines all replies into one trip plan.
"""
import asyncio
import json
import uuid
import httpx
from common.llm import client, MODEL

AGENT_URLS = ["http://localhost:8001", "http://localhost:8002", "http://localhost:8003"]

SYSTEM = """You are a travel planning orchestrator. You cannot look up data yourself:
delegate to your specialist agents (weather, hotels, flights), then combine
their answers into a clear trip plan.

Rules:
- Use the whole conversation: details the user gave earlier still apply.
  A short reply like 'yes' or '10th dec' answers your previous question.
- As soon as you know the origin and destination, CALL THE AGENTS. Do not ask for
  confirmation. If something minor is missing (dates, hotel type), assume a sensible
  default, say so, and continue.
- Ask a question only if the origin or destination is truly unknown, and ask once.
- Fix typos in city names (Banglore -> Bangalore).
- Hotel budget is per night in INR unless the user says otherwise.
- You and your agents can only SEARCH and PLAN. Nobody can book anything. Never claim to book;
  if the user says 'yes' or 'book it', explain that and offer to adjust the plan instead."""


async def discover_agents():
    """Step 1: fetch Agent Cards."""
    agents = {}
    async with httpx.AsyncClient() as http:
        for url in AGENT_URLS:
            card = (await http.get(f"{url}/.well-known/agent.json")).json()
            key = "ask_" + card["name"].lower().replace(" ", "_")
            agents[key] = {"url": card["url"], "card": card}
            print(f"  discovered: {card['name']} @ {card['url']}")
    return agents


def agents_to_tools(agents):
    """Step 2: one OpenAI tool per agent, described by its Agent Card."""
    return [{
        "type": "function",
        "function": {
            "name": key,
            "description": a["card"]["description"],
            "parameters": {
                "type": "object",
                "properties": {"request": {"type": "string",
                                           "description": "Natural-language task for this agent"}},
                "required": ["request"],
            },
        },
    } for key, a in agents.items()]


async def send_a2a(url, text):
    """Step 4: the actual A2A call."""
    payload = {
        "jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": "message/send",
        "params": {"message": {"role": "user", "messageId": str(uuid.uuid4()),
                               "parts": [{"kind": "text", "text": text}]}},
    }
    async with httpx.AsyncClient(timeout=120) as http:
        data = (await http.post(url, json=payload)).json()
    return data["result"]["parts"][0]["text"]


async def plan_trip(messages, user_text, agents, tools):
    """`messages` is the running chat history, so the orchestrator remembers earlier turns."""
    messages.append({"role": "user", "content": user_text})
    for _ in range(5):
        resp = await client.chat.completions.create(model=MODEL, messages=messages, tools=tools)
        msg = resp.choices[0].message
        if not msg.tool_calls:
            messages.append({"role": "assistant", "content": msg.content})
            return msg.content  # Step 5: final answer
        messages.append(msg)

        # Step 3/4: run all requested agent calls in parallel
        async def delegate(call):
            req = json.loads(call.function.arguments)["request"]
            print(f"  [A2A] -> {call.function.name}: {req}")
            return await send_a2a(agents[call.function.name]["url"], req)

        results = await asyncio.gather(*(delegate(c) for c in msg.tool_calls))
        for call, result in zip(msg.tool_calls, results):
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
    return "Could not complete the plan."


async def main():
    print("Discovering agents...")
    agents = await discover_agents()
    tools = agents_to_tools(agents)
    print("\nTravel Orchestrator ready. Try: Plan my Goa trip from Mumbai, budget Rs 5000/night. (quit to exit)")
    history = [{"role": "system", "content": SYSTEM}]
    while True:
        text = input("\nYou: ").strip()
        if text.lower() in ("quit", "exit"):
            break
        print("\nAssistant:", await plan_trip(history, text, agents, tools))


if __name__ == "__main__":
    asyncio.run(main())
