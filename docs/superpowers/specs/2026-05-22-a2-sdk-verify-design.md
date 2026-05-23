# A2 SDK 验证脚本 — 设计文档

> 2026-05-22 | brainstorming 产出

## 目标

敏捷迭代验证 A2 狗各条数据链路，全部通过后重新设计平台接口层。

## 技术路线

**方案A — ROS2 (light)**：只编译 unitree_ros2 消息定义（unitree_go_msgs + unitree_api_msgs），用 rclpy 直读。狗上已有 ROS2 Humble，topic 已通，只缺 msg 包。

## 架构

```
本机 xiu3 ──mihomo clone──→ unitree_ros2 (仅msg)
                                  │
                            scp msg 到狗
                                  │
狗 PC2 ──colcon build──→ unitree_go_msgs + unitree_api_msgs
                                  │
                  ┌──────────┬──────────┬──────────┬──────────┐
             verify_sport  verify_lidar verify_cam verify_move
                  │            │          │          │
            sportmodestate  JT128点云  摄像头图像  move响应
                                  │
                        verify_report.json
                                  │
                     全部绿 → 平台接口设计
```

## 验证步骤

| 步骤 | 脚本 | 内容 | 成功标准 |
|------|------|------|---------|
| 0 | setup_msgs.sh | clone + 编译 msg | rclpy 能 import |
| 1 | verify_sport.py | 订阅 sportmodestate | 打印 position/velocity/mode × 10s |
| 2 | verify_lidar.py | 订阅 JT128 点云 | 打印一帧点云数量和范围 |
| 3 | verify_cam.py | 订阅摄像头图像 | 打印分辨率和帧率 |
| 4 | verify_move.py | 发 move 读响应 | 返回 API 响应码（低速，人在场） |

每步独立脚本，单文件几十行，失败不阻塞后续。

## 环境

- 狗 PC2：ROS2 Humble，unitree@192.168.124.162（Tailscale 100.65.245.29）
- 本机 xiu3：通过 mihomo 走代理 clone GitHub
