# Verification receipt

Verified on 2026-09-01:

- `python3 -m py_compile analysis/zenith-host-audit/extract.py` — passed;
- extractor run twice over the same source snapshot — identical `findings.db` SHA-256 both times;
- `PRAGMA integrity_check` — `ok`;
- database counts — 521 findings, 42 missions, 1 136 attempts, 1 893 task nodes;
- `git diff --check` — passed;
- secret-pattern scan over text outputs — no matches.

Pinned hashes:

| Artifact | SHA-256 |
|---|---|
| `evidence/findings.db` | `42452018fd65c87b0ea403d3d7b91c13d80dce082a3cfaa20f3a12bcd30ac0e5` |
| `evidence/summary.json` | `b3db9c66e127bed426f8ee7e34a138842fbb3f2808202c83aec8b93f47be510e` |
| `extract.py` | `c0b5888298235f71dea5f93b39e3f20e388cf135d5e49d05fd1eca5d6c724aa5` |

The database hash is deterministic for the audited snapshot. If source artifacts change, rerun the extractor and update this receipt.
