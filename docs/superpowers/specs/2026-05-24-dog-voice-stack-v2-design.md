# A2 狗语音栈 v2 — 本地优先三层路由设计

> 日期: 2026-05-24 | 状态: 设计已确认 | 后续: writing-plans

## 目标

将 A2 狗语音交互延迟从 8-35 秒压到：本地命令 <500ms，云端对话 <5s。

## 架构总览

```
麦克风 → wake_dog_oww.py(常驻) → 唤醒"俊秀俊秀"
                                        │
                                        ▼
                              dialog(): 录音(3-5s)
                                        │
                                        ▼
                              sherpa-onnx SenseVoice ASR (~150ms)
                                        │
                                        ▼
                              router(rules.yaml) 关键词匹配
                                        │
                         ┌──────────────┴──────────────┐
                         │                             │
                    本地命令                      云端对话
              ("坐下"/"过来"/"趴下")           (其他所有)
                         │                             │
                         ▼                             ▼
                动作执行 + 预录wav            🔒安全门: stand_down
                (<100ms, 零网络)              POST xiu1/speak
                                                    │
                                                    ▼
                                              Hermes → TTS → 播放
                                                    │
                                                    ▼
                                              恢复待命 stand
```

## 延迟对比

| 环节 | 当前(v1) | v2 |
|---|---|---|
| ASR | 腾讯云 ~800ms | SenseVoice ~150ms |
| 本地命令 | 不存在 | <500ms 端到端 |
| 云端对话 | 30-60s (DeepSeek v4) | 暂不变(Hermes瓶颈等GLM) |
| 网络依赖 | 全程需要 | 本地命令零依赖 |

## 模块

### 1. ASR 引擎

- 方案: k2-fsa/sherpa-onnx 1.13.2
- 模型: SenseVoice int8 (229MB, RTF ~0.15 on X99, 预估~0.1 on A2 i7)
- API: `OfflineRecognizer.from_sense_voice(model=..., tokens=..., language="zh", use_itn=True)`
- 部署: `pip install sherpa-onnx` + 下载模型到 `~/.sherpa-onnx/sense-voice/`

### 2. 路由器 + 安全门

- rules.yaml 驱动, 关键词匹配(零依赖)
- 本地命中 → 动作 + 预录 wav
- 本地未命中 → 🔒安全门 stand_down → POST xiu1/speak → 超时护

rules.yaml 结构:
```yaml
local:
  - keywords: ["坐下", "sit", "停"]
    action: damp
    reply_wav: "stop.wav"
  - keywords: ["过来", "come", "来"]
    action: come_forward
    reply_wav: "coming.wav"
  - keywords: ["趴下", "down"]
    action: stand_down
    reply_wav: "down.wav"
  - keywords: ["你好", "hello", "hi", "俊秀"]
    action: null
    reply_wav: "zaijia.wav"

safety_on_cloud: stand_down
cloud_timeout: 30
```

### 3. 预录音频

- TTS 批量生成 → `~/dog_audio/replies/*.wav`
- 生成脚本: `tts_generate.py` 调腾讯云 TTS 或 sherpa-onnx TTS
- 播放: A2 AudioClient PlayStream PCM

### 4. 进程模型

- **唯一进程**: `wake_dog_oww.py` 常驻守护
  - 主循环: UDP 组播监听 → 唤醒词 LR → dialog()
  - dialog(): 录音 → ASR → router → 动作/云端 → 回到监听

代码组织:
```
dog_voice_v2/
├── wake_dog_oww.py      # 唯一运行的进程（常驻守护）
├── asr_engine.py         # sherpa-onnx SenseVoice 封装
├── router.py             # rules.yaml 加载 + 关键词匹配
├── rules.yaml            # 本地命令/应答规则
├── cloud_client.py       # POST xiu1/speak + 安全门
├── audio_player.py       # 预录wav播 + TTS播放
├── tts_generate.py       # TTS批量生成脚本
└── audio/
    └── replies/          # 预录wav文件
```

## 实现阶段

| 阶段 | 内容 | 依赖 |
|---|---|---|
| P1 | sherpa-onnx SenseVoice 集成到 wake_dog_oww.py | 模型已下载到X99 |
| P2 | router.py + rules.yaml + 安全门 | P1 |
| P3 | 预录音频 TTS 批量生成 + 播放 | P2 |
| P4 | 环境音负样本重训唤醒词 | 狗开机在旁 |
| P5 | 实机联调 | 所有 |

## 踩坑记录

- sherpa-onnx 1.13 API: `OfflineRecognizer.from_sense_voice()` 工厂方法，需要 model + tokens 参数
- SenseVoice model.int8.onnx = 229MB，tokens.txt = 309KB
- 模型下载方案: 直接 wget from HF，走代理
