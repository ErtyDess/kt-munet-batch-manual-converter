# MuNET to Tachi BATCH-MANUAL Converter

Converts washing machine arcade game score exports from **MuNET** (private server) into the **BATCH-MANUAL** JSON format used by [Kamaitachi] for score imports.

## Requirements

- Python 3.10+

## Tutorial

1. **Export your MuNET profile**: go to the MuNET web panel → **maimai DX** tab → **Data import / export** tab → In the Export section click **All data JSON**. A file named `MuNET Export - <username> - <date>.json` will be downloaded.
2. **Download this repository**: click the green **Code** button on GitHub → **Download ZIP**, then extract the archive.
3. **Place the export in the script folder**: move the `MuNET Export - ....json` file from step 1 into the same folder as `run_convert.ps1` and the Python script.
4. **Run the converter**: right-click `run_convert.ps1` → **Run with PowerShell**. The output file `mai2_tachi_batch_manual_import_munet_<date>.json` will appear in the same folder.
5. **Import into Kamaitachi**: go to [Kamaitachi] → **Import Scores** → **BATCH-MANUAL** (or navigate directly to `/import/batch-manual`) and upload the output file from step 4.

## Files

| File | Description |
|------|-------------|
| `convert_munet_scores_to_tachi_batch_manual.py` | Main converter script |
| `run_convert.ps1` | PowerShell helper that auto-detects the input file and runs the converter |

## Usage

### Option 1: PowerShell helper (Windows, recommended)

1. Place your MuNET export JSON in the same folder as the scripts.
2. Right-click `run_convert.ps1` → **Run with PowerShell**.

The output file will be named `mai2_tachi_batch_manual_import_munet_<date>.json`.

### Option 2: Direct Python command

```bash
python convert_munet_scores_to_tachi_batch_manual.py <input.json> [output.json]
```

**Arguments:**

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `input.json` | Yes | — | Path to the MuNET export JSON file |
| `output.json` | No | `tachi_import.json` | Path for the output file |

## Data Source

Reads from `userPlaylogList` in the MuNET export. Each entry is an individual play session and includes:

- Achievement percentage
- Lamp status (FAILED, CLEAR, FULL COMBO, FULL COMBO+, ALL PERFECT, ALL PERFECT+)
- Timestamp
- Full judgement breakdown (pcrit, perfect, great, good, miss)
- Fast/slow counts and max combo

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

Included whenever the source field exists in MuNET, even when the value is `0`.

### Timestamp

MuNET stores two time fields per play:

- **`loginDate`** — Unix timestamp (seconds, UTC). Accurate but identical for every song in the same credit.
- **`userPlayDate`** — Datetime string. Shifted by a server-side offset that varies across server versions (e.g. +18 h or +9 h), but the relative deltas between songs within a session are correct.

The converter combines both to produce per-song completion timestamps:

1. For each session (`loginDate` group), it finds the earliest `userPlayDate`.
2. The raw offset `earliest_userPlayDate − loginDate` contains the server shift plus a small variable login-to-first-song gap.
3. Because the server shift is always an exact number of hours and the login-to-song gap is always under 30 minutes, rounding to the nearest hour isolates the server shift exactly.
4. Each song's `timeAchieved` is then `userPlayDate − rounded_offset`, converted to milliseconds.

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

Tachi handles deduplication automatically — re-importing the same scores will not create duplicates.

## Known Limitations

- **No `percentGraph` or `lifeGraph`**: those values are not present in the export json.
- **Timestamp accuracy**: `timeAchieved` may be off by a few minutes compared to the real completion time, due to the hour-rounding heuristic used to correct MuNET's server-side time offset.
