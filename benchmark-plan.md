# STT Benchmark Plan

> 繁體中文版：[benchmark-plan.zh.md](benchmark-plan.zh.md)

## Purpose

Don't make engine decisions based on vendor claims. Compare `whisper.cpp`, `mlx-whisper`, and `lightning-whisper-mlx` against real workloads before changing the production default.

## Candidates

| Engine | Role | Production default |
|---|---|---|
| whisper.cpp | Stable baseline | Yes |
| mlx-whisper | Apple Silicon native A/B | No |
| lightning-whisper-mlx | Speed experiment | No |

## Test Data

Prepare at least three categories:

```text
short-command:  5–20 s  — voice commands, short messages
normal-message: 30–90 s — everyday voice messages
long-audio:     5–20 min — meetings or extended recordings
```

At least 10 samples per category, covering:

```text
Mandarin Chinese
English
Code-switching (mixed)
Background noise
Mobile-compressed audio
```

## Metrics

| Metric | Description |
|---|---|
| RTF | Real-time factor — lower is better. |
| p50 latency | Typical perceived latency. |
| p95 latency | Tail latency under queue backpressure. |
| failure rate | Decode errors / timeouts / hallucinations. |
| manual quality score | Human-sampled 1–5 rating. |
| memory pressure | Impact on other local services. |

## Pass Criteria

A candidate engine must satisfy all of the following to become the production default:

```text
p95 short-command  < 10 s
p95 normal-message < 45 s
long-audio does not timeout
failure rate < 2%
does not cause noticeable latency for other local services
```

## Test Order

1. `whisper.cpp small`
2. `whisper.cpp medium`
3. `mlx-whisper small`
4. `mlx-whisper distil-whisper`
5. `lightning-whisper-mlx distil-medium.en`

If `small` produces insufficient quality for the target language, upgrade to `medium` directly. Do not mask model quality issues with queue-side complexity.

## Report Format

```text
engine:
model:
sample_count:
p50_latency_sec:
p95_latency_sec:
rtf_avg:
failure_rate:
manual_quality_avg:
notes:
recommendation:
```
