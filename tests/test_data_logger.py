#!/usr/bin/env python3
"""测试 data_logger — mock验证CSV写入逻辑 (不依赖真实rclpy)"""

import unittest
import sys
import tempfile
import os
import csv
from unittest.mock import MagicMock, PropertyMock


class FakeNode:
    """假ROS2 Node基类"""
    def create_subscription(self, *a, **kw):
        return MagicMock()
    def get_logger(self):
        return MagicMock()


class FakeIMU:
    rpy = [0.1, 0.2, 0.3]
    gyroscope = [0.01, 0.02, 0.03]
    accelerometer = [0.1, 0.2, 9.8]


class FakeLowState:
    tick = 42
    imu_state = FakeIMU()


class FakeClock:
    def now(self):
        class T:
            nanoseconds = 123456789
        return T()


class TestDataLogger(unittest.TestCase):

    def test_csv_write(self):
        """Mock LowState → CSV写入验证"""

        # 构造假模块 — Node是真正的类才能被继承
        rclpy_mock = MagicMock()
        rclpy_mock.node = MagicMock()
        rclpy_mock.node.Node = FakeNode

        unitree_hg_mock = MagicMock()
        unitree_hg_mock.msg = MagicMock()
        unitree_hg_mock.msg.LowState = FakeLowState

        # 注入sys.modules
        sys.modules['rclpy'] = rclpy_mock
        sys.modules['rclpy.node'] = rclpy_mock.node
        sys.modules['unitree_hg'] = unitree_hg_mock
        sys.modules['unitree_hg.msg'] = unitree_hg_mock.msg

        # 清除旧的import缓存
        for k in list(sys.modules):
            if k.startswith('exploration'):
                del sys.modules[k]

        with tempfile.TemporaryDirectory() as d:
            from exploration.data_logger import DataLogger

            # 手动构造, 绕过ROS2 init
            logger = DataLogger.__new__(DataLogger)
            logger.output_dir = d
            os.makedirs(d, exist_ok=True)
            logger.csv_path = os.path.join(d, 'test.csv')
            logger.csv_file = open(logger.csv_path, 'w', newline='')
            logger.writer = csv.writer(logger.csv_file)
            logger.writer.writerow([
                'tick', 'timestamp_ns',
                'roll', 'pitch', 'yaw',
                'gyro_x', 'gyro_y', 'gyro_z',
                'acc_x', 'acc_y', 'acc_z',
            ])
            logger.get_clock = lambda: FakeClock()

            logger.callback(FakeLowState())
            logger.csv_file.close()

            with open(logger.csv_path) as f:
                reader = csv.reader(f)
                rows = list(reader)

            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0][0], 'tick')
            self.assertEqual(int(rows[1][0]), 42)
            self.assertAlmostEqual(float(rows[1][2]), 0.1)

        # 清理
        for k in ['rclpy', 'rclpy.node', 'unitree_hg', 'unitree_hg.msg']:
            sys.modules.pop(k, None)


if __name__ == '__main__':
    unittest.main()
