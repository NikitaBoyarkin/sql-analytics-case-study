# PRD: SQL Analytics Case Study — Portfolio → Conversion

**Автор:** Nikita Boyarkin
**Дата:** 2026-09-19
**Статус:** Draft
**Версия:** 1.0 (роадмап v2.0 проекта)
**Источник:** AJTBD Full Audit — `Obsidian/Z-core/AJTBD - SQL Analytics Case Study Full Audit.md`

---

## 1. Executive Summary

Портфолио из 25 SQL-кейсов технически сильное, но его ценность как hiring-сигнала ограничена: нанимающий может не открыть ссылку (риск #1), портфолио не покрывает dbt/warehouse-стек (риск #5), а честные бизнес-выводы не вынесены в «первые 5 минут» (риск #4). PRD описывает 2-недельный (30–40 ч) роадмап: упаковать доставку сигнала, добавить dbt-паритет на DuckDB и один real-data кейс, инструментировать воронку откликов. Ожидаемый эффект — измеримый рост interview rate при входе в сегменты 1 (SaaS / product analytics) и 2 (e-commerce).

## 2. Problem Statement

### Текущая ситуация

25 self-contained SQL-кейсов, детерминированные данные (seed 42), тесты с golden answers, CI, self-contained HTML-отчёт с графиками, публикация на GitHub Pages. Репозиторий: `github.com/NikitaBoyarkin/sql-analytics-case-study`. Технический слой зрелый; слой «донесения сигнала» и stack-паритета — отсутствует.

### Влияние на пользователя

- **Кто затронут:** нанимающая сторона сегментов 1–2 — Head of Product Analytics / Head of Product / Head of Growth.
- **Как затронут:**
  1. Ссылка на портфолио может не открываться до решения об интервью — актив не работает.
  2. В вакансиях требуются dbt / warehouse-навыки, которых в кейсах нет — отклик фильтруется.
  3. Сильные выводы (one-and-done движок, «no whale tier») спрятаны в 25 кейсах — считываются не за 5 минут.
  4. Нет доказательств переносимости на реальные данные — synthetic-риск.
- **Серьёзность:** High — риски #1–#2 имеют Score 16 (макс.), они обесценивают сам актив.

### Бизнес-влияние

- **Стоимость проблемы:** потерянные интервью/офферы (SOM 4–7 офферов при полной валидации); недоиспользованный актив стоимостью 25 кейсов.
- **Стратегическая важность:** канал найма в сегменты 1–2; вход через портфолио вместо рефералов.

### Почему решать сейчас

Аудит (2026-09-19) зафиксировал: кейсы → есть, delivery и stack parity → нет. Это дешёвые фиксы (30–40 ч), а отклик рынка измерим за 2 недели — до того, как вкладываться в новый стек.

## 3. Goals & Success Metrics

### Goal 1: Доставка сигнала

- **Описание:** нанимающий открывает и просматривает портфолио до интервью.
- **Метрика:** open-rate трекинговой ссылки; interview rate «со ссылкой vs без».
- **Baseline:** 0 (трекинга нет) — *assumption*.
- **Target:** ≥30% открытий на 10 целевых контактах; интервью-рейт со ссылкой выше на ≥20% на 40 откликах.
- **Срок:** 2 недели.
- **Метод измерения:** трекинговая ссылка (Bitly/custom), `GitHub Traffic → Views/Referrers`, A/B-лог откликов.

### Goal 2: Stack parity

- **Описание:** портфолио демонстрирует dbt + warehouse-паттерны.
- **Метрика:** число кейсов, портированных в dbt; число dbt-тестов.
- **Baseline:** 0/25 кейсов; 0 dbt-тестов.
- **Target:** ≥3 кейса в dbt (DuckDB) + ≥1 real-data кейс; ≥5 dbt-тестов зелёные в CI.
- **Срок:** 2 недели.
- **Метод измерения:** файлы `dbt/models/`, `dbt test`, CI-лог.

### Goal 3: Упаковка сигнала

- **Описание:** ценность считывается за 5 минут.
- **Метрика:** наличие README 5-мин блока, live-отчёта, teaser.
- **Baseline:** 0 из 3.
- **Target:** 3 из 3 — блок + live-ссылка + teaser с 3 выводами.
- **Срок:** 2 недели.
- **Метод измерения:** ревью README/лендинга; тайминг прочтения на 3 тестовых читателях.

## 4. User Stories

### Story 1: Хирменеджер оценивает за 5 минут

**As a** Head of Product Analytics, **I want to** get proof of depth in 5 minutes, **So that I can** decide to invite without reading 25 cases.

**Acceptance Criteria:**
- [ ] README содержит блок «How to evaluate in 5 minutes» со ссылкой на live-отчёт.
- [ ] Live-отчёт открывается одним кликом и грузится < 2s на десктопе.
- [ ] Teaser показывает 3 бизнес-вывода (funnel drop, retention cliff, repeat engine).
- [ ] 3 тестовых читателя находят главный вывод за ≤5 минут.

**Dependencies:** REQ-001, REQ-002, REQ-003.

### Story 2: Закрыт dbt-gap

**As a** hiring manager screening for dbt, **I want to** see dbt models and tests, **So that I can** trust the candidate works in our stack.

**Acceptance Criteria:**
- [ ] Поднят dbt-проект на DuckDB (`dbt-duckdb`).
- [ ] ≥3 модели + ≥5 тестов, `dbt build` зелёный локально и в CI.
- [ ] README документирует запуск dbt за ≤3 команды.

**Dependencies:** REQ-004.

### Story 3: Переносимость на реальные данные

**As a** hiring manager, **I want to** see one real-data case, **So that I can** discount the synthetic-demo risk.

**Acceptance Criteria:**
- [ ] 1 кейс на open dataset, воспроизводимый пайплайн.
- [ ] Бизнес-вывод + тест на результат.
- [ ] Источник данных и лицензия указаны.

**Dependencies:** REQ-006.

### Story 4: Кандидат измеряет сигнал

**As the** candidate, **I want to** log applications and outcomes, **So that I can** validate риски #1–#2 и итерировать.

**Acceptance Criteria:**
- [ ] Лог откликов: дата, сегмент, ссылка (да/нет), ответ, исход.
- [ ] A/B-метка «со ссылкой / без» на каждой строке.
- [ ] Open-rate трекинг активен и снимается минимум раз в неделю.

**Dependencies:** REQ-005, REQ-008.

## 5. Functional Requirements

### Must Have (P0) — критично для запуска

#### REQ-001: README «How to evaluate in 5 minutes»

**Описание:** Блок в начале README, который снижает усилие нанимающего до 5 минут: что это, что доказывает, куда смотреть, чем отличается от учебного SQL-проекта.

**Acceptance Criteria:**
- [ ] Блок идёт до раздела «Topics covered» и содержит ссылку на live-отчёт.
- [ ] Явно названы 3 сигнала: глубина SQL, продуктовая рамка (business signal), дисциплина (тесты/golden answers).
- [ ] Есть строка «dbt-версия: см. `dbt/`» со ссылкой.
- [ ] Блок укладывается в ≤200 слов.

**Техническая спецификация:**
```markdown
## How to evaluate in 5 minutes
1. Open the live report → <link>
2. Look at cases 01, 09, 19 (funnel, A/B, repeat engine)
3. Note: every case ships a business signal + tests; dbt models in `dbt/`
```

**Task Breakdown:**
- Черновик блока: Small (2–3h)
- Ревью на 3 читателях: Small (1h)

**Dependencies:** REQ-002 (ссылка на отчёт).

#### REQ-002: Live-отчёт одним кликом (GitHub Pages)

**Описание:** Стабильная публичная ссылка на self-contained HTML-отчёт, доступная без клонов репозитория; навигация по 25 кейсам.

**Acceptance Criteria:**
- [ ] Отчёт доступен по постоянному URL (GitHub Pages) и открывается без авторизации.
- [ ] TOC-навигация работает по всем 25 кейсам.
- [ ] Загрузка < 2s на десктопе; корректный рендер на мобильном (ширина ≥360px).
- [ ] Рендер воспроизводится командой `uv run python scripts/report.py` в CI.

**Техническая спецификация:**
```
.github/workflows/ci.yml → job "report": generate + deploy to gh-pages
artifacts: reports/index.html (self-contained, embedded base64 PNG)
```

**Task Breakdown:**
- Проверка/починка Pages-деплоя: Small (2–3h)
- Ссылка + бейдж в README: Small (1h)

**Dependencies:** None.

#### REQ-003: Signal teaser (3 вывода)

**Описание:** Teaser с 3 сильнейшими бизнес-выводами, пригодный для README и резюме/профиля — увеличивает шанс открытия ссылки.

**Acceptance Criteria:**
- [ ] Ровно 3 вывода: (1) drop add-to-cart→checkout 54%; (2) retention cliff ~21%→5%; (3) repeat rate 3.5% / one-and-done.
- [ ] Каждый вывод — одно предложение с числом.
- [ ] Версия-сниппет ≤3 строк для резюме/LinkedIn.
- [ ] Числа совпадают с `cases.md` (golden answers).

**Техническая спецификация:**
```markdown
> 3 findings: funnel drops 54% at cart→checkout; D1→D30 retention falls 21%→5%;
> only 3.5% of buyers repeat — a one-and-done engine.
```

**Task Breakdown:**
- Отбор и формулировка: Small (2h)
- Сверка с golden answers: Small (1h)

**Dependencies:** None.

#### REQ-004: dbt-проект на DuckDB + 3 портированных кейса

**Описание:** dbt-проект, доказывающий навык model layer: staging → marts, тесты, документация; ≥3 кейса из `cases/` переписаны как dbt-модели на том же DuckDB.

**Acceptance Criteria:**
- [ ] `dbt/` содержит `dbt_project.yml`, `profiles.yml` (duckdb), `models/staging/`, `models/marts/`.
- [ ] ≥3 кейса портированы (например, 01 funnel, 02 retention, 14 MRR) с идентичными golden-числами.
- [ ] ≥5 dbt-тестов (`not_null`, `unique`, `relationships`, custom) — `dbt build` зелёный.
- [ ] README описывает запуск ≤3 командами (`uv sync`, `dbt deps`, `dbt build`).

**Техническая спецификация:**
```
dbt/
  dbt_project.yml
  profiles.yml            # target: duckdb, path: ../data/analytics.duckdb
  models/staging/stg_events.sql
  models/marts/fct_funnel.sql
  models/marts/fct_retention.sql
  models/marts/fct_mrr.sql
  models/schema.yml       # tests
```

**Task Breakdown:**
- Инициализация проекта + профиль: Small (2–3h)
- 3 модели (port): Medium (6–8h)
- 5 тестов + `schema.yml`: Small (3h)
- CI job `dbt build`: Small (2h)

**Dependencies:** REQ-002 (DB в CI).

#### REQ-005: Трекинг внимания

**Описание:** Механика измерения риска #1: открывается ли ссылка. Короткая трекинговая ссылка + документация baseline GitHub traffic.

**Acceptance Criteria:**
- [ ] Создана трекинговая ссылка на live-отчёт (Bitly или self-hosted редирект).
- [ ] Зафиксирован baseline `GitHub Traffic → Views/Referrers` за 30 дней (скриншот/число в лог).
- [ ] Open-rate считается из кликов трекинговой ссылки и пишется в лог откликов (REQ-008).
- [ ] Ссылка используется минимум в 10 целевых контактах.

**Техническая спецификация:**
```
tracking/links.md   # link -> destination, created_at
log/applications.csv # date,segment,link_used,opened,response,outcome
```

**Task Breakdown:**
- Создание ссылки + baseline: Small (1–2h)
- Инструкция фиксации: Small (1h)

**Dependencies:** REQ-002.

### Should Have (P1) — важно, но не блокирует

#### REQ-006: Real-data case study (1 кейс)

**Описание:** Один end-to-end кейс на открытых данных — закрывает synthetic-риск и доказывает переносимость.

**Acceptance Criteria:**
- [ ] Выбран open dataset с лицензией (permissive) и указан источник.
- [ ] Пайплайн воспроизводим одной командой; результат — таблица + график.
- [ ] Есть бизнес-вывод и ≥1 тест на результат.
- [ ] Кейс добавлен в отчёт рядом с synthetic-кейсами.

**Техническая спецификация:**
```
cases/26_realdata_<topic>.sql   (или dbt-модель, если тема в model layer)
data/realdata/README.md          # источник, лицензия, как скачать
```

**Task Breakdown:**
- Выбор датасета + EDA: Medium (4h)
- Кейс + визуализация: Medium (4–6h)
- Тест: Small (2h)

**Dependencies:** REQ-004 (если делается как dbt-модель).

#### REQ-007: Portfolio card / index entry

**Описание:** Карточка проекта в общем портфолио/резюме: что доказывает, стек, ссылки, результат — чтобы сигнал жил вне репозитория.

**Acceptance Criteria:**
- [ ] Карточка содержит: 1 строку ценности, стек, ссылку на live-отчёт, ссылку на репозиторий.
- [ ] Указаны 3 ключевых сигнала из teaser (REQ-003).
- [ ] Карточка добавлена в `00 portfolio`-хаб / персональный сайт.

**Task Breakdown:**
- Текст + вёрстка: Small (2–3h)

**Dependencies:** REQ-002, REQ-003.

#### REQ-008: Application log + A/B «со ссылкой vs без»

**Описание:** Лог откликов, который превращает поиск в измеримый эксперимент и закрывает риск #2.

**Acceptance Criteria:**
- [ ] Лог содержит ≥20 строк за период с колонками: дата, сегмент, ссылка (да/нет), открытие, ответ, исход.
- [ ] Формируется вывод: interview rate «со ссылкой» vs «без» (числа + знак).
- [ ] Правило решения зафиксировано: если lift < 0 — менять доставку, не кейсы.

**Техническая спецификация:**
```
log/applications.csv
log/README.md  # protocol: как заполнять, как считать lift
```

**Task Breakdown:**
- Схема + протокол: Small (2h)
- Ведение и подсчёт: Ongoing (мало часов/неделя)

**Dependencies:** REQ-005.

### Nice to Have (P2) — будущее улучшение

#### REQ-009: dbt docs + lineage + CI dbt job

**Описание:** `dbt docs generate` + линейдж и отдельный CI-job, усиливающие dbt-сигнал.

**Acceptance Criteria:**
- [ ] `dbt docs generate` отрабатывает; lineage доступен.
- [ ] CI-job `dbt build` блокирует merge при падении.
- [ ] README/бейдж показывает статус dbt.

**Task Breakdown:**
- Docs + CI: Medium (4h)

**Dependencies:** REQ-004.

#### REQ-010: Параметризация отчёта (фильтры)

**Описание:** Интерактивные фильтры (channel/country) в HTML-отчёте — усиливает «продуктовость» подачи.

**Acceptance Criteria:**
- [ ] Фильтр по `channel` и `country` пересчитывает хотя бы 3 кейса.
- [ ] Отчёт остаётся self-contained (без внешних ассетов).
- [ ] Не ломает CI-рендер и golden tests.

**Task Breakdown:**
- Прототип фильтра: Large (8h)

**Dependencies:** REQ-002.

## 6. Non-Functional Requirements

### Performance
- Live-отчёт: first paint < 2s на десктопе (self-contained, без сети).
- `dbt build`: < 60s на DuckDB (20k users).
- CI полный прогон (pytest + report + dbt): < 5 мин.

### Security
- Нет секретов/PII в репозитории; данные синтетические + open (с указанием лицензии).
- `profiles.yml` не коммитит креды (для DuckDB креды не требуются).

### Scalability
- Масштаб данных фиксирован (20k users / ~183k events); рост не целевой.
- Отчёт масштабируется по числу кейсов (26+).

### Reliability
- Воспроизводимость: seed 42 → идентичный вывод (golden answers).
- CI зелёный на `main` обязателен перед merge.
- Error rate рендера отчёта: 0 (падает — CI красный).

## 7. Technical Considerations

### Архитектура

```
data/generate_data.py → data/analytics.duckdb (seed 42)
        │                        │
        ├── cases/*.sql ─────────┤
        │                        ├── run.py (CLI)
        └── dbt/models/* ────────┘      │
                                  scripts/report.py → reports/index.html → GitHub Pages
tests/ (pytest: invariants + golden) ──┘
```

### Технологический стек

- **Language:** Python ≥3.10 (`uv` для зависимостей).
- **Analytics DB:** DuckDB (единый движок для cases и dbt).
- **Model layer:** dbt-core + dbt-duckdb.
- **Presentation:** matplotlib (Agg) → self-contained HTML (base64 PNG).
- **CI/CD:** GitHub Actions; деплой отчёта на GitHub Pages.

### Внешние зависимости

1. **Open dataset (REQ-006):** цель — real-data proof; источник с permissive-лицензией; fallback — популярный open dataset (например, e-commerce), зафиксированный в `data/realdata/README.md`.
2. **Bitly / редирект (REQ-005):** цель — трекинг open-rate; fallback — self-hosted редирект или `GitHub Traffic`.

### Миграция

Не ломающая: 25 существующих `.sql` кейсов и golden answers остаются источником истины. dbt-слой — аддитивный (`dbt/`), CI проверяет равенство чисел с кейсами. `cases.md` и `tests/test_golden_answers.py` — по-прежнему две точки истины (при изменении — синхронно).

### Тестирование

- Unit/invariant: существующий pytest для кейсов (сохраняется).
- dbt: ≥5 тестов, `dbt build` в CI.
- Report: CI-рендер без ошибок + ручная проверка на мобильном.
- Golden: числа dbt-моделей = golden answers.

## 8. Implementation Roadmap

### Phase 1: Delivery (Days 1–3, ~10h)

**Goal:** сигнал доходит и считывается за 5 минут.
**Tasks:**
- [ ] Task 1.1: live-отчёт + Pages-ссылка (REQ-002) — Small (3h)
- [ ] Task 1.2: README 5-мин блок (REQ-001) — Small (3h)
- [ ] Task 1.3: teaser 3 вывода (REQ-003) — Small (2h)
- [ ] Task 1.4: трекинговая ссылка + baseline (REQ-005) — Small (2h)

**Validation Checkpoint:** отчёт открывается публично, блок и teaser в README, трекинг активен.

### Phase 2: Stack parity (Days 4–8, ~14h)

**Goal:** закрыт dbt-gap.
**Tasks:**
- [ ] Task 2.1: dbt-проект + профиль (REQ-004) — Small (3h)
- [ ] Task 2.2: 3 модели-порта (REQ-004) — Medium (7h)
- [ ] Task 2.3: 5 тестов + schema.yml (REQ-004) — Small (3h)
- [ ] Task 2.4: CI-job `dbt build` (REQ-004) — Small (2h)

**Validation Checkpoint:** `dbt build` зелёный локально и в CI; числа = golden answers.

### Phase 3: Real data & measurement (Days 9–14, ~12h)

**Goal:** переносимость доказана, воронка измеряется.
**Tasks:**
- [ ] Task 3.1: real-data кейс (REQ-006) — Medium (7h)
- [ ] Task 3.2: portfolio card (REQ-007) — Small (3h)
- [ ] Task 3.3: application log + A/B (REQ-008) — Small (2h)

**Validation Checkpoint:** real-data кейс в отчёте; лог ≥20 откликов; посчитан lift.

### Зависимости задач

```
REQ-002 → REQ-001, REQ-005, REQ-007, REQ-010
REQ-004 → REQ-006(?), REQ-009
REQ-005 → REQ-008
Critical Path: REQ-002 → REQ-004 → REQ-006 → REQ-008
```

### Оценка усилий

- Phase 1: ~10h
- Phase 2: ~14h
- Phase 3: ~12h
- **Итого:** ~36h (~2 недели part-time при ~18h/неделю)
- **Риск-буфер:** +20% (~43h)

## 9. Out of Scope

1. **Cloud warehouse (BigQuery/Snowflake)** — выбран минимальный DuckDB+dbt; переезд — отдельная итерация после валидации сигнала.
2. **Полный перенос всех 25 кейсов в dbt** — достаточно 3 для сигнала; остальное — по мере надобности.
3. **Orchestration (Airflow) и streaming** — не релевантно портфолио-цели.
4. **ML/DS-кейсы** — фокус на SQL/dbt-аналитике.
5. **Платное продвижение** — канал найма тестируется органически (риски #1–#2).

## 10. Open Questions & Risks

### Open Questions

#### Q1: Какой open dataset взять для REQ-006?
- **Статус:** открыт.
- **Варианты:** (A) Brazilian E-Commerce (Olist) — домен совпадает с сегментом 2; (B) NYC taxi — объём, но слабее продуктовая рамка; (C) open retail/sales.
- **Владелец:** кандидат.
- **Дедлайн:** Phase 3, Day 9.
- **Влияние:** Medium.

#### Q2: DuckDB+dbt достаточно для сегмента 1?
- **Статус:** открыт (assumption).
- **Варианты:** (A) да, dbt-навык переносим; (B) нужен cloud warehouse в следующей итерации.
- **Владелец:** кандидат.
- **Дедлайн:** после Phase 2.
- **Влияние:** Medium.

### Risks & Mitigation

| Риск | Вероятность | Влияние | Severity | Митигация | Контингенция |
|------|-------------|---------|----------|-----------|--------------|
| Не открывают ссылку (audit #1) | High | High | **Critical** | REQ-002/003/005: live-ссылка + teaser + трекинг | Сменить доставку (резюме/сообщения), не кейсы |
| Просмотр не конвертит в интервью (audit #2) | High | High | **Critical** | REQ-008: A/B «со ссылкой vs без» + порог ≥20% | Править подачу: teaser, карточка (REQ-007) |
| Навыки не переносятся в прод (audit #3) | Medium | High | **High** | REQ-004/006: dbt на реальных данных | 3 open-data задачи за 1 день, зафиксировать пробелы |
| Не отличает от массы (audit #4) | High | Medium | **High** | Уникальность: tests + golden + honest findings в teaser | Усилить узкую нишу (product/SQL + честные выводы) |
| Stack-vakancij gap (audit #5) | Medium | Medium | **Medium** | REQ-004/009: dbt + CI | Добавить postgres-вариант моделей |

## 11. Validation Checkpoints

### Checkpoint 1: Конец Phase 1

**Критерии:**
- [ ] Live-отчёт доступен по публичному URL; грузится < 2s.
- [ ] README содержит 5-мин блок и teaser (числа = golden answers).
- [ ] Трекинговая ссылка создана, baseline GitHub traffic зафиксирован.

**Если провален:** не переходить к Phase 2 — сначала восстановить доставку (без сигнала stack-parity бесполезен).

### Checkpoint 2: Конец Phase 2

**Критерии:**
- [ ] `dbt build` зелёный локально и в CI; ≥3 модели, ≥5 тестов.
- [ ] Числа dbt = golden answers (`cases.md`).
- [ ] README документирует запуск dbt.

**Если провален:** зафиксировать пробелы, добавить postgres-адаптер или упростить модели до 2.

### Checkpoint 3: Конец Phase 3

**Критерии:**
- [ ] Real-data кейс в отчёте с источником/лицензией и тестом.
- [ ] Лог ≥20 откликов; посчитан interview-rate lift.
- [ ] Портфолио-карточка опубликована.

**Если провален:** решение по правилу REQ-008 — если lift < 0, менять доставку, а не наращивать кейсы.

---

**Конец PRD**

*Шаблон: comprehensive.*
