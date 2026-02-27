# MuNET to Tachi BATCH-MANUAL Converter

Converts maimai DX score exports from **MuNET** (private server) into the **BATCH-MANUAL** JSON format used by [Kamaitachi] for score imports.

## Requirements

- Python 3.10+

## Files

| File | Description |
|------|-------------|
| `convert_munet_scores_to_tachi_batch_manual.py` | Main converter script |
| `run_convert.ps1` | PowerShell helper that auto-detects the input file and runs the converter |

## Usage

### Option 1: PowerShell helper (Windows)

1. Place your MuNET export JSON in the same folder as the scripts.
2. Run:

```powershell
.\run_convert.ps1
```

The output file will be named `mai2_munet_tachi_import_<today's date>.json`.

### Option 2: Direct Python command

```bash
python convert_munet_scores_to_tachi_batch_manual.py <input.json> [output.json] [playlog|best]
```

**Arguments:**

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `input.json` | Yes | — | Path to the MuNET export JSON file |
| `output.json` | No | `tachi_import.json` | Path for the output file |
| `playlog\|best` | No | `playlog` | Data source to use (see below) |

## Data Sources

### `playlog` (default, recommended)

Reads from `userPlaylogList` in the MuNET export. Each entry is an individual play session and includes:

- Achievement percentage
- Lamp status (FAILED, CLEAR, FULL COMBO, FULL COMBO+, ALL PERFECT, ALL PERFECT+)
- Timestamp
- Full judgement breakdown (pcrit, perfect, great, good, miss)
- Fast/slow counts and max combo

### `best`

Reads from `userMusicDetailList`. Contains only the best score per chart. Less detailed — no timestamps, no individual judgements. Use this as a fallback if `userPlaylogList` is empty or unavailable.

## Field Mapping

### Score (percent)

MuNET stores achievement as a raw integer (e.g. `990758`). The converter divides by 10000 to get the percentage Tachi expects (e.g. `99.0758`).

### Lamp

Determined from multiple MuNET fields with the following priority:

| Condition | Tachi Lamp |
|-----------|------------|
| `isAllPerfect` = true and all Break judgements are Critical Perfect | ALL PERFECT+ |
| `isAllPerfect` = true | ALL PERFECT |
| `comboStatus` >= 2 | FULL COMBO+ |
| `comboStatus` >= 1 or `isFullCombo` = true | FULL COMBO |
| `isClear` = true | CLEAR |
| Otherwise | FAILED |

### Difficulty

Uses a heuristic based on `musicId`:

- IDs **< 10000** → Standard charts: Basic, Advanced, Expert, Master, Re:Master
- IDs **>= 10000** → DX charts: DX Basic, DX Advanced, DX Expert, DX Master, DX Re:Master

The numeric `level` field (0–4) maps to the difficulty name within each category.

### Judgements

Aggregated from all note types (tap, hold, slide, touch, break) for each judgement tier:

| Tachi Field | MuNET Fields Summed |
|-------------|---------------------|
| `pcrit` | `tapCriticalPerfect` + `holdCriticalPerfect` + `slideCriticalPerfect` + `touchCriticalPerfect` + `breakCriticalPerfect` |
| `perfect` | `tapPerfect` + `holdPerfect` + `slidePerfect` + `touchPerfect` + `breakPerfect` |
| `great` | `tapGreat` + `holdGreat` + `slideGreat` + `touchGreat` + `breakGreat` |
| `good` | `tapGood` + `holdGood` + `slideGood` + `touchGood` + `breakGood` |
| `miss` | `tapMiss` + `holdMiss` + `slideMiss` + `touchMiss` + `breakMiss` |

### Optional Metrics

| Tachi Field | MuNET Field |
|-------------|-------------|
| `fast` | `fastCount` |
| `slow` | `lateCount` |
| `maxCombo` | `maxCombo` |

Only included if the value is greater than 0.

### Timestamp

MuNET's `userPlayDate` (e.g. `"2025-11-17 04:56:21.0"`) is converted to Unix milliseconds for Tachi's `timeAchieved`.

## Output Format

The output follows the [Tachi BATCH-MANUAL specification](https://docs.tachi.ac/codebase/batch-manual/):

```json
{
  "meta": {
    "game": "maimaidx",
    "playtype": "Single",
    "service": "MuNET"
  },
  "scores": [
    {
      "percent": 99.0758,
      "lamp": "CLEAR",
      "matchType": "inGameID",
      "identifier": "11663",
      "difficulty": "DX Advanced",
      "timeAchieved": 1763438751000,
      "judgements": {
        "pcrit": 6,
        "perfect": 491,
        "great": 36,
        "good": 5,
        "miss": 1
      },
      "optional": {
        "fast": 27,
        "slow": 14,
        "maxCombo": 464
      }
    }
  ]
}
```

## Importing into Kamaitachi

1. Run the converter to generate the output JSON.
2. Go to [Kamaitachi] → Import Scores → BATCH-MANUAL.
3. Upload the generated JSON file.

Tachi handles deduplication automatically — re-importing the same scores will not create duplicates.

## Known Limitations

- **No `percentGraph` or `lifeGraph`**: those values are not present in the export json.
- The Standard vs. DX chart distinction relies on a `musicId` threshold heuristic (< 10000 = Standard, >= 10000 = DX). If Tachi rejects specific scores, you may need to manually adjust the difficulty for those songs.
- The `best` mode derives lamp status from `comboStatus` alone (numeric 0–4), which is less precise than the `playlog` mode that uses multiple boolean flags and judgement counts.
