"""OrientBot in HATH0R-CLI delegating canonically to Hath0r Framework (hath0r_engine.bots.orient_bot).

OrientBot resides canonically in the Hath0r Framework and can be called from any repository.
"""

from __future__ import annotations

try:
    from hath0r_engine.bots.orient_bot import OrientBot, orient_bot
except ImportError:
    import sys
    from pathlib import Path

    # Attempt locating hath0r-framework sibling in ~/Development/OpenSource/hath0r-framework/src
    dev_framework = Path.home() / "Development" / "OpenSource" / "hath0r-framework" / "src"
    if dev_framework.is_dir() and str(dev_framework) not in sys.path:
        sys.path.insert(0, str(dev_framework))

    try:
        from hath0r_engine.bots.orient_bot import OrientBot, orient_bot
    except ImportError:
        raise ImportError(
            "Could not import OrientBot from hath0r_engine.bots.orient_bot. "
            "Please ensure Hath0r Framework is installed or available in PYTHONPATH."
        )

__all__ = [
    "OrientBot",
    "orient_bot",
]
