from pathlib import Path
from common.a2a_server import create_agent_app, serve

PORT = 8001
app = create_agent_app(
    name="Weather Agent",
    description="Gives weather forecasts for any city.",
    skills=[{"id": "forecast", "name": "Weather forecast",
             "description": "Daily temperature and rain forecast for a city"}],
    port=PORT,
    system_prompt="You are a weather assistant. Use your tool for real data, then answer briefly.",
    mcp_script=str(Path(__file__).parent.parent / "mcp_servers" / "weather_mcp.py"),
)

if __name__ == "__main__":
    serve(app, PORT)
