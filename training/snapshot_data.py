"""Download keyless FRED CSV snapshots into data/raw and write manifest.json.

Run manually (network required): python -m training.snapshot_data
The pipeline never downloads; it only reads the committed snapshot and verifies hashes.
"""
import datetime as dt
import hashlib
import json
import urllib.request

from nexus.config import RAW_DIR
from nexus.data.pipeline import SERIES

URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    entries = []
    for name, meta in SERIES.items():
        url = URL.format(sid=meta["id"])
        with urllib.request.urlopen(url, timeout=60) as r:  # noqa: S310 (fixed https URL)
            body = r.read()
        path = RAW_DIR / f"{meta['id']}.csv"
        path.write_bytes(body)
        entries.append({
            "variable": name, "series_id": meta["id"], "file": path.name, "source_url": url,
            "publisher": meta["publisher"], "retrieved_utc": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
            "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body),
        })
    (RAW_DIR / "manifest.json").write_text(json.dumps({"files": entries}, indent=2))
    print(f"wrote {len(entries)} files")


if __name__ == "__main__":
    main()
