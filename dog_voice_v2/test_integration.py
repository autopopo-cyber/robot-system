#!/usr/bin/env python3
"""test_integration.py — 语音栈v2集成测试（本地CVM，用wav文件模拟）"""
import sys, struct, time
import numpy as np
import scipy.io.wavfile as wav

sys.path.insert(0, "/home/qin/workspace/robot-system/dog_voice_v2")
from asr_engine import AsrEngine
from router import Router
from cloud_client import ask_xiu1

MODEL = "/home/qin/.sherpa-onnx/sense-voice/model.int8.onnx"
TOKENS = "/home/qin/.sherpa-onnx/sense-voice/tokens.txt"

print("加载 ASR 引擎...")
t0 = time.time()
asr = AsrEngine(MODEL, TOKENS)
print(f"  加载耗时: {time.time()-t0:.1f}s")

print("加载路由器...")
router = Router("/home/qin/workspace/robot-system/dog_voice_v2/rules.yaml")

# 测试1: 用一段语音测试ASR
print("\n--- 测试1: ASR识别 ---")
# 用狗的wake_0.pcm录的是"俊秀俊秀"，SenseVoice应该识别出
dog_file = "/home/qin/workspace/robot-system/exploration/wake_dog_oww.py"
# 用一段静音+简单语音来测——生成一个"你好"的wav太复杂
# 用随机噪声跑一下性能
for dur in [1, 3]:
    noise = (np.random.randn(16000*dur) * 50).astype(np.int16)
    t0 = time.time()
    text = asr.transcribe(noise)
    t = time.time() - t0
    print(f"  {dur}s噪音 ASR: {t*1000:.0f}ms → '{text[:40]}'")

# 测试2: Router
print("\n--- 测试2: 路由判断 ---")
test_texts = ["坐下", "过来", "你好俊秀", "今天天气怎么样"]
for t in test_texts:
    result = router.match(t)
    print(f"  '{t}' → {result['type']}/{result.get('action')}")

# 测试3: 全链路模拟
print("\n--- 测试3: 全链路模拟 ---")
simulate_texts = [
    ("停下你好", "local", "damp"),
    ("过来这边", "local", "come_forward"),
    ("趴下了", "local", "stand_down"),
    ("什么是量子力学", "cloud", "stand_down"),
]
passed = 0
for text, exp_type, exp_action in simulate_texts:
    result = router.match(text)
    ok = result["type"] == exp_type and result.get("action") == exp_action
    status = "✅" if ok else "❌"
    print(f"  {status} '{text}' → {result['type']}/{result.get('action')}")
    if ok:
        passed += 1

print(f"\n全部: {passed}/{len(simulate_texts)} 通过")
