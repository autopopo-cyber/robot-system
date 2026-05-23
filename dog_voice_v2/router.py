#!/usr/bin/env python3
"""router.py — 本地NLU路由器: rules.yaml 关键词匹配"""
from pathlib import Path
import yaml


class Router:
    def __init__(self, rules_path: str):
        with open(rules_path) as f:
            self.rules = yaml.safe_load(f)
        self.local_rules = self.rules.get("local", [])
        self.safety_action = self.rules.get("safety_on_cloud", "stand_down")
        self.cloud_timeout = self.rules.get("cloud_timeout", 30)

    def match(self, text: str) -> dict | None:
        """匹配本地规则, 命中返回 rule dict, 否则 None"""
        text_lower = text.lower().strip()
        for rule in self.local_rules:
            keywords = rule.get("keywords", [])
            if any(kw in text_lower for kw in keywords):
                return {
                    "type": "local",
                    "action": rule.get("action"),
                    "reply_wav": rule.get("reply_wav"),
                    "matched_keyword": next(kw for kw in keywords if kw in text_lower)
                }
        return {"type": "cloud", "action": self.safety_action}
