with open("src/hath0r_cli/step_runner.py", "r") as f:
    content = f.read()

if "MemoryManagerBot" not in content:
    content = content.replace(
        "from hath0r_cli.bots.voice_converse import VoiceServiceBot",
        "from hath0r_cli.bots.voice_converse import VoiceServiceBot\nfrom hath0r_cli.bots.memory_manager import MemoryManagerBot"
    )
    
    content = content.replace(
        '"voice-service-bot": VoiceServiceBot(cwd=self.cwd),',
        '"voice-service-bot": VoiceServiceBot(cwd=self.cwd),\n            "memory-manager-bot": MemoryManagerBot(cwd=self.cwd),'
    )
    
    content = content.replace(
        'elif bot_id == "voice-service-bot":',
        'elif bot_id == "memory-manager-bot":\n                return self._dispatch_memory_manager_bot(bot, action, args, dry_run=dry_run, context=ctx)\n            elif bot_id == "voice-service-bot":'
    )
    
    new_method = """
    def _dispatch_memory_manager_bot(
        self, bot: MemoryManagerBot, action: str, args: Dict[str, Any], dry_run: bool = False, context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        if action == "init":
            return bot.initialize_memory(dry_run=dry_run)
        elif action == "read":
            return bot.read_memory(topic=args.get("topic", "core"))
        elif action == "update":
            return bot.update_memory(topic=args.get("topic"), content=args.get("content", ""), dry_run=dry_run)
        else:
            return {
                "success": False,
                "bot_id": "memory-manager-bot",
                "action": action,
                "error": f"Unknown action '{action}' for memory-manager-bot."
            }
"""
    content += new_method

    with open("src/hath0r_cli/step_runner.py", "w") as f:
        f.write(content)
