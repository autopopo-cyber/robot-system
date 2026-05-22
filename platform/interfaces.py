"""
platform/interfaces.py — 机器人统一抽象接口

所有机器人适配器必须实现此接口。
上层应用通过此接口操作机器人，不关心具体硬件。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
from enum import IntEnum


class FsmMode(IntEnum):
    """FSM 状态机"""
    PASSIVE = 0
    DAMP = 1
    STAND = 2
    WALK = 3
    TROT = 4
    # 5~15 其他状态


@dataclass
class ImuState:
    """IMU 姿态"""
    quaternion: tuple = (0, 0, 0, 1)
    rpy: tuple = (0, 0, 0)        # roll, pitch, yaw (rad)
    gyroscope: tuple = (0, 0, 0)  # 角速度

@dataclass
class RobotState:
    """机器人完整状态"""
    timestamp: float = 0.0
    fsm_mode: FsmMode = FsmMode.PASSIVE
    position: tuple = (0, 0, 0)    # x, y, z (m)
    velocity: tuple = (0, 0, 0)    # vx, vy, vyaw
    body_height: float = 0.0
    yaw_speed: float = 0.0
    imu: ImuState = field(default_factory=ImuState)
    foot_force: tuple = (0, 0, 0, 0)
    error_code: int = 0
    battery: Optional[float] = None

@dataclass
class JointState:
    """关节状态"""
    position: float   # rad
    velocity: float   # rad/s
    torque: float     # N·m

@dataclass
class LidarScan:
    """激光雷达扫描"""
    timestamp: float
    ranges: list      # 距离 (m)
    angles: list      # 角度 (rad)
    intensities: Optional[list] = None


class RobotAdapter(ABC):
    """机器人适配器抽象基类"""

    # === 状态读取 (只读) ===

    @abstractmethod
    def get_state(self) -> RobotState:
        """获取当前状态"""
        ...

    @abstractmethod
    def get_joint_states(self) -> dict[str, JointState]:
        """获取关节状态"""
        ...

    @abstractmethod
    def is_connected(self) -> bool:
        """是否连接"""
        ...

    # === 传感器 ===

    def get_lidar_scan(self) -> Optional[LidarScan]:
        """获取激光雷达扫描 (可选实现)"""
        return None

    def get_camera_image(self) -> Optional[bytes]:
        """获取相机图像 (可选实现)"""
        return None

    # === 生命周期 ===

    @abstractmethod
    def connect(self) -> bool:
        """建立连接"""
        ...

    @abstractmethod
    def disconnect(self):
        """断开连接"""
        ...


class PayloadAdapter(ABC):
    """上装设备适配器基类 (机械臂/传感器等)"""

    @abstractmethod
    def initialize(self) -> bool: ...
    @abstractmethod
    def is_ready(self) -> bool: ...
    @abstractmethod
    def shutdown(self): ...
