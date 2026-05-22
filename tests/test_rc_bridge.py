#!/usr/bin/env python3
"""测试 rc_bridge — mock验证 Move/Damp 发布逻辑"""

import unittest
import sys
from unittest.mock import MagicMock


class FakeNode:
    def create_publisher(self, *a, **kw):
        return MagicMock()
    def get_logger(self):
        return MagicMock()


class FakeRequestHeader:
    class identity:
        api_id = 0


class FakeRequest:
    header = FakeRequestHeader()
    parameter = ''


class FakeSportModeCmd:
    mode = 0
    velocity = [0, 0, 0]
    yaw_speed = 0.0


class TestRCBridge(unittest.TestCase):

    def setUp(self):
        # 注入mock模块
        rclpy_mock = MagicMock()
        rclpy_mock.node = MagicMock()
        rclpy_mock.node.Node = FakeNode

        unitree_api_mock = MagicMock()
        unitree_api_mock.msg = MagicMock()
        unitree_api_mock.msg.Request = FakeRequest
        unitree_api_mock.msg.RequestHeader = FakeRequestHeader
        unitree_api_mock.msg.RequestIdentity = MagicMock()

        unitree_go_mock = MagicMock()
        unitree_go_mock.msg = MagicMock()
        unitree_go_mock.msg.SportModeCmd = FakeSportModeCmd

        sys.modules['rclpy'] = rclpy_mock
        sys.modules['rclpy.node'] = rclpy_mock.node
        sys.modules['unitree_api'] = unitree_api_mock
        sys.modules['unitree_api.msg'] = unitree_api_mock.msg
        sys.modules['unitree_go'] = unitree_go_mock
        sys.modules['unitree_go.msg'] = unitree_go_mock.msg

        for k in list(sys.modules):
            if k.startswith('exploration'):
                del sys.modules[k]

    def tearDown(self):
        for k in ['rclpy', 'rclpy.node', 'unitree_api', 'unitree_api.msg',
                  'unitree_go', 'unitree_go.msg']:
            sys.modules.pop(k, None)

    def test_move_publish(self):
        """send_move发布 → API_ID=1008"""
        from exploration.rc_bridge import RCBridge

        node = RCBridge.__new__(RCBridge)
        mock_pub = MagicMock()
        node.pub = mock_pub
        node._seq = 0
        node.get_logger = MagicMock()

        node.send_move(0.5, 0.0, 0.0)
        mock_pub.publish.assert_called_once()
        self.assertEqual(node._seq, 1)

    def test_damp_publish(self):
        """send_damp发布 → API_ID=1001"""
        from exploration.rc_bridge import RCBridge

        node = RCBridge.__new__(RCBridge)
        mock_pub = MagicMock()
        node.pub = mock_pub
        node._seq = 0
        node.get_logger = MagicMock()

        node.send_damp()
        mock_pub.publish.assert_called_once()
        self.assertEqual(node._seq, 1)


if __name__ == '__main__':
    unittest.main()
