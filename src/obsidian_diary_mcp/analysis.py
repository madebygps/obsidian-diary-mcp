"""AI-powered analysis for diary entries."""

import re
from typing import List, Optional

from .ollama_client import ollama_client
from .entry_manager import entry_manager
from .logger import analysis_logger as logger, log_section


class AnalysisEngine:
    """Handles AI-powered analysis of diary entries."""

    def __init__(self):
        self._theme_cache = {}

    def _extract_brain_dump(self, content: str) -> str:
        """Extract the Brain Dump section which contains actual reflections (not prompts)."""
        brain_dump_match = re.search(
            r"##\s*(?:💭|🧠)\s*Brain Dump\s*\n+(.*?)(?=\n---|\n##|\Z)",
            content,
            re.DOTALL | re.IGNORECASE,
        )

        if brain_dump_match:
            brain_dump = brain_dump_match.group(1).strip()
            brain_dump = re.sub(
                r"\*Your thoughts, experiences, and observations\.\.\.\*",
                "",
                brain_dump,
            ).strip()
            return brain_dump

        return ""

    def _extract_reflection_prompts(self, content: str) -> str:
        """Extract the reflection prompts section to identify unresolved questions."""
        prompts_match = re.search(
            r"##\s*(?:💭|🤔|🧠)\s*(?:Daily Reflection|Reflection Questions|Reflection Prompts|Weekly Reflection)\s*\n+(.*?)(?=\n---|\n##|\Z)",
            content,
            re.DOTALL | re.IGNORECASE,
        )

        if prompts_match:
            prompts = prompts_match.group(1).strip()
            prompts = re.sub(r"\*\*.*?\*\*", "", prompts)
            return prompts

        return ""

    async def extract_themes_and_topics(self, content: str) -> List[str]:
        """Extract key themes from diary entry content, prioritizing Brain Dump section."""
        brain_dump = self._extract_brain_dump(content)

        if len(brain_dump) > 50:
            analysis_content = brain_dump
            logger.debug(f"Analyzing Brain Dump section ({len(brain_dump)} chars)")
        else:
            analysis_content = re.sub(
                r"\*\*Related entries:\*\*.*$", "", content, flags=re.DOTALL
            )
            analysis_content = re.sub(
                r"##\s*🔗\s*Memory Links.*$", "", analysis_content, flags=re.DOTALL
            )
            logger.debug("No substantial Brain Dump found, analyzing full entry")

        if len(analysis_content.strip()) < 20:
            return []

        prompt = f"""Analyze this journal entry and extract 3-5 key themes or topics.

Entry content: {analysis_content}

Return ONLY the themes as a simple comma-separated list with no other text:
friendship, work-stress, creativity"""

        try:
            logger.debug("Extracting themes with Ollama...")
            response_text = await ollama_client.generate(
                prompt,
                "You are an expert at identifying key themes in personal writing. Extract the most meaningful concepts.",
            )
            logger.debug("Theme extraction successful")
        except Exception as e:
            logger.error(f"Theme extraction failed: {e}")
            return []

        themes = [
            theme.strip().lower()
            for theme in response_text.strip().split(",")
            if theme.strip()
        ]
        return themes[:5]

    async def get_themes_cached(self, content: str, file_stem: str) -> List[str]:
        """Get themes for content with caching to avoid redundant AI calls."""
        cache_key = f"{file_stem}_{len(content)}_{hash(content[:100])}"

        if cache_key in self._theme_cache:
            return self._theme_cache[cache_key]

        themes = await self.extract_themes_and_topics(content)
        self._theme_cache[cache_key] = themes
        return themes

    def generate_topic_tags(self, themes: List[str]) -> List[str]:
        """Convert themes to Obsidian-compatible topic tags."""
        if not themes:
            return []

        skip_phrases = {"key themes", "extracted", "journal entry"}
        topic_tags = []

        for theme in themes:
            if any(skip in theme.lower() for skip in ["key themes", "extracted from"]):
                parts = re.split(r"[:\n•\-]", theme)
                for part in parts:
                    clean_part = part.strip()
                    if (
                        clean_part
                        and len(clean_part) < 50
                        and not any(skip in clean_part.lower() for skip in skip_phrases)
                    ):
                        clean_theme = re.sub(
                            r"[^\w\s-]+", "-", clean_part.lower()
                        ).strip("-")
                        clean_theme = re.sub(r"-+", "-", clean_theme)
                        if clean_theme:
                            topic_tags.append(f"#{clean_theme}")
            else:
                clean_theme = re.sub(r"[^\w\s-]+", "-", theme.lower()).strip("-")
                clean_theme = re.sub(r"-+", "-", clean_theme)
                if clean_theme:
                    topic_tags.append(f"#{clean_theme}")

        return topic_tags

    async def find_related_entries(
        self,
        current_content: str,
        exclude_date: Optional[str] = None,
        max_related: int = 6,
    ) -> List[str]:
        """Find related entries using cached theme analysis (prioritizes Brain Dump content)."""
        current_themes = set(
            await self.get_themes_cached(current_content, exclude_date or "current")
        )

        if not current_themes:
            logger.info("No themes extracted for current entry")
            return []

        entries = entry_manager.get_all_entries()
        similarity_scores = []

        logger.info(
            f"Finding related entries based on themes: {', '.join(sorted(current_themes))}"
        )
        logger.debug(f"Analyzing {len(entries)} entries for connections")

        for date, file_path in entries:
            if exclude_date and file_path.stem == exclude_date:
                logger.debug(f"  Skipping {file_path.stem} (excluded date)")
                continue

            entry_content = entry_manager.read_entry(file_path)
            if entry_content.startswith("Error reading file"):
                logger.debug(f"  Skipping {file_path.stem} (read error)")
                continue

            logger.debug(f"  Getting themes for {file_path.stem}...")
            entry_themes = set(
                await self.get_themes_cached(entry_content, file_path.stem)
            )
            logger.debug(
                f"  Themes for {file_path.stem}: {sorted(entry_themes) if entry_themes else 'EMPTY'}"
            )

            if entry_themes:
                intersection = current_themes & entry_themes
                union = current_themes | entry_themes
                similarity = len(intersection) / len(union)

                logger.debug(
                    f"  {file_path.stem}: themes={sorted(entry_themes)}, intersection={sorted(intersection)}, union={sorted(union)}, similarity={similarity:.3f}"
                )

                if similarity > 0.08:
                    similarity_scores.append((similarity, file_path.stem))
                    logger.debug("    ✓ Above threshold (0.08), added to results")
                else:
                    logger.debug("    ✗ Below threshold (0.08), skipped")
            else:
                logger.debug(f"  {file_path.stem}: No themes extracted")

        similarity_scores.sort(reverse=True, key=lambda x: x[0])

        backlinks = [f"[[{stem}]]" for _, stem in similarity_scores[:max_related]]

        if backlinks:
            logger.info(f"✓ Found {len(backlinks)} cognitive connections")
        else:
            logger.info(
                "No connections found - similarity threshold not met or insufficient entries"
            )

        return backlinks

    async def generate_reflection_prompts(
        self,
        recent_content: str,
        focus: Optional[str] = None,
        count: int = 3,
        is_sunday: bool = False,
    ) -> List[str]:
        """Generate reflection prompts based on recent content, prioritizing Brain Dump sections."""
        log_section(logger, "Generate Reflection Prompts")
        logger.info(
            f"Input: {len(recent_content):,} chars | Count: {count} | Sunday: {is_sunday} | Focus: {focus or 'None'}"
        )

        if len(recent_content.strip()) < 20:
            logger.warning("Content too short (<20 chars), returning empty")
            return []

        entry_pattern = re.compile(r"##\s*(?:MOST RECENT ENTRY|Earlier entry)\s*\(([^)]+)\):\n(.*?)(?=##\s*(?:MOST RECENT ENTRY|Earlier entry)|$)", re.DOTALL)
        entry_matches = entry_pattern.findall(recent_content)
        
        date_map = {}
        entries = []
        
        if entry_matches:
            for date_str, content in entry_matches:
                entries.append(content)
                if len(entries) == 1:
                    date_map["Day 1"] = date_str.strip()
                else:
                    date_map[f"Day {len(entries)}"] = date_str.strip()
            
            logger.debug(f"Date map: {date_map}")
            
            most_recent_brain_dump = self._extract_brain_dump(entries[0])
            most_recent_content = most_recent_brain_dump if len(most_recent_brain_dump) > 50 else entries[0]
            
            logger.info(f"Day 1 ({date_map.get('Day 1', 'today')}): {len(most_recent_content):,} chars ({'Brain Dump' if len(most_recent_brain_dump) > 50 else 'full entry'})")
            
            if len(entries) > 1:
                context_parts = []
                prompt_parts = []
                
                for i, entry in enumerate(entries[1:], 2):
                    brain_dump = self._extract_brain_dump(entry)
                    content = brain_dump if len(brain_dump) > 50 else entry
                    
                    if i == 2:
                        priority_label = "SECONDARY PRIORITY"
                    elif i == 3:
                        priority_label = "TERTIARY PRIORITY"
                    else:
                        priority_label = f"Day {i} context"
                    
                    context_parts.append(f"### {priority_label} - Day {i}:\n{content}")
                    logger.debug(f"Day {i}: {len(content):,} chars ({'Brain Dump' if len(brain_dump) > 50 else 'full'})")
                    
                    prompts = self._extract_reflection_prompts(entry)
                    if prompts:
                        prompt_parts.append(f"Day {i} prompts:\n{prompts}")
                        logger.debug(f"Day {i}: Extracted {len(prompts)} chars of reflection prompts")
                
                context_text = "\n\n".join(context_parts)
                
                if prompt_parts:
                    prompts_text = "\n\n".join(prompt_parts)
                    analysis_content = f"""## PRIMARY FOCUS - Day 1 (Today):
{most_recent_content}

## Historical Context (use for patterns/connections only):
{context_text}

## Reflection Prompts from Previous Days (LOWEST PRIORITY - only reference if detecting unresolved thoughts):
{prompts_text}"""
                    logger.info(f"Total: {len(analysis_content):,} chars with hierarchical priority (Day 1 > Day 2 > Day 3 > Prompts)")
                else:
                    analysis_content = f"""## PRIMARY FOCUS - Day 1 (Today):
{most_recent_content}

## Historical Context (use for patterns/connections only):
{context_text}"""
                    logger.info(f"Total: {len(analysis_content):,} chars with hierarchical priority (Day 1 > Day 2 > Day 3)")
            else:
                analysis_content = f"## PRIMARY FOCUS - Day 1 (Today):\n{most_recent_content}"
                logger.info(f"Single entry: {len(analysis_content):,} chars")
        else:
            brain_dump = self._extract_brain_dump(recent_content)
            analysis_content = brain_dump if len(brain_dump) > 50 else recent_content
            logger.debug(f"Single entry mode: using {'Brain Dump' if len(brain_dump) > 50 else 'full content'}")

        focus_instruction = (
            f"\n\nFocus specifically on {focus} for all questions." if focus else ""
        )
        weekly_instruction = (
            "\n\nThis is a Sunday reflection - synthesize the past week and set intentions for the week ahead."
            if is_sunday
            else ""
        )

        prompt = f"""Generate {count} thoughtful reflection questions with a strong emphasis on what they wrote TODAY (Day 1).

PRIORITY SYSTEM:
1. PRIMARY: Day 1 (Today) - Prioritize today's writing heavily
2. SECONDARY: Day 2 - Reference if there's a meaningful connection or ongoing pattern
3. TERTIARY: Day 3+ - Reference only if it reveals important context
4. PROMPTS: Previous questions - Reference only if genuinely unresolved{focus_instruction}{weekly_instruction}

{analysis_content}

CRITICAL RULES:
- STRONGLY prioritize Day 1 (today) - most questions should be about today's content
- You MAY reference Day 2/3 if there's a genuinely important pattern, connection, or unresolved thread
- MANDATORY: If ANY part of your question references content from a specific day (including Day 1), you MUST cite it using [Day X] format
- When citing, add a brief reason in parentheses explaining WHY: (pattern, unresolved, connection to today, ongoing theme, etc.)
- BUT: Don't ask follow-up questions about old topics just because they exist in the history
- Use your judgment: Is this old topic still relevant? Did today's writing connect to it? Is there an unresolved question?
- NEVER invent feelings, concerns, or problems they didn't express
- Reference their actual words, ideas, observations, plans, or questions
- Write questions that EXPAND on what they said, not assume negativity

Good examples:
"What do you think is contributing to your improved sleep metrics [Day 1] (mentioned today)?"
"You mentioned Python community connections [Day 2] (ongoing theme) - how do you want to continue building on that?"
"In light of your VS Code Dev Days experiences [Day 3] (recent learning), how might you apply those insights to your current work?"
"I notice you raised concerns about work deadlines [Day 3] (unresolved question) but haven't mentioned them since - has that shifted?"

Bad examples:
"You mentioned feeling frustrated about X a few days ago..." (missing day citation and reason)
"What's making you feel worried about..." (inventing a feeling)
"Why are you concerned about..." (when they said "thinking about" not "concerned")
"What skills from your recent experiences..." (referencing previous day but missing [Day X] citation)

Output format - numbered questions with MANDATORY day citations and reasons:
1. What connections do you see between X [Day 1] (reason) and...
2. You mentioned X [Day 2] (reason) - how might you explore...
3. In light of Y [Day 3] (reason), what would it look like if..."""

        logger.debug(f"Prompt size: {len(prompt):,} chars | Preview: {prompt[:100]}...")

        try:
            logger.info("Calling Ollama API for prompt generation...")
            response_text = await ollama_client.generate(
                prompt,
                "You are a thoughtful journaling coach. STRONGLY prioritize Day 1 (today's writing) for questions. You may reference previous days if there's a meaningful ongoing pattern or connection, but use discretion - don't resurrect old topics that aren't currently relevant. Never assume feelings or invent problems. Output ONLY numbered questions, nothing else.",
            )
            logger.info(f"Received response: {len(response_text)} chars")
            logger.debug(f"Full response: {response_text}")
        except Exception as e:
            logger.error(f"Ollama call failed ({type(e).__name__}): {e}")
            return []

        logger.debug("Parsing prompts from response...")

        response_text = re.sub(
            r"<think>.*?</think>", "", response_text, flags=re.DOTALL
        )

        skip_phrases = {
            "unresolved",
            "worth exploring",
            "here are",
            "**",
            "topics:",
            "questions:",
            "output format",
        }
        prompts = []
        for line in response_text.split("\n"):
            line = line.strip()
            if any(skip in line.lower() for skip in skip_phrases) or not line:
                continue

            if line and (line[0].isdigit() or line[0] == "-"):
                clean_prompt = re.sub(r"^[\d.\-\s]+", "", line).strip()
                if clean_prompt and (
                    clean_prompt.endswith("?") or len(clean_prompt) > 20
                ):
                    for day_ref in ["Day 1", "Day 2", "Day 3", "Day 4", "Day 5", "Day 6", "Day 7"]:
                        if day_ref in clean_prompt and day_ref in date_map:
                            date_str = date_map[day_ref]
                            clean_prompt = clean_prompt.replace(f"[{day_ref}]", f"[[{date_str}]]")
                            logger.debug(f"  Converted [{day_ref}] to [[{date_str}]]")
                    
                    logger.debug(f"  ✓ {clean_prompt[:60]}...")
                    prompts.append(clean_prompt)

        logger.info(f"✓ Extracted {len(prompts)} prompts (returning first {count})")
        return prompts[:count]

    async def extract_todos(self, content: str) -> List[str]:
        """Extract action items and todos from diary entry content."""
        log_section(logger, "Extract Todos")
        logger.info(f"Analyzing content: {len(content):,} chars")

        if len(content.strip()) < 20:
            logger.warning("Content too short (<20 chars), returning empty")
            return []

        brain_dump = self._extract_brain_dump(content)
        analysis_content = brain_dump if len(brain_dump) > 50 else content

        prompt = f"""Analyze this journal entry and extract ALL action items, tasks, and todos mentioned.

Journal entry:
{analysis_content}

Your task:
- Identify any tasks, action items, or things the person needs/wants to do
- Include both explicit todos ("I need to...", "I should...") and implicit ones (unfinished work, intentions, goals)
- Be specific and actionable
- Extract the person's own words where possible
- If there are no clear action items, return "No action items found"

Format as a simple bulleted list with one action per line:
- [Action item 1]
- [Action item 2]
- [Action item 3]

IMPORTANT: Only output the bulleted list, no other text or commentary."""

        logger.debug(f"Prompt size: {len(prompt):,} chars")

        try:
            logger.info("Calling Ollama API for todo extraction...")
            response_text = await ollama_client.generate(
                prompt,
                "You are a helpful assistant that extracts action items from journal entries. Be thorough but focused on actionable tasks. Output ONLY a bulleted list of action items, nothing else.",
            )
            logger.info(f"Received response: {len(response_text)} chars")
            logger.debug(f"Full response: {response_text}")
        except Exception as e:
            logger.error(f"Ollama call failed ({type(e).__name__}): {e}")
            return []

        if "no action items" in response_text.lower():
            logger.info("No action items found in entry")
            return []

        logger.debug("Parsing todos from response...")
        todos = []
        skip_phrases = {"action items:", "tasks:", "todos:", "here are"}
        for line in response_text.split("\n"):
            line = line.strip()
            if any(skip in line.lower() for skip in skip_phrases):
                continue

            if line and line[0] in "-*•":
                clean_todo = re.sub(r"^[-*•\s]+", "", line).strip()
                if len(clean_todo) > 3:
                    logger.debug(f"  ✓ {clean_todo[:60]}...")
                    todos.append(clean_todo)

        logger.info(f"✓ Extracted {len(todos)} action items")
        return todos


analysis_engine = AnalysisEngine()
