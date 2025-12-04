"""
BharatBuild CLI Notification Sounds

Plays notification sounds for events:
  /sounds on     Enable sounds
  /sounds off    Disable sounds
"""

import os
import sys
import threading
from typing import Optional, Dict, Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from rich.console import Console


class SoundEvent(str, Enum):
    """Events that can trigger sounds"""
    COMPLETE = "complete"       # Task completed
    ERROR = "error"             # Error occurred
    ATTENTION = "attention"     # Needs user attention
    MESSAGE = "message"         # New message
    START = "start"             # Task started
    SUCCESS = "success"         # Success
    WARNING = "warning"         # Warning


@dataclass
class SoundConfig:
    """Sound configuration"""
    enabled: bool = True
    volume: float = 0.5  # 0.0 to 1.0
    use_system_sounds: bool = True
    custom_sounds: Dict[SoundEvent, str] = None  # Event -> file path


class NotificationSounds:
    """
    Manages notification sounds.

    Usage:
        sounds = NotificationSounds(console)

        # Play sound
        sounds.play(SoundEvent.COMPLETE)

        # Toggle sounds
        sounds.toggle()

        # Set volume
        sounds.set_volume(0.7)
    """

    # System bell/beep patterns (terminal bell codes)
    BELL_PATTERNS = {
        SoundEvent.COMPLETE: 1,      # Single beep
        SoundEvent.ERROR: 3,         # Triple beep
        SoundEvent.ATTENTION: 2,     # Double beep
        SoundEvent.MESSAGE: 1,       # Single beep
        SoundEvent.START: 1,         # Single beep
        SoundEvent.SUCCESS: 1,       # Single beep
        SoundEvent.WARNING: 2,       # Double beep
    }

    def __init__(
        self,
        console: Console,
        config: Optional[SoundConfig] = None
    ):
        self.console = console
        self.config = config or SoundConfig()
        self._sound_available = self._check_sound_support()

    def _check_sound_support(self) -> bool:
        """Check if sound playback is available"""
        # Check for various sound libraries
        try:
            # Try playsound
            import playsound
            return True
        except ImportError:
            pass

        try:
            # Try pygame
            import pygame
            pygame.mixer.init()
            return True
        except ImportError:
            pass

        try:
            # Try simpleaudio
            import simpleaudio
            return True
        except ImportError:
            pass

        # Terminal bell is always available
        return True

    def play(self, event: SoundEvent, async_play: bool = True):
        """Play sound for an event"""
        if not self.config.enabled:
            return

        if async_play:
            thread = threading.Thread(target=self._play_sound, args=(event,), daemon=True)
            thread.start()
        else:
            self._play_sound(event)

    def _play_sound(self, event: SoundEvent):
        """Internal sound playback"""
        # Try custom sound first
        if self.config.custom_sounds and event in self.config.custom_sounds:
            sound_file = self.config.custom_sounds[event]
            if self._play_file(sound_file):
                return

        # Try system sounds
        if self.config.use_system_sounds:
            if self._play_system_sound(event):
                return

        # Fall back to terminal bell
        self._play_bell(event)

    def _play_file(self, path: str) -> bool:
        """Play a sound file"""
        if not os.path.exists(path):
            return False

        try:
            # Try playsound
            import playsound
            playsound.playsound(path, block=False)
            return True
        except ImportError:
            pass
        except Exception:
            pass

        try:
            # Try pygame
            import pygame
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self.config.volume)
            pygame.mixer.music.play()
            return True
        except ImportError:
            pass
        except Exception:
            pass

        try:
            # Try simpleaudio
            import simpleaudio as sa
            wave_obj = sa.WaveObject.from_wave_file(path)
            wave_obj.play()
            return True
        except ImportError:
            pass
        except Exception:
            pass

        return False

    def _play_system_sound(self, event: SoundEvent) -> bool:
        """Play system notification sound"""
        if sys.platform == "darwin":
            # macOS
            return self._play_macos_sound(event)
        elif sys.platform == "win32":
            # Windows
            return self._play_windows_sound(event)
        else:
            # Linux
            return self._play_linux_sound(event)

    def _play_macos_sound(self, event: SoundEvent) -> bool:
        """Play macOS system sound"""
        sound_map = {
            SoundEvent.COMPLETE: "Glass",
            SoundEvent.ERROR: "Basso",
            SoundEvent.ATTENTION: "Ping",
            SoundEvent.MESSAGE: "Pop",
            SoundEvent.SUCCESS: "Hero",
            SoundEvent.WARNING: "Sosumi",
        }

        sound_name = sound_map.get(event, "Pop")

        try:
            import subprocess
            subprocess.run(
                ["afplay", f"/System/Library/Sounds/{sound_name}.aiff"],
                capture_output=True,
                timeout=2
            )
            return True
        except Exception:
            return False

    def _play_windows_sound(self, event: SoundEvent) -> bool:
        """Play Windows system sound"""
        try:
            import winsound

            sound_map = {
                SoundEvent.COMPLETE: winsound.MB_OK,
                SoundEvent.ERROR: winsound.MB_ICONHAND,
                SoundEvent.ATTENTION: winsound.MB_ICONEXCLAMATION,
                SoundEvent.MESSAGE: winsound.MB_OK,
                SoundEvent.SUCCESS: winsound.MB_OK,
                SoundEvent.WARNING: winsound.MB_ICONEXCLAMATION,
            }

            sound_type = sound_map.get(event, winsound.MB_OK)
            winsound.MessageBeep(sound_type)
            return True

        except ImportError:
            return False
        except Exception:
            return False

    def _play_linux_sound(self, event: SoundEvent) -> bool:
        """Play Linux system sound"""
        try:
            import subprocess

            # Try paplay (PulseAudio)
            sound_map = {
                SoundEvent.COMPLETE: "/usr/share/sounds/freedesktop/stereo/complete.oga",
                SoundEvent.ERROR: "/usr/share/sounds/freedesktop/stereo/dialog-error.oga",
                SoundEvent.ATTENTION: "/usr/share/sounds/freedesktop/stereo/bell.oga",
                SoundEvent.MESSAGE: "/usr/share/sounds/freedesktop/stereo/message.oga",
            }

            sound_file = sound_map.get(event)
            if sound_file and os.path.exists(sound_file):
                subprocess.run(["paplay", sound_file], capture_output=True, timeout=2)
                return True

        except Exception:
            pass

        return False

    def _play_bell(self, event: SoundEvent):
        """Play terminal bell"""
        beeps = self.BELL_PATTERNS.get(event, 1)

        for _ in range(beeps):
            print("\a", end="", flush=True)
            if beeps > 1:
                import time
                time.sleep(0.1)

    def toggle(self) -> bool:
        """Toggle sounds on/off"""
        self.config.enabled = not self.config.enabled
        status = "enabled" if self.config.enabled else "disabled"
        self.console.print(f"[green]✓ Sounds {status}[/green]")
        return self.config.enabled

    def enable(self):
        """Enable sounds"""
        self.config.enabled = True
        self.console.print("[green]✓ Sounds enabled[/green]")

    def disable(self):
        """Disable sounds"""
        self.config.enabled = False
        self.console.print("[green]✓ Sounds disabled[/green]")

    def set_volume(self, volume: float):
        """Set volume (0.0 to 1.0)"""
        self.config.volume = max(0.0, min(1.0, volume))
        self.console.print(f"[green]✓ Volume set to {int(self.config.volume * 100)}%[/green]")

    def test(self):
        """Test all sounds"""
        self.console.print("[cyan]Testing sounds...[/cyan]")

        import time
        for event in SoundEvent:
            self.console.print(f"  Playing: {event.value}")
            self.play(event, async_play=False)
            time.sleep(0.5)

        self.console.print("[green]✓ Sound test complete[/green]")

    def show_status(self):
        """Show sound status"""
        status = "enabled" if self.config.enabled else "disabled"
        volume = int(self.config.volume * 100)

        self.console.print(f"[bold]Sounds:[/bold] {status}")
        self.console.print(f"[bold]Volume:[/bold] {volume}%")
        self.console.print(f"[bold]System sounds:[/bold] {'yes' if self.config.use_system_sounds else 'no'}")
        self.console.print(f"[bold]Sound support:[/bold] {'available' if self._sound_available else 'limited (bell only)'}")


class DesktopNotifications:
    """
    Desktop notifications for important events.

    Usage:
        notifier = DesktopNotifications()
        notifier.notify("Task Complete", "Your code has been generated.")
    """

    def __init__(self, app_name: str = "BharatBuild AI"):
        self.app_name = app_name
        self._available = self._check_support()

    def _check_support(self) -> bool:
        """Check if desktop notifications are available"""
        try:
            from plyer import notification
            return True
        except ImportError:
            pass

        if sys.platform == "darwin":
            return True  # osascript always available

        if sys.platform == "win32":
            try:
                from win10toast import ToastNotifier
                return True
            except ImportError:
                pass

        return False

    def notify(
        self,
        title: str,
        message: str,
        timeout: int = 5,
        icon: Optional[str] = None
    ):
        """Send a desktop notification"""
        if not self._available:
            return

        try:
            # Try plyer (cross-platform)
            from plyer import notification
            notification.notify(
                title=title,
                message=message,
                app_name=self.app_name,
                timeout=timeout
            )
            return
        except ImportError:
            pass
        except Exception:
            pass

        if sys.platform == "darwin":
            self._notify_macos(title, message)
        elif sys.platform == "win32":
            self._notify_windows(title, message, timeout)
        else:
            self._notify_linux(title, message, timeout)

    def _notify_macos(self, title: str, message: str):
        """macOS notification via osascript"""
        try:
            import subprocess
            script = f'display notification "{message}" with title "{title}"'
            subprocess.run(["osascript", "-e", script], capture_output=True)
        except Exception:
            pass

    def _notify_windows(self, title: str, message: str, timeout: int):
        """Windows notification"""
        try:
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            toaster.show_toast(title, message, duration=timeout, threaded=True)
        except ImportError:
            pass
        except Exception:
            pass

    def _notify_linux(self, title: str, message: str, timeout: int):
        """Linux notification via notify-send"""
        try:
            import subprocess
            subprocess.run([
                "notify-send",
                "-t", str(timeout * 1000),
                title,
                message
            ], capture_output=True)
        except Exception:
            pass


class NotificationManager:
    """
    Combined notification manager for sounds and desktop notifications.

    Usage:
        notifications = NotificationManager(console)

        # Notify completion
        notifications.notify_complete("Project generated successfully!")

        # Notify error
        notifications.notify_error("Build failed")
    """

    def __init__(
        self,
        console: Console,
        enable_sounds: bool = True,
        enable_desktop: bool = True
    ):
        self.console = console
        self.sounds = NotificationSounds(console)
        self.desktop = DesktopNotifications()

        self.sounds.config.enabled = enable_sounds
        self._desktop_enabled = enable_desktop

    def notify_complete(self, message: str = "Task complete"):
        """Notify task completion"""
        self.sounds.play(SoundEvent.COMPLETE)
        if self._desktop_enabled:
            self.desktop.notify("BharatBuild AI", message)

    def notify_error(self, message: str = "An error occurred"):
        """Notify error"""
        self.sounds.play(SoundEvent.ERROR)
        if self._desktop_enabled:
            self.desktop.notify("BharatBuild AI - Error", message)

    def notify_attention(self, message: str = "Needs your attention"):
        """Notify attention needed"""
        self.sounds.play(SoundEvent.ATTENTION)
        if self._desktop_enabled:
            self.desktop.notify("BharatBuild AI", message)

    def notify_message(self, message: str = "New message"):
        """Notify new message"""
        self.sounds.play(SoundEvent.MESSAGE)

    def toggle_sounds(self) -> bool:
        """Toggle sounds"""
        return self.sounds.toggle()

    def toggle_desktop(self) -> bool:
        """Toggle desktop notifications"""
        self._desktop_enabled = not self._desktop_enabled
        status = "enabled" if self._desktop_enabled else "disabled"
        self.console.print(f"[green]✓ Desktop notifications {status}[/green]")
        return self._desktop_enabled
