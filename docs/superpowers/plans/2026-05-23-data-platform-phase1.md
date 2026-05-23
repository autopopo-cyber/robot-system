# 数据采集平台 — 一期实现计划

> **For Hermes:** 逐任务执行，每任务提交一次 commit。

**目标:** 搭建通用数据采集平台层，DDS+RPC采集，config驱动，在A2狗上验证

**架构:** Python 3.10 + rclpy + YAML config → collector.py 动态加载 source

**技术栈:** rclpy, PyYAML, unitree_hg/unitree_api/unitree_go msg, OpenCV+GStreamer

---

## 项目结构（目标）

```
robot-system/
├── src/platform/
│   ├── __init__.py
│   ├── collector.py         # 主入口
│   ├── config_loader.py     # YAML加载+验证
│   ├── sources/
│   │   ├── __init__.py
│   │   ├── base.py          # Source基类
│   │   ├── dds_source.py    # DDS订阅
│   │   └── rpc_source.py    # RPC轮询
│   ├── writers/
│   │   ├── __init__.py
│   │   ├── csv_writer.py
│   │   └── jpeg_writer.py
│   └── launcher.py
├── robots/
│   └── a2/
│       ├── base.yaml
│       └── explore/
│           └── config.yaml
├── tests/
│   ├── test_config_loader.py
│   ├── test_dds_source.py
│   └── test_collector.py
└── docs/superpowers/specs/2026-05-23-data-platform-design.md
```

---

### Task 1: 平台包骨架

**Objective:** 建立 `src/platform/` 包结构

**Files:**
- Create: `src/platform/__init__.py`
- Create: `src/platform/sources/__init__.py`
- Create: `src/platform/sources/base.py`
- Create: `src/platform/writers/__init__.py`

**Step 1: 写 base.py（Source 基类）**

```python
# src/platform/sources/base.py
"""数据源基类"""

class SourceBase:
    """所有数据源实现这个接口"""
    def __init__(self, config: dict):
        self.name = config['name']
        self.enabled = config.get('enabled', True)

    def start(self):
        """启动采集"""
        raise NotImplementedError

    def stop(self):
        """停止采集"""
        raise NotImplementedError
```

**Step 2: 写 __init__.py 文件（空）**

**Step 3: 验证导入**

```bash
cd ~/workspace/robot-system
python3 -c "from src.platform.sources.base import SourceBase; print('OK')"
```

预期: `OK`

---

### Task 2: 配置加载器 + 单元测试

**Objective:** YAML config 加载 + 结构验证

**Files:**
- Create: `src/platform/config_loader.py`
- Create: `tests/test_config_loader.py`
- Create: `robots/a2/base.yaml` (最小)
- Create: `robots/a2/explore/config.yaml` (最小)

**Step 1: 写测试（先失败）**

```python
# tests/test_config_loader.py
import unittest
import tempfile
import os

class TestConfigLoader(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def _write(self, name, content):
        path = os.path.join(self.tmp, name)
        with open(path, 'w') as f:
            f.write(content)
        return path

    def test_load_minimal_config(self):
        yaml = """
robot:
  name: test_bot
scene: test
output_dir: /tmp/test
sources: []
"""
        path = self._write('config.yaml', yaml)
        from src.platform.config_loader import load_config
        cfg = load_config(path)
        self.assertEqual(cfg['robot']['name'], 'test_bot')
        self.assertEqual(cfg['scene'], 'test')

    def test_reject_missing_scene(self):
        yaml = """
robot:
  name: test_bot
output_dir: /tmp/test
sources: []
"""
        path = self._write('config.yaml', yaml)
        from src.platform.config_loader import load_config
        with self.assertRaises(ValueError):
            load_config(path)

if __name__ == '__main__':
    unittest.main()
```

**Step 2: 运行测试 → 确认失败**

```bash
cd ~/workspace/robot-system && python3 -m pytest tests/test_config_loader.py -v
```
预期: FAIL — module not found

**Step 3: 写 config_loader.py**

```python
# src/platform/config_loader.py
"""YAML配置加载 + 验证"""
import yaml

REQUIRED_KEYS = ['robot', 'scene', 'output_dir', 'sources']

def load_config(path: str) -> dict:
    with open(path) as f:
        cfg = yaml.safe_load(f)

    for key in REQUIRED_KEYS:
        if key not in cfg:
            raise ValueError(f"Missing required key: {key}")

    return cfg
```

**Step 4: 运行测试 → 确认通过**

```bash
cd ~/workspace/robot-system && python3 -m pytest tests/test_config_loader.py -v
```
预期: `2 passed`

**Step 5: 写最简 base.yaml 和 explore/config.yaml**

```yaml
# robots/a2/base.yaml
robot:
  name: a2
  network_interface: eth0
  unitree_class: a2
```

```yaml
# robots/a2/explore/config.yaml
robot:
  name: a2
scene: explore
output_dir: /home/unitree/exploration_data
sources: []
```

**Step 6: Commit**

```bash
git add src/platform/ robots/a2/ tests/
git commit -m "feat: config_loader + base.yaml + explore/config.yaml"
```

---

### Task 3: CSV Writer

**Objective:** 通用 CSV 输出，支持动态列

**Files:**
- Create: `src/platform/writers/csv_writer.py`

```python
# src/platform/writers/csv_writer.py
"""CSV Writer"""
import csv
import os
from datetime import datetime

class CSVWriter:
    def __init__(self, path: str, columns: list[str]):
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        self.file = open(path, 'w', newline='')
        self.writer = csv.writer(self.file)
        self.writer.writerow(['timestamp_ns'] + columns)

    def write(self, timestamp_ns: int, row: list):
        self.writer.writerow([timestamp_ns] + row)
        self.file.flush()

    def close(self):
        self.file.close()
```

**验证:**

```bash
cd ~/workspace/robot-system
python3 -c "
from src.platform.writers.csv_writer import CSVWriter
w = CSVWriter('/tmp/test.csv', ['x','y'])
w.write(1000, [1.0, 2.0])
w.close()
import csv
with open('/tmp/test.csv') as f:
    rows = list(csv.reader(f))
assert rows[0] == ['timestamp_ns','x','y']
assert rows[1] == ['1000','1.0','2.0']
print('OK')
"
```

**Commit:**

```bash
git add src/platform/writers/
git commit -m "feat: CSV writer"
```

---

### Task 4: DDS Source — LowState采集

**Objective:** 把 verify_lowstate.py 的逻辑抽象成通用 dds_source.py，读 config 的 fields 动态订阅

**Files:**
- Create: `src/platform/sources/dds_source.py`
- Create: `tests/test_dds_source.py`

**Step 1: 写 dds_source.py**

```python
# src/platform/sources/dds_source.py
"""DDS订阅数据源"""
import rclpy
from rclpy.node import Node
from .base import SourceBase

# msg类型注册表 — 加新类型只需加一行
MSG_TYPES = {
    'unitree_hg/msg/LowState': 'unitree_hg.msg.LowState',
}

def _get_msg_class(msg_type: str):
    if msg_type not in MSG_TYPES:
        raise ValueError(f"Unknown msg_type: {msg_type}")
    mod_path, cls_name = MSG_TYPES[msg_type].rsplit('.', 1)
    mod = __import__(mod_path, fromlist=[cls_name])
    return getattr(mod, cls_name)

def _resolve_field(obj, path: str):
    """解析嵌套字段: 'imu_state.rpy' → getattr链"""
    for part in path.split('.'):
        obj = getattr(obj, part)
    return obj

class DDSSource(Node, SourceBase):
    def __init__(self, config: dict, write_callback):
        super().__init__('dds_' + config['name'])
        self.config = config
        self.write_callback = write_callback
        self.msg_class = _get_msg_class(config['msg_type'])
        self.fields = config.get('fields', [])
        self.sub = self.create_subscription(
            self.msg_class, config['topic'], self._callback, 10
        )

    def _callback(self, msg):
        row = []
        for f in self.fields:
            val = _resolve_field(msg, f)
            if isinstance(val, (list, tuple)):
                row.extend(val)
            else:
                row.append(val)
        self.write_callback(self.name, self.get_clock().now().nanoseconds, row)

    def start(self):
        pass  # ROS2 spin中已订阅

    def stop(self):
        self.destroy_node()
```

**Step 2: 写测试**

```python
# tests/test_dds_source.py
import unittest

class TestDDSSource(unittest.TestCase):
    def test_resolve_simple(self):
        from src.platform.sources.dds_source import _resolve_field
        class Obj:
            pass
        obj = Obj()
        obj.x = Obj()
        obj.x.y = 42
        result = _resolve_field(obj, 'x.y')
        self.assertEqual(result, 42)

    def test_msg_type_lowstate(self):
        from src.platform.sources.dds_source import _get_msg_class
        cls = _get_msg_class('unitree_hg/msg/LowState')
        self.assertEqual(cls.__name__, 'LowState')

if __name__ == '__main__':
    unittest.main()
```

**Step 3: 验证**

```bash
cd ~/workspace/robot-system && python3 -m pytest tests/test_dds_source.py -v
```
预期: `2 passed`

**Step 4: Commit**

---

### Task 5: Collector 主入口

**Objective:** 读 config → 初始化 source → 配 writer → spin

**Files:**
- Create: `src/platform/collector.py`

```python
#!/usr/bin/env python3
"""通用数据采集器 — 读config → 初始化sources → spin"""
import rclpy
import argparse
from src.platform.config_loader import load_config
from src.platform.writers.csv_writer import CSVWriter
from src.platform.sources.dds_source import DDSSource

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--robot', required=True, help='e.g. a2')
    parser.add_argument('--scene', required=True, help='e.g. explore')
    args = parser.parse_args()

    path = f'robots/{args.robot}/{args.scene}/config.yaml'
    cfg = load_config(path)

    rclpy.init()
    sources = []
    writers = {}

    for src_cfg in cfg.get('sources', []):
        if not src_cfg.get('enabled', True):
            continue

        if src_cfg['type'] == 'dds':
            output = src_cfg['output']
            if output['format'] == 'csv':
                col_names = src_cfg.get('fields', [])
                w = CSVWriter(output['file'], col_names)
                writers[src_cfg['name']] = w

                def write_cb(name, ts, row):
                    writers[name].write(ts, row)

                src = DDSSource(src_cfg, write_cb)
                sources.append(src)
            else:
                print(f"  ⏭  {src_cfg['name']}: 格式 {output['format']} 暂未支持")

    print(f"Collector: {len(sources)} sources active")
    try:
        rclpy.spin_once(None, timeout_sec=0.1)  # 初始化
        while rclpy.ok():
            rclpy.spin_once(None, timeout_sec=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        for s in sources:
            s.stop()
        for w in writers.values():
            w.close()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
```

**Step 1: 验证语法**

```bash
python3 -m py_compile src/platform/collector.py
```

**Step 2: Commit**

---

### Task 6: A2 explore config — 全量采集

**Objective:** 写真正的 explore/config.yaml，包含 LowState 采集

**Files:**
- Modify: `robots/a2/explore/config.yaml`

```yaml
robot:
  name: a2
  network_interface: eth0
  unitree_class: a2

scene: explore
description: 探索场景 — 全量传感器采集
output_dir: /home/unitree/exploration_data

sources:
  - name: lowstate
    type: dds
    topic: /lf/lowstate
    msg_type: unitree_hg/msg/LowState
    rate_hz: 50
    fields:
      - tick
      - imu_state.rpy
      - imu_state.gyroscope
      - imu_state.accelerometer
    output:
      format: csv
      file: /home/unitree/exploration_data/lowstate.csv

  # LiDAR（OTA后启用）
  - name: lidar
    type: dds
    topic: rt/unitree/slam_lidar/points1
    msg_type: sensor_msgs/msg/PointCloud2
    rate_hz: 10
    enabled: false
    output:
      format: rosbag
      file: /home/unitree/exploration_data/lidar.bag

  # JPEG拍照（Go2兼容，A2可用）
  - name: jpeg_camera
    type: rpc
    service: video_client
    method: GetImageSample
    interval_sec: 3
    output:
      format: jpeg
      dir: /home/unitree/exploration_data/images/
```

**Commit:**

```bash
git add robots/a2/explore/config.yaml
git commit -m "feat: A2 explore config — LowState+LiDAR+camera"
```

---

### Task 7: A2 真机验证

**Objective:** 部署到 xiu5，跑 LowState 采集

**Step 1: 打包推送到狗**

```bash
cd ~/workspace/robot-system
tar czf /tmp/platform.tar.gz src/platform/ robots/a2/
sshpass -p 'Unitree#24226' scp /tmp/platform.tar.gz unitree@100.65.245.29:/tmp/
ssh unitree@100.65.245.29 "cd ~/robot-system && tar xzf /tmp/platform.tar.gz"
```

**Step 2: 狗上运行采集器**

```bash
ssh unitree@100.65.245.29
cd ~/robot-system
source /opt/ros/humble/setup.bash
python3 src/platform/collector.py --robot a2 --scene explore
```

**Step 3: 验证输出**

```bash
ssh unitree@100.65.245.29 "ls -la /home/unitree/exploration_data/ && head -5 /home/unitree/exploration_data/lowstate.csv"
```

预期: CSV 文件存在，有 header + 数据行

---

## 交付清单

| 任务 | 内容 | 状态 |
|---|---|---|
| T1 | platform 包骨架 | ⬜ |
| T2 | config_loader + 测试 | ⬜ |
| T3 | CSV Writer | ⬜ |
| T4 | DDS Source (LowState) | ⬜ |
| T5 | Collector 主入口 | ⬜ |
| T6 | A2 explore config 全量 | ⬜ |
| T7 | A2 真机验证 | ⬜ |

**一期不在范围:**
- GStreamer拉流（狗没电，充电后补）
- RPC JPEG拍照（狗没电）
- rosbag writer
- LiDAR（等OTA）
