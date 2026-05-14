# STT Queue Architecture

## 目標

降低音檔搬運成本。音檔只在本機傳一次，後續在本機完成 decode、normalize、STT、transcript storage，再把文字交給下游工作流程。

## 拓撲

```text
Client
  -> 本機 ingress
      -> audio file on disk
      -> SQLite stt_jobs
      -> STT worker
          -> whisper.cpp
          -> transcript JSON / TXT
      -> 下游文字工作流程
```

## 元件

| 元件 | 建議 | 說明 |
|---|---|---|
| Ingress API | FastAPI / small Node service | 接收音檔、建立 job、回 job id。 |
| Queue DB | SQLite WAL | Mac Mini 單機 queue 足夠，不先引入 Redis。 |
| Audio store | local filesystem | 音檔不進 DB，只存 path 與 checksum。 |
| Worker | single process | 初始 concurrency `1`，後續再壓測 `2`。 |
| STT engine | whisper.cpp | production baseline。 |
| Optional engine | mlx-whisper / lightning-whisper-mlx | 只透過同一 worker interface A/B。 |

## 資料流

1. Ingress 收到音檔，寫入 `data/incoming/{job_id}/original.*`。
2. 用 `ffmpeg` normalize 成 `16kHz mono wav`，寫入 `data/processing/{job_id}/input.wav`。
3. 建立 `stt_jobs` row，狀態為 `queued`。
4. Worker 用 atomic claim 把 job 改為 `processing`。
5. Worker 呼叫 STT engine 產生 transcript。
6. 結果寫入 `data/transcripts/{job_id}.json` 與 `.txt`。
7. Job 改為 `done`；若設定 callback_url，通知下游。
8. 原始音檔依 TTL 清除，transcript 保留較久。

## 為什麼在本機跑 STT

跨機搬運音檔有 LAN 成本，也會佔用遠端機器（如 GPU 伺服器）不必要的前處理資源。音檔大、文字小；STT 在 ingress 機本地完成是比較乾淨的邊界。

## 模型策略

production 初始：

```text
engine: whisper.cpp
model: large-v3-turbo-q5_0
language: auto 或 zh/en 指定
timestamps: segment-level
```

Fallback:

```text
model: small
```

速度 A/B：

```text
engine: mlx-whisper
model: mlx-community/whisper-small 或 distil-whisper
```

不納入：

```text
Qwen-ASR
SenseVoice
FunASR
其他中國 / 大陸模型
```
