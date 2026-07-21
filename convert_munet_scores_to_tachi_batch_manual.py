import json
import os
import time
import argparse
import urllib.request
import urllib.error
from datetime import datetime, timezone

USER_AGENT = "kt-munet-batch-manual-converter/1.0"
DEFAULT_BASE_URL = "https://kamai.tachi.ac"
IMPORT_ENDPOINT = "/ir/direct-manual/import"

DIFFICULTY_STD = {0: "Basic", 1: "Advanced", 2: "Expert", 3: "Master", 4: "Re:Master"}
DIFFICULTY_DX = {0: "DX Basic", 1: "DX Advanced", 2: "DX Expert", 3: "DX Master", 4: "DX Re:Master"}

# Songs with in-game ID < 10000 use Standard difficulty names,
# songs >= 10000 use DX difficulty names. This heuristic covers:
#   - IDs 1-9999: original maimai Standard charts
#   - IDs 10000-10999: DX re-charts of original songs
#   - IDs 11000+: newer DX-only songs
# If Tachi rejects some scores, you may need to flip specific IDs manually.
DX_THRESHOLD = 10000


def get_difficulty(music_id, level):
    table = DIFFICULTY_DX if music_id >= DX_THRESHOLD else DIFFICULTY_STD
    return table.get(level, f"Unknown({level})")


def get_lamp(entry):
    is_ap = entry.get("isAllPerfect", False)
    combo = entry.get("comboStatus", 0)
    is_fc = entry.get("isFullCombo", False)
    is_clear = entry.get("isClear", False)

    if is_ap:
        non_crit_break = sum(
            entry.get(k, 0)
            for k in ["breakPerfect", "breakGreat", "breakGood", "breakMiss"]
        )
        return "ALL PERFECT+" if non_crit_break == 0 else "ALL PERFECT"

    if combo >= 2:
        return "FULL COMBO+"
    if combo >= 1 or is_fc:
        return "FULL COMBO"
    if is_clear:
        return "CLEAR"
    return "FAILED"


def sum_judgement(entry, suffix):
    return sum(
        entry.get(f"{note_type}{suffix}", 0)
        for note_type in ["tap", "hold", "slide", "touch", "break"]
    )


def parse_user_play_date(date_str):
    """Parse userPlayDate string to unix seconds (treating it as naive UTC)."""
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except ValueError:
            continue
    return None


def build_session_offsets(playlogs):
    """For each loginDate group, estimate the server-side time shift.

    userPlayDate is the play time in the server's local timezone; loginDate is a
    true UTC unix timestamp. Their raw difference (earliest_userPlayDate - login)
    equals the timezone shift plus the always-positive, sub-hour gap between
    logging in and finishing the first song.

    Since the shift is always a whole number of hours and the gap is < 1 hour,
    flooring the raw difference to the hour recovers the exact shift. round() was
    fragile: a gap above 30 min pushed the offset to the wrong hour, shifting a
    whole session by an hour. floor tolerates gaps up to ~59 min.
    """
    earliest = {}
    for entry in playlogs:
        login = entry.get("loginDate")
        if login is None:
            continue
        upd = parse_user_play_date(entry.get("userPlayDate"))
        if upd is None:
            continue
        if login not in earliest or upd < earliest[login]:
            earliest[login] = upd
    offsets = {}
    for login, upd in earliest.items():
        raw = upd - login
        if raw < 0:  # guard against tiny clock jitter making the gap negative
            raw = 0
        offsets[login] = (raw // 3600) * 3600
    return offsets


def get_time_achieved(entry, session_offsets):
    """Compute per-song timestamp: loginDate anchors the session,
    userPlayDate deltas spread the songs across real time."""
    login = entry.get("loginDate")
    if login is None:
        return None
    upd = parse_user_play_date(entry.get("userPlayDate"))
    offset = session_offsets.get(login)
    if upd is not None and offset is not None:
        return (upd - offset) * 1000
    return login * 1000


def convert_playlog_entry(entry, session_offsets):
    music_id = entry["musicId"]
    level = entry["level"]
    achievement = entry["achievement"]

    score = {
        "percent": achievement / 10000.0,
        "lamp": get_lamp(entry),
        "matchType": "inGameID",
        "identifier": str(music_id),
        "difficulty": get_difficulty(music_id, level),
    }

    ts = get_time_achieved(entry, session_offsets)
    if ts is not None:
        score["timeAchieved"] = ts

    score["judgements"] = {
        "pcrit": sum_judgement(entry, "CriticalPerfect"),
        "perfect": sum_judgement(entry, "Perfect"),
        "great": sum_judgement(entry, "Great"),
        "good": sum_judgement(entry, "Good"),
        "miss": sum_judgement(entry, "Miss"),
    }

    optional = {}
    if "fastCount" in entry and entry["fastCount"] is not None:
        optional["fast"] = entry["fastCount"]
    if "lateCount" in entry and entry["lateCount"] is not None:
        optional["slow"] = entry["lateCount"]
    if "maxCombo" in entry and entry["maxCombo"] is not None:
        optional["maxCombo"] = entry["maxCombo"]
    if optional:
        score["optional"] = optional

    return score


def _log_import_result(body):
    """Print a short summary of a completed Tachi import document."""
    score_ids = body.get("scoreIDs") or []
    sessions = body.get("createdSessions") or []
    errors = body.get("errors") or []
    print(
        f"Import done: {len(score_ids)} scores, "
        f"{len(sessions)} sessions, {len(errors)} errors"
    )
    for err in errors:
        print(f"  > {err.get('type')}: {err.get('message')}")


def poll_import(url, api_key, interval=1.0, timeout=300.0):
    """Poll an async import poll URL until it reports 'completed'."""
    deadline = time.monotonic() + timeout
    while True:
        req = urllib.request.Request(url, method="GET")
        req.add_header("User-Agent", USER_AGENT)
        req.add_header("Authorization", f"Bearer {api_key}")
        with urllib.request.urlopen(req) as resp:
            payload = json.loads(resp.read().decode("utf-8"))

        if not payload.get("success", False):
            print(f"Import failed: {payload.get('description')}")
            return False

        body = payload.get("body") or {}
        status = body.get("importStatus")
        if status == "completed":
            _log_import_result(body.get("import") or {})
            return True

        progress = body.get("progress") or {}
        if progress:
            print(f"  ...{progress.get('description', 'processing')} ({progress.get('value', '?')})")

        if time.monotonic() > deadline:
            print("Timed out waiting for the import to complete.")
            return False
        time.sleep(interval)


def submit_import(batch_manual, base_url, api_key):
    """POST the batch-manual document to Tachi's direct-manual import endpoint.

    Returns True on success. Mirrors Rizu's Exporter.SubmitImport: a 200 means
    the import finished synchronously, a 202 means it is async and we must poll
    the returned URL.
    """
    url = base_url.rstrip("/") + IMPORT_ENDPOINT
    body_bytes = json.dumps(batch_manual, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(url, data=body_bytes, method="POST")
    req.add_header("User-Agent", USER_AGENT)
    req.add_header("Content-Type", "application/json")
    req.add_header("X-User-Intent", "true")
    req.add_header("Authorization", f"Bearer {api_key}")

    try:
        with urllib.request.urlopen(req) as resp:
            status_code = resp.getcode()
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        print(f"Upload failed (HTTP {e.code}): {detail}")
        return False
    except urllib.error.URLError as e:
        print(f"Upload failed (network error): {e.reason}")
        return False

    if not payload.get("success", False):
        print(f"Upload rejected by Tachi: {payload.get('description')}")
        return False

    print(f"Tachi: {payload.get('description')}")

    if status_code == 202:
        poll_url = (payload.get("body") or {}).get("url")
        if not poll_url:
            print("Import accepted but no poll URL was returned.")
            return False
        return poll_import(poll_url, api_key)

    _log_import_result(payload.get("body") or {})
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Convert MuNET scores to Tachi batch manual format."
    )
    parser.add_argument("input_file", help="Path to MuNET export JSON file.")
    parser.add_argument(
        "output_file",
        nargs="?",
        default="tachi_import.json",
        help="Output JSON path (default: tachi_import.json).",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="After conversion, upload the result directly to Tachi.",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("TACHI_API_KEY"),
        help="Tachi API key (or set the TACHI_API_KEY environment variable).",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Tachi base URL (default: {DEFAULT_BASE_URL}).",
    )
    args = parser.parse_args()

    if args.upload and not args.api_key:
        parser.error(
            "--upload requires an API key: pass --api-key or set TACHI_API_KEY."
        )

    input_file = args.input_file
    output_file = args.output_file

    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    playlogs = data.get("userPlaylogList", [])
    session_offsets = build_session_offsets(playlogs)
    scores = [convert_playlog_entry(p, session_offsets) for p in playlogs]
    print(f"Converted {len(scores)} plays from userPlaylogList")

    batch_manual = {
        "meta": {
            "game": "maimaidx",
            "playtype": "Single",
            "service": "MuNET",
        },
        "scores": scores,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(batch_manual, f, indent=2, ensure_ascii=False)

    print(f"Output: {output_file}")

    if args.upload:
        print(f"Uploading to {args.base_url}{IMPORT_ENDPOINT} ...")
        ok = submit_import(batch_manual, args.base_url, args.api_key)
        if not ok:
            print(f"Upload did not complete. The file is kept at {output_file}.")
            raise SystemExit(1)


if __name__ == "__main__":
    main()
