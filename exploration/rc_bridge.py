#!/usr/bin/env python3
"""遥控桥: HTTP→ROS2运动API"""
import rclpy
from rclpy.node import Node
from unitree_api.msg import Request, RequestHeader, RequestIdentity
from unitree_go.msg import SportModeCmd
import json


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
        cmd.mode = 0              # 0=速度模式
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
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
