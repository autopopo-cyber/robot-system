#!/usr/bin/env python3
"""
wake_dog_oww.py — openwakeword 本地唤醒 + 对话
===============================================
UDP组播麦克风 → 滑动窗口 → melspectrogram → ONNX 96维 embedding
→ sklearn LR predict → 唤醒 → dialog()
"""
import sys, os, time, struct, socket, json, pickle, urllib.request
import numpy as np
import onnxruntime as ort

sys.path.insert(0, '/home/unitree')
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from a2_audio_client import A2AudioClient
from openwakeword.utils import AudioFeatures

# ── 配置 ──────────────────────
XIU1_SPEAK = "http://49.232.136.220:8100/speak?token=junxiu2026"
MIC_GROUP = "239.168.123.161"
MIC_PORT = 5555
SAMPLE_RATE = 16000
CHUNK_MS = 80
CHUNK_BYTES = CHUNK_MS * 32           # 2560 bytes
CHUNK_SAMPLES = CHUNK_MS * 16         # 1280 samples
WINDOW_S = 1.5
WINDOW_SAMPLES = int(SAMPLE_RATE * WINDOW_S)  # 24000
CHECK_INTERVAL = 5                     # 每 5 个 chunk (400ms) 检查一次
CONSECUTIVE_HITS = 2                   # 连续命中次数才唤醒
COOLDOWN_S = 3.0                       # 唤醒后冷却
THRESHOLD = 0.7                        # LR 概率阈值
DIALOG_RECORD_S = 5.0

# ── 初始化 ────────────────────
print("[oww] DDS Init...")
ChannelFactoryInitialize(0, 'eth0')
print("[oww] Audio Init...")
audio = A2AudioClient()
audio.SetTimeout(10.0)
audio.Init()
audio.SetVolume(100)

print("[oww] 加载模型...")
with open("/home/unitree/junxiu_ww_v2.pkl", 'rb') as f:
    model = pickle.load(f)
pipeline = model['pipeline']

print("[oww] 初始化 AudioFeatures + ONNX embedding...")
af = AudioFeatures()
emb_path = os.path.expanduser(
    "~/.local/lib/python3.10/site-packages/openwakeword/resources/models/embedding_model.onnx"
)
emb_sess = ort.InferenceSession(emb_path)

def extract_embedding(pcm: np.ndarray) -> np.ndarray:
    spec = af._get_melspectrogram(pcm)
    windows = []
    for i in range(0, spec.shape[0], 8):
        w = spec[i:i+76]
        if w.shape[0] == 76:
            windows.append(w)
    if not windows:
        return np.zeros((0, 96))
    batch = np.expand_dims(np.array(windows), -1).astype(np.float32)
    return emb_sess.run(None, {'input_1': batch})[0].squeeze()

def predict(pcm: np.ndarray) -> float:
    """返回正样本概率（取所有帧的最大值）"""
    emb = extract_embedding(pcm)
    if emb.ndim == 1:  # 单帧
        emb = emb.reshape(1, -1)
    if emb.shape[0] == 0:
        return 0.0
    proba = pipeline.predict_proba(emb)[:, 1]
    return float(proba.max())

def dialog():
    print("[dialog] 唤醒！")
    audio.TtsMaker("在呢，主人请说。", 0)
    time.sleep(1.5)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', MIC_PORT))
    mreq = struct.pack("4s4s", socket.inet_aton(MIC_GROUP),
                       socket.inet_aton("192.168.123.162"))
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    sock.settimeout(0.3)
    target = int(DIALOG_RECORD_S * 32000)
    buf = b''
    while len(buf) < target:
        try:
            d, _ = sock.recvfrom(4096)
            buf += d
        except socket.timeout:
            pass
    sock.close()
    pcm = buf[:target]
    print(f"[dialog] 录音 {len(pcm)/1024:.1f}KB")

    try:
        req = urllib.request.Request(
            XIU1_SPEAK, data=pcm,
            headers={'Content-Type': 'application/octet-stream'}, method='POST'
        )
        resp = urllib.request.urlopen(req, timeout=90)
        result = json.loads(resp.read())
        if result.get('ok') and result.get('reply'):
            print(f"[dialog] ASR: '{result.get('text','')}'")
            print(f"[junxiu] {result['reply'][:80]}...")
            audio.TtsMaker(result['reply'], 0)
    except Exception as e:
        print(f"[dialog] err: {e}")

# ── 主循环 ────────────────────
print("[oww] 开始监听... 说'俊秀俊秀'唤醒我")
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('', MIC_PORT))
mreq = struct.pack("4s4s", socket.inet_aton(MIC_GROUP),
                   socket.inet_aton("192.168.123.162"))
sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
sock.settimeout(0.1)

ring_buf = bytearray()
tick = 0
hit_count = 0
last_wake = 0

try:
    while True:
        try:
            data, _ = sock.recvfrom(CHUNK_BYTES)
        except socket.timeout:
            continue

        ring_buf += data
        # 保持大小为 WINDOW_SAMPLES * 2 bytes
        max_bytes = WINDOW_SAMPLES * 2
        if len(ring_buf) > max_bytes:
            ring_buf = ring_buf[-max_bytes:]

        tick += 1
        if tick % CHECK_INTERVAL != 0:
            continue

        # 取最近 WINDOW_SAMPLES 个 int16
        raw = ring_buf[-max_bytes:] if len(ring_buf) >= max_bytes else ring_buf
        if len(raw) < max_bytes:
            continue
        samples = np.array(struct.unpack(f'<{len(raw)//2}h', raw[:max_bytes]),
                          dtype=np.int16)

        prob = predict(samples)
        now = time.time()

        if prob > THRESHOLD:
            hit_count += 1
            print(f"[oww] 🔥 prob={prob:.3f} hits={hit_count}/{CONSECUTIVE_HITS}")
            if hit_count >= CONSECUTIVE_HITS and now - last_wake > COOLDOWN_S:
                dialog()
                last_wake = now
                hit_count = 0
        else:
            if hit_count > 0:
                print(f"[oww] ❄️  prob={prob:.3f} (reset)")
            hit_count = 0

except KeyboardInterrupt:
    print("\n[oww] 停止")
