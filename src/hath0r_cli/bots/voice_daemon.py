"""Persistent Voice Audio Streaming and IPC Event Broadcast Daemon for Hath0r."""

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from hath0r_cli.bots.voice_speaker import VoiceSpeakerBot, filter_speech_text


class VoiceDaemonBot:
    """Manages ambient voice streaming, event IPC, and spoken task feedback."""

    def __init__(self, cwd: Optional[Path] = None):
        self.cwd = cwd or Path.cwd()
        self.state_dir = self.cwd / ".hath0r" / "state"
        self.pid_file = self.state_dir / "voice_daemon.pid"
        self.state_file = self.state_dir / "voice_daemon.json"
        self.events_file = self.state_dir / "voice_events.jsonl"
        self.socket_path = self.state_dir / "voice_daemon.sock"

    def _ensure_dirs(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def is_running(self) -> Tuple[bool, Optional[int]]:
        """Check if voice daemon is currently running."""
        if not self.pid_file.is_file():
            return False, None
        try:
            pid = int(self.pid_file.read_text(encoding="utf-8").strip())
            os.kill(pid, 0)
            return True, pid
        except (ValueError, OSError, ProcessLookupError):
            try:
                self.pid_file.unlink(missing_ok=True)
            except OSError:
                pass
            return False, None

    def start_daemon(self, background: bool = True) -> Dict[str, Any]:
        """Start the persistent voice streaming daemon."""
        self._ensure_dirs()
        running, pid = self.is_running()
        if running:
            return {
                "success": True,
                "status": "already_running",
                "pid": pid,
                "message": f"Voice daemon is already running (PID: {pid})",
            }

        if background:
            cmd = [
                sys.executable,
                "-m",
                "hath0r_cli.bots.voice_daemon",
                "--run-loop",
                "--dir",
                str(self.cwd),
            ]
            proc = subprocess.Popen(
                cmd,
                cwd=str(self.cwd),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
            # Give daemon process a moment to initialize
            time.sleep(0.3)
            self.pid_file.write_text(str(proc.pid), encoding="utf-8")
            return {
                "success": True,
                "status": "started",
                "pid": proc.pid,
                "mode": "background",
                "socket": str(self.socket_path),
            }
        else:
            self.run_daemon_loop()
            return {"success": True, "status": "stopped"}

    def stop_daemon(self) -> Dict[str, Any]:
        """Stop running voice daemon."""
        running, pid = self.is_running()
        if not running or pid is None:
            return {
                "success": True,
                "status": "not_running",
                "message": "Voice daemon is not running.",
            }

        try:
            os.kill(pid, signal.SIGTERM)
            for _ in range(20):
                time.sleep(0.1)
                try:
                    os.kill(pid, 0)
                except OSError:
                    break
        except OSError:
            pass

        self.pid_file.unlink(missing_ok=True)
        if self.socket_path.exists():
            try:
                self.socket_path.unlink(missing_ok=True)
            except OSError:
                pass

        return {
            "success": True,
            "status": "stopped",
            "pid": pid,
            "message": f"Voice daemon stopped (PID: {pid}).",
        }

    def status(self) -> Dict[str, Any]:
        """Get live status and telemetry of voice daemon."""
        running, pid = self.is_running()
        state_data: Dict[str, Any] = {}
        if self.state_file.is_file():
            try:
                state_data = json.loads(self.state_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        return {
            "running": running,
            "pid": pid,
            "socket": str(self.socket_path),
            "state_file": str(self.state_file),
            "uptime_seconds": state_data.get("uptime_seconds", 0.0) if running else 0.0,
            "events_processed": state_data.get("events_processed", 0) if running else 0,
            "last_event": state_data.get("last_event") if running else None,
        }

    def emit_event(
        self,
        event_type: str,
        message: str,
        payload: Optional[Dict[str, Any]] = None,
        speak: bool = True,
    ) -> Dict[str, Any]:
        """Emit a task/system lifecycle event to the running daemon or fallback spool."""
        self._ensure_dirs()
        event_record = {
            "id": f"evt-{int(time.time() * 1000)}",
            "type": event_type,
            "message": message,
            "payload": payload or {},
            "speak": speak,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        running, _ = self.is_running()

        # Try Unix Domain Socket IPC first
        delivered_socket = False
        if running and self.socket_path.exists():
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                    s.settimeout(1.0)
                    s.connect(str(self.socket_path))
                    payload_bytes = json.dumps(event_record).encode("utf-8") + b"\n"
                    s.sendall(payload_bytes)
                    delivered_socket = True
            except Exception:
                delivered_socket = False

        # Fallback to persistent events spool file
        if not delivered_socket:
            with open(self.events_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event_record) + "\n")

        # If daemon not running and direct speak requested, vocalize via VoiceSpeakerBot
        if not running and speak:
            try:
                speaker = VoiceSpeakerBot()
                speaker.speak(filter_speech_text(message))
            except Exception:
                pass

        return {
            "success": True,
            "event_id": event_record["id"],
            "event_type": event_type,
            "ipc_delivery": "socket" if delivered_socket else "file_spool",
            "message": message,
        }

    def run_daemon_loop(self) -> None:
        """Main blocking event loop for voice daemon worker."""
        self._ensure_dirs()
        self.pid_file.write_text(str(os.getpid()), encoding="utf-8")

        start_time = time.time()
        events_processed = 0
        last_event = None
        speaker = VoiceSpeakerBot()

        # Clean up stale socket if present
        if self.socket_path.exists():
            try:
                self.socket_path.unlink()
            except OSError:
                pass

        server_sock: Optional[socket.socket] = None
        try:
            server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server_sock.bind(str(self.socket_path))
            server_sock.listen(5)
            server_sock.settimeout(0.5)
        except Exception:
            server_sock = None

        running = True

        def _handle_signal(sig: int, frame: Any) -> None:
            nonlocal running
            running = False

        signal.signal(signal.SIGTERM, _handle_signal)
        signal.signal(signal.SIGINT, _handle_signal)

        try:
            while running:
                # 1. Accept IPC socket events
                if server_sock:
                    try:
                        conn, _ = server_sock.accept()
                        with conn:
                            conn.settimeout(0.5)
                            data = conn.recv(8192)
                            if data:
                                evt = json.loads(data.decode("utf-8").strip())
                                events_processed += 1
                                last_event = evt
                                msg = evt.get("message", "")
                                if evt.get("speak", True) and msg:
                                    clean_text = filter_speech_text(msg)
                                    speaker.speak(clean_text)
                    except (socket.timeout, OSError):
                        pass

                # 2. Drain file event spool if any
                if self.events_file.is_file() and self.events_file.stat().st_size > 0:
                    try:
                        lines = self.events_file.read_text(encoding="utf-8").splitlines()
                        self.events_file.unlink(missing_ok=True)
                        for line in lines:
                            if not line.strip():
                                continue
                            evt = json.loads(line)
                            events_processed += 1
                            last_event = evt
                            msg = evt.get("message", "")
                            if evt.get("speak", True) and msg:
                                clean_text = filter_speech_text(msg)
                                speaker.speak(clean_text)
                    except Exception:
                        pass

                # 3. Update telemetry state snapshot
                telemetry = {
                    "running": True,
                    "pid": os.getpid(),
                    "start_time": datetime.fromtimestamp(start_time, tz=timezone.utc).isoformat(),
                    "uptime_seconds": round(time.time() - start_time, 1),
                    "events_processed": events_processed,
                    "last_event": last_event,
                }
                self.state_file.write_text(json.dumps(telemetry, indent=2), encoding="utf-8")

                time.sleep(0.2)

        finally:
            if server_sock:
                try:
                    server_sock.close()
                except OSError:
                    pass
            if self.socket_path.exists():
                try:
                    self.socket_path.unlink()
                except OSError:
                    pass
            self.pid_file.unlink(missing_ok=True)
            self.state_file.write_text(
                json.dumps({"running": False, "events_processed": events_processed}, indent=2),
                encoding="utf-8",
            )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--run-loop", action="store_true")
    parser.add_argument("--dir", default=None)
    args = parser.parse_args()

    target_dir = Path(args.dir) if args.dir else Path.cwd()
    bot = VoiceDaemonBot(cwd=target_dir)
    bot.run_daemon_loop()
