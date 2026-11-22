"""N8-Hotspot: web interface for MMDVMHost + DMRGateway hotspots (DMR Die N8schicht)."""
from pathlib import Path as _Path

try:
    __version__ = (_Path(__file__).resolve().parent.parent / "VERSION").read_text(encoding="utf-8").strip() or "1.1.0"
except OSError:
    __version__ = "1.1.0"
