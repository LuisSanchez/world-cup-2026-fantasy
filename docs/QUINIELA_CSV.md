# Quiniela CSV format

Admins can bulk-import player predictions by uploading a CSV in **Admin → Resultados**.

## Templates (download)

| File | Use |
|------|-----|
| [**quiniela_template.csv**](quiniela_template.csv) | Full header + **3 example players** (scores you can open in Excel/Sheets) |
| [**quiniela_template_blank.csv**](quiniela_template_blank.csv) | Full header + one empty row to fill with real emails |

## Column structure

| Column | Required | Description |
|--------|----------|-------------|
| `Marca temporal` | No | Timestamp (Google Forms export). Ignored by the importer. |
| `Dirección de correo electrónico` | **Yes** | Player email (must match Google login when they sign in). Column index **1**. |
| `Partido N: Home-Away` | Yes* | One column per match. Header must start with `Partido`. |

\* At least one `Partido …` column is required. Empty score cells are skipped (player has no prediction for that match).

### Match headers

```text
Partido 1: México-Sudáfrica
Partido 2: Corea-Republica Checa
…
Partido 73: 16vos Por Definir
…
Partido 103: Final Por Definir
Partido 104: 3ero Por Definir
```

- Group stage (1–72): real team names separated by `-` (Spanish names as in the schedule).
- Knockout (73–104): often `16vos Por Definir`, `8vos Por Definir`, etc., until teams are known.
- Score cells: `home-away` with a hyphen, e.g. `2-1`, `0-0`, `3-2`. Spaces around the dash are OK (`2 - 1`).

### Example rows (abbreviated)

```csv
Marca temporal,Dirección de correo electrónico,Partido 1: México-Sudáfrica,Partido 2: Corea-Republica Checa,...
2026-06-01 10:00:00,alice@example.com,2-0,1-1,...
2026-06-01 11:30:00,bob@example.com,1-0,0-0,...
```

See the full files above for all 104 match columns and complete examples.

## Import rules

1. Encoding: UTF-8 (BOM allowed).
2. Users are **created** from emails if they do not exist yet.
3. Predictions are **upserted** (with `update_existing=true`, sheet values overwrite previous picks for those matches).
4. Empty cells do **not** clear an existing prediction; only non-empty scores are written.
5. Official match results are **not** taken from this CSV — use Admin score entry or results sync.
6. Each admin upload is stored as a new `{stem}_{uuid}.csv`; re-upload when the sheet changes.

## Typical workflow

1. Export your Google Sheet / Forms responses as CSV, **or** start from [quiniela_template_blank.csv](quiniela_template_blank.csv).
2. Ensure emails match the accounts players will use with Google.
3. As admin: **Admin → Resultados → Quiniela CSV** → drop the file → **Importar CSV subido**.

API:

```http
POST /api/admin/import-quiniela?update_existing=true&also_sync_results=false
Content-Type: multipart/form-data
file=<quiniela.csv>
```
