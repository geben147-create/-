# ID naming

One scheme, fixed now, because renaming identifiers later is what forces a
re-audit of every stored file.

| Prefix  | Applies to        | Example                  |
|---------|-------------------|--------------------------|
| `PRJ_`  | project           | `PRJ_seoul_survey`       |
| `EP_`   | episode           | `EP_012`                 |
| `S{n}_SH{n}` | shot         | `S3_SH07`                |
| `CHAR_` | character         | `CHAR_narrator_m`        |
| `PROP_` | prop              | `PROP_survey_rod`        |
| `LOC_`  | location          | `LOC_alley_north`        |
| `CAP_`  | model capability  | `CAP_DIAGRAM_MOTION`     |
| `SHOT_` | shot vocabulary   | `ARCH_SLICE_REVEAL`      |

Rules that matter more than the table:

- An id is permanent. A renamed character is a new id with a pointer from the old.
- Re-running the same `shot_id` reuses the existing result rather than
  regenerating it. Idempotency is what stops a retry from costing twice.
- Every manifest carries `schema_version`.
- Local files are the source of truth. Any spreadsheet or dashboard is a
  one-way mirror of them, read-only. Two writers on one cell cannot be made
  safe — the losing write disappears silently, which is how blank fields and
  duplicated rows appear. If a value must come back the other way, let it be a
  single approval flag, written under an owner check.
