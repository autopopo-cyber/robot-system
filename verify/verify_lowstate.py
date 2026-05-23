#!/usr/bin/env python3
"""读A2 LowState — IMU+35电机"""
import rclpy
from rclpy.node import Node
from unitree_hg.msg import LowState

class LowStateReader(Node):
    def __init__(self):
        super().__init__('verify_lowstate')
        self.sub = self.create_subscription(
            LowState, '/lf/lowstate', self.cb, 10)
        self.count = 0

    def cb(self, msg):
        self.count += 1
        imu = msg.imu_state
        self.get_logger().info(
            f'[{self.count}] tick={msg.tick} '
            f'mode_pr={msg.mode_pr} mode_mach={msg.mode_machine} '
            f'rpy=({imu.rpy[0]:.1f},{imu.rpy[1]:.1f},{imu.rpy[2]:.1f}) '
            f'quat=({imu.quaternion[0]:.2f},{imu.quaternion[1]:.2f},{imu.quaternion[2]:.2f},{imu.quaternion[3]:.2f}) '
            f'gyro=({imu.gyroscope[0]:.2f},{imu.gyroscope[1]:.2f},{imu.gyroscope[2]:.2f}) '
            f'motors={len(msg.motor_state)}'
        )

rclpy.init()
node = LowStateReader()
try:
    rclpy.spin(node)
except KeyboardInterrupt:
    pass
node.destroy_node()
