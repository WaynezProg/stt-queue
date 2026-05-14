# STT Benchmark Plan

## 目的

不要憑工具宣稱決策。用 Mac Mini 真實 workload 比較 `whisper.cpp`、`mlx-whisper`、`lightning-whisper-mlx`。

## 候選

| Engine | 定位 | 是否 production 預設 |
|---|---|---|
| whisper.cpp | 穩定 baseline | 是 |
| mlx-whisper | Apple Silicon 原生 A/B | 否 |
| lightning-whisper-mlx | 速度實驗 | 否 |

## 測試資料

至少準備三類：

```text
short-command: 5-20 秒，LINE/語音指令
normal-message: 30-90 秒，日常留言
long-audio: 5-20 分鐘，會議或長語音
```

每類至少 10 筆，包含：

```text
中文
英文
中英混雜
背景噪音
手機壓縮音訊
```

## 指標

| 指標 | 說明 |
|---|---|
| RTF | real-time factor，越低越好。 |
| p50 latency | 一般體感。 |
| p95 latency | queue 積壓時的尾端延遲。 |
| failure rate | decode / timeout / hallucination。 |
| manual quality score | 人工抽樣 1-5 分。 |
| memory pressure | 是否影響 OpenClaw / n8n。 |

## 通過門檻

正式預設 engine 必須同時滿足：

```text
p95 short-command < 10 秒
p95 normal-message < 45 秒
long-audio 不 timeout
failure rate < 2%
不造成 OpenClaw gateway 明顯延遲
```

## 測試順序

1. `whisper.cpp small`
2. `whisper.cpp medium`
3. `mlx-whisper small`
4. `mlx-whisper distil-whisper`
5. `lightning-whisper-mlx distil-medium.en`

如果 `small` 中文品質不足，直接升 `medium`，不要用更複雜 queue 設計掩蓋模型品質問題。

## 報告格式

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
