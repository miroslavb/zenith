# Таксономия findings

| Pattern ID | Смысл | Интерпретация |
|---|---|---|
| `ZH-ACP-HANDOFF` | Attempt не содержит обязательного `end_node` | Protocol delivery failure; не считать автоматически product failure |
| `ZH-RATE-LIMIT` | В attempt report есть rate-limit signal | External/runtime pressure; возможен повтор без изменения задачи |
| `ZH-REGRESSION` | Создан regression artifact | Независимая проверка нашла или зафиксировала дефект |
| `ZH-SCIENCE-MATERIAL-GAP` | Terminal review содержит научный material gap | Сильное свидетельство ценности high-assurance review |
| `ZH-FORMAL-FALSE-NEGATIVE` | Работа подтверждена, но mission verdict ухудшен protocol failure | Требуется разделение product и protocol verdicts |
| `ZH-OPERATOR-OVERHEAD-STOP` | Оператор остановил миссию из-за protocol overhead | Прямое свидетельство несоответствия assurance profile задаче |

Текущий findings store содержит 521 запись: 267 handoff, 122 regression, 119 rate-limit, 9 science material gaps, 3 formal false negatives и 1 operator overhead stop.
