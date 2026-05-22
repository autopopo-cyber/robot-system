# 探索狗平台 — 一期实现计划（遥控 + 数据收集）

> **For Hermes:** 逐任务执行，每任务提交一次commit。

**目标:** PC2上跑遥控桥 + 数据记录器 → 操作员遥控狗进室内 → 全程记录LiDAR点云+图像+姿态 → 导出到2080Ti生成3DGS

**架构:** 两个ROS2节点 — `rc_bridge.py`（遥控转发） + `data_logger.py`（数据记录）

**技术栈:** Python 3.10 + rclpy + unitree_go/unitree_api msg + numpy

---

## 项目结构（一期）

```
robot-system/
├── exploration/
│   ├── __init__.py
│   ├── rc_bridge.py          # 遥控桥: RTC/HTTP→API_ID=1008
│   ├── data_logger.py        # 数据记录: LowState+LiDAR+图像→SSD
│   └── grid.py               # 体素grid(一期不用, 预留给二期)
├── tests/
│   ├── test_rc_bridge.py
│   └── test_data_logger.py
└── docs/
    └── superpowers/specs/2026-05-22-exploration-dog-design.md
```

---

## 任务列表

### Task 1: 创建项目骨架

**Objective:** 建立ROS2 Python包 + 单元测试框架

**Files:**
- Create: `exploration/__init__.py`
- Create: `exploration/rc_bridge.py` (空壳)
- Create: `exploration/data_logger.py` (空壳)
- Create: `tests/__init__.py`
- Create: `tests/test_rc_bridge.py` (空壳)
- Create: `tests/test_data_logger.py` (空壳)
- Create: `setup.py`
- Create: `setup.cfg`
- Create: `package.xml`

**Step 1: 写setup.py**

```python
from setuptools import setup

package_name = 'exploration'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
)
```

**Step 2: 写setup.cfg**

```ini
[develop]
script_dir=$base/lib/exploration
[install]
install_scripts=$base/lib/exploration
```

**Step 3: 写package.xml**

```xml
<?xml version="1.0"?>
<package format="2">
  <name>exploration</name>
  <version>0.1.0</version>
  <description>Exploration engine for quadruped robot</description>
  <maintainer email="qin@autopopo.cyber">Qin</maintainer>
  <license>MIT</license>
  <exec_depend>rclpy</exec_depend>
  <exec_depend>unitree_go</exec_depend>
  <exec_depend>unitree_api</exec_depend>
  <export>
    <build_type>ament_python</build_type>
  </export>
</package>
```

**Step 4: 验证**

```bash
cd ~/workspace/robot-system && python3 -c "import exploration; print('OK')"
```

预期: `OK`（允许空包导入失败，后面填代码）

**Step 5: Commit**

```bash
cd ~/workspace/robot-system
git add exploration/ tests/ setup.py setup.cfg package.xml
git commit -m "feat: exploration package skeleton"
```

---

### Task 2: 数据记录器 — LowState订阅+CSV写入

**Objective:** 订阅`/lf/lowstate`，提取IMU姿态写入CSV

**Files:**
- Modify: `exploration/data_logger.py`
- Create: `tests/test_data_logger.py`

**Step 1: 写data_logger.py**

```python
#!/usr/bin/env python3
"""数据记录器: 订阅LowState → 写CSV"""
import rclpy
from rclpy.node import Node
from unitree_hg.msg import LowState
import csv
import os
from datetime import datetime

class DataLogger(Node):
    def __init__(self, output_dir="/tmp/exploration_data"):
        super().__init__('data_logger')
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.csv_path = os.path.join(output_dir, f"state_{timestamp}.csv")
        self.csv_file = open(self.csv_path, 'w', newline='')
        self.writer = csv.writer(self.csv_file)
        self.writer.writerow([
            'tick', 'timestamp_ns',
            'roll', 'pitch', 'yaw',
            'gyro_x', 'gyro_y', 'gyro_z',
            'acc_x', 'acc_y', 'acc_z',
        ])
        self.sub = self.create_subscription(
            LowState, '/lf/lowstate', self.callback, 10
        )
        self.get_logger().info(f'DataLogger ready → {self.csv_path}')

    def callback(self, msg: LowState):
        imu = msg.imu_state
        self.writer.writerow([
            msg.tick,
            self.get_clock().now().nanoseconds,
            imu.rpy[0], imu.rpy[1], imu.rpy[2],
            imu.gyroscope[0], imu.gyroscope[1], imu.gyroscope[2],
            imu.accelerometer[0], imu.accelerometer[1], imu.accelerometer[2],
        ])
        self.csv_file.flush()

    def destroy_node(self):
        self.csv_file.close()
        super().destroy_node()

def main():
    rclpy.init()
    node = DataLogger()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
```

**Step 2: 写测试 — tests/test_data_logger.py**

用`unittest.mock`模拟LowState消息，验证回调写入CSV：

```python
import unittest
from unittest.mock import MagicMock, patch
import tempfile, os, csv

class FakeIMU:
    def __init__(self):
        self.rpy = [0.0, 0.0, 0.0]
        self.gyroscope = [0.0, 0.0, 0.0]
        self.accelerometer = [0.0, 0.0, 0.0]

class FakeLowState:
    def __init__(self):
        self.tick = 0
        self.imu_state = FakeIMU()

class TestDataLogger(unittest.TestCase):
    def test_csv_write(self):
        with tempfile.TemporaryDirectory() as d:
            from exploration.data_logger import DataLogger
            import rclpy
            rclpy.init()
            logger = DataLogger(output_dir=d)
            # Manual callback test (bypass spin)
            logger.callback(FakeLowState())
            logger.destroy_node()
            rclpy.shutdown()
            # Read CSV
            files = [f for f in os.listdir(d) if f.endswith('.csv')]
            self.assertEqual(len(files), 1)
            with open(os.path.join(d, files[0])) as f:
                reader = csv.reader(f)
                rows = list(reader)
            self.assertEqual(len(rows), 2)  # header + 1 data row
            self.assertEqual(rows[0][0], 'tick')
            self.assertEqual(rows[1][0], '0')

if __name__ == '__main__':
    unittest.main()
```

**Step 3: 运行测试**

```bash
cd ~/workspace/robot-system && python3 -m pytest tests/test_data_logger.py -v
```

预期: `1 passed`

**Step 4: Commit**

```bash
cd ~/workspace/robot-system
git add exploration/data_logger.py tests/test_data_logger.py
git commit -m "feat: data_logger — LowState→CSV"
```

---

### Task 3: 遥控桥 — API_ID=1008 Move发布

**Objective:** 接收遥控指令（先做HTTP接口，RTC走宇树自带），转发为ROS2 `/api/sport/request` 发布

**Files:**
- Modify: `exploration/rc_bridge.py`
- Create: `tests/test_rc_bridge.py`

**Step 1: 写rc_bridge.py**

```python
#!/usr/bin/env python3
"""遥控桥: HTTP→ROS2运动API"""
import rclpy
from rclpy.node import Node
from unitree_api.msg import Request, RequestHeader, RequestIdentity
from unitree_go.msg import SportModeCmd
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

class RCBridge(Node):
    def __init__(self):
        super().__init__('rc_bridge')
        self.pub = self.create_publisher(Request, '/api/sport/request', 10)
        self._seq = 0
        self.get_logger().info('RCBridge ready — /api/sport/request')

    def send_move(self, vx: float, vy: float, vyaw: float):
        """发布Move指令 (API_ID=1008)"""
        self._seq += 1
        
        header = RequestHeader()
        header.identity.api_id = 1008
        
        cmd = SportModeCmd()
        cmd.mode = 0           # 0=速度模式
        cmd.velocity = [vx, vy, vyaw]
        cmd.yaw_speed = vyaw
        
        req = Request()
        req.header = header
        req.parameter = json.dumps({
            'velocity': [vx, vy, 0.0],
            'yaw_speed': vyaw,
        })
        
        self.pub.publish(req)
        self.get_logger().debug(f'Move: vx={vx:.2f} vy={vy:.2f} vyaw={vyaw:.2f}')

    def send_damp(self):
        """紧急停止 (API_ID=1001)"""
        self._seq += 1
        header = RequestHeader()
        header.identity.api_id = 1001
        req = Request()
        req.header = header
        req.parameter = '{}'
        self.pub.publish(req)
        self.get_logger().info('DAMP')

def main():
    rclpy.init()
    node = RCBridge()
    # TODO: HTTP server or RTC integration in later task
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
```

**Step 2: 写测试 — tests/test_rc_bridge.py**

```python
import unittest
from unittest.mock import MagicMock, patch
import rclpy

class TestRCBridge(unittest.TestCase):
    def test_move_publish(self):
        rclpy.init()
        from exploration.rc_bridge import RCBridge
        node = RCBridge()
        mock_pub = MagicMock()
        node.pub = mock_pub
        node.send_move(0.5, 0.0, 0.0)
        mock_pub.publish.assert_called_once()
        call_arg = mock_pub.publish.call_args[0][0]
        self.assertEqual(call_arg.header.identity.api_id, 1008)
        node.destroy_node()
        rclpy.shutdown()

    def test_damp_publish(self):
        rclpy.init()
        from exploration.rc_bridge import RCBridge
        node = RCBridge()
        mock_pub = MagicMock()
        node.pub = mock_pub
        node.send_damp()
        call_arg = mock_pub.publish.call_args[0][0]
        self.assertEqual(call_arg.header.identity.api_id, 1001)
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    unittest.main()
```

**Step 3: 运行测试**

```bash
cd ~/workspace/robot-system && python3 -m pytest tests/test_rc_bridge.py -v
```

预期: `2 passed`

**Step 4: Commit**

```bash
cd ~/workspace/robot-system
git add exploration/rc_bridge.py tests/test_rc_bridge.py
git commit -m "feat: rc_bridge — HTTP→API_ID Move/Damp"
```

---

### Task 4: 遥控桥 — HTTP REST接口

**Objective:** 给RCBridge加HTTP接口，接收JSON遥控指令

**Files:**
- Modify: `exploration/rc_bridge.py`

**Step 1: 加HTTPHandler + 启动**

在rc_bridge.py末尾的`main()`里嵌入HTTP server：

```python
class MoveHandler(BaseHTTPRequestHandler):
    bridge = None  # Set before server start

    def do_POST(self):
        if self.path != '/move':
            self.send_error(404)
            return
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length) if length else b'{}'
        data = json.loads(body)
        vx = data.get('vx', 0.0)
        vy = data.get('vy', 0.0)
        vyaw = data.get('vyaw', 0.0)
        self.bridge.send_move(vx, vy, vyaw)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'ok': True, 'vx': vx, 'vy': vy, 'vyaw': vyaw}).encode())

    def log_message(self, *args):
        pass  # 静默HTTP日志

def main():
    rclpy.init()
    bridge = RCBridge()
    
    # HTTP server on port 8400
    MoveHandler.bridge = bridge
    server = HTTPServer(('0.0.0.0', 8400), MoveHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    bridge.get_logger().info('HTTP server on :8400/move')
    
    try:
        rclpy.spin(bridge)
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        bridge.destroy_node()
        rclpy.shutdown()
```

**Step 2: 测试 — 手动curl验证（不提交真机运动）**

```bash
# 仅验证HTTP响应，不连真机
python3 exploration/rc_bridge.py &
sleep 2
curl -s -X POST http://localhost:8400/move -d '{"vx":0.3,"vy":0,"vyaw":0}'
# 预期: {"ok":true,"vx":0.3,"vy":0,"vyaw":0}
kill %1
```

**Step 3: Commit**

```bash
cd ~/workspace/robot-system
git add exploration/rc_bridge.py
git commit -m "feat: rc_bridge HTTP /move endpoint"
```

---

### Task 5: 数据记录器 — 加图像+点云预留接口

**Objective:** data_logger加可选订阅：摄像头图像 + LiDAR点云

**Files:**
- Modify: `exploration/data_logger.py`

**Step 1: 加可选订阅器**

```python
# 在DataLogger.__init__末尾加:
# 摄像头（等USB摄像头就绪后取消注释）
# from sensor_msgs.msg import Image
# self.create_subscription(Image, '/usb_cam/image_raw', self.image_cb, 10)

# LiDAR点云（等OTA后就绪后取消注释）
# from sensor_msgs.msg import PointCloud2
# self.create_subscription(PointCloud2, '/utlidar/cloud', self.lidar_cb, 10)
```

**Step 2: 加回调存根 + init参数**

```python
def __init__(self, output_dir="/tmp/exploration_data", 
             enable_camera=False, enable_lidar=False):
    # ... existing code ...
    self.enable_camera = enable_camera
    self.enable_lidar = enable_lidar
    # 摄像头目录
    if enable_camera:
        self.img_dir = os.path.join(output_dir, 'images')
        os.makedirs(self.img_dir, exist_ok=True)
    # LiDAR目录
    if enable_lidar:
        self.lidar_dir = os.path.join(output_dir, 'lidar')
        os.makedirs(self.lidar_dir, exist_ok=True)

# def image_cb(self, msg):  # 预留
#     pass

# def lidar_cb(self, msg):  # 预留
#     pass
```

**Step 3: 验证CSV功能不受影响**

```bash
cd ~/workspace/robot-system && python3 -m pytest tests/test_data_logger.py -v
```

**Step 4: Commit**

```bash
cd ~/workspace/robot-system
git add exploration/data_logger.py
git commit -m "feat: data_logger — camera+lidar stubs"
```

---

### Task 6: launch文件 — 一键启动两个节点

**Objective:** 写ROS2 launch文件，同时启动rc_bridge + data_logger

**Files:**
- Create: `exploration/launch/exploration.launch.py`

**Step 1: 写launch文件**

```python
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='exploration',
            executable='rc_bridge.py',
            name='rc_bridge',
            output='screen',
        ),
        Node(
            package='exploration',
            executable='data_logger.py',
            name='data_logger',
            output='screen',
            parameters=[{'output_dir': '/home/unitree/exploration_data'}]
        ),
    ])
```

**Step 2: 更新setup.py加entry_points**

```python
setup(
    # ...existing...
    entry_points={
        'console_scripts': [
            'rc_bridge = exploration.rc_bridge:main',
            'data_logger = exploration.data_logger:main',
        ],
    },
)
```

**Step 3: 语法验证**

```bash
cd ~/workspace/robot-system && python3 -c "
from launch import LaunchDescription
from launch_ros.actions import Node
print('launch OK')
"
```

**Step 4: Commit**

```bash
cd ~/workspace/robot-system
git add exploration/launch/ setup.py
git commit -m "feat: launch file + entry_points"
```

---

## 交付清单

| 任务 | 产物 | 状态 |
|------|------|------|
| T1 项目骨架 | package.xml, setup.py, setup.cfg | ⬜ |
| T2 data_logger CSV | LowState→CSV + 单元测试 | ⬜ |
| T3 rc_bridge Move | API_ID=1008/1001发布 + 单元测试 | ⬜ |
| T4 rc_bridge HTTP | :8400/move REST接口 | ⬜ |
| T5 预留接口 | 摄像头+LiDAR订阅存根 | ⬜ |
| T6 launch文件 | 一键启动两节点 | ⬜ |

**一期不在范围内:**
- 自主导航（萤火V3）→ 二期
- LiDAR/摄像头驱动 → 等硬件就绪
- 3DGS训练 → 2080Ti笔记本，独立脚本
