# Robot System SDK — Unitree A2

> 整理: 俊秀 (xiu3) | 2026-05-22
> 基于 A2技术手册v2 + 实机摸底

## 快速开始

```bash
# SSH 到狗
ssh unitree@100.65.245.29  # Tailscale

# 确认 ROS2 环境
source /opt/ros/humble/setup.bash
ros2 topic list | grep sport   # 验证 DDS 链路
```

## 网络拓扑

```
PC1 (运控)           PC2 (用户i7)          LiDAR
192.168.123.161      192.168.124.162       192.168.124.20
      │                    │                    │
  交换机1(123.0/24)    交换机2(124.0/24)─────────┘
                                           WiFi (wlx...)
                                           Tailscale: 100.65.245.29
```

- **123网段 = SDK开发** | **124网段 = 雷达点云** | WiFi = 远程管理
- Tailscale走WiFi口绕开双网段隔离

## DDS 通信架构

```
用户代码(i7)                   运控CPU(8核)
┌──────────────┐              ┌──────────────┐
│ rclpy / SDK2 │──CycloneDDS──│ SportSrv     │
│ 订阅状态      │  (共享内存)   │ 执行运动      │
│ 发送指令      │              │ 发布状态      │
└──────────────┘              └──────────────┘
```

核心: 用户代码与运控CPU通过 CycloneDDS 共享内存通信，非 TCP/UDP。

## API 端点 (23个)

| 端点 | 方向 | 用途 |
|------|------|------|
| `/api/sport/request` | 用户→狗 | 运动指令 (Move/Stand/Damp…) |
| `/api/sport/response` | 狗→用户 | 运动指令响应 |
| `/api/loco/request` | 用户→狗 | 步态控制 |
| `/api/config/request` | 用户→狗 | 参数配置 |
| `/api/bashrunner/request` | 用户→狗 | 执行脚本 |
| `/api/audiohub/request` | 用户→狗 | 语音播放 |
| `/api/gpt/request` | 用户→狗 | AI对话 |
| … | | 共23个 /api/* 端点 |

## 状态话题 (ROS2)

| Topic | 类型 | 频率 | 内容 |
|-------|------|------|------|
| `/lf/sportmodestate` | SportModeState | 低频(~10Hz) | FSM+位置+速度+IMU |
| `/sportmodestate` | SportModeState | 高频(~100Hz) | 同上, 更快 |
| `/lf/lowstate` | LowState | ~100Hz | 关节力矩/角度/速度 |
| `/lf/bmsstate` | BmsState | ~1Hz | 电池电压/电流/温度 |

### SportModeState 结构 (CycloneDDS, 156字节)

| 字段 | 类型 | 说明 |
|------|------|------|
| stamp | TimeSpec | 时间戳 |
| error_code | uint32 | 错误码 |
| imu_state | IMUState | 姿态(四元数+rpy+角速度) |
| mode | uint8 | FSM状态 (0=待机, 1=阻尼, 2=站立…) |
| progress | float | 动作进度 0.0~1.0 |
| gait_type | uint8 | 步态类型 |
| foot_raise_height | float | 抬脚高度 |
| position | float[3] | x,y,z (m) |
| body_height | float | 机身高度 |
| velocity | float[3] | vx,vy,vyaw |
| yaw_speed | float | 偏航角速度 |
| range_obstacle | float[4] | 四向障碍距离 |
| foot_force | int16[4] | 四足足底力 |
| foot_position_body | float[12] | 足端位置(机身系) |
| foot_speed_body | float[12] | 足端速度(机身系) |
| path_point | PathPoint[10] | 路径点 |

## Move 速度档位

| 档位 | 走路(m/s) | 跑步(m/s) | 攀爬(m/s) |
|------|----------|----------|----------|
| 低速 | ±0.8 | ±2.5 | ±0.6 |
| 高速 | ±1.5 | ±4.0 | ±0.6 |

## FSM 状态机 (16状态)

| 状态 | 含义 |
|------|------|
| 0 | 待机 (PASSIVE) |
| 1 | 阻尼 (DAMP) |
| 2 | 站立 (STAND) |
| 3 | 行走 (WALK) |
| 4 | 小跑 (TROT) |
| 5~15 | 其他 (跳跃/爬楼梯/恢复/趴下…) |

## 三类SDK对比

| SDK | 语言 | 通信 | 状态 |
|-----|------|------|------|
| unitree_sdk2 (C++) | C++ | CycloneDDS原生 | 官方维护 ⭐1k |
| unitree_sdk2_python | Python | CycloneDDS绑定 | 需编译DDS |
| unitree_ros2 | C++/Python | ROS2→DDS桥接 | 官方 ⭐693 |
| **robot-system (本仓库)** | **Python** | **rclpy直通DDS** | **只读验证通过** |

## 开发铁律

1. ❌ **严禁调用运动API** — 只读订阅状态，不发送 `/api/sport/request`
2. ❌ **PC1不可SSH** — 运控CPU，只通过DDS通信
3. ✅ **rclpy可用** — Python直读ROS2 topic，无需编译unitree_sdk2
4. ✅ **WiFi+Tailscale = 远程开发** — 不影响123/124网段DDS通信

## 已验证 (2026-05-22)

- [x] SSH到狗 (100.65.245.29 via Tailscale)
- [x] 111个 ROS2 topic 可发现
- [x] 23个 /api/* 端点可发现
- [x] /lf/sportmodestate 有发布者 (CycloneDDS, RELIABLE)
- [x] /sportmodestate 有发布者
- [x] 消息格式从 C++ header 解码 (SportModeState_.hpp)
- [x] 5G WiFi 连上 (780Mb/s, 5.745GHz)
- [ ] rclpy 订阅成功并解析数据 (msg包未安装)
- [ ] unitree_sdk2_python 编译安装
