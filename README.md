# Robot System

通用机器人控制平台。向下对接多品牌机器人，向上统一机械臂/相机/雷达接口。

> 🚧 开发中 — A2只读验证阶段

## 架构

```
platform/interfaces.py    ← 抽象接口 (RobotAdapter, PayloadAdapter)
adapters/unitree_a2.py    ← 宇树A2 适配器 (ROS2 rclpy直连DDS)
payload/                  ← 上装设备适配器 (机械臂/相机/雷达)
apps/                     ← 上层应用
```

## 快速开始

```bash
# 1. SSH 到狗
ssh unitree@100.65.245.29

# 2. 运行适配器测试
source /opt/ros/humble/setup.bash
python3 adapters/unitree_a2.py
```

## 开发铁律

- ❌ 严禁调用运动API (sport/loco/move)
- ✅ 只读订阅状态 (sportmodestate/lowstate/bmsstate)
- ✅ rclpy直通DDS，不编译unitree_sdk2

## 文档

- [A2 SDK 手册](docs/ROBOT_SDK.md)
- [宇树官方文档](https://support.unitree.com/home/zh/developer)
