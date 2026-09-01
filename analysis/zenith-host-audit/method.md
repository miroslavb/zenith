# Методика воспроизводимого аудита

Дата среза: 2026-09-01.

## Источники

Авторитетный mission registry: `/root/.zenith/projects`.

Дополнительные corpus units:

- `/root/.codex/sessions/2026/{06,07,08}`;
- каждый каталог `/root/.claude/projects/*`;
- шесть обнаруженных Hermes homes;
- `/root/.gstack/projects/*/checkpoints`;
- bridge/openclaw evidence units;
- read-only gbrain export mirror.

Все corpus units перечислены в `evidence/coverage_manifest.csv`. Пустой или отсутствующий unit имеет структурную причину пропуска. Сентябрьские Codex sessions исключены, чтобы текущий аудит не создавал собственные совпадения.

## Алгоритм

1. Перечислить все project directories в registry.
2. Прочитать project state и task inventory.
3. Классифицировать nodes как work/validate/gate по ID и сохранить исходный status.
4. Перечислить все attempt reports; извлечь timestamps, `done`, `passed`, `request_attention`, missing `end_node`, rate-limit/timeout/internal-error signals.
5. Считать duration как разницу между filename timestamp и `mtime`; устойчивыми считать 0–6 часов.
6. Перечислить contracts, regressions, evidence и terminal reviews.
7. Выполнить full-file `rg --json` prefilter по каждому corpus unit; сохранить только наличие точной ссылки на зарегистрированный mission ID.
8. Создать редактированные findings по заранее заданной taxonomy; не копировать полные transcripts.
9. Записать детерминированные CSV, JSON и SQLite; повторить запуск и сверить SHA-256 БД.

## Интерпретация

- `validate + gate share` измеряет сложность формального графа.
- `validator agent-hours share` измеряет только наблюдаемое выполнение validator agents.
- Разница между ними не равна overhead: gate может быть полезным state constraint без отдельного agent run.
- Attempt `done=0` — protocol/runtime outcome, не product defect.
- Project `state=done` — terminal registry state, не независимая оценка качества.
- Внешние системы сравниваются по опубликованным результатам только качественно; apples-to-apples speed claim запрещён без локального A/B.

## Privacy

Extractor редактирует bearer/key/password-подобные значения, длинные hex, IPv4 и email. В БД не сохраняются полные raw transcripts. Source paths и locators оставлены для локальной проверяемости.
