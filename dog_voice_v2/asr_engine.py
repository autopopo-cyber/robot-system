#!/usr/bin/env python3
"""asr_engine.py — sherpa-onnx SenseVoice 封装"""
import numpy as np
from sherpa_onnx import offline_recognizer as off


class AsrEngine:
    def __init__(self, model_path: str, tokens_path: str):
        self.rec = off.OfflineRecognizer.from_sense_voice(
            model=model_path,
            tokens=tokens_path,
            language="zh",
            use_itn=True
        )
        self.sr = 16000

    def transcribe(self, pcm_int16: np.ndarray) -> str:
        """int16 PCM → 识别文本"""
        samples = pcm_int16.astype(np.float32) / 32768.0
        stream = self.rec.create_stream()
        stream.accept_waveform(self.sr, samples)
        self.rec.decode_stream(stream)
        return stream.result.text.strip()
