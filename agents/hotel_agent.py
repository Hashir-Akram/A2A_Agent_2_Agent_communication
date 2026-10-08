from pathlib import Path
from common.a2a_server import create_agent_app, serve

PORT = 8002
app = create_agent_app(
    name="Hotel Agent",
    description="Finds hotels in a city within a budget.",
    skills=[{"id": "hotel_search", "name": "Hotel search",
             "description": "Search hotels by city and max price per night (INR)"}],
    port=PORT,
    system_prompt="You are a hotel assistant. Use your tool to find hotels and recommend the best one.",
    mcp_script=str(Path(__file__).parent.parent / "mcp_servers" / "hotel_mcp.py"),
)

if __name__ == "__main__":
    serve(app, PORT)
