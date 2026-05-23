# robot-system

通用机器人数据采集平台。**加新设备 = 写一个 YAML，代码零改动。**

## 用法

```bash
pip install -e .
python -m robot_system.platform.collector --robot a2 --scene explore
```

## 架构

```
src/robot_system/
├── platform/        # 平台层：通用数据采集（DDS + RPC + GStreamer）
│   ├── collector.py # 入口
│   ├── config.py    # YAML 配置加载
│   ├── sources/     # 数据源插件
│   └── writers/     # 输出插件
└── robots/          # 机器人配置（纯 YAML）
    ├── a2/          # 宇树 A2
    └── go2/         # 宇树 Go2
```

## 支持的数据源

| 类型 | 实现 | 例子 |
|---|---|---|
| `dds` | ROS2 subscriber | LowState、LiDAR |
| `rpc` | Client 轮询 | JPEG拍照、麦克风 |
| `gstreamer` | OpenCV+Gst | h264图传 |

## 传感器状态（A2）

| 传感器 | 状态 |
|---|---|
| LowState (IMU+电机) | ✅ 已验证 |
| 运动 API | ✅ 已验证 |
| 摄像头 JPEG | ✅ Go2 兼容，待充电后测 |
| h264 图传 | ✅ 待充电后测 |
| 麦克风/喇叭 | ✅ A2 自有 DDS 接口 |
| LiDAR | ❌ 待宇树 OTA |

## 目录

- `docs/` — 设计文档、实现计划
- `verify/` — 实机验证脚本
- `tools/` — 离线工具
- `deploy/` — 部署脚本
