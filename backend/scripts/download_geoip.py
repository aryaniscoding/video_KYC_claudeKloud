"""
Download MaxMind GeoLite2-City database and Tor exit node list.

Requires a free MaxMind account — sign up at: https://www.maxmind.com/en/geolite2/signup
Then set MAXMIND_LICENSE_KEY in your .env.

Usage:
  MAXMIND_LICENSE_KEY=your_key python -m scripts.download_geoip
"""
import os
import sys
import tarfile
from pathlib import Path

import httpx

GEOIP_DIR = Path("data/geoip")
TOR_FILE = Path("data/tor_exit_nodes.txt")
GEOIP_DB_FILE = GEOIP_DIR / "GeoLite2-City.mmdb"

MAXMIND_URL = (
    "https://download.maxmind.com/app/geoip_download"
    "?edition_id=GeoLite2-City&license_key={key}&suffix=tar.gz"
)
TOR_LIST_URL = "https://check.torproject.org/torbulkexitlist"


def download_geoip(license_key: str):
    GEOIP_DIR.mkdir(parents=True, exist_ok=True)
    url = MAXMIND_URL.format(key=license_key)
    print("Downloading GeoLite2-City database...")

    with httpx.Client(follow_redirects=True, timeout=60) as client:
        resp = client.get(url)
        resp.raise_for_status()

    tar_path = GEOIP_DIR / "GeoLite2-City.tar.gz"
    tar_path.write_bytes(resp.content)
    print(f"  Downloaded {len(resp.content) / 1024 / 1024:.1f} MB")

    with tarfile.open(tar_path, "r:gz") as tar:
        for member in tar.getmembers():
            if member.name.endswith(".mmdb"):
                member.name = GEOIP_DB_FILE.name
                tar.extract(member, GEOIP_DIR)
                print(f"  Extracted to {GEOIP_DB_FILE}")
                break

    tar_path.unlink()
    print("  GeoIP setup complete.")


def download_tor_list():
    TOR_FILE.parent.mkdir(parents=True, exist_ok=True)
    print("Downloading Tor exit node list...")
    with httpx.Client(timeout=30) as client:
        resp = client.get(TOR_LIST_URL)
        resp.raise_for_status()
    TOR_FILE.write_text(resp.text)
    count = len([l for l in resp.text.splitlines() if l and not l.startswith("#")])
    print(f"  Saved {count} Tor exit nodes to {TOR_FILE}")


if __name__ == "__main__":
    key = os.getenv("MAXMIND_LICENSE_KEY", "")
    if not key:
        print("ERROR: Set MAXMIND_LICENSE_KEY environment variable.")
        print("  Get a free key at https://www.maxmind.com/en/geolite2/signup")
        sys.exit(1)

    download_geoip(key)
    download_tor_list()
    print("\nAll geo data ready.")
