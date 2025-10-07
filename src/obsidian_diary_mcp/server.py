from datetime import datetime, timedelta
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from .config import PLANNER_PATH, DIARY_PATH
from .ollama_client import initialize_ollama
from .entry_manager import entry_manager
from .analysis import analysis_engine
from .template_generator import template_generator
from .logger import server_logger

mcp = FastMCP("obsidian-diary")

server_logger.info(f"📁 Diary Path: {DIARY_PATH}")
server_logger.info(f"📋 Planner Path: {PLANNER_PATH}")

initialize_ollama()


@mcp.tool(
    annotations={
        "title": "Preview Memory Log Template",
        "readOnlyHint": True,
        "openWorldHint": False
    }
)
async def create_diary_template(
    date: Annotated[str, "REQUIRED: Current date in YYYY-MM-DD format. For 'today', pass the current system date like '2025-10-07'"],
    focus: Annotated[str | None, "Optional focus area (e.g., 'current struggles', 'cognitive patterns')"] = None
) -> str:
    """Create a sophisticated diary template with intellectually rigorous prompts for deep cognitive exploration."""
    try:
        entry_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return "Error: Date must be in YYYY-MM-DD format"

    if entry_manager.entry_exists(entry_date):
        return f"Memory log for {date} already exists. Use read_diary_entry to view it."

    return await template_generator.generate_template_content(entry_date, date, focus)


@mcp.tool(
    annotations={
        "title": "Create New Memory Log",
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def create_diary_entry_file(
    date: Annotated[str, "REQUIRED: Current date in YYYY-MM-DD format. For 'today', pass the current system date like '2025-10-07'"],
    focus: Annotated[str | None, "Optional focus area (e.g., 'current struggles', 'cognitive patterns')"] = None
) -> str:
    """Create a sophisticated diary entry file with AI-generated analytical prompts for deep intellectual exploration."""
    try:
        entry_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return "Error: Date must be in YYYY-MM-DD format"

    file_path = entry_manager.get_entry_path(entry_date)

    if entry_manager.entry_exists(entry_date):
        return f"Memory log for {date} already exists at {file_path}"

    template_content = await template_generator.generate_template_content(entry_date, date, focus)

    if entry_manager.write_entry(file_path, template_content):
        return f"🧠 Created memory log: {file_path}\n\nExplore the prompts, then use 'complete_diary_entry' when done to auto-generate memory links!"
    else:
        return "Error creating file: Permission denied or I/O error"


@mcp.tool(
    annotations={
        "title": "Complete & Link Memory Log",
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def complete_diary_entry(
    date: Annotated[str, "REQUIRED: Current date in YYYY-MM-DD format. For 'today', pass the current system date like '2025-10-07'"]
) -> str:
    """Complete your diary entry - automatically generates Obsidian-compatible memory links and provides cognitive analysis.
    Use this when you're done writing. Creates [[YYYY-MM-DD]] backlinks that integrate with Obsidian's backlink system.
    """
    try:
        entry_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return "Error: Date must be in YYYY-MM-DD format"

    file_path = entry_manager.get_entry_path(entry_date)

    if not entry_manager.entry_exists(entry_date):
        return f"No memory log found for {date}. Create one first."

    content = entry_manager.read_entry(file_path)
    related = await analysis_engine.find_related_entries(content, exclude_date=date)

    themes = await analysis_engine.extract_themes_and_topics(content)
    topic_tags = analysis_engine.generate_topic_tags(themes)
    
    content = entry_manager.add_memory_links(content, related, topic_tags)

    if entry_manager.write_entry(file_path, content):
        themes_str = ", ".join(themes[:5]) if themes else "philosophical inquiry"
        
        total_entries = len(entry_manager.get_all_entries())
        connection_percentage = (len(related) / max(total_entries - 1, 1)) * 100 if related else 0
        
        connection_parts = [f"{len(related)} temporal"] if related else []
        if topic_tags:
            connection_parts.append(f"{len(topic_tags)} topics")
        
        connections_desc = " + ".join(connection_parts) if connection_parts else "novel territory"
        
        return f"🧠 **Cognitive trace completed** for {date}\n\n🔍 **Analytical themes:** {themes_str}\n🔗 **Memory network:** {connections_desc} ({connection_percentage:.1f}% temporal coverage)\n\n📚 **Integration status:** Your exploration is now woven into Obsidian's knowledge graph!\n\n💡 **Discover more:** Backlinks panel (temporal), Tags panel (topics), Graph view (visual network)"
    else:
        return "Error completing entry: Permission denied or I/O error"


@mcp.tool(
    annotations={
        "title": "Refresh Memory Links",
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def update_entry_backlinks(
    date: Annotated[str, "Date of the entry in YYYY-MM-DD format"]
) -> str:
    """Update the backlinks for an existing diary entry based on its current content."""
    try:
        entry_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return "Error: Date must be in YYYY-MM-DD format"

    file_path = entry_manager.get_entry_path(entry_date)

    if not entry_manager.entry_exists(entry_date):
        return f"No memory log found for {date}"

    content = entry_manager.read_entry(file_path)
    related = await analysis_engine.find_related_entries(content, exclude_date=date)

    themes = await analysis_engine.extract_themes_and_topics(content)
    topic_tags = analysis_engine.generate_topic_tags(themes)
    
    content = entry_manager.add_memory_links(content, related, topic_tags)

    if entry_manager.write_entry(file_path, content):
        connection_types = [f"{len(related)} temporal"] if related else []
        if topic_tags:
            connection_types.append(f"{len(topic_tags)} topic tags")
        
        connections_str = " + ".join(connection_types) if connection_types else "none found"
        
        return (
            f"✅ **Memory links updated** for {date}\n\n🔗 **Connections:** {connections_str}\n\n💡 **Obsidian power:** Use Backlinks panel for temporal connections, Tags panel for topics, Graph view for visual exploration!"
        )
    else:
        return "Error updating entry: Permission denied or I/O error"


@mcp.tool(
    annotations={
        "title": "Bulk Refresh Memory Network",
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def refresh_recent_backlinks(
    days: Annotated[int, Field(ge=1, le=365, description="Number of recent days to update")] = 30
) -> str:
    """Update backlinks for recent diary entries only - much faster than full refresh."""
    entries = entry_manager.get_all_entries()
    if not entries:
        return "No memory logs found to update"

    cutoff_date = datetime.now() - timedelta(days=days)
    recent_entries = [(date, path) for date, path in entries if date >= cutoff_date]
    
    if not recent_entries:
        return f"No memory logs found in the last {days} days"
    
    print(f"🔄 Refreshing backlinks for {len(recent_entries)} entries from last {days} days...")
    
    updated_count = 0
    errors = []
    
    for date, file_path in recent_entries:
        try:
            content = entry_manager.read_entry(file_path)
            
            if content.startswith("Error reading file"):
                errors.append(f"{file_path.stem}: {content}")
                continue
                
            related = await analysis_engine.find_related_entries(content, exclude_date=file_path.stem)
            
            themes = await analysis_engine.extract_themes_and_topics(content)
            topic_tags = analysis_engine.generate_topic_tags(themes)
            
            content = entry_manager.add_memory_links(content, related, topic_tags)
            
            if entry_manager.write_entry(file_path, content):
                updated_count += 1
                print(f"✅ Updated {file_path.stem} ({len(related)} connections)")
            else:
                errors.append(f"{file_path.stem}: Write error")
            
        except Exception as e:
            errors.append(f"{file_path.stem}: {str(e)}")
            print(f"❌ Error: {file_path.stem}: {e}")
    
    result = f"🧠 **Memory network refreshed!**\n\n✅ **Updated:** {updated_count} memory logs from last {days} days"
    
    if errors:
        result += f"\n\n⚠️ **Errors:** {len(errors)} memory logs had issues"
    
    result += "\n\n💡 **Tip:** This is much faster than refreshing all memory logs!"
    return result


@mcp.tool(
    annotations={
        "title": "Read Memory Log",
        "readOnlyHint": True,
        "openWorldHint": False
    }
)
def read_diary_entry(
    date: Annotated[str, "Date of the entry in YYYY-MM-DD format"]
) -> str:
    """Read a specific diary entry by date."""
    try:
        entry_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return "Error: Date must be in YYYY-MM-DD format"

    file_path = entry_manager.get_entry_path(entry_date)

    if not entry_manager.entry_exists(entry_date):
        return f"No memory log found for {date}"

    return entry_manager.read_entry(file_path)


@mcp.tool(
    annotations={
        "title": "List Recent Memory Logs",
        "readOnlyHint": True,
        "openWorldHint": False
    }
)
def list_recent_entries(
    count: Annotated[int, Field(ge=1, le=100, description="Number of recent entries to list")] = 10
) -> str:
    """List your most recent diary entries."""
    entries = entry_manager.get_all_entries()[:count]

    if not entries:
        return "No memory logs found"

    result = [f"📅 Your {len(entries)} most recent memory logs:\n"]
    result.extend(
        f"- {date.strftime('%Y-%m-%d')} ({date.strftime('%A, %B %d, %Y')})"
        for date, path in entries
    )

    return "\n".join(result)


@mcp.tool(
    annotations={
        "title": "Show Recurring Themes",
        "readOnlyHint": True,
        "openWorldHint": False
    }
)
async def show_themes(
    days: Annotated[int, Field(ge=1, le=365, description="Number of recent days to analyze")] = 7
) -> str:
    """Show recurring themes and topics from recent memory logs without exposing diary content."""
    entries = entry_manager.get_all_entries()
    
    if not entries:
        return "No memory logs found"
    
    cutoff_date = datetime.now() - timedelta(days=days)
    recent_entries = [(date, path) for date, path in entries if date >= cutoff_date]
    
    if not recent_entries:
        return f"No memory logs found in the last {days} days"
    
    from collections import Counter
    theme_frequency = Counter()
    
    for date, file_path in recent_entries:
        content = entry_manager.read_entry(file_path)
        if not content.startswith("Error"):
            themes = await analysis_engine.get_themes_cached(content, file_path.stem)
            theme_frequency.update(themes)
    
    if not theme_frequency:
        return f"No themes identified in the last {days} days"
    
    sorted_themes = sorted(theme_frequency.items(), key=lambda x: x[1], reverse=True)
    
    result = [f"🧠 **Recurring themes from the last {days} days** ({len(recent_entries)} entries analyzed):\n"]
    result.extend(
        f"- **{theme}** ({count}× across {(count / len(recent_entries)) * 100:.0f}% of entries)"
        for theme, count in sorted_themes[:15]
    )
    
    if len(sorted_themes) > 15:
        result.append(f"\n_...and {len(sorted_themes) - 15} more themes_")
    
    return "\n".join(result)


@mcp.tool(
    annotations={
        "title": "Create Memory Trace",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def create_memory_trace(
    days: Annotated[int, Field(ge=1, le=365, description="Number of days to analyze (e.g., 30 for last month, 365 for last year)")] = 30,
    save_to_file: Annotated[bool, "Whether to save the memory trace to a file in the diary directory"] = True
) -> str:
    """Generate a comprehensive Memory Trace document analyzing themes, patterns, and connections across your diary entries.
    
    This creates a detailed visualization of your journey including:
    - Timeline overview with key themes
    - Core themes with evolution tracking
    - Relationship maps
    - Pattern recognition
    - Growth trajectories
    - Wisdom extracted from entries
    
    Optionally saves to a markdown file in your diary directory for easy reference in Obsidian.
    """
    from .memory_trace import generate_memory_trace
    
    entries = entry_manager.get_all_entries()
    
    if not entries:
        return "No memory logs found to analyze"
    
    cutoff_date = datetime.now() - timedelta(days=days)
    recent_entries = [(date, path) for date, path in entries if date >= cutoff_date]
    
    if not recent_entries:
        return f"No memory logs found in the last {days} days"
    
    print(f"🧠 Generating Memory Trace for {len(recent_entries)} entries from last {days} days...")
    
    trace_content = await generate_memory_trace(recent_entries, analysis_engine, entry_manager)
    
    if save_to_file:
        trace_filename = f"memory-trace-{datetime.now().strftime('%Y-%m-%d')}.md"
        trace_path = entry_manager.diary_path / trace_filename
        
        if entry_manager.write_entry(trace_path, trace_content):
            return f"✨ **Memory Trace generated!**\n\n📊 Analyzed {len(recent_entries)} entries from the last {days} days\n📁 Saved to: {trace_path}\n\n💡 Open in Obsidian to explore your cognitive patterns, theme evolution, and personal growth trajectory!"
        else:
            return f"✨ Memory Trace generated but couldn't save to file.\n\n{trace_content}"
    else:
        return trace_content


@mcp.tool(
    annotations={
        "title": "Extract Todos from Entry",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def extract_todos(
    date: Annotated[str, "Date of the entry in YYYY-MM-DD format (e.g., '2025-10-07' for today)"]
) -> str:
    """Extract action items and todos from a diary entry and save them to a planner file.
    
    Analyzes the diary entry for the specified date, extracts all action items,
    and creates a markdown file in Documents/planner/ with the todos organized
    for easy review and planning.
    """
    try:
        entry_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return "Error: Date must be in YYYY-MM-DD format"
    
    file_path = entry_manager.get_entry_path(entry_date)
    
    if not entry_manager.entry_exists(entry_date):
        return f"No memory log found for {date}. Create one first."
    
    print(f"📝 Extracting todos from {date}...")
    
    content = entry_manager.read_entry(file_path)
    if content.startswith("Error reading file"):
        return f"Error reading entry: {content}"
    
    todos = await analysis_engine.extract_todos(content)
    
    if not todos:
        return f"No action items found in entry for {date}. Your entry may not contain any explicit tasks or todos."
    
    PLANNER_PATH.mkdir(parents=True, exist_ok=True)
    
    planner_path = PLANNER_PATH / f"todos-{date}.md"
    
    planner_content = f"# Action Items - {entry_date.strftime('%B %d, %Y')}\n\n"
    planner_content += f"Extracted from diary entry: [[{date}]]\n\n"
    planner_content += "## 📋 Tasks\n\n"
    
    for todo in todos:
        planner_content += f"- [ ] {todo}\n"
    
    planner_content += f"\n---\n\n*Extracted on {datetime.now().strftime('%Y-%m-%d at %H:%M')}*\n"
    
    try:
        planner_path.write_text(planner_content, encoding="utf-8")
        return f"✅ **Extracted {len(todos)} action items!**\n\n📁 Saved to: {planner_path}\n\n💡 **Next steps:**\n- Review and prioritize your tasks\n- Add deadlines or context as needed\n- Check off items as you complete them\n\n📝 **Preview:**\n{chr(10).join([f'- {todo}' for todo in todos[:5]])}{'...' if len(todos) > 5 else ''}"
    except Exception as e:
        return f"Error writing planner file: {e}\n\n📝 **Extracted todos:**\n{chr(10).join([f'- {todo}' for todo in todos])}"


if __name__ == "__main__":
    mcp.run()