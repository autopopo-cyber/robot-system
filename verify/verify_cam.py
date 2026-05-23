#!/usr/bin/env python3
"""读A2前视摄像头"""
import rclpy
from rclpy.node import Node
from unitree_go.msg import Go2FrontVideoData

class CamReader(Node):
    def __init__(self):
        super().__init__('verify_cam')
        self.sub = self.create_subscription(
            Go2FrontVideoData, '/frontvideostream', self.cb, 10)
        self.count = 0

    def cb(self, msg):
        self.count += 1
        self.get_logger().info(
            f'[{self.count}] time={msg.time_frame} '
            f'720p={len(msg.video720p)}B '
            f'360p={len(msg.video360p)}B '
            f'180p={len(msg.video180p)}B'
        )

rclpy.init()
node = CamReader()
try:
    rclpy.spin(node)
except KeyboardInterrupt:
    pass
node.destroy_node()
