"""Entry management for diary files."""

from datetime import datetime
from pathlib import Path
from typing import List, Tuple
import re

from .config import DIARY_PATH


class EntryManager:
    """Manages diary entry files and operations."""
    
    def __init__(self, diary_path: Path = DIARY_PATH):
        self.diary_path = diary_path
    
    def get_all_entries(self) -> List[Tuple[datetime, Path]]:
        """Get all diary entries sorted by date (newest first)."""
        entries = []
        for file in self.diary_path.glob("*.md"):
            if file.name.startswith("."):
                continue
            try:
                date_str = file.stem
                date = datetime.strptime(date_str, "%Y-%m-%d")
                entries.append((date, file))
            except ValueError:
                continue
        
        return sorted(entries, key=lambda x: x[0], reverse=True)
    
    def read_entry(self, file_path: Path) -> str:
        """Read the content of a diary entry file."""
        try:
            return file_path.read_text(encoding="utf-8")
        except (FileNotFoundError, PermissionError, OSError) as e:
            return f"Error reading file: {e}"
    
    def write_entry(self, file_path: Path, content: str) -> bool:
        """Write content to a diary entry file."""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            return True
        except (PermissionError, OSError):
            return False
    
    def entry_exists(self, date: datetime) -> bool:
        """Check if an entry exists for the given date."""
        filename = date.strftime("%Y-%m-%d")
        file_path = self.diary_path / f"{filename}.md"
        return file_path.exists()
    
    def get_entry_path(self, date: datetime) -> Path:
        """Get the file path for an entry on the given date."""
        filename = date.strftime("%Y-%m-%d")
        return self.diary_path / f"{filename}.md"
    
    def remove_existing_backlinks(self, content: str) -> str:
        """Remove existing backlinks sections from content (including placeholder sections)."""
        patterns = [
            r"---\n\*\*(?:Related entries|Memory links):\*\*.*$",
            r"---\s*##\s*Memory Links\s*\n+\*Temporal connections.*?\*",
            r"---\s*##\s*Memory Links\s*\n+.*?(?=\n---|\Z)"
        ]
        
        for pattern in patterns:
            content = re.sub(pattern, "", content, flags=re.DOTALL | re.IGNORECASE)
        
        return content.rstrip()
    
    def add_memory_links(self, content: str, related: List[str], topic_tags: List[str]) -> str:
        """Add memory links section to content, replacing any existing placeholder."""
        content = self.remove_existing_backlinks(content)
        
        memory_section = "\n\n---\n\n## Memory Links\n\n"
        
        if related:
            memory_section += f"**Temporal connections:** {' • '.join(related)}\n\n"
        
        if topic_tags:
            memory_section += f"**Topic tags:** {' '.join(topic_tags)}\n\n"
        
        if related or topic_tags:
            memory_section += "*Temporal connections and topic exploration available in Obsidian.*"
        else:
            memory_section += "*No connections found - this represents novel cognitive territory.*"
        
        return content + memory_section


entry_manager = EntryManager()