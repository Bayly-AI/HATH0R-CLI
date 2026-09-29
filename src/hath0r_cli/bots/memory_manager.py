from pathlib import Path
from typing import Any, Dict, Optional


class MemoryManagerBot:
    """Bot to manage the Canonical Local Memory Space for AI Agents."""

    def __init__(self, cwd: Optional[Path] = None):
        self.cwd = cwd or Path.cwd()
        self.memory_dir = self.cwd / ".hath0r" / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    def initialize_memory(self, dry_run: bool = False) -> Dict[str, Any]:
        """Initialize the core Hath0r memory spaces."""
        core_file = self.memory_dir / "core_rules.md"
        arch_file = self.memory_dir / "architecture.md"

        core_content = (
            "# Core Hath0r Rules\n"
            "1. CLI-First (CR-CLI-ENTRY-001): Always start with the CLI capabilities before improvising.\n"
            "2. Bots not Daemons: Background tasks are bots/factories.\n"
            "3. Hyper-Context: Always traverse the defined context paths (playbooks, procedures).\n"
            "4. Promotion Path: local -> development -> testing -> staging -> master.\n"
        )

        arch_content = (
            "# Canonical Architecture\n"
            "The HATH0R-CLI repository acts as the OpenSource Control Tower.\n"
            "Agents orienting to any Hath0r app MUST read this Local Memory Space first "
            "to align with current objectives.\n"
        )

        if not dry_run:
            core_file.write_text(core_content)
            arch_file.write_text(arch_content)

        return {
            "success": True,
            "message": "Initialized core memory spaces.",
            "files": [str(core_file), str(arch_file)],
        }

    def init_memory(self, dry_run: bool = False) -> Dict[str, Any]:
        """Alias for initialize_memory."""
        return self.initialize_memory(dry_run=dry_run)

    def read_topic(self, topic: str) -> Optional[str]:
        """Read content of a topic directly."""
        res = self.read_memory(topic)
        if res.get("success"):
            return res.get("content")
        return None

    def update_topic(self, topic: str, content: str, dry_run: bool = False) -> Dict[str, Any]:
        """Alias for update_memory."""
        return self.update_memory(topic=topic, content=content, dry_run=dry_run)

    def read_memory(self, topic: str) -> Dict[str, Any]:
        """Read a specific memory topic."""
        # Handle aliases: rules -> core_rules, core -> core_rules
        actual_topic = "core_rules" if topic in ("rules", "core") else topic
        target_file = self.memory_dir / f"{actual_topic}.md"
        if not target_file.exists():
            # Try exact match without translation
            target_file = self.memory_dir / f"{topic}.md"
            if not target_file.exists():
                return {"success": False, "error": f"Memory topic '{topic}' does not exist."}

        return {"success": True, "topic": topic, "content": target_file.read_text()}

    def update_memory(self, topic: str, content: str, dry_run: bool = False) -> Dict[str, Any]:
        """Update or create a specific memory topic."""
        actual_topic = "core_rules" if topic in ("rules", "core") else topic
        target_file = self.memory_dir / f"{actual_topic}.md"
        if not dry_run:
            target_file.write_text(content)

        return {"success": True, "message": f"Updated memory topic '{topic}'.", "file": str(target_file)}

