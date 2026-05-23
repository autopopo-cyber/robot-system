# 语音栈 v2 实现计划（极简）

**设计**: 2026-05-24-dog-voice-stack-v2-design.md

## P1: CVM本地ASR验证
- [ ] 安装 sherpa-onnx + SenseVoice 模型
- [ ] 测试延迟(RTF)
- commit: P1完成

## P2: 路由器 + 安全门
- [ ] router.py: rules.yaml关键词匹配
- [ ] rules.yaml: 第一版命令规则
- [ ] cloud_client.py: POST xiu1/speak + 安全门

## P3: P1+P2集成
- [ ] 修改 wake_dog_oww.py dialog() 接入 ASR+router
- [ ] 本地测试全链路

## P4: 预录音频
- [ ] tts_generate.py: 批量生成wav
