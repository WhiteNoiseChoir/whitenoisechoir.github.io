#!/usr/bin/env python3
"""Validate actual HTTP source candidates for Rainy Valley Treehouse's six nature tracks."""
import json
import urllib.error
import urllib.request

ORIGIN = "https://whitenoisechoir.com"
MEDIA = "https://media.whitenoisechoir.com/"
SOURCES = {
    "rain-on-window": [
        ORIGIN + "/audio/rain-on-window-real.mp3",
        MEDIA + "audio/rain-on-window-real.mp3",
        ORIGIN + "/signature/audio/rain-window.mp3",
    ],
    "heavy-rain": [MEDIA + "audio/heavy-rain-real.mp3"],
    "rain-leaves": [
        ORIGIN + "/audio/rain-leaves-real.mp3",
        MEDIA + "audio/rain-leaves-real.mp3",
    ],
    "forest-stream": [
        MEDIA + "asset-library/studio-loop/sha256/ee/eed2cf72da87123b94bfc6388ac2ebe5395f2137aaebed9e2f4ac27bb4ab30b7.mp3",
    ],
    "fireplace": [
        ORIGIN + "/audio/fireplace-real.mp3",
        MEDIA + "audio/fireplace-real.mp3",
        ORIGIN + "/signature/audio/fireplace.mp3",
    ],
    "wind": [
        MEDIA + "asset-library/studio-loop/sha256/63/636a28c6a8d3350c906a635aa5bec8bdf72b015a885bd4da360924bad1db8334.mp3",
    ],
}


def inspect(address):
    req = urllib.request.Request(address, headers={
        "Origin": ORIGIN, "Range": "bytes=0-2047", "User-Agent": "WNC-Nature-Source-Diagnostics/1.0"
    })
    try:
        with urllib.request.urlopen(req, timeout=25) as res:
            data = res.read(2048)
            result = {
                "http": res.status, "size": len(data),
                "type": res.headers.get("content-type", ""),
                "cors": res.headers.get("access-control-allow-origin", ""),
                "range": res.headers.get("content-range", ""),
            }
            result["pass"] = (res.status in (200, 206) and len(data) == 2048
                and not result["type"].startswith(("text/html", "application/json"))
                and (address.startswith(ORIGIN) or result["cors"] in ("*", ORIGIN)))
            return result
    except Exception as exc:
        return {"pass":False, "error":str(exc)[:180]}


def main():
    failed = []
    for label, addresses in SOURCES.items():
        attempts = []
        for address in addresses:
            check = inspect(address)
            attempts.append({"url":address, **check})
        passed = any(a["pass"] for a in attempts)
        print("WNC_RAINY_VALLEY_SOURCE " + json.dumps({
            "name":label, "pass":passed, "attempts":attempts},ensure_ascii=False),flush=True)
        if not passed: failed.append(label)
    print("WNC_RAINY_VALLEY_SUMMARY "+json.dumps({"failed":failed}),flush=True)
    if failed:raise SystemExit(1)


if __name__ == "__main__":
    main()
