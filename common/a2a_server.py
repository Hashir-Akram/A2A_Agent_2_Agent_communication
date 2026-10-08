"""
A minimal A2A *server* (the "Weather Agent" etc. boxes in the diagram).

A2A needs only two things from an agent:
    1. An Agent Card   -> GET  /.well-known/agent.json   ("who am I, what can I do?")
    2. A task endpoint -> POST /   JSON-RPC method "message/send"

Every specialist agent is just this server + a system prompt + an MCP script.

NOTE: A2A does not *create* an agent. The agent (LLM + tools) is built in
common/agent_brain.py. This file only EXPOSES that agent so others can discover
and call it. Think "give the agent a phone number", not "create the agent".
"""
import uuid
import uvicorn
from fastapi import FastAPI
from common.agent_brain import run_agent_with_mcp


def expose_as_a2a_agent(name, description, skills, port, system_prompt, mcp_script):
    app = FastAPI(title=name)

    # 1. Agent Card: the orchestrator reads this to discover the agent
    agent_card = {
        "name": name,
        "description": description,
        "url": f"http://localhost:{port}/",
        "version": "1.0.0",
        "capabilities": {"streaming": False},
        "defaultInputModes": ["text"],
        "defaultOutputModes": ["text"],
        "skills": skills,
    }

    @app.get("/.well-known/agent.json")
    async def card():
        return agent_card

    # 2. Task endpoint: JSON-RPC 2.0
    @app.post("/")
    async def handle(request: dict):
        if request.get("method") != "message/send":
            return {"jsonrpc": "2.0", "id": request.get("id"),
                    "error": {"code": -32601, "message": "Method not found"}}

        parts = request["params"]["message"]["parts"]
        user_text = " ".join(p["text"] for p in parts if p.get("kind") == "text")
        print(f"[{name}] received: {user_text}")

        answer = await run_agent_with_mcp(system_prompt, user_text, mcp_script)

        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "kind": "message",
                "role": "agent",
                "messageId": str(uuid.uuid4()),
                "parts": [{"kind": "text", "text": answer}],
            },
        }

    return app


def serve(app, port):
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
