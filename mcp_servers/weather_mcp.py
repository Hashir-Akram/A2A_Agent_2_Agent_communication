"""Weather MCP server: real data from Open-Meteo (free, no API key)."""
import httpx
from fastmcp import FastMCP

mcp = FastMCP("weather")
ALIASES = {"goa": "Panaji"}


@mcp.tool
def get_forecast(city: str, days: int = 3, country_code: str = "IN") -> str:
    """Get the daily weather forecast for a city (max 7 days).
    country_code is the 2-letter ISO code (default IN = India)."""
    city = ALIASES.get(city.lower(), city)  # the geocoder knows Panaji, not the state "Goa"
    geo = httpx.get("https://geocoding-api.open-meteo.com/v1/search",
                    params={"name": city, "count": 10}, timeout=15).json()
    results = geo.get("results") or []
    if not results:
        return f"City '{city}' not found."
    # Prefer a match in the requested country, otherwise take the first result
    place = next((r for r in results if r.get("country_code") == country_code.upper()), results[0])

    data = httpx.get("https://api.open-meteo.com/v1/forecast", params={
        "latitude": place["latitude"], "longitude": place["longitude"],
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "forecast_days": min(days, 7), "timezone": "auto",
    }, timeout=15).json()["daily"]

    lines = [f"Forecast for {place['name']}, {place.get('country', '')}:"]
    for i, day in enumerate(data["time"]):
        lines.append(f"{day}: {data['temperature_2m_min'][i]} to {data['temperature_2m_max'][i]} C, "
                     f"rain {data['precipitation_sum'][i]} mm")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()  # stdio
