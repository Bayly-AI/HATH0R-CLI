with open("src/hath0r_cli/bots/__init__.py", "r") as f:
    content = f.read()

if "MemoryManagerBot" not in content:
    content = content.replace(
        "from hath0r_cli.bots.voice_converse import VoiceServiceBot",
        "from hath0r_cli.bots.voice_converse import VoiceServiceBot\nfrom hath0r_cli.bots.memory_manager import MemoryManagerBot"
    )
    content = content.replace(
        '"VoiceServiceBot",',
        '"VoiceServiceBot",\n    "MemoryManagerBot",'
    )
    with open("src/hath0r_cli/bots/__init__.py", "w") as f:
        f.write(content)
