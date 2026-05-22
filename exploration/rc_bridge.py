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


# ── HTTP REST 接口 ──────────────────────────────
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler


class MoveHandler(BaseHTTPRequestHandler):
    bridge = None

    def do_POST(self):
        if self.path != '/move':
            self.send_error(404)
            return
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length) if length else b'{}'
        data = json.loads(body)
        vx = float(data.get('vx', 0.0))
        vy = float(data.get('vy', 0.0))
        vyaw = float(data.get('vyaw', 0.0))
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


if __name__ == '__main__':
    main()
