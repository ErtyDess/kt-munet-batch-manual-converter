# MuNET → Tachi BATCH-MANUAL

Converts **maimai DX** score exports from **MuNET** into **BATCH-MANUAL** JSON for import on [Kamaitachi](https://kamaitachi.xyz).

**Online converter:** [https://ertydess.github.io/kt-munet-batch-manual-converter/](https://ertydess.github.io/kt-munet-batch-manual-converter/)

## Tutorial

1. **Export your MuNET profile** — web panel → **maimai DX** tab → **Data import / export** → in Export pick **All Data JSON** or **Legacy → All Data JSON**. You’ll get something like `MuNET Export - <username> - <date>.json`.
2. **Convert on the site** — open the [converter](https://ertydess.github.io/kt-munet-batch-manual-converter/), drag or select the file. The converted JSON downloads automatically (everything stays in your browser).
3. **Import into Kamaitachi** — [Import Scores](https://kamaitachi.xyz) → **BATCH-MANUAL** (or `/import/batch-manual`) and upload the downloaded file.

## Notes

- Percent = MuNET achievement ÷ 10000 (e.g. `990758` → `99.0758`)
- Lamp from AP/FC flags and judgements (AP+, AP, FC+, FC, CLEAR, FAILED)
- `musicId` under 10000 → Standard difficulties; 10000+ → DX; Utage skipped
- Per-song timestamps from `loginDate` + `userPlayDate` (with MuNET’s hour-level server offset corrected)
- Plays Tachi would reject are dropped, with a summary on screen

Tachi deduplicates on re-import. No `percentGraph` / `lifeGraph` (not in the MuNET export); `timeAchieved` may be off by a few minutes.

## Local backup

`convert_munet_scores_to_tachi_batch_manual.py` and `run_convert.ps1` were the old command-line / PowerShell converter; they remain in the repo as a backup only. Use the [site](https://ertydess.github.io/kt-munet-batch-manual-converter/) now.
