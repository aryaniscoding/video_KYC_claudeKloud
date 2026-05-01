"""Refresh Tor exit node list in-place. Run as a daily cron inside the container."""
from pathlib import Path
import httpx

TOR_FILE = Path("data/tor_exit_nodes.txt")
TOR_LIST_URL = "https://check.torproject.org/torbulkexitlist"


def refresh():
    TOR_FILE.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=20) as client:
        resp = client.get(TOR_LIST_URL)
        resp.raise_for_status()
    TOR_FILE.write_text(resp.text)
    # Reload in running process by clearing the in-memory set and re-reading
    from app.services.scoring_service import _TOR_EXIT_NODES
    _TOR_EXIT_NODES.clear()
    _TOR_EXIT_NODES.update(TOR_FILE.read_text().splitlines())
    print(f"Tor list refreshed: {len(_TOR_EXIT_NODES)} exit nodes")


if __name__ == "__main__":
    refresh()
