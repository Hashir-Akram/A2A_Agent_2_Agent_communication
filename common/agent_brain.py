"""
The "brain" of every specialist agent.

Flow (this is the whole idea of an agent with tools):
    1. Ask the MCP server which tools it has.
    2. Give those tools to the LLM.
    3. If the LLM wants a tool -> call it on the MCP server, give the result back.
    4. Repeat until the LLM answers in plain text.
"""
import json
from fastmcp import Client
from common.llm import client, MODEL


async def run_agent_with_mcp(system_prompt: str, user_text: str, mcp_script: str) -> str:
    # Client("file.py") starts that MCP server as a subprocess (stdio) for us.
    async with Client(mcp_script) as mcp:
        # Step 1: discover tools and convert them to OpenAI's "function" format
        mcp_tools = await mcp.list_tools()
        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description or "",
                    "parameters": t.inputSchema,
                },
            }
            for t in mcp_tools
        ]

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ]

        for _ in range(5):  # safety limit on tool-call rounds
            # Step 2: ask the LLM
            resp = await client.chat.completions.create(
                model=MODEL, messages=messages, tools=openai_tools
            )
            msg = resp.choices[0].message

            # Step 4: no tool wanted -> this is the final answer
            if not msg.tool_calls:
                return msg.content or ""

            # Step 3: run every requested tool on the MCP server
            messages.append(msg)
            for call in msg.tool_calls:
                args = json.loads(call.function.arguments or "{}")
                print(f"   [MCP] {call.function.name}({args})")
                result = await mcp.call_tool(call.function.name, args)
                text = "\n".join(c.text for c in result.content if hasattr(c, "text"))
                messages.append(
                    {"role": "tool", "tool_call_id": call.id, "content": text}
                )
    return "Sorry, I could not finish the task."
