# Mac Mini Deployment Notes

## Runtime 原則

遵守目前環境管理規則：

- 系統工具用 Homebrew。
- Python package 用 `uv`，不污染 system Python。
- 不用 `nvm` / `pyenv` / `asdf` / curl installer。
- 不改 `~/.zshrc` 或 `~/.profile`。

## whisper.cpp baseline

```bash
brew install whisper-cpp ffmpeg
```

模型檔不放 repo。建議放：

```text
/Users/dbuadmin/stt-models/whisper.cpp/
```

Production 預設模型：

```text
ggml-large-v3-turbo-q5_0.bin
```

Fallback 模型：

```text
ggml-small.bin
```

## Service 位置

建議在 Mac Mini 建獨立 service root：

```text
/Users/dbuadmin/stt-service/
```

不要塞進 `~/.openclaw`。OpenClaw 只呼叫 STT API，不直接管理 STT queue internals。

## Port

建議只綁 loopback：

```text
127.0.0.1:8787
```

如果要讓 Nginx 暴露，只暴露內部 route，並加 token。

```text
/stt/ -> 127.0.0.1:8787
```

## launchd

建議拆兩個 LaunchAgent：

```text
ai.stt.api.plist
ai.stt.worker.plist
```

API 與 worker 拆開的原因：API 要穩定接 job，worker 可以單獨 restart / 換 engine / 跑 benchmark。

## Worker profiles

Production:

```text
STT_ENGINE=whisper.cpp
STT_MODEL=large-v3-turbo-q5_0
STT_MODEL_PATH=/Users/dbuadmin/stt-models/whisper.cpp/ggml-large-v3-turbo-q5_0.bin
STT_CONCURRENCY=1
```

A/B:

```text
STT_ENGINE=mlx-whisper
STT_MODEL=mlx-community/whisper-small
STT_CONCURRENCY=1
```

Speed experiment:

```text
STT_ENGINE=lightning-whisper-mlx
STT_MODEL=distil-medium.en
STT_CONCURRENCY=1
```

## OpenClaw / n8n 整合

OpenClaw 或 n8n 不直接等 STT 長任務完成。建議模式：

```text
submit audio -> receive job id -> poll/callback -> continue text workflow
```

短語音可同步等最多 30 秒；超過就回「已收到，轉錄中」類狀態，避免 webhook timeout。

## 安全性

- STT API 預設 loopback only。
- 若經 Nginx 暴露，需要 bearer token。
- 原始音檔設 TTL cleanup。
- log 不記完整 transcript，避免敏感資料外洩。
- failed job 保留音檔以利 debug，但最多 7 天。
