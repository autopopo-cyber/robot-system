#!/usr/bin/env python3
"""tts_generate.py — 批量生成预录音频 (腾讯云TTS → wav)"""

import os, sys, json, time, yaml
from pathlib import Path

# 腾讯云 TTS
from tencentcloud.common import credential
from tencentcloud.tts.v20190823 import tts_client, models

SECRET_ID = os.environ.get("TENCENT_SECRET_ID", "")
SECRET_KEY = os.environ.get("TENCENT_SECRET_KEY", "")
REGION = "ap-beijing"
VOICE_TYPE = 601009  # 爱小芊

# 回复文本映射
REPLIES = {
    "stop.wav": "收到，已停住。",
    "coming.wav": "来啦主人。",
    "down.wav": "好的，趴下。",
    "zaijia.wav": "在呢，主人请说。",
    "unknown.wav": "稍等，我想想……",
}

OUT_DIR = Path("/home/qin/workspace/robot-system/dog_voice_v2/audio/replies")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def generate(text: str, out_path: str):
    cred = credential.Credential(SECRET_ID, SECRET_KEY)
    client = tts_client.TtsClient(cred, REGION)
    req = models.TextToVoiceRequest()
    req.Text = text
    req.VoiceType = VOICE_TYPE
    req.Codec = "wav"
    req.SampleRate = 16000
    req.Volume = 0
    req.Speed = 0
    req.SessionId = str(int(time.time() * 1000))

    resp = client.TextToVoice(req)
    audio = resp.Audio  # base64

    import base64
    with open(out_path, "wb") as f:
        f.write(base64.b64decode(audio))
    size = os.path.getsize(out_path)
    print(f"  ✅ {out_path} ({size/1024:.1f}KB)")


if __name__ == "__main__":
    print("生成预录音频...")
    for filename, text in REPLIES.items():
        path = OUT_DIR / filename
        generate(text, str(path))
        time.sleep(0.3)  # API频率限制

    print(f"\n全部生成到 {OUT_DIR}")
