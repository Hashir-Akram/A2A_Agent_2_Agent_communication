"""One shared OpenAI client + .env loading."""
import os
import sys
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
client = AsyncOpenAI()  # reads OPENAI_API_KEY from the environment

# Windows consoles default to cp1252 and crash on symbols like the rupee sign.
for _stream in (sys.stdout, sys.stderr):
    _stream.reconfigure(encoding="utf-8", errors="replace")
