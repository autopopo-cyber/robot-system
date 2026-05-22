"""
adapters/unitree_a2.py — 宇树 A2 适配器

基于 ROS2 rclpy 直连 DDS，只读状态。
严禁调用运动 API (sport/loco/move)。
"""

import threading
import time
from typing import Optional

# rclpy 在狗上可用，本地可能缺失
try:
    import rclpy
    from rclpy.node import Node
    HAS_RCLPY = True
except ImportError:
    HAS_RCLPY = False

from platform.interfaces import RobotAdapter, RobotState, ImuState, FsmMode


class UnitreeA2Adapter(RobotAdapter):
    """宇树 A2 四足机器人 — 只读适配器"""

    # DDS 话题常量
    TOPIC_SPORT_STATE = "/lf/sportmodestate"      # 低频状态 (~10Hz)
    TOPIC_SPORT_STATE_HF = "/sportmodestate"      # 高频状态 (~100Hz)
    TOPIC_LOW_STATE = "/lf/lowstate"              # 关节力矩/角度
    TOPIC_BMS_STATE = "/lf/bmsstate"              # 电池

    def __init__(self, node_name: str = "a2_adapter"):
        self._node: Optional[Node] = None
        self._node_name = node_name
        self._state: RobotState = RobotState()
        self._lock = threading.Lock()
        self._connected = False

    # === RobotAdapter 实现 ===

    def connect(self) -> bool:
        if not HAS_RCLPY:
            raise RuntimeError("rclpy 未安装，无法连接 A2。"
                               "在机器狗上运行需 source /opt/ros/humble/setup.bash")
        if self._connected:
            return True

        rclpy.init(args=[])
        self._node = Node(self._node_name)

        # 订阅低频状态
        self._node.create_subscription(
            self._node.get_message_type("unitree_go/msg/SportModeState"),
            self.TOPIC_SPORT_STATE,
            self._on_sport_state,
            10
        )

        # 验证连接
        time.sleep(2.0)
        with self._lock:
            self._connected = self._state.timestamp > 0

        return self._connected

    def disconnect(self):
        if self._node:
            self._node.destroy_node()
            self._node = None
        self._connected = False

    def get_state(self) -> RobotState:
        with self._lock:
            return self._state

    def get_joint_states(self) -> dict:
        return {}  # TODO: 订阅 /lf/lowstate 解析

    def is_connected(self) -> bool:
        return self._connected

    # === 内部回调 ===

    def _on_sport_state(self, msg):
        """SportModeState DDS 消息回调"""
        try:
            state = RobotState(
                timestamp=msg.stamp.sec + msg.stamp.nanosec * 1e-9,
                fsm_mode=FsmMode(msg.mode),
                position=(msg.position[0], msg.position[1], msg.position[2]),
                velocity=(msg.velocity[0], msg.velocity[1], msg.velocity[2]),
                body_height=msg.body_height,
                yaw_speed=msg.yaw_speed,
                imu=ImuState(
                    rpy=(msg.imu_state.rpy[0], msg.imu_state.rpy[1], msg.imu_state.rpy[2]),
                    quaternion=(
                        msg.imu_state.quaternion[0],
                        msg.imu_state.quaternion[1],
                        msg.imu_state.quaternion[2],
                        msg.imu_state.quaternion[3],
                    ),
                    gyroscope=(
                        msg.imu_state.gyroscope[0],
                        msg.imu_state.gyroscope[1],
                        msg.imu_state.gyroscope[2],
                    ),
                ),
                foot_force=tuple(msg.foot_force),
                error_code=msg.error_code,
            )
            with self._lock:
                self._state = state
        except Exception:
            pass  # 消息格式不匹配时忽略


# === 快速测试 ===
if __name__ == "__main__":
    adapter = UnitreeA2Adapter()
    if adapter.connect():
        print("✅ A2 连接成功")
        for i in range(5):
            time.sleep(1)
            s = adapter.get_state()
            print(f"[{s.timestamp:.1f}] mode={s.fsm_mode.name} "
                  f"pos=({s.position[0]:.2f},{s.position[1]:.2f},{s.position[2]:.2f}) "
                  f"vel=({s.velocity[0]:.2f},{s.velocity[1]:.2f},{s.velocity[2]:.2f})")
        adapter.disconnect()
    else:
        print("❌ 未收到 SportModeState 数据 — 检查 DDS 链路")
