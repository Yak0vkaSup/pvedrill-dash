#!/usr/bin/env python3
"""Fetch Polymarket activity and bake it into the dashboard as a static snapshot."""
import argparse
import json
import pathlib
import time

import requests
from tqdm import tqdm

API = "https://data-api.polymarket.com/activity"
PAGE = 500
MAX_PAGES = 80  # safety: stop if the API keeps returning full pages


def fetch(wallet: str, start: int) -> list:
    events, offset = [], 0
    with tqdm(desc="pages", unit="page") as bar:
        while offset < MAX_PAGES * PAGE:
            params = {"user": wallet, "limit": PAGE, "offset": offset}
            if start:
                params["start"] = start
            r = requests.get(API, params=params, timeout=30)
            r.raise_for_status()
            batch = r.json()
            events += batch
            bar.update(1)
            bar.set_postfix(events=len(events))
            if len(batch) < PAGE:
                return events
            offset += PAGE
    print(f"warning: hit {MAX_PAGES}-page cap, oldest events truncated")
    return events


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--wallet", default="0x92fae79010ef399d035523a8b7d805fcc1f28b17")
    p.add_argument("--days", type=float, default=7, help="0 = full history")
    p.add_argument("--template", default="pvedrill-dashboard.html")
    p.add_argument("--out", default="pvedrill-snapshot.html")
    a = p.parse_args()

    start = int(time.time() - a.days * 86400) if a.days else 0
    events = fetch(a.wallet, start)
    print(f"{len(events)} events")

    html = pathlib.Path(a.template).read_text()
    marker = "const EMBEDDED=null;"
    if marker not in html:
        raise SystemExit(f"marker not found in {a.template} — wrong template file")
    html = html.replace(marker, "const EMBEDDED=" + json.dumps(events, separators=(",", ":")) + ";", 1)
    html = html.replace("const BUILT=null;", f"const BUILT={int(time.time())};", 1)
    html = html.replace('value="0x92fae79010ef399d035523a8b7d805fcc1f28b17"', f'value="{a.wallet}"', 1)
    pathlib.Path(a.out).write_text(html)
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
