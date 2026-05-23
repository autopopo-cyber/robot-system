# A2 SDK 验证脚本 — 实现计划

> **For Hermes:** 使用 subagent-driven-development skill 逐任务实现。
> 或者直接按顺序执行各任务。

**Goal:** 从零到全链路验证 A2 狗的四条数据通道（状态/激光/摄像头/运动）

**Architecture:** clone unitree_ros2 → 在狗上只编译 msg 包 → rclpy 脚本逐条验证

**Tech Stack:** ROS2 Humble, rclpy, Python 3.10, colcon, CycloneDDS

---

## Step 0: 在狗上编译 unitree 消息包

### 0.1 本机 clone unitree_ros2 仓库

```bash
cd /tmp
git clone -c http.proxy=http://127.0.0.1:7897 https://github.com/unitreerobotics/unitree_ros2.git
```

预期：clone 完成，`/tmp/unitree_ros2/` 目录存在

### 0.2 只拷贝消息定义到狗

```bash
# unitree_ros2 的消息包通常在:
# - unitree_go/  或  unitree_go_msgs/
# - unitree_api/ 或  hg_messages/  (不同版本路径不同)

# 先确认目录结构:
ls /tmp/unitree_ros2/

# 找到 msg 包目录后 scp 到狗:
sshpass -p 'Unitree#24226' scp -r /tmp/unitree_ros2/unitree_go unitree@100.65.245.29:~/msg_ws/src/
sshpass -p 'Unitree#24226' scp -r /tmp/unitree_ros2/unitree_api unitree@100.65.245.29:~/msg_ws/src/
```

### 0.3 在狗上编译

```bash
sshpass -p 'Unitree#24226' ssh unitree@100.65.245.29 "
  source /opt/ros/humble/setup.bash
  cd ~/msg_ws
  colcon build --packages-select unitree_go unitree_api
"
```

预期：编译成功，无错误

### 0.4 验证 import

```bash
sshpass -p 'Unitree#24226' ssh unitree@100.65.245.29 "
  source /opt/ros/humble/setup.bash
  source ~/msg_ws/install/setup.bash
  python3 -c 'from unitree_go.msg import SportModeState; print(\"OK\")'
"
```

预期：打印 `OK`

---

## Step 1: verify_sport.py — 运动状态

```python
# 在狗上运行，打印 sportmodestate 10 秒
import rclpy
from rclpy.node import Node
from unitree_go.msg import SportModeState

class SportReader(Node):
    def __init__(self):
        super().__init__('verify_sport')
        self.sub = self.create_subscription(
            SportModeState, '/lf/sportmodestate', self.cb, 10)
        self.count = 0
    def cb(self, msg):
        self.count += 1
        self.get_logger().info(
            f'[{self.count}] mode={msg.mode} '
            f'pos=({msg.position[0]:.2f},{msg.position[1]:.2f},{msg.position[2]:.2f}) '
            f'vel=({msg.velocity[0]:.2f},{msg.velocity[1]:.2f},{msg.velocity[2]:.2f}) '
            f'rpy=({msg.imu_state.rpy[0]:.1f},{msg.imu_state.rpy[1]:.1f},{msg.imu_state.rpy[2]:.1f})'
        )

rclpy.init()
node = SportReader()
try:
    rclpy.spin_once(node, timeout_sec=10)
except KeyboardInterrupt:
    pass
node.destroy_node()
```

成功标准：打印 position/velocity/mode/IMU ≥ 3 条

---

## Step 2: verify_lidar.py — 激光点云

> JT128 雷达通过124网段连接，数据可能通过 ROS2 topic 发布
> 先查 topic: `ros2 topic list | grep -i 'scan\|point\|cloud\|lidar'`

```python
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan, PointCloud2

class LidarReader(Node):
    def __init__(self):
        super().__init__('verify_lidar')
        # 尝试 LaserScan
        self.sub = self.create_subscription(
            LaserScan, '/scan', self.cb_scan, 10)
    def cb_scan(self, msg):
        self.get_logger().info(
            f'LaserScan: {len(msg.ranges)} ranges, '
            f'[0]={msg.ranges[0]:.2f}m, '
            f'angle_min={msg.angle_min:.2f} angle_max={msg.angle_max:.2f}'
        )

rclpy.init()
node = LidarReader()
rclpy.spin_once(node, timeout_sec=10)
```

如果 `/scan` 不存在，改用 `PointCloud2` 订阅 `/livox/lidar` 或类似 topic。

成功标准：打印一帧点云数量/范围

---

## Step 3: verify_cam.py — 摄像头图像

```python
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image

class CamReader(Node):
    def __init__(self):
        super().__init__('verify_cam')
        # A2 内置摄像头 topic 名不确定，先查
        self.sub = self.create_subscription(
            Image, '/camera/image_raw', self.cb, 10)
    def cb(self, msg):
        self.get_logger().info(
            f'Image: {msg.width}x{msg.height} '
            f'encoding={msg.encoding} '
            f'size={len(msg.data)} bytes'
        )

rclpy.init()
node = CamReader()
rclpy.spin_once(node, timeout_sec=10)
```

成功标准：打印图像分辨率和编码格式

---

## Step 4: verify_move.py — 运动控制（只发指令，人在场）

```python
import rclpy
from rclpy.node import Node
from unitree_api.msg import Request, Response

# ⚠️ 此脚本会实际控制狗移动！
# 仅在人在场、空旷环境、遥控器急停就绪时运行
# 只发低速 Move 指令，立即 Stop

class MoveTest(Node):
    def __init__(self):
        super().__init__('verify_move')
        self.client = self.create_client(Request, '/api/sport/request')
        self.resp_sub = self.create_subscription(
            Response, '/api/sport/response', self.on_resp, 10)
        self.got_resp = False

    def on_resp(self, msg):
        self.get_logger().info(f'Response: code={msg.code} msg={msg.msg}')
        self.got_resp = True

    def send_request(self, api_id, params):
        req = Request()
        req.header.identity.api_id = api_id
        req.parameter = str(params)  # JSON
        self.client.wait_for_service(timeout_sec=3)
        self.client.send_async(req)

rclpy.init()
node = MoveTest()
# 只发一个 Damp 指令（不移动，只松关节）
# 发送前需人在狗旁，遥控器在手
input('人在狗旁准备好后按 Enter...')
# 实际 API 格式需查 unitree_ros2 文档
# --- 此处需实地验证 API 请求格式 ---
```

> ⚠️ Step 4 是最危险的一步——API 请求格式需从 unitree_ros2 源码确认后才能执行

成功标准：返回 API 响应码 ≠ 0

---

## 文件结构

```
~/workspace/robot-system/verify/
├── setup_msgs.sh        # Step 0 一键脚本
├── verify_sport.py      # Step 1
├── verify_lidar.py      # Step 2
├── verify_cam.py        # Step 3
├── verify_move.py       # Step 4 (危险，标记 ⚠️)
└── verify_report.json   # 执行结果汇总
```
