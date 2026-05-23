#!/usr/bin/env python3
"""verify_sport.py — 验证 A2 运动状态订阅"""
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
        x, y, z = msg.position[0], msg.position[1], msg.position[2]
        vx, vy, vz = msg.velocity[0], msg.velocity[1], msg.velocity[2]
        roll, pitch, yaw = msg.imu_state.rpy[0], msg.imu_state.rpy[1], msg.imu_state.rpy[2]
        self.get_logger().info(
            f'[{self.count}] mode={msg.mode} '
            f'pos=({x:.2f},{y:.2f},{z:.2f}) '
            f'vel=({vx:.2f},{vy:.2f},{vz:.2f}) '
            f'rpy=({roll:.1f},{pitch:.1f},{yaw:.1f}) '
            f'height={msg.body_height:.2f} progress={msg.progress:.1f}'
        )

def main():
    rclpy.init()
    node = SportReader()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()

if __name__ == '__main__':
    main()
