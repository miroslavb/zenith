# Repository agent notes

## Zenith host audit

The reproducible host-side analysis is under `analysis/zenith-host-audit/`.

- Treat `/root/.zenith/projects` as the authoritative mission registry.
- Keep transcript corpora read-only and never copy full raw conversations into report artifacts.
- Preserve redaction in `extract.py`; do not persist credentials, IP addresses, emails, or long token-like strings.
- Run `python3 analysis/zenith-host-audit/extract.py` twice and require an identical `findings.db` SHA-256 before updating `verification.md`.
- Interpret `state=done`, attempt `done`, formal control share, and validator agent-hours as different measures; do not call any of them a mission success rate.
- External orchestrator comparisons must use primary sources and must not claim apples-to-apples speed or quality parity without a controlled local A/B.
