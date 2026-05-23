#!/usr/bin/env python3
"""cloud_client.py — 联网对话: POST xiu1/speak + 安全门"""

import json, urllib.request, time

XIU1_SPEAK = "http://49.232.136.220:8100/speak?token=junxiu2026"


def ask_xiu1(pcm: bytes, timeout: int = 90) -> dict | None:
    """发送 PCM 到 xiu1, 返回 {"text":..., "reply":..., "audio_url":...}"""
    try:
        req = urllib.request.Request(
            XIU1_SPEAK, data=pcm,
            headers={"Content-Type": "application/octet-stream"},
            method="POST"
        )
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read())
    except Exception as e:
        print(f"[cloud] err: {e}")
        return None
