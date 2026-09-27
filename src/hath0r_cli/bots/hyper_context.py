from pathlib import Path
from typing import Any


class HyperContextBot:
    """Bot for managing Hyper Context architecture."""

    def spread_context(self, target_dir: str, feature_name: str) -> dict[str, Any]:
        """Spread AGENTS.md, rules.md, and canonical.md to the target directory."""
        target = Path(target_dir)
        target.mkdir(parents=True, exist_ok=True)

        agents_md = target / "AGENTS.md"
        rules_md = target / "rules.md"
        canonical_md = target / "canonical.md"

        if not agents_md.exists():
            content = (
                f"# {feature_name} - AGENTS Context\n\n"
                f"> This file contains hyper-localized context for {feature_name}.\n\n"
                "## Roles and Focus\n- Localized focus rules go here.\n"
            )
            agents_md.write_text(content, encoding="utf-8")

        if not rules_md.exists():
            content = (
                f"# {feature_name} - Local Rules\n\n"
                f"> Specific rules and constraints for the {feature_name} module.\n\n"
                "## Constraints\n- \n"
            )
            rules_md.write_text(content, encoding="utf-8")

        if not canonical_md.exists():
            content = (
                f"# {feature_name} - Canonical Reference\n\n"
                f"> Canonical sources of truth for {feature_name}.\n\n"
                "## Architecture\n- \n"
            )
            canonical_md.write_text(content, encoding="utf-8")

        # Append pointer to root AGENTS.md
        root_agents = Path("AGENTS.md")
        if root_agents.exists():
            content = root_agents.read_text(encoding="utf-8")
            pointer = f"- **{feature_name}**: `{target_dir}/AGENTS.md`"
            if pointer not in content:
                with root_agents.open("a", encoding="utf-8") as f:
                    f.write(f"\n## Hyper Context Pointers\n{pointer}\n")

        return {
            "success": True,
            "message": f"Successfully spread hyper context to {target_dir}",
            "files_created": [str(agents_md), str(rules_md), str(canonical_md)],
        }
