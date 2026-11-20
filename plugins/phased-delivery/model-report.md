# Model report

Generated daily by `.github/workflows/model-report.yml` from
`model-report.json`; do not edit by hand. `scripts/select-models.py` reads
the JSON; this file is for people.

Checked: 2026-11-19
Intelligence index version: 5
Rows: 194 (Anthropic and OpenAI, one per model and thinking level)

Effort comes from the name's suffix, for example "(Max)". Benchmark run cost
is what running the whole intelligence benchmark cost at that model and
level, so it counts the tokens the level spends, not only the price.

| Creator | Model | Effort | Variant | Slug | Released | Intelligence | Engineering | Benchmark run cost (USD) | Price in / out ($ per 1M) | Output tokens/s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Anthropic | Claude 2.0 |  |  | claude-2 | 2023-07-11 |  |  |  |  |  |
| Anthropic | Claude 2.1 |  |  | claude-21 | 2023-11-21 |  |  |  |  |  |
| Anthropic | Claude 3 Haiku |  |  | claude-3-haiku | 2024-03-04 |  |  |  | 0.25 / 1.25 |  |
| Anthropic | Claude 3 Opus |  |  | claude-3-opus | 2024-03-04 |  |  |  | 15.00 / 75.00 |  |
| Anthropic | Claude 3 Sonnet |  |  | claude-3-sonnet | 2024-03-04 |  |  |  |  |  |
| Anthropic | Claude 3.5 Haiku |  |  | claude-3-5-haiku | 2024-10-22 |  |  |  |  |  |
| Anthropic | Claude 3.5 Sonnet | june '24 | June '24 | claude-35-sonnet-june-24 | 2024-06-21 |  |  |  | 3.00 / 15.00 |  |
| Anthropic | Claude 3.5 Sonnet | oct '24 | Oct '24 | claude-35-sonnet | 2024-10-22 |  |  |  | 3.00 / 15.00 |  |
| Anthropic | Claude 3.7 Sonnet | non-reasoning | Non-reasoning | claude-3-7-sonnet | 2025-02-24 |  |  |  | 3.00 / 15.00 |  |
| Anthropic | Claude 3.7 Sonnet | reasoning | Reasoning | claude-3-7-sonnet-thinking | 2025-02-24 |  |  |  |  |  |
| Anthropic | Claude 4 Opus | non-reasoning | Non-reasoning | claude-4-opus | 2025-05-22 |  |  |  | 15.00 / 75.00 |  |
| Anthropic | Claude 4 Opus | reasoning | Reasoning | claude-4-opus-thinking | 2025-05-22 |  |  |  | 15.00 / 75.00 |  |
| Anthropic | Claude 4 Sonnet | non-reasoning | Non-reasoning | claude-4-sonnet | 2025-05-22 |  |  |  |  |  |
| Anthropic | Claude 4 Sonnet | reasoning | Reasoning | claude-4-sonnet-thinking | 2025-05-22 |  |  |  |  |  |
| Anthropic | Claude 4.1 Opus | non-reasoning | Non-reasoning | claude-4-1-opus | 2025-08-05 |  |  |  | 15.00 / 75.00 |  |
| Anthropic | Claude 4.1 Opus | reasoning | Reasoning | claude-4-1-opus-thinking | 2025-08-05 |  |  |  | 15.00 / 75.00 |  |
| Anthropic | Claude 4.5 Haiku | non-reasoning | Non-reasoning | claude-4-5-haiku | 2025-10-15 |  |  |  | 1.00 / 5.00 | 97 |
| Anthropic | Claude 4.5 Haiku | reasoning | Reasoning | claude-4-5-haiku-reasoning | 2025-10-15 | 7.4 | 17.0 | 541.07 | 1.00 / 5.00 | 109 |
| Anthropic | Claude 4.5 Sonnet | non-reasoning | Non-reasoning | claude-4-5-sonnet | 2025-09-29 |  |  |  | 3.00 / 15.00 | 53 |
| Anthropic | Claude 4.5 Sonnet | reasoning | Reasoning | claude-4-5-sonnet-thinking | 2025-09-29 |  |  |  | 3.00 / 15.00 | 56 |
| Anthropic | Claude Fable 5 | max | Max, Opus 4.8 Fallback | claude-fable-5 | 2026-06-09 |  |  |  | 10.00 / 50.00 | 85 |
| Anthropic | Claude Fable 5.1 | high | High, Default Fallback | claude-fable-5-1-high | 2026-09-01 | 47.2 | 54.3 | 6617.89 | 10.00 / 50.00 | 84 |
| Anthropic | Claude Fable 5.1 | low | Low, Default Fallback | claude-fable-5-1-low | 2026-09-01 | 38.7 | 45.6 | 3885.94 | 10.00 / 50.00 | 83 |
| Anthropic | Claude Fable 5.1 | max | Max, Default Fallback | claude-fable-5-1 | 2026-09-01 | 49.2 | 56.7 | 13326.78 | 10.00 / 50.00 | 90 |
| Anthropic | Claude Fable 5.1 | medium | Medium, Default Fallback | claude-fable-5-1-medium | 2026-09-01 | 43.2 | 50.2 | 4896.58 | 10.00 / 50.00 | 84 |
| Anthropic | Claude Fable 5.1 | xhigh | Xhigh, Default Fallback | claude-fable-5-1-xhigh | 2026-09-01 | 50.0 | 57.2 | 10096.62 | 10.00 / 50.00 | 84 |
| Anthropic | Claude Fable 5.2 | high | High, Default Fallback | claude-fable-5-2-high | 2026-11-09 | 61.8 | 69.6 | 7105.77 | 8.00 / 40.00 | 107 |
| Anthropic | Claude Fable 5.2 | low | Low, Default Fallback | claude-fable-5-2-low | 2026-11-09 | 53.9 | 61.6 | 2861.78 | 8.00 / 40.00 | 109 |
| Anthropic | Claude Fable 5.2 | max | Max, Default Fallback | claude-fable-5-2 | 2026-11-09 | 64.6 | 72.6 | 22191.42 | 8.00 / 40.00 | 110 |
| Anthropic | Claude Fable 5.2 | medium | Medium, Default Fallback | claude-fable-5-2-medium | 2026-11-09 | 56.4 | 64.7 | 3359.66 | 8.00 / 40.00 | 111 |
| Anthropic | Claude Fable 5.2 | xhigh | Xhigh, Default Fallback | claude-fable-5-2-xhigh | 2026-11-09 | 62.2 | 70.2 | 11741.62 | 8.00 / 40.00 | 110 |
| Anthropic | Claude Haiku 5.5 | high | High | claude-haiku-5-5-high | 2026-10-07 | 29.9 | 36.5 | 121.41 | 0.10 / 0.50 | 226 |
| Anthropic | Claude Haiku 5.5 | low | Low | claude-haiku-5-5-low | 2026-10-07 | 18.6 | 26.8 | 39.60 | 0.10 / 0.50 | 212 |
| Anthropic | Claude Haiku 5.5 | max | Max | claude-haiku-5-5 | 2026-10-07 | 36.5 | 42.5 | 339.47 | 0.10 / 0.50 | 254 |
| Anthropic | Claude Haiku 5.5 | medium | Medium | claude-haiku-5-5-medium | 2026-10-07 | 24.6 | 31.8 | 72.70 | 0.10 / 0.50 | 221 |
| Anthropic | Claude Haiku 5.5 | xhigh | Xhigh | claude-haiku-5-5-xhigh | 2026-10-07 | 34.6 | 40.6 | 192.70 | 0.10 / 0.50 | 237 |
| Anthropic | Claude Instant |  |  | claude-instant | 2023-03-14 |  |  |  |  |  |
| Anthropic | Claude Opus 4.5 | non-reasoning | Non-reasoning | claude-opus-4-5 | 2025-11-24 |  |  |  | 5.00 / 25.00 | 58 |
| Anthropic | Claude Opus 4.5 | reasoning | Reasoning | claude-opus-4-5-thinking | 2025-11-24 |  |  |  | 5.00 / 25.00 | 60 |
| Anthropic | Claude Opus 4.6 | max | Max | claude-opus-4-6-adaptive | 2026-02-05 |  |  |  | 5.00 / 25.00 | 52 |
| Anthropic | Claude Opus 4.6 | non-reasoning | Non-reasoning, High | claude-opus-4-6 | 2026-02-05 |  |  |  | 5.00 / 25.00 | 50 |
| Anthropic | Claude Opus 4.7 | max | Max | claude-opus-4-7 | 2026-04-16 |  |  |  | 5.00 / 25.00 | 81 |
| Anthropic | Claude Opus 4.7 | non-reasoning | Non-reasoning, High | claude-opus-4-7-non-reasoning | 2026-04-16 |  |  |  | 5.00 / 25.00 | 74 |
| Anthropic | Claude Opus 4.8 | max | Max | claude-opus-4-8 | 2026-05-28 |  |  |  | 5.00 / 25.00 | 84 |
| Anthropic | Claude Opus 5 | high | High | claude-opus-5-high | 2026-07-24 |  |  |  | 5.00 / 25.00 | 80 |
| Anthropic | Claude Opus 5 | low | Low | claude-opus-5-low | 2026-07-24 |  |  |  | 5.00 / 25.00 | 74 |
| Anthropic | Claude Opus 5 | max | Max | claude-opus-5 | 2026-07-24 | 44.2 | 51.3 | 9009.82 | 5.00 / 25.00 | 80 |
| Anthropic | Claude Opus 5 | medium | Medium | claude-opus-5-medium | 2026-07-24 |  |  |  | 5.00 / 25.00 | 77 |
| Anthropic | Claude Opus 5 | xhigh | Xhigh | claude-opus-5-xhigh | 2026-07-24 |  |  |  | 5.00 / 25.00 | 80 |
| Anthropic | Claude Opus 5.5 | high | High, Default Fallback | claude-opus-5-5-high | 2026-09-22 | 51.8 | 57.8 | 2715.98 | 4.00 / 20.00 | 106 |
| Anthropic | Claude Opus 5.5 | low | Low, Default Fallback | claude-opus-5-5-low | 2026-09-22 | 34.8 | 43.2 | 979.66 | 4.00 / 20.00 | 103 |
| Anthropic | Claude Opus 5.5 | max | Max, Default Fallback | claude-opus-5-5 | 2026-09-22 | 59.1 | 65.3 | 8909.67 | 4.00 / 20.00 | 115 |
| Anthropic | Claude Opus 5.5 | medium | Medium, Default Fallback | claude-opus-5-5-medium | 2026-09-22 | 48.2 | 53.7 | 2031.27 | 4.00 / 20.00 | 105 |
| Anthropic | Claude Opus 5.5 | xhigh | Xhigh, Default Fallback | claude-opus-5-5-xhigh | 2026-09-22 | 57.4 | 62.9 | 4765.91 | 4.00 / 20.00 | 107 |
| Anthropic | Claude Sonnet 4.6 | max | Max | claude-sonnet-4-6-adaptive | 2026-02-17 |  |  |  | 3.00 / 15.00 | 59 |
| Anthropic | Claude Sonnet 4.6 | non-reasoning | Non-reasoning, High | claude-sonnet-4-6 | 2026-02-17 |  |  |  | 3.00 / 15.00 | 53 |
| Anthropic | Claude Sonnet 4.6 | non-reasoning | Non-reasoning, Low | claude-sonnet-4-6-non-reasoning-low-effort | 2026-02-17 |  |  |  | 3.00 / 15.00 | 57 |
| Anthropic | Claude Sonnet 5 | high | High | claude-sonnet-5-high | 2026-06-30 |  |  |  | 2.00 / 10.00 | 103 |
| Anthropic | Claude Sonnet 5 | low | Low | claude-sonnet-5-low | 2026-06-30 |  |  |  | 2.00 / 10.00 | 92 |
| Anthropic | Claude Sonnet 5 | max | Max | claude-sonnet-5 | 2026-06-30 |  |  |  | 2.00 / 10.00 | 104 |
| Anthropic | Claude Sonnet 5 | medium | Medium | claude-sonnet-5-medium | 2026-06-30 |  |  |  | 2.00 / 10.00 | 93 |
| Anthropic | Claude Sonnet 5 | non-reasoning | Non-reasoning, High | claude-sonnet-5-non-reasoning | 2026-06-30 |  |  |  | 2.00 / 10.00 | 96 |
| Anthropic | Claude Sonnet 5 | xhigh | Xhigh | claude-sonnet-5-xhigh | 2026-06-30 |  |  |  | 2.00 / 10.00 | 103 |
| Anthropic | Claude Sonnet 5.5 | high | High, Default Fallback | claude-sonnet-5-5-high | 2026-09-28 | 41.5 | 46.2 | 1268.30 | 2.00 / 10.00 | 135 |
| Anthropic | Claude Sonnet 5.5 | low | Low, Default Fallback | claude-sonnet-5-5-low | 2026-09-28 | 25.6 | 33.4 | 499.20 | 2.00 / 10.00 | 133 |
| Anthropic | Claude Sonnet 5.5 | max | Max, Default Fallback | claude-sonnet-5-5 | 2026-09-28 | 54.5 | 58.5 | 7980.63 | 2.00 / 10.00 | 145 |
| Anthropic | Claude Sonnet 5.5 | medium | Medium, Default Fallback | claude-sonnet-5-5-medium | 2026-09-28 | 30.8 | 37.3 | 679.16 | 2.00 / 10.00 | 135 |
| Anthropic | Claude Sonnet 5.5 | xhigh | Xhigh, Default Fallback | claude-sonnet-5-5-xhigh | 2026-09-28 | 49.9 | 53.8 | 2902.50 | 2.00 / 10.00 | 141 |
| OpenAI | Astra for Law 6.2 | max | Max | astra-for-law-6-2 | 2026-11-17 |  |  |  | 8.00 / 40.00 |  |
| OpenAI | GPT-3.5 Turbo |  |  | gpt-35-turbo | 2022-11-30 |  |  |  |  |  |
| OpenAI | GPT-3.5 Turbo | 0613 | 0613 | gpt-3-5-turbo-0613 | 2023-06-13 |  |  |  |  |  |
| OpenAI | GPT-4 |  |  | gpt-4 | 2023-03-14 |  |  |  |  |  |
| OpenAI | GPT-4 Turbo |  |  | gpt-4-turbo | 2023-11-06 |  |  |  | 10.00 / 30.00 | 83 |
| OpenAI | GPT-4.1 |  |  | gpt-4-1 | 2025-04-14 |  |  |  | 2.00 / 8.00 | 108 |
| OpenAI | GPT-4.1 mini |  |  | gpt-4-1-mini | 2025-04-14 |  |  |  | 0.40 / 1.60 | 81 |
| OpenAI | GPT-4.1 nano |  |  | gpt-4-1-nano | 2025-04-14 |  |  |  | 0.10 / 0.40 | 162 |
| OpenAI | GPT-4.5 | preview | Preview | gpt-4-5 | 2025-02-27 |  |  |  |  |  |
| OpenAI | GPT-4o | aug '24 | Aug '24 | gpt-4o-2024-08-06 | 2024-08-06 |  |  |  | 2.50 / 10.00 | 85 |
| OpenAI | GPT-4o | chatgpt | ChatGPT | gpt-4o-chatgpt | 2025-02-15 |  |  |  |  |  |
| OpenAI | GPT-4o | march 2025 | March 2025, chatgpt-4o-latest | gpt-4o-chatgpt-03-25 | 2025-03-27 |  |  |  |  |  |
| OpenAI | GPT-4o | may '24 | May '24 | gpt-4o-2024-05-13 | 2024-05-13 |  |  |  | 5.00 / 15.00 | 94 |
| OpenAI | GPT-4o | nov '24 | Nov '24 | gpt-4o | 2024-11-20 |  |  |  | 2.50 / 10.00 | 107 |
| OpenAI | GPT-4o Realtime | dec '24 | Dec '24 | gpt-4o-realtime-dec-2024 | 2024-12-17 |  |  |  |  |  |
| OpenAI | GPT-4o mini |  |  | gpt-4o-mini | 2024-07-18 |  |  |  | 0.15 / 0.60 | 53 |
| OpenAI | GPT-4o mini Realtime | dec '24 | Dec '24 | gpt-4o-mini-realtime-dec-2024 | 2024-12-17 |  |  |  |  |  |
| OpenAI | GPT-5 | chatgpt | ChatGPT | gpt-5-chatgpt | 2025-08-07 |  |  |  |  |  |
| OpenAI | GPT-5 | high | High | gpt-5 | 2025-08-07 |  |  |  | 1.25 / 10.00 | 78 |
| OpenAI | GPT-5 | low | Low | gpt-5-low | 2025-08-07 |  |  |  | 1.25 / 10.00 | 67 |
| OpenAI | GPT-5 | medium | Medium | gpt-5-medium | 2025-08-07 |  |  |  | 1.25 / 10.00 | 82 |
| OpenAI | GPT-5 | minimal | Minimal | gpt-5-minimal | 2025-08-07 |  |  |  | 1.25 / 10.00 | 62 |
| OpenAI | GPT-5 Codex | high | High | gpt-5-codex | 2025-09-23 |  |  |  | 1.25 / 10.00 | 128 |
| OpenAI | GPT-5 mini | high | High | gpt-5-mini | 2025-08-07 |  |  |  | 0.25 / 2.00 | 92 |
| OpenAI | GPT-5 mini | medium | Medium | gpt-5-mini-medium | 2025-08-07 |  |  |  | 0.25 / 2.00 | 88 |
| OpenAI | GPT-5 mini | minimal | Minimal | gpt-5-mini-minimal | 2025-08-07 |  |  |  | 0.25 / 2.00 | 75 |
| OpenAI | GPT-5 nano | high | High | gpt-5-nano | 2025-08-07 |  |  |  | 0.05 / 0.40 | 149 |
| OpenAI | GPT-5 nano | medium | Medium | gpt-5-nano-medium | 2025-08-07 |  |  |  | 0.05 / 0.40 | 150 |
| OpenAI | GPT-5 nano | minimal | Minimal | gpt-5-nano-minimal | 2025-08-07 |  |  |  | 0.05 / 0.40 | 128 |
| OpenAI | GPT-5.1 | high | High | gpt-5-1 | 2025-11-13 |  |  |  | 1.25 / 10.00 | 85 |
| OpenAI | GPT-5.1 | non-reasoning | Non-reasoning | gpt-5-1-non-reasoning | 2025-11-13 |  |  |  | 1.25 / 10.00 | 67 |
| OpenAI | GPT-5.1 Codex | high | High | gpt-5-1-codex | 2025-11-13 |  |  |  | 1.25 / 10.00 | 106 |
| OpenAI | GPT-5.1 Codex mini | high | High | gpt-5-1-codex-mini | 2025-11-13 |  |  |  | 0.25 / 2.00 | 135 |
| OpenAI | GPT-5.2 | medium | Medium | gpt-5-2-medium | 2025-12-11 |  |  |  | 1.75 / 14.00 | 69 |
| OpenAI | GPT-5.2 | non-reasoning | Non-reasoning | gpt-5-2-non-reasoning | 2025-12-11 |  |  |  | 1.75 / 14.00 | 59 |
| OpenAI | GPT-5.2 | xhigh | Xhigh | gpt-5-2 | 2025-12-11 |  |  |  | 1.75 / 14.00 | 70 |
| OpenAI | GPT-5.2 Codex | xhigh | Xhigh | gpt-5-2-codex | 2025-12-11 |  |  |  | 1.75 / 14.00 | 74 |
| OpenAI | GPT-5.3 Codex | xhigh | Xhigh | gpt-5-3-codex | 2026-02-05 |  |  |  | 1.75 / 14.00 | 81 |
| OpenAI | GPT-5.4 | low | Low | gpt-5-4-low | 2026-03-05 |  |  |  | 2.50 / 15.00 | 57 |
| OpenAI | GPT-5.4 | non-reasoning | Non-reasoning | gpt-5-4-non-reasoning | 2026-03-05 |  |  |  | 2.50 / 15.00 | 47 |
| OpenAI | GPT-5.4 | xhigh | Xhigh | gpt-5-4 | 2026-03-05 |  |  |  | 2.50 / 15.00 | 65 |
| OpenAI | GPT-5.4 Pro | xhigh | Xhigh | gpt-5-4-pro | 2026-03-05 |  |  |  | 30.00 / 180.00 |  |
| OpenAI | GPT-5.4 mini | medium | Medium | gpt-5-4-mini-medium | 2026-03-17 |  |  |  | 0.75 / 4.50 | 147 |
| OpenAI | GPT-5.4 mini | non-reasoning | Non-reasoning | gpt-5-4-mini-non-reasoning | 2026-03-17 |  |  |  | 0.75 / 4.50 | 115 |
| OpenAI | GPT-5.4 mini | xhigh | Xhigh | gpt-5-4-mini | 2026-03-17 |  |  |  | 0.75 / 4.50 | 173 |
| OpenAI | GPT-5.4 nano | medium | Medium | gpt-5-4-nano-medium | 2026-03-17 |  |  |  | 0.20 / 1.25 | 133 |
| OpenAI | GPT-5.4 nano | non-reasoning | Non-reasoning | gpt-5-4-nano-non-reasoning | 2026-03-17 |  |  |  | 0.20 / 1.25 | 109 |
| OpenAI | GPT-5.4 nano | xhigh | Xhigh | gpt-5-4-nano | 2026-03-17 |  |  |  | 0.20 / 1.25 | 150 |
| OpenAI | GPT-5.5 | high | High | gpt-5-5-high | 2026-04-23 |  |  |  | 5.00 / 30.00 | 72 |
| OpenAI | GPT-5.5 | low | Low | gpt-5-5-low | 2026-04-23 |  |  |  | 5.00 / 30.00 | 65 |
| OpenAI | GPT-5.5 | medium | Medium | gpt-5-5-medium | 2026-04-23 |  |  |  | 5.00 / 30.00 | 72 |
| OpenAI | GPT-5.5 | non-reasoning | Non-reasoning | gpt-5-5-non-reasoning | 2026-04-23 |  |  |  | 5.00 / 30.00 | 70 |
| OpenAI | GPT-5.5 | xhigh | Xhigh | gpt-5-5 | 2026-04-23 |  |  |  | 5.00 / 30.00 | 83 |
| OpenAI | GPT-5.5 Instant | june 2026 | June 2026 | gpt-5-5-instant-06-26 | 2026-06-25 |  |  |  | 5.00 / 30.00 | 123 |
| OpenAI | GPT-5.5 Instant | may 2026 | May 2026 | gpt-5-5-instant-05-26 | 2026-05-05 |  |  |  | 5.00 / 30.00 |  |
| OpenAI | GPT-5.5 Pro | xhigh | Xhigh | gpt-5-5-pro | 2026-04-23 |  |  |  |  |  |
| OpenAI | GPT-5.6 Luna | high | High | gpt-5-6-luna-high | 2026-07-09 |  |  |  | 0.20 / 1.20 | 95 |
| OpenAI | GPT-5.6 Luna | low | Low | gpt-5-6-luna-low | 2026-07-09 |  |  |  | 0.20 / 1.20 | 93 |
| OpenAI | GPT-5.6 Luna | max | Max | gpt-5-6-luna | 2026-07-09 | 23.8 | 29.4 | 334.35 | 0.20 / 1.20 | 96 |
| OpenAI | GPT-5.6 Luna | medium | Medium | gpt-5-6-luna-medium | 2026-07-09 |  |  |  | 0.20 / 1.20 | 94 |
| OpenAI | GPT-5.6 Luna | non-reasoning | Non-reasoning | gpt-5-6-luna-non-reasoning | 2026-07-09 |  |  |  | 0.20 / 1.20 | 92 |
| OpenAI | GPT-5.6 Luna | xhigh | Xhigh | gpt-5-6-luna-xhigh | 2026-07-09 |  |  |  | 0.20 / 1.20 | 101 |
| OpenAI | GPT-5.6 Sol | high | High | gpt-5-6-sol-high | 2026-07-09 |  |  |  | 4.00 / 20.00 | 93 |
| OpenAI | GPT-5.6 Sol | low | Low | gpt-5-6-sol-low | 2026-07-09 |  |  |  | 4.00 / 20.00 | 86 |
| OpenAI | GPT-5.6 Sol | max | Max | gpt-5-6-sol | 2026-07-09 |  |  |  | 4.00 / 20.00 | 94 |
| OpenAI | GPT-5.6 Sol | medium | Medium | gpt-5-6-sol-medium | 2026-07-09 |  |  |  | 4.00 / 20.00 | 95 |
| OpenAI | GPT-5.6 Sol | non-reasoning | Non-reasoning | gpt-5-6-sol-non-reasoning | 2026-07-09 |  |  |  | 4.00 / 20.00 | 86 |
| OpenAI | GPT-5.6 Sol | xhigh | Xhigh | gpt-5-6-sol-xhigh | 2026-07-09 |  |  |  | 4.00 / 20.00 | 103 |
| OpenAI | GPT-5.6 Terra | high | High | gpt-5-6-terra-high | 2026-07-09 |  |  |  | 2.00 / 12.00 | 85 |
| OpenAI | GPT-5.6 Terra | low | Low | gpt-5-6-terra-low | 2026-07-09 |  |  |  | 2.00 / 12.00 | 75 |
| OpenAI | GPT-5.6 Terra | max | Max | gpt-5-6-terra | 2026-07-09 | 32.3 | 36.6 | 3250.14 | 2.00 / 12.00 | 83 |
| OpenAI | GPT-5.6 Terra | medium | Medium | gpt-5-6-terra-medium | 2026-07-09 |  |  |  | 2.00 / 12.00 | 81 |
| OpenAI | GPT-5.6 Terra | non-reasoning | Non-reasoning | gpt-5-6-terra-non-reasoning | 2026-07-09 |  |  |  | 2.00 / 12.00 | 76 |
| OpenAI | GPT-5.6 Terra | xhigh | Xhigh | gpt-5-6-terra-xhigh | 2026-07-09 |  |  |  | 2.00 / 12.00 | 82 |
| OpenAI | GPT-6 Astra | high | High | gpt-6-astra-high | 2026-09-03 | 54.8 | 60.0 | 3204.00 | 10.00 / 50.00 | 44 |
| OpenAI | GPT-6 Astra | low | Low | gpt-6-astra-low | 2026-09-03 | 43.3 | 49.8 | 1650.75 | 10.00 / 50.00 | 45 |
| OpenAI | GPT-6 Astra | max | Max | gpt-6-astra | 2026-09-03 | 56.9 | 61.8 | 5661.18 | 10.00 / 50.00 | 42 |
| OpenAI | GPT-6 Astra | medium | Medium | gpt-6-astra-medium | 2026-09-03 | 51.6 | 56.8 | 2638.29 | 10.00 / 50.00 | 46 |
| OpenAI | GPT-6 Astra | xhigh | Xhigh | gpt-6-astra-xhigh | 2026-09-03 | 55.3 | 60.4 | 3746.22 | 10.00 / 50.00 | 44 |
| OpenAI | GPT-6 Luna | high | High | gpt-6-luna-high | 2026-09-22 | 21.4 | 27.3 | 62.58 | 0.10 / 0.50 | 92 |
| OpenAI | GPT-6 Luna | low | Low | gpt-6-luna-low | 2026-09-22 | 9.7 | 18.7 | 9.09 | 0.10 / 0.50 | 87 |
| OpenAI | GPT-6 Luna | max | Max | gpt-6-luna | 2026-09-22 | 27.9 | 33.3 | 136.06 | 0.10 / 0.50 | 104 |
| OpenAI | GPT-6 Luna | medium | Medium | gpt-6-luna-medium | 2026-09-22 | 18.5 | 24.9 | 39.55 | 0.10 / 0.50 | 93 |
| OpenAI | GPT-6 Luna | non-reasoning | Non-reasoning | gpt-6-luna-non-reasoning | 2026-09-22 | 9.4 | 16.6 | 53.14 | 0.10 / 0.50 | 84 |
| OpenAI | GPT-6 Luna | xhigh | Xhigh | gpt-6-luna-xhigh | 2026-09-22 | 23.5 | 29.0 | 85.74 | 0.10 / 0.50 | 100 |
| OpenAI | GPT-6 Sol | daybreak blue | Daybreak Blue, max | gpt-6-sol-daybreak-blue | 2026-09-22 |  |  |  | 2.00 / 10.00 |  |
| OpenAI | GPT-6 Sol | high | High | gpt-6-sol-high | 2026-09-22 |  |  |  | 2.00 / 10.00 | 103 |
| OpenAI | GPT-6 Sol | low | Low | gpt-6-sol-low | 2026-09-22 |  |  |  | 2.00 / 10.00 | 92 |
| OpenAI | GPT-6 Sol | max | Max | gpt-6-sol | 2026-09-22 | 44.2 | 48.9 | 1930.40 | 2.00 / 10.00 | 115 |
| OpenAI | GPT-6 Sol | medium | Medium | gpt-6-sol-medium | 2026-09-22 |  |  |  | 2.00 / 10.00 |  |
| OpenAI | GPT-6 Sol | non-reasoning | Non-reasoning | gpt-6-sol-non-reasoning | 2026-09-22 |  |  |  | 2.00 / 10.00 | 100 |
| OpenAI | GPT-6 Sol | xhigh | Xhigh | gpt-6-sol-xhigh | 2026-09-22 |  |  |  | 2.00 / 10.00 | 105 |
| OpenAI | GPT-6.1 Sol | high | High | gpt-6-1-sol-high | 2026-09-29 | 50.3 | 55.4 | 573.17 | 2.00 / 10.00 | 51 |
| OpenAI | GPT-6.1 Sol | low | Low | gpt-6-1-sol-low | 2026-09-29 | 34.8 | 42.6 | 237.91 | 2.00 / 10.00 | 51 |
| OpenAI | GPT-6.1 Sol | max | Max | gpt-6-1-sol | 2026-09-29 | 54.6 | 59.4 | 1123.97 | 2.00 / 10.00 | 48 |
| OpenAI | GPT-6.1 Sol | medium | Medium | gpt-6-1-sol-medium | 2026-09-29 | 46.3 | 52.1 | 388.57 | 2.00 / 10.00 | 53 |
| OpenAI | GPT-6.1 Sol | xhigh | Xhigh | gpt-6-1-sol-xhigh | 2026-09-29 | 52.5 | 57.5 | 717.71 | 2.00 / 10.00 | 52 |
| OpenAI | GPT-6.1 Terra | high | High | gpt-6-1-terra-high | 2026-10-26 | 42.4 | 46.4 | 266.79 | 1.00 / 5.00 | 62 |
| OpenAI | GPT-6.1 Terra | low | Low | gpt-6-1-terra-low | 2026-10-26 | 29.4 | 35.2 | 111.16 | 1.00 / 5.00 | 57 |
| OpenAI | GPT-6.1 Terra | max | Max | gpt-6-1-terra | 2026-10-26 | 51.3 | 54.7 | 972.34 | 1.00 / 5.00 | 65 |
| OpenAI | GPT-6.1 Terra | medium | Medium | gpt-6-1-terra-medium | 2026-10-26 | 38.2 | 42.6 | 190.36 | 1.00 / 5.00 | 60 |
| OpenAI | GPT-6.1 Terra | non-reasoning | Non-reasoning | gpt-6-1-terra-non-reasoning | 2026-10-26 | 30.5 | 32.8 | 213.33 | 1.00 / 5.00 | 59 |
| OpenAI | GPT-6.1 Terra | xhigh | Xhigh | gpt-6-1-terra-xhigh | 2026-10-26 | 45.3 | 49.4 | 400.18 | 1.00 / 5.00 | 62 |
| OpenAI | GPT-6.2 Astra | high | High | gpt-6-2-astra-high | 2026-11-17 | 60.1 | 63.6 | 2006.78 | 8.00 / 40.00 | 48 |
| OpenAI | GPT-6.2 Astra | low | Low | gpt-6-2-astra-low | 2026-11-17 | 45.7 | 50.5 | 794.01 | 8.00 / 40.00 | 46 |
| OpenAI | GPT-6.2 Astra | max | Max | gpt-6-2-astra | 2026-11-17 | 62.1 | 66.6 | 4530.46 | 8.00 / 40.00 | 49 |
| OpenAI | GPT-6.2 Astra | medium | Medium | gpt-6-2-astra-medium | 2026-11-17 | 57.0 | 59.9 | 1456.80 | 8.00 / 40.00 | 47 |
| OpenAI | GPT-6.2 Astra | xhigh | Xhigh | gpt-6-2-astra-xhigh | 2026-11-17 | 61.6 | 65.1 | 2483.62 | 8.00 / 40.00 | 48 |
| OpenAI | GPT-6.2 Sol | high | High | gpt-6-2-sol-high | 2026-11-17 | 54.9 | 58.7 | 552.68 | 2.00 / 10.00 | 69 |
| OpenAI | GPT-6.2 Sol | low | Low | gpt-6-2-sol-low | 2026-11-17 | 40.6 | 44.4 | 224.22 | 2.00 / 10.00 | 63 |
| OpenAI | GPT-6.2 Sol | max | Max | gpt-6-2-sol | 2026-11-17 | 57.3 | 61.2 | 1108.28 | 2.00 / 10.00 | 74 |
| OpenAI | GPT-6.2 Sol | medium | Medium | gpt-6-2-sol-medium | 2026-11-17 | 52.7 | 56.2 | 405.17 | 2.00 / 10.00 | 67 |
| OpenAI | GPT-6.2 Sol | xhigh | Xhigh | gpt-6-2-sol-xhigh | 2026-11-17 | 55.7 | 59.9 | 698.10 | 2.00 / 10.00 | 73 |
| OpenAI | gpt-oss-120b | high | High | gpt-oss-120b | 2025-08-05 | 3.8 | 11.2 | 264.99 | 0.15 / 0.60 | 205 |
| OpenAI | gpt-oss-120b | low | Low | gpt-oss-120b-low | 2025-08-05 |  |  |  | 0.12 / 0.59 | 178 |
| OpenAI | gpt-oss-20b | high | High | gpt-oss-20b | 2025-08-05 |  |  |  | 0.05 / 0.22 | 113 |
| OpenAI | gpt-oss-20b | low | Low | gpt-oss-20b-low | 2025-08-05 |  |  |  | 0.07 / 0.30 | 122 |
| OpenAI | o1 |  |  | o1 | 2024-12-05 |  |  |  | 15.00 / 60.00 |  |
| OpenAI | o1-mini |  |  | o1-mini | 2024-09-12 |  |  |  |  |  |
| OpenAI | o1-preview |  |  | o1-preview | 2024-09-12 |  |  |  | 16.50 / 66.00 |  |
| OpenAI | o1-pro |  |  | o1-pro | 2025-03-19 |  |  |  | 150.00 / 600.00 |  |
| OpenAI | o3 |  |  | o3 | 2025-04-16 |  |  |  | 2.00 / 8.00 | 114 |
| OpenAI | o3-mini |  |  | o3-mini | 2025-01-31 |  |  |  | 1.10 / 4.40 | 186 |
| OpenAI | o3-mini | high | High | o3-mini-high | 2025-01-31 |  |  |  | 1.10 / 4.40 | 204 |
| OpenAI | o3-pro |  |  | o3-pro | 2025-06-10 |  |  |  | 20.00 / 80.00 |  |
| OpenAI | o4-mini | high | High | o4-mini | 2025-04-16 |  |  |  | 1.10 / 4.40 | 106 |

Data: [Artificial Analysis](https://artificialanalysis.ai)
