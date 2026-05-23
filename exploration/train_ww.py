#!/usr/bin/env python3
"""在狗上训练俊秀俊秀唤醒词模型"""
import sys, os, struct, pickle
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import scipy.io.wavfile as wav
import onnxruntime as ort

sys.path.insert(0, '/home/unitree')
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from openwakeword.utils import AudioFeatures

# ── 配置 ──────────────────────
OUTPUT = "/home/unitree/junxiu_ww_v2.pkl"
SAMPLE_RATE = 16000
WINDOW_S = 1.5
WINDOW_SAMPLES = int(SAMPLE_RATE * WINDOW_S)  # 24000

# ── 初始化 ────────────────────
ChannelFactoryInitialize(0, 'eth0')
af = AudioFeatures()
emb_path = os.path.expanduser(
    "~/.local/lib/python3.10/site-packages/openwakeword/resources/models/embedding_model.onnx"
)
emb_sess = ort.InferenceSession(emb_path)

def extract_embedding(pcm_int16: np.ndarray) -> np.ndarray:
    spec = af._get_melspectrogram(pcm_int16)
    windows = []
    for i in range(0, spec.shape[0], 8):
        w = spec[i:i+76]
        if w.shape[0] == 76:
            windows.append(w)
    if not windows:
        return np.zeros((0, 96))
    batch = np.expand_dims(np.array(windows), -1).astype(np.float32)
    return emb_sess.run(None, {'input_1': batch})[0].squeeze()

def pcm_to_int16(pcm_bytes: bytes, max_samples=None) -> np.ndarray:
    n = len(pcm_bytes) // 2
    if max_samples:
        n = min(n, max_samples)
    return np.array(struct.unpack(f'<{n}h', pcm_bytes[:n*2]), dtype=np.int16)

# ── 1. 正样本 ──
print("[train] 提取正样本 embedding...")
pos_embs = []
for i in range(3):
    with open(f"/home/unitree/wake_{i}.pcm", 'rb') as f:
        raw = f.read()
    samples = pcm_to_int16(raw, WINDOW_SAMPLES)
    emb = extract_embedding(samples)
    pos_embs.append(emb)
    print(f"  wake_{i}.pcm → {emb.shape}")
X_pos = np.vstack(pos_embs)
print(f"  正样本: {X_pos.shape}")

# ── 2. 负样本 ──
print("[train] 生成负样本 embedding...")
neg_embs = []

for _ in range(3):
    silence = np.zeros(WINDOW_SAMPLES, dtype=np.int16)
    e = extract_embedding(silence)
    if e.shape[0] > 0:
        neg_embs.append(e)

for _ in range(3):
    noise = (np.random.randn(WINDOW_SAMPLES) * 100).astype(np.int16)
    e = extract_embedding(noise)
    if e.shape[0] > 0:
        neg_embs.append(e)

for i in range(3):
    with open(f"/home/unitree/wake_{i}.pcm", 'rb') as f:
        raw = f.read()
    offset = 2 * 16000 * 2
    if len(raw) > offset + WINDOW_SAMPLES * 2:
        slice_bytes = raw[offset:offset + WINDOW_SAMPLES * 2]
        samples = pcm_to_int16(slice_bytes, WINDOW_SAMPLES)
        e = extract_embedding(samples)
        if e.shape[0] > 0:
            neg_embs.append(e)

X_neg = np.vstack(neg_embs)
print(f"  负样本: {X_neg.shape}")

# ── 3. 训练 ──
X = np.vstack([X_pos, X_neg])
y = np.array([1]*len(X_pos) + [0]*len(X_neg))
print(f"\n[train] X={X.shape}, pos={len(X_pos)}, neg={len(X_neg)}")

pipeline = Pipeline([
    ('scaler', StandardScaler()),
    ('clf', LogisticRegression(max_iter=2000, class_weight='balanced'))
])
pipeline.fit(X, y)

# ── 4. 评估 ──
from sklearn.model_selection import cross_val_score
scores = cross_val_score(pipeline, X, y, cv=min(5, len(X_pos)))
print(f"[eval] CV: {scores.mean():.3f} ± {scores.std():.3f}")

train_pred = pipeline.predict(X)
print(f"[eval] acc={(train_pred==y).mean():.3f} "
      f"TP={(train_pred[y==1]==1).sum()}/{len(X_pos)} "
      f"TN={(train_pred[y==0]==0).sum()}/{len(X_neg)}")

# ── 5. 保存 ──
model = {
    'pipeline': pipeline,
    'window_samples': WINDOW_SAMPLES,
    'sample_rate': SAMPLE_RATE,
    'threshold': 0.5,
}
with open(OUTPUT, 'wb') as f:
    pickle.dump(model, f)
print(f"\n[done] → {OUTPUT}")
