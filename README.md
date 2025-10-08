# Obsidian Diary MCP Server

AI-powered journaling with local processing, automatic backlinks, and smart prompts.
## Features

- AI-generated reflection prompts based on past 3 calendar days
- Day citations with automatic `[[YYYY-MM-DD]]` backlinks
- Brain dump prioritization (analyzes your writing, not prompts)
- Smart `#tag` extraction using theme similarity
- Todo extraction to organized checklists
- Memory trace analysis with theme evolution
- Sunday synthesis (weekly reflection prompts)

## Requirements

- **uv** (Python package manager)
- **Ollama** (llama3.1 or compatible model)
- **MCP client** (e.g., GitHub Copilot CLI)
- **Obsidian vault** (for markdown files)

## Setup

**1. Clone and install:**
```bash
git clone https://github.com/madebygps/obsidian-diary-mcp.git
```
```bash
cd obsidian-diary-mcp
```
```bash
uv sync
```
```bash
chmod +x start-server.sh
```

**2. Configure:**
```bash
cp .env.example .env
```
Edit `.env`: set `DIARY_PATH` and `PLANNER_PATH` (required)

**3. Add to MCP client config (e.g., GitHub Copilot CLI):**
- Name: `diary`
- Command: `/full/path/to/obsidian-diary-mcp/start-server.sh`


**Configuration (.env):**

Required: `DIARY_PATH`, `PLANNER_PATH`

Optional: `OLLAMA_MODEL` (default: llama3.1:latest), `OLLAMA_TIMEOUT` (60s), `OLLAMA_TEMPERATURE` (0.7), `OLLAMA_NUM_PREDICT` (1000 tokens)


## Usage

1. **Create:** `"create a memory log for today"` → AI prompts based on past 3 days
2. **Write:** Open in Obsidian, write freely in Brain Dump section
3. **Extract:** `"extract todos from today's entry"` → Action items to planner
4. **Link:** `"link today's memory log"` → Auto-generates `[[YYYY-MM-DD]]` & `#tags`
5. **Explore:** Use Obsidian's backlinks panel and graph view

**More Commands:** `"show themes from last week"`, `"create memory trace for 30 days"`, `"refresh memory links for 30 days"`

## Debugging

Logs in `logs/` directory: `server-YYYY-MM-DD.log` (protocol), `debug-YYYY-MM-DD.log` (operations)

```bash
tail -f logs/debug-$(date +%Y-%m-%d).log  # Watch in real-time
grep ERROR logs/debug-*.log                # Find errors
grep "similarity" logs/debug-*.log         # Debug backlinks
```

## Troubleshooting

**Server issues:** Check `.env` exists with `DIARY_PATH` and `PLANNER_PATH` set. Run `./start-server.sh` directly to test.

**Ollama issues:** Verify running with `curl http://localhost:11434/api/tags`. Pull model: `ollama pull llama3.1:latest`

**No backlinks:** Need 2+ entries with similar themes (>8% overlap). Ensure Brain Dump section has substantial content (>50 chars). Check: `grep "Brain Dump" logs/debug-*.log`

**Timeouts:** Increase `OLLAMA_TIMEOUT` (90+) and `OLLAMA_NUM_PREDICT` (2000+) for reasoning models.


## How It Works

- **Local AI**: Ollama processes entries locally—content never leaves your machine
- **Calendar-Based**: Analyzes past 3 calendar days (not just last 3 entries)
- **Brain Dump Focus**: Prioritizes your writing over answered prompts for themes
- **Day Citations**: AI cites `[Day 1]`/`[Day 2]` → converts to `[[2025-10-07]]` backlinks
- **Smart Linking**: Jaccard similarity connects entries with >8% theme overlap
- **Sundays**: 5 weekly synthesis prompts (vs 3 daily)
- **Todo Extraction**: AI identifies action items from brain dumps


## Entry Format

Each entry (`YYYY-MM-DD.md`) has plain text headers:
```markdown
## Reflection Prompts
**1. Question with [[2025-10-06]] backlink (reason)...**

---

## Brain Dump
Your thoughts, experiences, observations...

---

## Memory Links
**Temporal connections:** [[2025-10-05]] • [[2025-10-04]]
**Topic tags:** #career-growth #self-reflection
```

## License

MIT • Python 3.13+ • FastMCP 2.12.4+ • Ollama