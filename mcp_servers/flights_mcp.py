"""
Flights MCP server.
Real flight APIs need paid keys, so this uses a small fake dataset.
To go real later: replace the body of search_flights with a call to
Amadeus / Skyscanner / etc. -- nothing else in the project changes.
"""
from fastmcp import FastMCP

mcp = FastMCP("flights")

FLIGHTS = [
    {"from": "Mumbai", "to": "Goa", "airline": "IndiGo", "depart": "07:15", "price": 3800},
    {"from": "Mumbai", "to": "Goa", "airline": "Air India", "depart": "13:40", "price": 5200},
    {"from": "Delhi", "to": "Goa", "airline": "Vistara", "depart": "09:00", "price": 7400},
    {"from": "Delhi", "to": "Goa", "airline": "IndiGo", "depart": "18:30", "price": 6100},
    {"from": "Bangalore", "to": "Goa", "airline": "Akasa", "depart": "11:20", "price": 3300},
    {"from": "Hyderabad", "to": "Goa", "airline": "IndiGo", "depart": "06:45", "price": 3600},
]


@mcp.tool
def search_flights(origin: str, destination: str) -> str:
    """Search flights between two cities, cheapest first."""
    hits = [f for f in FLIGHTS
            if f["from"].lower() == origin.lower() and f["to"].lower() == destination.lower()]
    if not hits:
        return f"No flights found from {origin} to {destination}."
    hits.sort(key=lambda f: f["price"])
    return "\n".join(f"{f['airline']} departs {f['depart']} - Rs {f['price']}" for f in hits)


if __name__ == "__main__":
    mcp.run()
