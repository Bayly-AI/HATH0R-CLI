"""Voice command for HATH0R CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import click
from rich.table import Table

from hath0r_cli.common import (
    _build_response,
    _emit_response,
    _output_mode,
    console,
)


@click.group()
def voice() -> None:
    """Voice interface subsystem and hands-free action dispatch."""


@voice.command("status")
@click.pass_context
def voice_status(ctx: click.Context) -> None:
    """Inspect audio devices, STT/TTS status, and router health."""
    from hath0r_cli.voice import inspect_voice_subsystem

    data = inspect_voice_subsystem()
    response = _build_response(ctx, command="voice.status", state="ok", data=data)

    def _text() -> None:
        table = Table(title="HATH0R Voice Subsystem Status")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="white")

        table.add_row("System Status", data.get("status", "ok"), f"Platform: {data.get('platform')}")
        stt = data.get("stt", {})
        table.add_row(
            "STT Provider",
            stt.get("status", "ok"),
            f"{stt.get('provider')} ({stt.get('sample_rate')}Hz, VAD={stt.get('vad_enabled')})",
        )
        tts = data.get("tts", {})
        table.add_row("TTS Engine", tts.get("status", "ok"), f"Engine: {tts.get('engine')}")
        router = data.get("router", {})
        table.add_row(
            "Router Fast-Path",
            router.get("status", "ok"),
            f"{router.get('provider')} (<={router.get('max_fastpath_latency_ms')}ms)",
        )

        ptt = data.get("push_to_talk", {})
        table.add_row(
            "Push-to-Talk",
            "enabled" if ptt.get("enabled", True) else "disabled",
            f"Key: {ptt.get('default_key', 'right_ctrl')} (ask_button={ptt.get('prompt_for_key', True)})",
        )
        gov = data.get("governance", {})
        table.add_row("Trust Governance", "active", f"Default Tier: {gov.get('default_tier')}")
        console.print(table)

    _emit_response(ctx, response, text_renderer=_text)


@voice.command("exec")
@click.argument("transcript")
@click.option(
    "--trust-tier",
    "-t",
    type=click.Choice(["guest", "elevated", "sovereign"]),
    default="elevated",
    show_default=True,
    help="Execution authorization tier.",
)
@click.option("--dry-run", is_flag=True, default=False, help="Simulate execution without triggering OS side-effects.")
@click.option("--speak/--no-speak", default=False, help="Speak feedback acknowledgment via TTS.")
@click.pass_context
def voice_exec(ctx: click.Context, transcript: str, trust_tier: str, dry_run: bool, speak: bool) -> None:
    """Evaluate and dispatch a transcribed voice statement."""
    from hath0r_cli.voice import evaluate_and_dispatch_voice

    data, diagnostics, state = evaluate_and_dispatch_voice(
        transcript=transcript,
        trust_tier=trust_tier,
        dry_run=dry_run,
        speak=speak,
    )
    response = _build_response(
        ctx, command="voice.exec", state=state, dry_run=dry_run, data=data, diagnostics=diagnostics
    )

    def _text() -> None:
        if data.get("blocked"):
            console.print(f"[bold red]✗ Voice Action Blocked:[/bold red] {data.get('rejection_reason')}")
            return

        action = data.get("action", {})
        intent = action.get("intent", "unresolved")
        tier = action.get("routing_tier", "system_one")
        duration = data.get("duration_ms", 0.0)

        console.print(f"[bold green]✓ Voice Action Resolved[/bold green] in {duration:.1f}ms ([cyan]{tier}[/cyan]):")
        console.print(f"  • [bold]Transcript:[/bold] \"{action.get('transcript')}\"")
        console.print(f"  • [bold]Intent:[/bold] {intent} (confidence={action.get('confidence', 1.0):.2f})")
        payload = action.get("payload", {})
        if "command" in payload:
            console.print(f"  • [bold]Command:[/bold] [yellow]{payload.get('command')}[/yellow]")
        if "target" in payload:
            console.print(f"  • [bold]Target:[/bold] [magenta]{payload.get('target')}[/magenta]")
        if "feedback_text" in payload:
            console.print(f"  • [bold]Feedback:[/bold] {payload.get('feedback_text')}")

    _emit_response(ctx, response, text_renderer=_text)
    if data.get("blocked"):
        ctx.exit(1)


@voice.command("listen")
@click.option(
    "--push-to-talk/--ambient",
    "push_to_talk",
    default=True,
    show_default=True,
    help="Enable push-to-talk mode or continuous ambient mode.",
)
@click.option(
    "--key",
    "-k",
    type=str,
    default=None,
    help="Designated push-to-talk button (defaults to interactive selection with 'right_ctrl').",
)
@click.option(
    "--ask-key/--no-ask-key",
    "ask_key",
    default=True,
    show_default=True,
    help="Always prompt operator to confirm/select which button to use for push-to-talk.",
)
@click.option(
    "--max-utterances",
    type=int,
    default=1,
    show_default=True,
    help="Number of utterances to capture before exiting.",
)
@click.option(
    "--trust-tier",
    "-t",
    type=click.Choice(["guest", "elevated", "sovereign"]),
    default="elevated",
    show_default=True,
    help="Execution authorization tier.",
)
@click.pass_context
def voice_listen(
    ctx: click.Context,
    push_to_talk: bool,
    key: Optional[str],
    ask_key: bool,
    max_utterances: int,
    trust_tier: str,
) -> None:
    """Continuous ambient or push-to-talk listening loop."""
    from hath0r_cli.voice import (
        evaluate_and_dispatch_voice,
        get_push_to_talk_config,
        wait_for_push_to_talk_trigger,
    )

    is_json = _output_mode(ctx) == "json"
    ptt_cfg = get_push_to_talk_config()

    selected_key = key or ptt_cfg.default_key
    if push_to_talk and (ask_key or ptt_cfg.prompt_for_key) and not is_json:
        console.print("[bold cyan]Push-to-Talk Activation Key Selection[/bold cyan]")
        console.print(f"Supported keys: [dim]{', '.join(ptt_cfg.supported_keys)}[/dim]")
        selected_key = (
            click.prompt(
                "Which button would you like to use for Push-to-Talk?",
                default=selected_key,
                show_default=True,
            )
            .strip()
            .lower()
            .replace(" ", "_")
            .replace("-", "_")
        )

    mode_label = f"Push-to-talk (key='{selected_key}')" if push_to_talk else "Ambient continuous"
    if not is_json:
        console.print(f"[bold cyan]HATH0R Voice Listening[/bold cyan] ({mode_label}, trust-tier={trust_tier})")
        console.print("[dim]Press Ctrl+C to stop listening.[/dim]\n")

    captured = 0
    results = []
    try:
        while max_utterances is None or captured < max_utterances:
            if push_to_talk and not is_json:
                console.print(f"[bold green]Hold / press [{selected_key}] to speak...[/bold green] (or press Enter)")
                wait_for_push_to_talk_trigger(selected_key, timeout_seconds=60.0)
                click.prompt(
                    "Press [Enter] to speak (or type transcript for simulated input)",
                    default="",
                    show_default=False,
                )

            if not is_json:
                console.print("[bold yellow]● Listening...[/bold yellow]")
                transcript = click.prompt("Utterance transcript", default="hath0r doctor", show_default=True)
                console.print(f"[dim]Processing: '{transcript}'...[/dim]")
            else:
                line = click.get_text_stream("stdin").readline()
                transcript = line.strip() if line else "hath0r doctor"

            data, diagnostics, state = evaluate_and_dispatch_voice(transcript=transcript, trust_tier=trust_tier)
            results.append(data)
            captured += 1

            if not is_json:
                if data.get("blocked"):
                    console.print(f"[red]✗ Blocked:[/red] {data.get('rejection_reason')}")
                else:
                    dur = data.get("duration_ms", 0.0)
                    act = data.get("action", {})
                    fb = act.get("payload", {}).get("feedback_text", "")
                    console.print(f"[green]✓ Dispatched[/green] ({act.get('intent')}, {dur:.1f}ms): {fb}\n")

    except (KeyboardInterrupt, click.Abort):
        if not is_json:
            console.print("\n[dim]Listening terminated by operator.[/dim]")

    response = _build_response(
        ctx,
        command="voice.listen",
        state="ok",
        data={
            "captured_count": captured,
            "push_to_talk": push_to_talk,
            "key": selected_key,
            "results": results,
        },
    )
    _emit_response(ctx, response)


@voice.command("converse")
@click.option(
    "--push-to-talk/--ambient",
    "push_to_talk",
    default=True,
    show_default=True,
    help="Enable push-to-talk mode or ambient continuous conversation.",
)
@click.option(
    "--key",
    "-k",
    type=str,
    default=None,
    help="Push-to-talk trigger button (default: right_ctrl).",
)
@click.option(
    "--max-turns",
    type=int,
    default=5,
    show_default=True,
    help="Maximum dialogue turns before ending conversation session.",
)
@click.option(
    "--trust-tier",
    "-t",
    type=click.Choice(["guest", "elevated", "sovereign"]),
    default="elevated",
    show_default=True,
    help="Execution authorization tier.",
)
@click.option(
    "--repo",
    type=click.Path(path_type=Path),
    default=None,
    help="Target repository context for agent reasoning.",
)
@click.pass_context
def voice_converse(
    ctx: click.Context,
    push_to_talk: bool,
    key: Optional[str],
    max_turns: int,
    trust_tier: str,
    repo: Optional[Path],
) -> None:
    """Run an interactive two-way voice dialogue session with active Hath0r agent."""
    from hath0r_cli.bots.voice_converse import AgentDialogueBot, SpeechListenerBot, VoiceSynthesizerBot

    target_repo = repo or Path.cwd()
    listener = SpeechListenerBot(cwd=target_repo)
    dialogue = AgentDialogueBot(cwd=target_repo)
    synth = VoiceSynthesizerBot(cwd=target_repo)

    is_json = _output_mode(ctx) == "json"
    if not is_json:
        console.print("[bold cyan]HATH0R Conversational Voice Session[/bold cyan]")
        console.print(f"[dim]Repo: {target_repo} | Trust Tier: {trust_tier} | Max Turns: {max_turns}[/dim]\n")
        synth.speak("Conversational voice session started. I am listening.")

    turns: list[dict[str, Any]] = []
    try:
        for turn_idx in range(1, max_turns + 1):
            if not is_json:
                console.print(f"[bold yellow]Turn {turn_idx}/{max_turns}: Listening...[/bold yellow]")

            listen_res = listener.listen(push_to_talk=push_to_talk, key=key)
            transcript = listen_res.get("transcript", "").strip()
            if not transcript or transcript.lower() in ("cancel", "stop", "exit", "quit", "bye"):
                if not is_json:
                    console.print("[dim]Conversation ended by operator.[/dim]")
                    synth.speak("Goodbye.")
                break

            if not is_json:
                console.print(f"[dim]You:[/dim] {transcript}")

            reason_res = dialogue.reason(transcript=transcript, trust_tier=trust_tier)
            reply = reason_res.get("response_text", "")

            if not is_json:
                console.print(f"[bold green]Agent:[/bold green] {reply}\n")

            synth.speak(reply)
            turns.append({"turn": turn_idx, "user": transcript, "agent": reply})
    except (KeyboardInterrupt, click.Abort):
        if not is_json:
            console.print("\n[dim]Conversation terminated by operator.[/dim]")

    response = _build_response(
        ctx,
        command="voice.converse",
        state="ok",
        data={"turns_count": len(turns), "turns": turns},
    )
    _emit_response(ctx, response)


@voice.command("meeting")
@click.option(
    "--mode",
    type=click.Choice(["standup", "review", "ambient"]),
    default="standup",
    show_default=True,
    help="Meeting participation mode.",
)
@click.option(
    "--topic",
    type=str,
    default="Daily Engineering Standup",
    show_default=True,
    help="Meeting topic or context.",
)
@click.pass_context
def voice_meeting(ctx: click.Context, mode: str, topic: str) -> None:
    """Hands-free meeting participant mode with proactive check-in."""
    from hath0r_cli.bots.voice_converse import ProactiveSpeakerBot

    speaker = ProactiveSpeakerBot()
    checkin_res = speaker.check_in(topic=f"{topic} ({mode})", speak=True)

    response = _build_response(
        ctx,
        command="voice.meeting",
        state="ok",
        data={"mode": mode, "topic": topic, "check_in": checkin_res},
    )
    _emit_response(ctx, response)


@voice.command("speak")
@click.argument("message")
@click.option(
    "--voice",
    "-v",
    "voice_name",
    type=str,
    default=None,
    help="Optional TTS voice name identifier.",
)
@click.option(
    "--rate",
    "-r",
    "rate_wpm",
    type=int,
    default=None,
    help="Optional speech rate (words per minute).",
)
@click.option(
    "--no-filter",
    "no_filter",
    is_flag=True,
    default=False,
    help="Disable automatic markdown and code filtering.",
)
@click.pass_context
def voice_speak(
    ctx: click.Context,
    message: str,
    voice_name: Optional[str],
    rate_wpm: Optional[int],
    no_filter: bool,
) -> None:
    """Vocalize a message out loud using the platform speech engine."""
    from hath0r_cli.bots.voice_speaker import VoiceSpeakerBot

    speaker = VoiceSpeakerBot()
    dry_run = bool(ctx.obj.get("dry_run", False))
    res = speaker.speak(
        text=message,
        voice_name=voice_name,
        rate_wpm=rate_wpm,
        filter_code=not no_filter,
        dry_run=dry_run,
    )

    response = _build_response(
        ctx,
        command="voice.speak",
        state="ok" if res.get("success") else "degraded",
        data=res,
    )

    def _text() -> None:
        console.print(f"[bold green]✓ Spoken Message:[/bold green] {res.get('text')}")

    _emit_response(ctx, response, text_renderer=_text)


@voice.command("announce")
@click.argument("message")
@click.option(
    "--queue",
    "-q",
    "queue_only",
    is_flag=True,
    default=False,
    help="Enqueue to spoken notification spool rather than speaking synchronously.",
)
@click.option(
    "--priority",
    type=click.Choice(["low", "normal", "high", "urgent"]),
    default="normal",
    help="Announcement priority level.",
)
@click.pass_context
def voice_announce(ctx: click.Context, message: str, queue_only: bool, priority: str) -> None:
    """Make a spoken announcement or queue it for background voice broadcaster."""
    from hath0r_cli.bots.voice_speaker import SpokenNotificationServiceBot, VoiceSpeakerBot

    if queue_only:
        svc = SpokenNotificationServiceBot()
        res = svc.queue_message(message=message, priority=priority)
        response = _build_response(
            ctx,
            command="voice.announce",
            state="ok",
            data=res,
        )

        def _text() -> None:
            console.print(f"[bold green]✓ Queued spoken announcement:[/bold green] {message}")

        _emit_response(ctx, response, text_renderer=_text)
    else:
        speaker = VoiceSpeakerBot()
        dry_run = bool(ctx.obj.get("dry_run", False))
        res = speaker.speak(text=message, dry_run=dry_run)
        response = _build_response(
            ctx,
            command="voice.announce",
            state="ok" if res.get("success") else "degraded",
            data=res,
        )

        def _text() -> None:
            console.print(f"[bold green]✓ Spoken Announcement:[/bold green] {res.get('text')}")

        _emit_response(ctx, response, text_renderer=_text)


@voice.group("speaker")
def voice_speaker() -> None:
    """Manage background spoken notification bot worker."""


@voice_speaker.command("start")
@click.option(
    "--background/--foreground",
    "background",
    default=True,
    show_default=True,
    help="Run as a background bot process or foreground loop.",
)
@click.pass_context
def voice_speaker_start(ctx: click.Context, background: bool) -> None:
    """Start the background spoken notification service worker."""
    from hath0r_cli.bots.voice_speaker import SpokenNotificationServiceBot

    svc = SpokenNotificationServiceBot()
    res = svc.start_bot(background=background)

    response = _build_response(
        ctx,
        command="voice.speaker.start",
        state="ok" if res.get("success") else "degraded",
        data=res,
    )

    def _text() -> None:
        if res.get("status") == "already_running":
            console.print(f"[yellow]● Speaker Bot is already running[/yellow] (PID: [bold]{res.get('pid')}[/bold])")
        elif res.get("status") == "started":
            console.print(f"[bold green]✓ Speaker Bot Started[/bold green] (PID: [bold]{res.get('pid')}[/bold])")
        else:
            console.print(res.get("message", "Speaker bot status updated."))

    _emit_response(ctx, response, text_renderer=_text)


@voice_speaker.command("stop")
@click.pass_context
def voice_speaker_stop(ctx: click.Context) -> None:
    """Stop the running background spoken notification service worker."""
    from hath0r_cli.bots.voice_speaker import SpokenNotificationServiceBot

    svc = SpokenNotificationServiceBot()
    res = svc.stop_bot()

    response = _build_response(
        ctx,
        command="voice.speaker.stop",
        state="ok" if res.get("success") else "degraded",
        data=res,
    )

    def _text() -> None:
        if res.get("status") == "stopped":
            console.print(f"[bold green]✓ Speaker Bot Stopped[/bold green] (PID: [dim]{res.get('pid')}[/dim])")
        else:
            console.print("[dim]Speaker bot is not currently running.[/dim]")

    _emit_response(ctx, response, text_renderer=_text)


@voice_speaker.command("status")
@click.pass_context
def voice_speaker_status(ctx: click.Context) -> None:
    """Check the status of the background spoken notification worker."""
    from hath0r_cli.bots.voice_speaker import SpokenNotificationServiceBot

    svc = SpokenNotificationServiceBot()
    res = svc.status()

    response = _build_response(
        ctx,
        command="voice.speaker.status",
        state="ok",
        data=res,
    )

    def _text() -> None:
        if res.get("running"):
            console.print(f"[bold green]● Speaker Bot is RUNNING[/bold green] (PID: [bold]{res.get('pid')}[/bold])")
            console.print(f"  • Pending Queue Messages: [cyan]{res.get('pending_count')}[/cyan]")
        else:
            console.print("[dim]○ Speaker Bot is STOPPED[/dim]")
            console.print(f"  • Pending Queue Messages: [cyan]{res.get('pending_count')}[/cyan]")

    _emit_response(ctx, response, text_renderer=_text)


@voice_speaker.command("drain")
@click.option("--max-messages", type=int, default=None, help="Maximum messages to drain.")
@click.pass_context
def voice_speaker_drain(ctx: click.Context, max_messages: Optional[int]) -> None:
    """Drain and speak all pending queued spoken announcements."""
    from hath0r_cli.bots.voice_speaker import SpokenNotificationServiceBot

    svc = SpokenNotificationServiceBot()
    dry_run = bool(ctx.obj.get("dry_run", False))
    items = svc.drain_queue(max_messages=max_messages, dry_run=dry_run)

    response = _build_response(
        ctx,
        command="voice.speaker.drain",
        state="ok",
        data={"drained_count": len(items), "items": items},
    )

    def _text() -> None:
        console.print(f"[bold green]✓ Drained {len(items)} queued announcements.[/bold green]")

    _emit_response(ctx, response, text_renderer=_text)


@voice.group("profile", invoke_without_command=True)
@click.pass_context
def voice_profile_group(ctx: click.Context) -> None:
    """Manage and configure speech synthesis voice profiles."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(voice_profile_list)


@voice_profile_group.command("list")
@click.option("--all", "show_all", is_flag=True, default=False, help="Show all installed platform voices.")
@click.pass_context
def voice_profile_list(ctx: click.Context, show_all: bool) -> None:
    """List available voice profiles and inspect current active voice."""
    from hath0r_cli.bots.voice_speaker import VoiceProfileBot

    bot = VoiceProfileBot()
    res = bot.list_profiles()

    response = _build_response(
        ctx,
        command="voice.profile.list",
        state="ok",
        data=res,
    )

    def _text() -> None:
        table = Table(title="HATH0R Speech Synthesis Voice Profiles")
        table.add_column("Status", style="bold", width=8)
        table.add_column("Voice Name", style="bold cyan")
        table.add_column("Quality", style="yellow")
        table.add_column("Locale", style="dim")
        table.add_column("Description")

        voices = res.get("voices", [])
        # If not show_all, prioritize English / common voices
        if not show_all:
            voices = [v for v in voices if "en" in v.get("locale", "").lower()] or voices[:15]

        for v in voices:
            status_icon = "[green]● ACTIVE[/green]" if v.get("is_active") else ""
            q_color = "bold green" if v.get("quality") == "premium" else "cyan"
            quality_str = f"[{q_color}]{v.get('quality', 'compact').upper()}[/]"
            table.add_row(status_icon, v.get("name", ""), quality_str, v.get("locale", ""), v.get("description", ""))

        console.print(table)
        active_prof = res.get("active_profile", {})
        v_name = active_prof.get("voice_name")
        r_wpm = active_prof.get("rate_wpm")
        console.print(f"Active Voice: [bold green]{v_name}[/bold green] (Rate: {r_wpm} WPM)")
        console.print(
            "  • Change voice: 'hath0r voice profile set <name> [--rate relaxed|natural|standard|brisk|fast|<wpm>]'"
        )

    _emit_response(ctx, response, text_renderer=_text)


@voice_profile_group.command("set")
@click.argument("voice_name")
@click.option(
    "--rate",
    "-r",
    "rate_wpm",
    type=str,
    default=None,
    help="Optional speech rate (WPM or preset: relaxed, natural, standard, brisk, fast).",
)
@click.option("--no-preview", is_flag=True, default=False, help="Set voice without vocal preview.")
@click.pass_context
def voice_profile_set(ctx: click.Context, voice_name: str, rate_wpm: Optional[str], no_preview: bool) -> None:
    """Set and persist the active voice profile for all spoken outputs."""
    from hath0r_cli.bots.voice_speaker import VoiceProfileBot

    bot = VoiceProfileBot()
    dry_run = bool(ctx.obj.get("dry_run", False))
    res = bot.set_profile(
        voice_name=voice_name,
        rate_wpm=rate_wpm,
        preview=not no_preview and not dry_run,
        dry_run=dry_run,
    )

    response = _build_response(
        ctx,
        command="voice.profile.set",
        state="ok",
        data=res,
    )

    def _text() -> None:
        console.print(f"[bold green]✓ Voice Profile Set:[/bold green] [cyan]{res.get('voice_name')}[/cyan]")
        console.print(f"  • Speech Rate: {res.get('rate_wpm')} WPM")
        console.print(f"  • Configuration saved to {res.get('config_file')}")

    _emit_response(ctx, response, text_renderer=_text)


@voice_profile_group.command("status")
@click.pass_context
def voice_profile_status(ctx: click.Context) -> None:
    """Get active voice profile status."""
    from hath0r_cli.bots.voice_speaker import VoiceProfileBot

    bot = VoiceProfileBot()
    res = bot.get_active_profile()

    response = _build_response(
        ctx,
        command="voice.profile.status",
        state="ok",
        data=res,
    )

    def _text() -> None:
        v_name = res.get("voice_name")
        r_wpm = res.get("rate_wpm")
        console.print(f"Active Voice Profile: [bold green]{v_name}[/bold green] (Rate: {r_wpm} WPM)")

    _emit_response(ctx, response, text_renderer=_text)


@voice.command("read")
@click.argument("text", required=False, default=None)
@click.option(
    "--selection",
    "-s",
    is_flag=True,
    default=False,
    help="Read highlighted/selected text from active app (Warp, Antigravity, VS Code).",
)
@click.pass_context
def voice_read(ctx: click.Context, text: Optional[str], selection: bool) -> None:
    """Read and speak active tab text, input text, or highlighted selection aloud."""
    from hath0r_cli.bots.voice_speaker import ActiveTabReaderBot

    bot = ActiveTabReaderBot()
    dry_run = bool(ctx.obj.get("dry_run", False))

    if selection or text is None:
        res = bot.read_selection(dry_run=dry_run)
    else:
        res = bot.read_text(text, dry_run=dry_run)

    state = "ok" if res.get("success") else "error"
    response = _build_response(
        ctx,
        command="voice.read",
        state=state,
        data=res,
    )

    def _text() -> None:
        if res.get("success"):
            console.print(f"[bold green]✓ Vocalized from {res.get('app')}:[/bold green] {res.get('spoken_text')}")
        else:
            console.print(f"[bold red]✗ Failed to read active window:[/bold red] {res.get('error')}")

    _emit_response(ctx, response, text_renderer=_text)


@voice.group("engine", invoke_without_command=True)
@click.pass_context
def voice_engine_group(ctx: click.Context) -> None:
    """Manage local neural and platform speech synthesis engines (CoreML / ONNX / say)."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(voice_engine_list)


@voice_engine_group.command("list")
@click.pass_context
def voice_engine_list(ctx: click.Context) -> None:
    """List available local neural (CoreML / ONNX) and platform speech engines."""
    from hath0r_cli.bots.voice_speaker import LocalNeuralVoiceEngine

    engine = LocalNeuralVoiceEngine()
    engines = engine.list_supported_engines()
    status = engine.get_models_status()

    response = _build_response(
        ctx,
        command="voice.engine.list",
        state="ok",
        data={"engines": engines, "status": status, "count": len(engines)},
    )

    def _text() -> None:
        table = Table(title="HATH0R Local Neural & Platform Voice Engines")
        table.add_column("Engine ID", style="bold cyan")
        table.add_column("Type", style="dim")
        table.add_column("Availability")
        table.add_column("Description")

        for eng in engines:
            avail = (
                "[green]● AVAILABLE[/green]"
                if eng.get("available")
                else "[dim]○ OFFLINE (model weights not found)[/dim]"
            )
            table.add_row(eng.get("id"), eng.get("type"), avail, eng.get("description"))

        console.print(table)
        console.print(f"  • Models Directory: [cyan]{status.get('models_dir')}[/cyan]")
        console.print("  • CoreML 82M: High-efficiency local neural speech engine for Apple Silicon.")
        console.print("  • Download weights: 'hath0r voice engine download --engine coreml-82m'")

    _emit_response(ctx, response, text_renderer=_text)


@voice_engine_group.command("download")
@click.option(
    "--engine",
    "-e",
    "engine_id",
    type=click.Choice(["coreml-82m", "onnx-neural"], case_sensitive=False),
    default="coreml-82m",
    help="Neural model engine weights to download.",
)
@click.option("--dry-run", is_flag=True, default=False, help="Simulate download without filesystem changes.")
@click.pass_context
def voice_engine_download(ctx: click.Context, engine_id: str, dry_run: bool) -> None:
    """Download and cache offline local neural weights (Kokoro-82M CoreML/ONNX)."""
    from hath0r_cli.bots.voice_speaker import LocalNeuralVoiceEngine

    engine = LocalNeuralVoiceEngine()
    is_dry_run = dry_run or bool(ctx.obj.get("dry_run", False))
    res = engine.download_weights(engine_id=engine_id, dry_run=is_dry_run)

    response = _build_response(
        ctx,
        command="voice.engine.download",
        state="ok",
        data=res,
    )

    def _text() -> None:
        console.print(f"[bold green]✓ {res.get('message')}[/bold green]")
        console.print(f"  • Target Path: [cyan]{res.get('target_path')}[/cyan]")

    _emit_response(ctx, response, text_renderer=_text)


@click.group("speak", invoke_without_command=True)
@click.pass_context
def speak_group(ctx: click.Context) -> None:
    """Manage global Hath0r spoken feedback mode (vocalize all agent outputs)."""
    if ctx.invoked_subcommand is None:
        from hath0r_cli.bots.voice_speaker import VoiceSpeakerModeBot

        bot = VoiceSpeakerModeBot()
        st = bot.status()
        response = _build_response(
            ctx,
            command="speak.status",
            state="ok",
            data=st,
        )

        def _text() -> None:
            state_label = "[bold green]ENABLED[/bold green]" if st["enabled"] else "[dim]DISABLED[/dim]"
            scope_label = f" (Scope: [cyan]{st.get('scope', 'global')}[/cyan])" if st["enabled"] else ""
            console.print(f"Hath0r Speak Mode: {state_label}{scope_label}")
            if st.get("scope") == "tab" and st.get("saved_tab"):
                console.print(f"  • Scoped Tab: {st.get('saved_tab')}")
            console.print("  • Use 'hath0r speak on' to enable across all tabs.")
            console.print("  • Use 'hath0r speak on --tab-only' for active tab only.")
            console.print("  • Use 'hath0r speak off' to disable automatic voice responses.")

        _emit_response(ctx, response, text_renderer=_text)


@speak_group.command("on")
@click.option(
    "--tab-only",
    "--this-tab",
    "tab_only",
    is_flag=True,
    default=False,
    help="Enable speak mode only for the current active terminal tab.",
)
@click.option("--silent", is_flag=True, default=False, help="Enable without vocal announcement.")
@click.pass_context
def speak_on(ctx: click.Context, tab_only: bool, silent: bool) -> None:
    """Turn ON spoken feedback mode (globally or for the current active tab only)."""
    from hath0r_cli.bots.voice_speaker import VoiceSpeakerModeBot

    bot = VoiceSpeakerModeBot()
    dry_run = bool(ctx.obj.get("dry_run", False))
    res = bot.enable(tab_only=tab_only, speak=not silent and not dry_run, dry_run=dry_run)

    response = _build_response(
        ctx,
        command="speak.on",
        state="ok",
        data=res,
    )

    def _text() -> None:
        scope_str = "ACTIVE TAB ONLY" if res.get("scope") == "tab" else "GLOBAL (ALL TABS)"
        console.print(f"[bold green]✓ Hath0r Speak Mode: ENABLED ({scope_str})[/bold green]")
        if res.get("tab_id"):
            console.print(f"  • Bound to Tab: [cyan]{res.get('tab_id')}[/cyan]")
        console.print("  • The agent will now vocalize all actions and responses out loud.")

    _emit_response(ctx, response, text_renderer=_text)


@speak_group.command("off")
@click.option("--silent", is_flag=True, default=False, help="Disable without vocal announcement.")
@click.pass_context
def speak_off(ctx: click.Context, silent: bool) -> None:
    """Turn OFF global spoken feedback mode."""
    from hath0r_cli.bots.voice_speaker import VoiceSpeakerModeBot

    bot = VoiceSpeakerModeBot()
    dry_run = bool(ctx.obj.get("dry_run", False))
    res = bot.disable(speak=not silent and not dry_run, dry_run=dry_run)

    response = _build_response(
        ctx,
        command="speak.off",
        state="ok",
        data=res,
    )

    def _text() -> None:
        console.print("[dim]○ Hath0r Speak Mode: DISABLED[/dim]")

    _emit_response(ctx, response, text_renderer=_text)


@speak_group.command("toggle")
@click.option(
    "--tab-only",
    "--this-tab",
    "tab_only",
    is_flag=True,
    default=False,
    help="Toggle speak mode scoped to active tab only.",
)
@click.pass_context
def speak_toggle(ctx: click.Context, tab_only: bool) -> None:
    """Toggle spoken feedback mode between on and off."""
    from hath0r_cli.bots.voice_speaker import VoiceSpeakerModeBot

    bot = VoiceSpeakerModeBot()
    dry_run = bool(ctx.obj.get("dry_run", False))
    res = bot.toggle(tab_only=tab_only, speak=not dry_run, dry_run=dry_run)

    response = _build_response(
        ctx,
        command="speak.toggle",
        state="ok",
        data=res,
    )

    def _text() -> None:
        if res.get("enabled"):
            scope_str = "ACTIVE TAB ONLY" if res.get("scope") == "tab" else "GLOBAL"
            console.print(f"[bold green]✓ Hath0r Speak Mode: ENABLED ({scope_str})[/bold green]")
        else:
            console.print("[dim]○ Hath0r Speak Mode: DISABLED[/dim]")

    _emit_response(ctx, response, text_renderer=_text)


@speak_group.command("status")
@click.pass_context
def speak_status(ctx: click.Context) -> None:
    """Check if global spoken feedback mode is active."""
    from hath0r_cli.bots.voice_speaker import VoiceSpeakerModeBot

    bot = VoiceSpeakerModeBot()
    st = bot.status()

    response = _build_response(
        ctx,
        command="speak.status",
        state="ok",
        data=st,
    )

    def _text() -> None:
        state_label = "[bold green]ENABLED[/bold green]" if st["enabled"] else "[dim]DISABLED[/dim]"
        console.print(f"Hath0r Speak Mode: {state_label}")

    _emit_response(ctx, response, text_renderer=_text)


@voice.group("service")
def voice_service() -> None:
    """Manage background voice listening and conversational service bot."""


@voice_service.command("start")
@click.option(
    "--background/--foreground",
    "background",
    default=True,
    show_default=True,
    help="Run as a background bot process or foreground loop.",
)
@click.option(
    "--ambient/--push-to-talk",
    "ambient",
    default=True,
    show_default=True,
    help="Enable ambient continuous listening or push-to-talk mode.",
)
@click.option(
    "-t",
    "--trust-tier",
    type=click.Choice(["guest", "elevated", "sovereign"], case_sensitive=False),
    default="elevated",
    show_default=True,
    help="Execution authorization tier.",
)
@click.pass_context
def voice_service_start(
    ctx: click.Context,
    background: bool,
    ambient: bool,
    trust_tier: str,
) -> None:
    """Start the background voice listener bot service."""
    from hath0r_cli.bots.voice_converse import VoiceServiceBot

    bot = VoiceServiceBot()
    res = bot.start_service(background=background, ambient=ambient, trust_tier=trust_tier)

    response = _build_response(
        ctx,
        command="voice.service.start",
        state="ok" if res.get("success") else "degraded",
        data=res,
    )

    def _text() -> None:
        if res.get("status") == "already_running":
            console.print(
                f"[yellow]● Voice Bot Service is already running[/yellow] (PID: [bold]{res.get('pid')}[/bold])"
            )
        elif res.get("status") == "started":
            mode_str = "Ambient Continuous" if ambient else "Push-to-Talk"
            console.print(f"[bold green]✓ Voice Bot Service Started[/bold green] (PID: [bold]{res.get('pid')}[/bold])")
            console.print(f"  • Mode: [cyan]{mode_str}[/cyan]")
            console.print(f"  • Trust Tier: [magenta]{trust_tier}[/magenta]")
            console.print(f"  • Log File: [dim]{res.get('log_file')}[/dim]")
        else:
            console.print(res.get("message", "Voice service status updated."))

    _emit_response(ctx, response, text_renderer=_text)


@voice_service.command("stop")
@click.pass_context
def voice_service_stop(ctx: click.Context) -> None:
    """Stop the active background voice listener bot service."""
    from hath0r_cli.bots.voice_converse import VoiceServiceBot

    bot = VoiceServiceBot()
    res = bot.stop_service()

    response = _build_response(
        ctx,
        command="voice.service.stop",
        state="ok" if res.get("success") else "degraded",
        data=res,
    )

    def _text() -> None:
        if res.get("status") == "stopped":
            console.print(f"[bold green]✓ Voice Bot Service Stopped[/bold green] (PID: [dim]{res.get('pid')}[/dim])")
        else:
            console.print("[dim]Voice bot service is not currently running.[/dim]")

    _emit_response(ctx, response, text_renderer=_text)


@voice_service.command("status")
@click.pass_context
def voice_service_status(ctx: click.Context) -> None:
    """Check the status of the background voice listener bot service."""
    from hath0r_cli.bots.voice_converse import VoiceServiceBot

    bot = VoiceServiceBot()
    res = bot.status()

    response = _build_response(
        ctx,
        command="voice.service.status",
        state="ok",
        data=res,
    )

    def _text() -> None:
        if res.get("running"):
            console.print(
                f"[bold green]● Voice Bot Service is RUNNING[/bold green] (PID: [bold]{res.get('pid')}[/bold])"
            )
            if res.get("log_file"):
                console.print(f"  • Log File: [dim]{res.get('log_file')}[/dim]")
        else:
            console.print("[dim]○ Voice Bot Service is STOPPED[/dim]")

    _emit_response(ctx, response, text_renderer=_text)


@voice_service.command("restart")
@click.option(
    "--ambient/--push-to-talk",
    "ambient",
    default=True,
    show_default=True,
    help="Enable ambient continuous listening or push-to-talk mode.",
)
@click.option(
    "-t",
    "--trust-tier",
    type=click.Choice(["guest", "elevated", "sovereign"], case_sensitive=False),
    default="elevated",
    show_default=True,
    help="Execution authorization tier.",
)
@click.pass_context
def voice_service_restart(
    ctx: click.Context,
    ambient: bool,
    trust_tier: str,
) -> None:
    """Restart the background voice listener bot service."""
    from hath0r_cli.bots.voice_converse import VoiceServiceBot

    bot = VoiceServiceBot()
    bot.stop_service()
    res = bot.start_service(background=True, ambient=ambient, trust_tier=trust_tier)

    response = _build_response(
        ctx,
        command="voice.service.restart",
        state="ok" if res.get("success") else "degraded",
        data=res,
    )

    def _text() -> None:
        mode_str = "Ambient Continuous" if ambient else "Push-to-Talk"
        console.print(f"[bold green]✓ Voice Bot Service Restarted[/bold green] (PID: [bold]{res.get('pid')}[/bold])")
        console.print(f"  • Mode: [cyan]{mode_str}[/cyan]")
        console.print(f"  • Trust Tier: [magenta]{trust_tier}[/magenta]")

    _emit_response(ctx, response, text_renderer=_text)


@voice_service.command("install")
@click.option(
    "--ambient/--push-to-talk",
    "ambient",
    default=True,
    show_default=True,
    help="Enable ambient continuous listening or push-to-talk mode.",
)
@click.option(
    "-t",
    "--trust-tier",
    type=click.Choice(["guest", "elevated", "sovereign"], case_sensitive=False),
    default="elevated",
    show_default=True,
    help="Execution authorization tier.",
)
@click.pass_context
def voice_service_install(
    ctx: click.Context,
    ambient: bool,
    trust_tier: str,
) -> None:
    """Install Hath0r voice service as a native OS background service (launchd/systemd)."""
    from hath0r_cli.bots.voice_converse import VoiceServiceBot

    bot = VoiceServiceBot()
    res = bot.install_os_service(ambient=ambient, trust_tier=trust_tier, speak=True)

    response = _build_response(
        ctx,
        command="voice.service.install",
        state="ok" if res.get("success") else "degraded",
        data=res,
    )

    def _text() -> None:
        if res.get("success"):
            mgr = res.get("service_manager")
            console.print(f"[bold green]✓ Hath0r Voice OS Service Installed[/bold green] ({mgr})")
            console.print(f"  • Path: [dim]{res.get('plist_path') or res.get('service_path')}[/dim]")
            console.print("  • Status: [cyan]Registered with OS session[/cyan]")
        else:
            console.print(f"[bold red]✗ Failed to install OS service:[/bold red] {res.get('error')}")

    _emit_response(ctx, response, text_renderer=_text)


@voice_service.command("uninstall")
@click.pass_context
def voice_service_uninstall(ctx: click.Context) -> None:
    """Uninstall and remove Hath0r voice service from native OS background service."""
    from hath0r_cli.bots.voice_converse import VoiceServiceBot

    bot = VoiceServiceBot()
    res = bot.uninstall_os_service(speak=True)

    response = _build_response(
        ctx,
        command="voice.service.uninstall",
        state="ok" if res.get("success") else "degraded",
        data=res,
    )

    def _text() -> None:
        if res.get("success"):
            console.print("[bold green]✓ Hath0r Voice OS Service Uninstalled[/bold green]")
            console.print(f"  • {res.get('message')}")
        else:
            console.print(f"[bold red]✗ Failed to uninstall OS service:[/bold red] {res.get('error')}")

    _emit_response(ctx, response, text_renderer=_text)



