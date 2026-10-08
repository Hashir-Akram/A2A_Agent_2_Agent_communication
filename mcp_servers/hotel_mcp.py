"""Hotel MCP server: tools on top of a small SQLite database (the 'Hotel DB')."""
import sqlite3
from pathlib import Path
from fastmcp import FastMCP

mcp = FastMCP("hotels")
DB = Path(__file__).parent / "hotels.db"


def _db():
    first_time = not DB.exists()
    conn = sqlite3.connect(DB)
    if first_time:  # create + seed demo data
        conn.execute("CREATE TABLE hotels (name TEXT, city TEXT, price_per_night INT, rating REAL, area TEXT)")
        conn.executemany("INSERT INTO hotels VALUES (?,?,?,?,?)", [
            ("Sea Breeze Resort", "Goa", 4500, 4.3, "Calangute"),
            ("Palm Grove Inn", "Goa", 2200, 3.9, "Anjuna"),
            ("Lotus Beach Villas", "Goa", 7800, 4.7, "Palolem"),
            ("Budget Backpackers", "Goa", 900, 3.5, "Baga"),
            ("Marina Bay Hotel", "Mumbai", 6000, 4.4, "Colaba"),
            ("City Stay", "Delhi", 3000, 4.0, "Connaught Place"),
        ])
        conn.commit()
    return conn


@mcp.tool
def search_hotels(city: str, max_price_per_night: int = 100000) -> str:
    """Find hotels in a city under a maximum price per night (INR), best rated first."""
    rows = _db().execute(
        "SELECT name, area, price_per_night, rating FROM hotels "
        "WHERE lower(city)=lower(?) AND price_per_night<=? ORDER BY rating DESC",
        (city, max_price_per_night)).fetchall()
    if not rows:
        return "No hotels found."
    return "\n".join(f"{n} ({a}) - Rs {p}/night - rating {r}" for n, a, p, r in rows)


if __name__ == "__main__":
    mcp.run()
