"""Starts the 3 specialist agents (each is its own server/process)."""
import subprocess
import sys
import time

AGENTS = ["weather_agent", "hotel_agent", "flight_agent"]
procs = [subprocess.Popen([sys.executable, "-m", f"agents.{a}"]) for a in AGENTS]
print("Agents running on ports 8001 (weather), 8002 (hotel), 8003 (flight). Ctrl+C to stop.")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    for p in procs:
        p.terminate()
