# MuNET to Tachi BATCH-MANUAL Converter

Converts washing machine arcade game score exports from **MuNET** (private server) into the **BATCH-MANUAL** JSON format used by [Kamaitachi] for score imports.

## Requirements

- Python 3.10+

## Tutorial

1. **Export your MuNET profile**: go to the MuNET web panel → **maimai DX** tab → **Data import / export** tab → In the Export section click either:
   - **All Data JSON** (current / non-legacy format), or
   - **Legacy → All Data JSON**
   
   Both formats are supported by this converter. A file named `MuNET Export - <username> - <date>.json` will be downloaded.
2. **Download this repository**: click the green **Code** button on GitHub → **Download ZIP**, then extract the archive.
3. **Place the export in the script folder**: move the `MuNET Export - ....json` file from step 1 into the same folder as `run_convert.ps1` and the Python script.
4. **Run the converter**: right-click `run_convert.ps1` → **Run with PowerShell**. The output file `mai2_tachi_batch_manual_import_munet_<date>.json` will appear in the same folder.
5. **Import into Kamaitachi**: go to [Kamaitachi] → **Import Scores** → **BATCH-MANUAL** (or navigate directly to `/import/batch-manual`) and upload the output file from step 4.

## Files

| File | Description |
|------|-------------|
| `convert_munet_scores_to_tachi_batch_manual.py` | Main converter script |
| `run_convert.ps1` | PowerShell helper that auto-detects the MuNET export and runs the converter |

## Usage

**PowerShell (Windows, recommended):** place the MuNET export JSON next to the scripts, then right-click `run_convert.ps1` → **Run with PowerShell**. Output: `mai2_tachi_batch_manual_import_munet_<date>.json`.

**Python:**

```bash
python convert_munet_scores_to_tachi_batch_manual.py <input.json> [output.json]
```

`output.json` defaults to `tachi_import.json`.

## Conversion notes

Reads `userPlaylogList` from MuNET All Data JSON (current and Legacy).

- **Percent:** MuNET achievement ÷ 10000 (e.g. `990758` → `99.0758`)
- **Lamp:** from AP/FC flags and judgements (AP+, AP, FC+, FC, CLEAR, FAILED)
- **Difficulty:** `musicId` < 10000 → Standard; ≥ 10000 → DX; Utage (`level == 10`) skipped
- **Judgements / optional:** aggregated pcrit–miss; `fast` / `slow` / `maxCombo` when present
- **Timestamp:** per-song times from `loginDate` + `userPlayDate`, correcting MuNET’s hour-level server offset

Plays that Tachi would reject (Utage, lamp/percent mismatches, judgement inconsistencies) are dropped with a console summary.

## Output

[BATCH-MANUAL](https://docs.tachi.ac/codebase/batch-manual/) JSON with `meta` (`maimaidx` / `Single` / `MuNET`) and a `scores` array. Tachi deduplicates on re-import.

## Known limitations

- No `percentGraph` / `lifeGraph` (not in the MuNET export)
- Utage scores are not imported
- `timeAchieved` may be off by a few minutes due to the offset heuristic
