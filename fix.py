with open("src/hath0r_cli/step_runner.py", "r") as f:
    text = f.read()

text = text.replace("bot: VoiceServiceBot,\n    MemoryManagerBot,", "bot: VoiceServiceBot,")
text = text.replace("bot: VoiceServiceBot,\n        MemoryManagerBot,", "bot: VoiceServiceBot,")

with open("src/hath0r_cli/step_runner.py", "w") as f:
    f.write(text)
