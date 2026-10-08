from pathlib import Path
from common.a2a_server import expose_as_a2a_agent, serve

PORT = 8003
app = expose_as_a2a_agent(
    name="Flight Agent",
    description="Finds flights between two cities.",
    skills=[{"id": "flight_search", "name": "Flight search",
             "description": "Search flights between an origin and destination city"}],
    port=PORT,
    system_prompt="You are a flight assistant. Use your tool to find flights and suggest the best option.",
    mcp_script=str(Path(__file__).parent.parent / "mcp_servers" / "flights_mcp.py"),
)

if __name__ == "__main__":
    serve(app, PORT)
