# 数据采集平台 — 设计规格 v1.0

> 作者: 俊秀 + 主人 | 日期: 2026-05-23 | 参考: fan-ziqi/rl_sar

## 1. 目标

搭建通用数据采集平台层。任何设备只需部署一个 ROS2 节点 + 写一个 `config.yaml`，就能拿到标准化的传感器数据。

**核心原则：**
- 加新设备 = 加一个 `robots/<name>/` 目录 + config.yaml，平台代码零改动
- 参考 rl_sar 架构：`robots/<name>/<scene>/config.yaml` 驱动
- 数据源分三类：DDS订阅 / RPC轮询 / GStreamer拉流
- 输出统一：CSV + rosbag + 图像文件

## 2. 架构

```
robot-system/
├── rl_sar/                          ← git submodule (不动)
│
├── src/platform/                    ← 平台层（Python）
│   ├── collector.py                 # 通用采集器入口
│   ├── sources/
│   │   ├── dds_source.py            # DDS订阅类型
│   │   ├── rpc_source.py            # RPC轮询类型
│   │   └── gstreamer_source.py      # GStreamer拉流类型
│   ├── writers/
│   │   ├── csv_writer.py
│   │   ├── rosbag_writer.py
│   │   └── jpeg_writer.py
│   └── launcher.py                  # 一键启动
│
├── robots/                          ← 机器人配置
│   ├── a2/
│   │   ├── base.yaml                # 基础参数
│   │   ├── explore/config.yaml      # 探索场景
│   │   ├── calibrate/config.yaml    # 标定场景
│   │   └── multimedia_test/config.yaml
│   └── go2/                         ← 未来
│       └── base.yaml
│
├── tools/
│   ├── replay.py
│   └── convert.py
│
└── verify/                          ← 已有验证脚本
```

**用法：**
```bash
ros2 run platform collector --robot a2 --scene explore
ros2 run platform collector --robot a2 --scene multimedia_test
```

## 3. config.yaml 规格

### 3.1 base.yaml（机器人基础参数）

```yaml
# robots/a2/base.yaml
robot:
  name: a2
  network_interface: eth0
  unitree_class: a2

joints:
  names: [FR_hip, FR_thigh, FR_calf, FL_hip, FL_thigh, FL_calf,
          RR_hip, RR_thigh, RR_calf, RL_hip, RL_thigh, RL_calf]
  default_pos: [0.0, 0.9, -1.8, 0.0, 0.9, -1.8,
                0.0, 0.9, -1.8, 0.0, 0.9, -1.8]
```

### 3.2 场景 config.yaml

```yaml
# robots/a2/explore/config.yaml
scene: explore
description: 探索场景 — 全量传感器采集
output_dir: /home/unitree/exploration_data

sources:
  # ── 类型1: DDS订阅 ──
  - name: lowstate
    type: dds
    topic: /lf/lowstate
    msg_type: unitree_hg/msg/LowState
    rate_hz: 50
    fields:
      - imu_state.rpy       # → roll, pitch, yaw
      - imu_state.gyroscope # → gyro_x, gyro_y, gyro_z
      - imu_state.accelerometer
      - tick
    output:
      format: csv
      file: lowstate.csv

  # LiDAR（OTA后启用）
  - name: lidar
    type: dds
    topic: rt/unitree/slam_lidar/points1
    msg_type: sensor_msgs/msg/PointCloud2
    rate_hz: 10
    enabled: false
    output:
      format: rosbag
      file: lidar.bag

  # ── 类型2: RPC轮询（JPEG拍照） ──
  - name: jpeg_camera
    type: rpc
    service: video_client
    method: GetImageSample
    interval_sec: 3
    output:
      format: jpeg
      dir: images/

  # ── 类型3: GStreamer拉流（h264图传） ──
  - name: h264_stream
    type: gstreamer
    pipeline: >
      udpsrc address=230.1.1.1 port=1720
      multicast-iface={network_interface}
      ! application/x-rtp, media=video, encoding-name=H264
      ! rtph264depay ! h264parse ! avdec_h264
      ! videoconvert
      ! video/x-raw,width=1280,height=720,format=BGR
      ! appsink drop=1
    output:
      format: rosbag
      file: h264_stream.bag

  # 麦克风（A2 DDS接口）
  - name: microphone
    type: rpc
    service: audio_client
    enabled: false
    output:
      format: rosbag
      file: audio.bag
```

### 3.3 多媒体测试场景

```yaml
# robots/a2/multimedia_test/config.yaml
scene: multimedia_test
description: 测试摄像头/麦克风/喇叭
output_dir: /tmp/multimedia_test

sources:
  - name: jpeg_camera
    type: rpc
    service: video_client
    method: GetImageSample
    interval_sec: 2
    output:
      format: jpeg
      dir: images/
  
  - name: microphone
    type: rpc
    service: audio_client
    interval_sec: 1
    output:
      format: rosbag
      file: audio.bag
```

## 4. 数据源类型

| 类型 | 实现 | 适用 |
|---|---|---|
| `dds` | ROS2 subscriber | LowState、LiDAR点云 |
| `rpc` | Client 定时轮询 | JPEG拍照(VideoClient)、音频(AudioClient) |
| `gstreamer` | OpenCV+Gst pipeline | h264图传 UDP拉流 |

## 5. 多媒体兼容性（Go2 → A2）

| Go2 接口 | 方式 | A2 能用？ | 依据 |
|---|---|---|---|
| JPEG 拍照 `VideoClient.GetImageSample()` | RPC | ✅ | 宇树官方确认 |
| h264 图传 UDP `230.1.1.1:1720` | GStreamer | ✅ | A2有HD Camera |
| 麦克风 | DDS | ✅ | A2内嵌麦克风阵列 |
| 喇叭 | DDS | ✅ | A2内嵌扬声器 |

相机参数: 1280×720, 15Hz, 水平100°FOV, 垂直56°FOV

## 6. 一期交付范围

| 模块 | 内容 |
|---|---|
| DDS采集 | LowState → CSV（从验证脚本迁移） |
| RPC采集 | JPEG拍照 VideoClient |
| GStreamer | 待狗充电后实际测试，代码框架先写 |
| 配置驱动 | collector.py 读 YAML → 动态加载 source |
| 一键启动 | launcher.py --robot a2 --scene X |
| 多媒体测试 | jpeg_camera + microphone |

**一期不在范围：**
- LiDAR（等OTA）
- USB摄像头（等购买）
- 自主导航（二期）

## 7. 部署

```bash
# 狗上（PC2）
cd ~/robot-system
pip install -e src/platform/
ros2 run platform collector --robot a2 --scene explore

# 或一键
./deploy.sh a2 explore
```

## 8. 规格自检

| 检查项 | 结果 |
|---|---|
| 占位符/TODO | 无 |
| 内部一致性 | config字段与source type对应 ✅ |
| 范围聚焦 | 一期仅数据采集 ✅ |
| 模糊性 | RPC接口依赖unitree_sdk2，需狗上有SDK ✅ |
