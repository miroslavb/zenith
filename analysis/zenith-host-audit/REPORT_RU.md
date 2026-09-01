# Отчёт: история Zenith-миссий на хосте и более быстрые альтернативы

Дата среза: 1 сентября 2026 года.

## 1. Executive summary

История хоста подтверждает исходную гипотезу частично:

- формальный validation/control слой разросся до 53,1% графа задач;
- фактическая доля времени validator-agents существенно меньше — 27,3% измеримых agent-hours;
- заметная часть задержек вызвана не поиском дефектов, а протокольным churn: missing handoff, rate limits, terminal-review transport failures и повторные dispatches;
- для научных миссий независимая проверка имеет доказанную локальную ценность: она находила ошибки, которые могли превратиться в неверные научные выводы;
- для прототипирования тот же режим избыточен: есть прямой host-side случай остановки Zenith оператором именно из-за protocol overhead.

Рекомендуемая архитектура — не новый монолит вместо Zenith, а risk-tiered portfolio:

- **Lean:** native Codex/Claude subagents + gstack для продукта и прототипов;
- **Standard:** Deep Agents/LangGraph либо нативная команда с одним milestone validator для длительных работ;
- **High:** Zenith для науки, security и необратимых production-изменений;
- **Scientific accelerators:** PaperQA2 для литературы; AiScientist/AI Scientist v2 только как ограниченные экспериментальные контуры.

Ни один найденный внешний benchmark не является apples-to-apples доказательством равного Zenith качества за меньшее время. Поэтому финальная рекомендация включает A/B-пилот, а не немедленную замену.

Краткая версия: [EXECUTIVE_SUMMARY_RU.md](EXECUTIVE_SUMMARY_RU.md).

## 2. Вопрос и границы анализа

Анализ отвечает на четыре вопроса:

1. Сколько формальной assurance-структуры создаёт Zenith на этом хосте?
2. Сколько фактического agent-time уходит на validators, а сколько потерь связано с runtime/protocol failures?
3. Когда эта цена приносила содержательную пользу?
4. Какие доступные оркестраторы или harnesses могут быстрее обслуживать разные классы задач?

Авторитетным реестром считался `/root/.zenith/projects`. Корпуса Codex, Claude, Hermes, gstack, bridge и gbrain export использовались только для установления наличия точных ссылок на идентификаторы миссий и поиска подтверждённых anti-patterns. Сырые диалоги в отчёт и БД не копировались.

Слово «успех» сознательно не используется как синоним `state=done`: миссии различаются по возрасту, критичности и условиям остановки; часть ещё выполняется.

## 3. Метод

Воспроизводимый extractor перечисляет каждый project/task/attempt artifact, классифицирует task nodes как work/validate/gate, считает состояния и извлекает безопасные паттерны из отчётов. Для transcript corpus используется полный file-level `rg --json` prefilter; в findings сохраняются только редактированные excerpts и locators.

Attempt duration вычисляется по timestamp имени attempt-файла и его `mtime`. В устойчивую метрику включены только значения от 0 до 6 часов. Это proxy:

- сумма agent-hours считает параллельных агентов отдельно;
- dispatch wall-hours используют максимум длительности внутри одновременного batch;
- не включают весь parent-orchestrator planning time, ожидание человека и contract-review размышления;
- поэтому 27,3% — оценка наблюдаемого validator execution, а не полная цена assurance.

Артефакты анализа:

- [воспроизводимый extractor](extract.py);
- [SQLite findings store](evidence/findings.db);
- [агрегированный JSON](evidence/summary.json);
- [метрики миссий](evidence/mission_metrics.csv);
- [метрики попыток](evidence/attempt_metrics.csv);
- [coverage manifest](coverage_manifest.md) и [машиночитаемый CSV](evidence/coverage_manifest.csv);
- [таксономия findings](taxonomy.md).
- [verification receipt](verification.md).

## 4. Количественная картина

### 4.1 Реестр и граф задач

| Метрика | Значение |
|---|---:|
| Проекты в реестре | 42 |
| Work nodes | 888 |
| Validate nodes | 662 |
| Gate nodes | 343 |
| Всего nodes | 1 893 |
| Validate + gate | 1 005, или 53,1% |
| Superseded nodes | 553, или 29,2% |
| Contracts | 1 079 |
| Regression artifacts | 122 |
| Evidence files | 14 343, около 1,06 GB |
| Terminal reviews | 52 |

Состояния на дату среза: 18 `done`, 10 `aborted`, 7 `attention_needed`, 4 `mission_running`, 2 `failed`, 1 `mission_planning`. Это snapshot, не коэффициент качества.

### 4.2 Реальное выполнение

| Тип | Attempts | Done | Non-done | Устойчивые agent-hours | Missing `end_node` | Rate limited |
|---|---:|---:|---:|---:|---:|---:|
| Work | 712 | 397 | 315 | 317,5 | 179 | 66 |
| Validate | 424 | 330 | 94 | 119,1 | 88 | 53 |
| **Всего** | **1 136** | **727** | **409** | **436,6** | **267** | **119** |

Выводы:

- 36,0% attempts не дошли до `done`; это attempt/runtime outcome, не дефект продукта;
- обязательный handoff отсутствовал у 23,5% attempts;
- валидаторы заняли 27,3% измеримых agent-hours;
- медиана устойчивой попытки — 15,5 минуты, p90 — 48,8 минуты;
- сумма dispatch-batch wall proxy — 327,9 часа, но она не является календарной длительностью миссий.

### 4.3 Различия по доменам

| Домен | Проекты | `done` на срезе | Nodes | Control share | Attempts | Non-done attempts | Regressions | Terminal GAP headings |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Infrastructure/security | 14 | 2 | 619 | 61,6% | 261 | 83 | 42 | 6 |
| Product/software | 13 | 6 | 901 | 43,8% | 579 | 232 | 45 | 39 |
| Research/process | 3 | 2 | 44 | 43,2% | 34 | 8 | 3 | 0 |
| Scientific | 12 | 8 | 329 | 63,8% | 262 | 86 | 32 | 53 |

Научный домен одновременно имеет самый большой control share и 53 из 98 terminal GAP headings. Это согласуется не с «бесполезной бюрократией», а с тем, что в science reviewer чаще находил содержательные пробелы. Но даже там число gate nodes не доказывает полезность каждого отдельного gate.

## 5. Что было полезным, а что — формальностью

### 5.1 Содержательная ценность

В миссии conformer audit два contract-review прохода нашли 12 материальных дефектов в постановке. Позднейшая проверка выявляла некорректные radial-scaling «conformers», отсутствие требуемых GFN2-xTB energies, устаревшие артефакты и слабую литературную трассируемость. Для научной базы это ошибки результата, а не оформления.

122 regression-артефакта во всём корпусе также не позволяют считать validation пустым. Финальный canary Pearl Hopper, несмотря на общую перегруженность процесса, нашёл реальные эксплуатационные проблемы.

### 5.2 Формальный false negative

В CloudStrix checkpoint зафиксировано: весь feedback batch выполнен, production проверен, 17/17 task nodes очищены, но `end_mission` поставил `failed`, потому что terminal reviewer завершился без `submit_terminal_review`. Это чистое смешение двух verdicts:

- **product verdict:** работа сделана и проверена;
- **protocol verdict:** обязательный transport/handoff не выполнен.

Система должна сохранять второй как recoverable orchestration error, не переписывая первый.

### 5.3 Прототипирование, где assurance стала дороже цели

Pearl Hopper был остановлен оператором с прямой формулировкой о чрезмерном protocol overhead для prototyping. При этом P0 был в основном завершён и 218/218 тестов проходили. Рекомендованный handoff — небольшие прямые slices вне Zenith. Это наиболее сильное локальное подтверждение исходного впечатления пользователя.

### 5.4 Structural cause

Текущий host orchestrator prompt требует минимум два последовательных contract-review passes для любой нетривиальной миссии. Для engineering default строится work → scrutiny validation + real-surface validation → gate. Это тяжелее адаптивного описания в техническом отчёте Zenith, где testing layers выбираются по risk profile.

Иными словами, проблема не только в Zenith как идее, а в локальном policy drift: адаптивная assurance превратилась в почти обязательную двойную assurance.

## 6. Альтернативы

### 6.1 Native Codex subagents + gstack — рекомендуемый default для продукта

Официальный Codex поддерживает специализированных subagents, параллельное выполнение, контекстную изоляцию и пользовательские роли с отдельными моделями, effort, sandbox, MCP и skills. Документация прямо предупреждает о росте token cost и конфликтах при параллельной записи ([OpenAI Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)).

Локальный gstack даёт уже знакомые stage-specific процедуры: plan/review/QA/ship без обязательного атомарного contract DAG для каждой задачи.

Подходит для:

- greenfield MVP;
- коротких product slices;
- рефакторинга с существующими тестами;
- задач, где acceptance можно выразить одним наблюдаемым surface check.

Не заменяет Zenith там, где нужен durable multi-day state machine с доказуемым stop condition.

### 6.2 Claude Code agent teams — быстрый параллельный research/build

Agent teams дают lead, независимых teammates, общий task list и mailbox. Anthropic рекомендует их для research/review, новых модулей, конкурирующих гипотез и cross-layer work. Ограничения существенны: функция experimental, in-process teammates плохо возобновляются, task status может запаздывать, token cost заметно выше ([Anthropic agent teams](https://docs.anthropic.com/en/docs/claude-code/agent-teams)).

Это сильный вариант для 2–4 независимых потоков, но не готовый replacement для многодневной mission ledger.

### 6.3 Deep Agents/LangGraph — основа для «Lean Zenith»

LangGraph предоставляет durable execution, persistence/resume и human-in-the-loop, оставляя архитектуру и prompts разработчику ([LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview)). Deep Agents добавляет filesystem, subagent spawning, long-term memory, context offloading и parallel delegation ([Deep Agents overview](https://docs.langchain.com/oss/python/deepagents/overview)).

Это наиболее подходящая база, если нужен собственный оркестратор с:

- сохраняемым состоянием;
- одним verifier на milestone;
- динамическим assurance profile;
- бюджетом wall-time/tokens;
- чётким разделением product и protocol verdicts.

Цена — собственная инженерия policy, observability и evaluator. Framework сам не гарантирует качество.

### 6.4 AutoGen GraphFlow — исследовательский вариант явного DAG

GraphFlow поддерживает sequential, parallel, conditional и loop control flow, а SelectorGroupChat — model-based выбор следующего агента и termination conditions. Но GraphFlow отмечен как experimental, API и поведение могут меняться ([AutoGen GraphFlow](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/graph-flow.html)).

Рекомендация: лабораторные workflows и сравнительные прототипы, не немедленный production replacement.

### 6.5 TheBotCompany — наиболее близкий внешний long-product pilot

Препринт описывает persistent orchestrator с тремя фазами: strategy, execution и independent verification; состояние хранится в SQLite и файловых артефактах. На четырёх системных проектах система достигла primary objective во всех 4, выполнила 164 milestones за 616 cycles и 142 wall-hours. В ProjDevBench reported overall score — 70; среднее execution — 53,2. При этом output tokens были выше, чем у Claude Code baseline, а авторы прямо отмечают diminishing returns на компактных задачах и bias к проектам с детерминированными oracles ([TheBotCompany preprint](https://arxiv.org/html/2603.25928)).

Это лучший кандидат на ограниченный full-product pilot, но не доказанный более быстрый Zenith: задачи, модели и evaluation различаются.

### 6.6 PaperQA2 — не общий оркестратор, а правильный научный accelerator

PaperQA2 выполняет поиск, сбор источников, citation traversal и synthesis. На LitQA2 reported precision — 85,2%, accuracy — 66%; среднее WikiCrow время — около 491,5 секунды, стоимость — $4,48. Ограничения включают доступность full text, ухудшение на меньших моделях и overconfidence при противоречиях ([PaperQA2](https://arxiv.org/html/2409.13740v2), [код](https://github.com/Future-House/paper-qa)).

Его стоит использовать вместо общего multi-agent DAG на стадии literature review. Он не заменяет экспериментальный контур и domain-specific проверки.

### 6.7 AiScientist и AI Scientist v2 — experimental computational science

Подход «thin control over thick state» использует компактный top-level orchestrator, иерархических агентов и versioned File-as-Bus. В препринте reported improvements на PaperBench и MLE-Bench при 24-часовом лимите на задачу, но публичного готового production runtime пока недостаточно ([AiScientist](https://arxiv.org/html/2604.13018v2)).

AI Scientist v2 автоматизирует hypothesis → experiment → analysis → manuscript; отдельные paper runs занимали от нескольких до 15 часов. Из трёх workshop submissions одна была оценена как acceptance-worthy, две отклонены. Авторы отмечают hallucinated citations, слабый rigor и необходимость ручной подготовки данных ([AI Scientist v2](https://arxiv.org/html/2504.08066v1), [код](https://github.com/SakanaAI/AI-Scientist-v2)).

Подходит только для bounded computational projects с независимой человеческой/Zenith-проверкой. Для wet lab, химической причинности или медицинских выводов это не автономный replacement.

### 6.8 Почему не MetaGPT/ChatDev как default

Исследование 150+ multi-agent traces выделило 14 failure modes: нарушения спецификаций и ролей, неэффективные коммуникации, слабую верификацию и cascading failures. Авторы подчёркивают, что добавление verifier не устраняет ошибки спецификации, дизайна и коммуникации ([MAS failure taxonomy](https://arxiv.org/html/2503.13657v1)). Это соответствует истории хоста: больше агентов и больше формальных сообщений сами по себе не дают более быстрый или более правильный результат.

## 7. Сравнительная рекомендация

| Вариант | Скорость запуска | Durable long-run | Независимая verification | Научная пригодность | Рекомендация |
|---|---|---|---|---|---|
| Native Codex + gstack | Высокая | Средняя | По требованию | Средняя | Default для продукта |
| Claude agent teams | Высокая | Низкая/средняя | По требованию | Хорошая для parallel research | Использовать для 2–4 потоков |
| Deep Agents/LangGraph | Средняя | Высокая | Проектируется | Зависит от tools | Строить Lean Zenith |
| AutoGen | Средняя | Средняя | Проектируется | Средняя | Только pilot |
| TheBotCompany | Средняя | Высокая | Встроена | Ограниченная | Full-product pilot |
| PaperQA2 | Высокая в своём контуре | Средняя | Citation-grounded | Высокая для литературы | Включить в science stack |
| AiScientist/AI Scientist v2 | Низкая/средняя | Высокая | Недостаточная без внешнего reviewer | Вычислительная наука | Experimental only |
| Zenith high assurance | Низкая | Высокая | Сильная | Высокая | Сохранить для high risk |

## 8. Предлагаемая operating model

### Lean

Критерии: обратимые изменения, нет чувствительных данных/денег/безопасности, acceptance наблюдаем тестом или UI/API check.

- один lead;
- до трёх subagents;
- contract — короткий checklist, не atomic DAG;
- один integration reviewer;
- terminal review advisory;
- жёсткий wall-time/token budget.

### Standard

Критерии: длительная задача, несколько компонентов, production-adjacent, но rollback реалистичен.

- durable state;
- milestones с runnable artifact;
- один contract review;
- один независимый validator, выбранный по поверхности: browser/API/CLI/security/data;
- один gate на milestone;
- дополнительный validator только при material finding.

### High assurance

Критерии: научные claims, безопасность, финансы, необратимая миграция, high-blast-radius production.

- текущий Zenith dual validation;
- source-grounded scientific review;
- hard terminal gate;
- независимые evidence artifacts;
- возможна human approval.

## 9. Изменения в Zenith

1. **Assurance profile как first-class state.** `lean | standard | high`, с явным upgrade по риску и downgrade после clean streak.
2. **Разделение verdicts.** `work_result`, `validation_result`, `protocol_delivery_result`. Missing `end_node` не должен менять доказанный product verdict.
3. **Один review loop по умолчанию.** Второй включается только после material gap, а не из-за самого факта нетривиальной задачи.
4. **Surface-selective validation.** Не запускать scrutiny и user-testing автоматически, если один из них не может добавить новую наблюдаемую информацию.
5. **Evidence reuse.** Assertions объединяются в evidence packages; один свежий тест может закрывать несколько assertions.
6. **Value telemetry.** `new material defects / validator-hour`, доля duplicate/no-new-finding reviews, handoff failure rate, wait time, model/token spend.
7. **Stop rules.** Завершать validation после одного clean pass в lean/standard; продолжать в high или после находки.
8. **Recovery.** Terminal reviewer crash повторяет только terminal review, а не миссию и не validators.

## 10. Оценка возможной экономии

Наблюдаемое validator execution — 119,1 часа. Удаление одной из двух lanes на low/medium-risk задачах даёт теоретический потолок около 59,6 agent-hours, или 13,6% от всех 436,6 измеримых agent-hours. Реальный wall-time эффект может быть меньше из-за параллельности или больше благодаря сокращению ожиданий, contract reviews и повторных dispatches.

Поэтому числа 30–50% для product и 10–20% для science следует использовать как **порог успеха пилота**, не как прогноз, уже доказанный историей.

## 11. A/B-пилот

Нужны 12 сопоставимых заданий:

- 4 product;
- 4 infrastructure;
- 4 scientific/computational.

Для каждого домена половина выполняется Zenith high, половина risk-tiered stack. Модель, effort, инструменты, fixtures и token cap одинаковы. Независимый blind evaluator не знает harness.

Primary metric:

`accepted deliverable by independent evaluator / wall-clock hour`.

Secondary metrics:

- escaped severity-1/2 defects;
- rework cycles;
- agent-hours и token cost;
- material findings на validator-hour;
- handoff/protocol failure rate;
- доля assertions с reused evidence.

Decision rule:

- product default меняется, если wall time ниже минимум на 30%, а escaped high-severity defects не растут;
- science меняется только при сохранении claim/citation/experiment correctness и экономии минимум 10%;
- TheBotCompany/Deep Agents допускаются в production только после recovery/resume и fault-injection tests.

## 12. Ограничения

- Нет единой ground-truth оценки качества всех 42 миссий.
- Provider attribution в runtime registry неполна. Точные mission IDs встречаются в 42 Codex и 39 Claude project corpora, но это доказывает участие/ссылку, а не единоличное авторство. Для Hermes надёжной атрибуции миссий не получено.
- `mtime` — proxy длительности; parent planning и человеческие паузы не измерены.
- Non-done attempt может означать полезную частичную работу, rate limit или потерянный handoff.
- Evidence volume и число contracts не являются сами по себе ни пользой, ни waste.
- Внешние benchmarks различаются по моделям, задачам, бюджетам и evaluator; прямой speed parity с Zenith не установлен.
- TheBotCompany, AiScientist и AI Scientist v2 — препринты; результаты следует воспроизводить локально.

## 13. Ключевые локальные источники

- Текущий policy: [`/root/.claude/orchestrator_prompt.md`](/root/.claude/orchestrator_prompt.md).
- CloudStrix false-negative checkpoint: [`20260701-191158-cloudstrix-18.06-feedback-closed-prod-bugs-fixed.md`](/root/.gstack/projects/miroslavb-cloudstrix-integra/checkpoints/20260701-191158-cloudstrix-18.06-feedback-closed-prod-bugs-fixed.md).
- Pearl Hopper operator stop: [`20260823-233359-pearl-hopper-zenith-stopped-p0-p1-p2-handoff.md`](/root/.gstack/projects/miroslavb-pearl-hopper/checkpoints/20260823-233359-pearl-hopper-zenith-stopped-p0-p1-p2-handoff.md).
- Scientific conformer audit: [`20260710-110724-zenith-conformer-audit-p0-p2.md`](/root/.gstack/projects/biometaldb-conformer-audit/checkpoints/20260710-110724-zenith-conformer-audit-p0-p2.md).

Все агрегаты и редактированные locators сохранены в [findings.db](evidence/findings.db).

## 14. Итог

Zenith на этом хосте слишком тяжёл для default product loop, но остаётся оправданным high-assurance режимом. Самая быстрая безопасная альтернатива уже есть на хосте: native subagents + gstack, дополненные одним независимым surface validator. Для многодневного состояния лучше строить Lean Zenith на Deep Agents/LangGraph или пилотировать TheBotCompany. Науку следует ускорять специализированными literature/experiment agents, не снимая внешнюю проверку claims.

Ключевая организационная смена: **проверять по риску и новой информации, а не по количеству формальных assertions**.
