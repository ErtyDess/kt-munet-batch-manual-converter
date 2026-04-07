import json
import argparse
from datetime import datetime, timezone

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
    """For each loginDate group, compute the offset between the earliest
    userPlayDate and loginDate so we can anchor per-song times correctly."""
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
    return {
        login: round((upd - login) / 3600) * 3600
        for login, upd in earliest.items()
    }


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
    args = parser.parse_args()

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


if __name__ == "__main__":
    main()
