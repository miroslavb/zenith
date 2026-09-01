# Coverage manifest

Полный per-unit manifest находится в [evidence/coverage_manifest.csv](evidence/coverage_manifest.csv). Все непустые units прочитаны полностью через file-level prefilter; пустые units помечены `STRUCTURAL`.

| Corpus | Units | Candidate files | Files read | Empty units |
|---|---:|---:|---:|---:|
| Claude | 88 | 4 182 | 4 182 | 17 |
| Codex, June–August 2026 | 3 | 2 268 | 2 268 | 0 |
| gbrain export mirror | 1 | 10 096 | 10 096 | 0 |
| gstack checkpoints | 43 | 88 | 88 | 21 |
| Hermes homes | 6 | 458 | 458 | 2 |
| Openclaw | 1 | 0 | 0 | 1 |
| Telegram bridge | 1 | 1 | 1 | 0 |

Точные ссылки на зарегистрированные mission IDs найдены в 42 Codex, 39 Claude и 3 gstack project mappings. Это показатель присутствия миссии в corpus, а не единоличного авторства агента. Для Hermes надёжных exact-ID mappings не найдено; поэтому сравнение качества по провайдеру не выполнялось.

Zenith registry охвачен отдельно и полностью: 42/42 project directories, 1 893 task nodes, 1 136 attempt artifacts, 1 079 contract artifacts и 14 343 evidence files.
