# MuNET → Tachi BATCH-MANUAL

Converte l’export score di **maimai DX** da **MuNET** nel JSON **BATCH-MANUAL** da importare su [Kamaitachi](https://kamaitachi.xyz).

**Converter online:** [https://ertydess.github.io/kt-munet-batch-manual-converter/](https://ertydess.github.io/kt-munet-batch-manual-converter/)

## Tutorial

1. **Esporta il profilo da MuNET** — pannello web → tab **maimai DX** → **Data import / export** → in Export scegli **All Data JSON** oppure **Legacy → All Data JSON**. Si scarica qualcosa tipo `MuNET Export - <username> - <date>.json`.
2. **Converti sul sito** — apri il [converter](https://ertydess.github.io/kt-munet-batch-manual-converter/), trascina o seleziona il file. Il JSON convertito si scarica da solo (tutto resta nel browser).
3. **Importa su Kamaitachi** — [Import Scores](https://kamaitachi.xyz) → **BATCH-MANUAL** (o `/import/batch-manual`) e carica il file scaricato.

## Note

- Percentuale = achievement MuNET ÷ 10000 (es. `990758` → `99.0758`)
- Lamp da flag AP/FC e giudizi (AP+, AP, FC+, FC, CLEAR, FAILED)
- `musicId` sotto 10000 → difficoltà Standard; da 10000 in su → DX; Utage saltate
- Timestamp per canzone da `loginDate` + `userPlayDate` (con correzione dell’offset orario del server)
- Le partite che Tachi rifiuterebbe vengono scartate, con un riepilogo a schermo

Tachi deduplica in caso di re-import. Non ci sono `percentGraph` / `lifeGraph` (non sono nell’export MuNET); `timeAchieved` può essere sfasato di pochi minuti.

## Backup locale

I file `convert_munet_scores_to_tachi_batch_manual.py` e `run_convert.ps1` erano il converter da riga di comando / PowerShell; restano nel repo solo come backup. Ora si usa il [sito](https://ertydess.github.io/kt-munet-batch-manual-converter/).
