"""Configuration settings for the Obsidian Diary MCP server."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

diary_path_env = os.getenv("DIARY_PATH")
planner_path_env = os.getenv("PLANNER_PATH")

if not diary_path_env:
    print("[CONFIG ERROR] DIARY_PATH must be set in .env file", file=sys.stderr)
    sys.exit(1)

if not planner_path_env:
    print("[CONFIG ERROR] PLANNER_PATH must be set in .env file", file=sys.stderr)
    sys.exit(1)

print(f"[CONFIG] DIARY_PATH: {diary_path_env}", file=sys.stderr)
print(f"[CONFIG] PLANNER_PATH: {planner_path_env}", file=sys.stderr)

DIARY_PATH = Path(diary_path_env)
PLANNER_PATH = Path(planner_path_env)
RECENT_ENTRIES_COUNT = int(os.getenv("RECENT_ENTRIES_COUNT", "3"))

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:latest")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "60"))
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "1000"))