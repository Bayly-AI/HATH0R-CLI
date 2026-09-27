import re

with open("src/hath0r_cli/cli.py", "r") as f:
    content = f.read()

if "@main.group()\ndef memory():" not in content:
    memory_cli = """
@main.group()
def memory():
    \"\"\"Manage canonical Local Memory Space for agents.\"\"\"
    pass

@memory.command("init")
@click.option("--dry-run", is_flag=True, help="Simulate initialization.")
def memory_init(dry_run):
    \"\"\"Initialize the core local memory spaces.\"\"\"
    from hath0r_cli.bots.memory_manager import MemoryManagerBot
    from rich.console import Console
    console = Console()
    bot = MemoryManagerBot()
    res = bot.initialize_memory(dry_run=dry_run)
    if res.get("success"):
        console.print(f"[green]✓ {res['message']}[/green]")
    else:
        console.print(f"[red]✗ {res.get('error')}[/red]")

@memory.command("read")
@click.argument("topic", default="core")
def memory_read(topic):
    \"\"\"Read a canonical memory topic.\"\"\"
    from hath0r_cli.bots.memory_manager import MemoryManagerBot
    from rich.console import Console
    from rich.markdown import Markdown
    console = Console()
    bot = MemoryManagerBot()
    res = bot.read_memory(topic=topic)
    if res.get("success"):
        console.print(Markdown(res["content"]))
    else:
        console.print(f"[red]✗ {res.get('error')}[/red]")

@memory.command("update")
@click.argument("topic")
@click.argument("content")
@click.option("--dry-run", is_flag=True, help="Simulate update.")
def memory_update(topic, content, dry_run):
    \"\"\"Update a canonical memory topic.\"\"\"
    from hath0r_cli.bots.memory_manager import MemoryManagerBot
    from rich.console import Console
    console = Console()
    bot = MemoryManagerBot()
    res = bot.update_memory(topic=topic, content=content, dry_run=dry_run)
    if res.get("success"):
        console.print(f"[green]✓ {res['message']}[/green]")
    else:
        console.print(f"[red]✗ {res.get('error')}[/red]")

"""
    # Insert before if __name__ == "__main__": or at end
    if "if __name__ == \"__main__\":" in content:
        content = content.replace("if __name__ == \"__main__\":", memory_cli + "\nif __name__ == \"__main__\":")
    else:
        content += memory_cli
        
    with open("src/hath0r_cli/cli.py", "w") as f:
        f.write(content)
