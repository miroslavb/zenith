# Zenith: новая политика маршрутизации миссий на хосте

Дата решения и внедрения: 1 сентября 2026 года.

## Executive summary

Zenith больше не является автоматической эскалацией для любой нетривиальной,
долгой, многошаговой или multi-agent задачи. Его запуск теперь требует либо
прямого указания пользователя (`/zenith`, «используй Zenith», «продолжи миссию
Zenith»), либо отдельного явного одобрения после того, как агент объяснил
конкретную high-assurance необходимость.

Обычная продуктовая разработка, прототипирование, debugging, исследования и
длительные, но обратимые изменения по умолчанию выполняются одним ведущим
агентом с ограниченным числом native subagents и одной интеграционной проверкой.
Zenith сохраняется для науки, security, финансовых или необратимых production-
изменений, когда цена ошибки высока, durable state необходим, а независимая
верификация даёт новую доказательную ценность.

## Почему политика изменена

Аудит 42 локальных Zenith-проектов показал:

- 1 005 из 1 893 task nodes, или **53,1%**, относятся к validate/gate;
- validator agents заняли **119,1 из 436,6 измеримых agent-hours — 27,3%**;
- 409 из 1 136 attempts, или **36,0%**, не дошли до `done`;
- у 267 attempts, или **23,5%**, отсутствовал обязательный `end_node`;
- 119 attempts содержали rate-limit signal;
- 122 regression artifacts подтверждают, что независимая проверка часто
  находит реальные дефекты;
- научные проекты имели самый высокий formal-control share — **63,8%**, но
  именно там reviewers находили материальные ошибки в конформерах, энергиях и
  литературной трассируемости;
- в CloudStrix завершённая и проверенная работа получила формальный `failed`
  из-за crash terminal reviewer;
- Pearl Hopper был остановлен оператором из-за чрезмерного protocol overhead
  для prototyping, несмотря на 218/218 проходящих тестов.

Следовательно, проблема не в независимой проверке как таковой, а в её
безусловном применении и смешении product verdict с transport/protocol verdict.

## Новое правило активации Zenith

Zenith разрешён только при одном из двух условий:

1. пользователь прямо вызывает `/zenith`, просит использовать Zenith или
   продолжить конкретную Zenith-миссию;
2. агент описывает high-assurance case, после чего пользователь отдельно и
   явно одобряет запуск Zenith.

Для второго условия одновременно необходимы:

- высокая цена ошибки: научная корректность, security, финансовый риск,
  необратимое production-изменение или сопоставимый blast radius;
- реальная потребность в durable multi-session state;
- независимые evidence surfaces, способные добавить новую информацию;
- ожидаемая ценность выше стоимости contracts, validators, gates и terminal
  review.

Complexity, длительность, multi-agent формулировка, совпадение с описанием skill
или доступность Zenith MCP **не являются разрешением**. При сомнении агент
остаётся в lean-режиме и спрашивает пользователя, а не запускает Zenith.

## Маршрутизация по умолчанию

| Задача | Default route | Когда повышать assurance |
|---|---|---|
| Продукт, MVP, прототип | Native Codex/Claude + bounded subagents + один integration check | Только при высоком blast radius |
| Обычная разработка/debugging | Lead agent + существующие tests/QA/review skills | При security/data/irreversibility |
| Длительная stateful работа | Staged native handoffs; при наличии — Deep Agents/LangGraph | Zenith только после отдельного одобрения |
| Параллельный research | Native subagents или Claude agent teams | Если выводы high-stakes и требуют независимого evidence review |
| Научная литература | TAMA/AskChem и PaperQA2-подобный citation-grounded контур | Zenith для итоговых claims высокой значимости |
| Вычислительная наука | Bounded experiment agents; AiScientist/AI Scientist v2 только как пилот | Независимый Zenith/human review обязателен для важных выводов |
| Security/необратимый production | Сначала risk assessment | Zenith — предпочтительный кандидат после approval |

## Оценённые альтернативы

- **Native Codex subagents + gstack** — основной быстрый путь для продукта:
  параллельная специализация без постоянного contract DAG. Ограничение — нет
  готовой многодневной mission ledger уровня Zenith.
  [Документация Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents).
- **Claude Code agent teams** — удобны для независимых research/build потоков,
  но experimental, расходуют больше токенов и имеют ограничения resume.
  [Документация Anthropic](https://docs.anthropic.com/en/docs/claude-code/agent-teams).
- **Deep Agents/LangGraph** — лучшая основа для лёгкого durable orchestrator:
  persistence, resume, HITL, memory и subagents; policy и evaluator нужно
  проектировать самостоятельно.
  [Deep Agents](https://docs.langchain.com/oss/python/deepagents/overview),
  [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview).
- **TheBotCompany** — наиболее близкий кандидат для многочасового создания
  полного продукта; результаты препринта сильные, но не являются прямым A/B с
  Zenith и требуют больше tokens.
  [Препринт](https://arxiv.org/html/2603.25928).
- **PaperQA2** — специализированный и более пропорциональный контур для поиска
  и синтеза литературы с citations; не заменяет экспериментальную проверку.
  [PaperQA2](https://arxiv.org/html/2409.13740v2).
- **AiScientist / AI Scientist v2** — перспективны для bounded computational
  science, но пока требуют внешней проверки из-за проблем rigor и citations.
  [AiScientist](https://arxiv.org/html/2604.13018v2),
  [AI Scientist v2](https://arxiv.org/html/2504.08066v1).

Ни одна альтернатива пока не доказала на тех же локальных задачах одновременно
«качество Zenith и меньшее wall time». Для такого вывода нужен controlled A/B.

## Что изменено на хосте

Политика добавлена в 18 live system-instruction surfaces:

- `/root/AGENTS.md`, `/root/.codex/AGENTS.md`;
- `/root/CLAUDE.md`, `/root/.claude/CLAUDE.md`;
- основной Hermes `SOUL.md`, шесть профильных SOUL и семь standalone Hermes
  homes/profiles.

Activation gate добавлен во все пять активных путей skill `zenith`:

- `/root/.agents/skills/zenith/`;
- `/root/.codex/skills/zenith/`;
- `/root/.claude/skills/zenith/`;
- `/root/.hermes/skills/zenith/`;
- `/root/.hermes-ox-alpha/skills/zenith/`.

Три OpenAI skill metadata-файла также переименовали действие в opt-in
high-assurance и больше не предлагают общий «long-running mission» как default.
Zenith MCP и ручная команда `/zenith` оставлены доступными: политика ограничивает
автоматический запуск, а не удаляет инструмент.

## Проверка внедрения

- каждый из 18 system-instruction файлов содержит ровно один marker
  `ZENITH-ROUTING-POLICY:start`;
- каждый активный skill-path содержит restricted frontmatter и `Activation gate`;
- Hermes и Hermes OX Alpha используют согласованный hard-linked skill;
- skill descriptions прямо запрещают auto-trigger по сложности, длительности,
  multi-agent характеру и пользе review;
- действующие Zenith missions не возобновляются без прямой просьбы пользователя.

## Следующий измеримый шаг

Провести A/B на 12 сопоставимых заданиях: по четыре product, infrastructure и
scientific. Primary metric — accepted deliverable независимым evaluator на час
wall time. Product default меняется окончательно при экономии не менее 30% без
роста escaped severity-1/2 defects; science — при экономии не менее 10% без
ухудшения claim/citation/experiment correctness.

## Источники и воспроизводимость

Полный локальный аудит, extractor, CSV и SQLite findings store:
`/root/zenith-alternatives-report/analysis/zenith-host-audit/`.

Полный отчёт:
`/root/zenith-alternatives-report/analysis/zenith-host-audit/REPORT_RU.md`.

Источник решения: анализ истории миссий и прямое указание пользователя от
2026-09-01. `[Source: User + host audit, 2026-09-01]`
