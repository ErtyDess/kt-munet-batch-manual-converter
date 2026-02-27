import json
import sys
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


def parse_play_date(date_str):
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(date_str, fmt)
            return int(dt.timestamp() * 1000)
        except ValueError:
            continue
    return None


def convert_playlog_entry(entry):
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

    ts = parse_play_date(entry.get("userPlayDate"))
    if ts:
        score["timeAchieved"] = ts

    score["judgements"] = {
        "pcrit": sum_judgement(entry, "CriticalPerfect"),
        "perfect": sum_judgement(entry, "Perfect"),
        "great": sum_judgement(entry, "Great"),
        "good": sum_judgement(entry, "Good"),
        "miss": sum_judgement(entry, "Miss"),
    }

    optional = {}
    if entry.get("fastCount", 0) > 0:
        optional["fast"] = entry["fastCount"]
    if entry.get("lateCount", 0) > 0:
        optional["slow"] = entry["lateCount"]
    if entry.get("maxCombo", 0) > 0:
        optional["maxCombo"] = entry["maxCombo"]
    if optional:
        score["optional"] = optional

    return score


def convert_best_score(detail):
    """Fallback: convert from userMusicDetailList (no timestamps/judgements)."""
    music_id = detail["musicId"]
    level = detail["level"]
    achievement = detail["achievement"]
    combo = detail.get("comboStatus", 0)

    if combo >= 4:
        lamp = "ALL PERFECT+"
    elif combo >= 3:
        lamp = "ALL PERFECT"
    elif combo >= 2:
        lamp = "FULL COMBO+"
    elif combo >= 1:
        lamp = "FULL COMBO"
    elif achievement > 0:
        lamp = "CLEAR"
    else:
        lamp = "FAILED"

    return {
        "percent": achievement / 10000.0,
        "lamp": lamp,
        "matchType": "inGameID",
        "identifier": str(music_id),
        "difficulty": get_difficulty(music_id, level),
    }


def main():
    input_file = sys.argv[1] if len(sys.argv) > 1 else None
    output_file = sys.argv[2] if len(sys.argv) > 2 else "tachi_import.json"
    source = sys.argv[3] if len(sys.argv) > 3 else "playlog"

    if not input_file:
        print("Usage: python convert.py <munet_export.json> [output.json] [playlog|best]")
        print("  playlog  - convert every individual play (default, recommended)")
        print("  best     - convert only best scores per chart (no timestamps)")
        sys.exit(1)

    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if source == "best":
        details = data.get("userMusicDetailList", [])
        scores = [convert_best_score(d) for d in details if d.get("achievement", 0) > 0]
        print(f"Converted {len(scores)} best scores from userMusicDetailList")
    else:
        playlogs = data.get("userPlaylogList", [])
        scores = [convert_playlog_entry(p) for p in playlogs]
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
