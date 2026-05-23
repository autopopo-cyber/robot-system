#!/usr/bin/env python3
"""test_router.py — router 单元测试"""

import sys
sys.path.insert(0, "/home/qin/workspace/robot-system/dog_voice_v2")
from router import Router

r = Router("/home/qin/workspace/robot-system/dog_voice_v2/rules.yaml")

tests = [
    # (输入, 期望类型, 期望动作)
    ("坐下", "local", "damp"),
    ("停下来", "local", "damp"),
    ("过来", "local", "come_forward"),
    ("来这边", "local", "come_forward"),
    ("趴下", "local", "stand_down"),
    ("你好俊秀", "local", None),  # null action
    ("今天天气怎么样", "cloud", "stand_down"),
    ("随便说点啥", "cloud", "stand_down"),
    ("sit down", "local", "damp"),
    ("hello", "local", None),
]

passed = 0
for text, exp_type, exp_action in tests:
    result = r.match(text)
    if result is None:
        print(f"  ❌ {text!r} → got None, expected {exp_type}/{exp_action}")
        continue
    ok_type = result["type"] == exp_type
    ok_action = result.get("action") == exp_action
    if ok_type and ok_action:
        passed += 1
        print(f"  ✅ {text!r} → {result['type']}/{result.get('action')}")
    else:
        print(f"  ❌ {text!r} → got {result['type']}/{result.get('action')}, "
              f"expected {exp_type}/{exp_action}")

print(f"\n{passed}/{len(tests)} passed")
if passed == len(tests):
    print("全部通过✅")
else:
    print("有失败❌")
    sys.exit(1)
