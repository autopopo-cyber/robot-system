#!/usr/bin/env python3
"""数据记录器: 订阅LowState → 写CSV"""
import rclpy
from rclpy.node import Node
from unitree_hg.msg import LowState
import csv
import os
from datetime import datetime


class DataLogger(Node):
    def __init__(self, output_dir="/tmp/exploration_data",
                 enable_camera=False, enable_lidar=False):
        super().__init__('data_logger')
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # --- LowState CSV ---
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.csv_path = os.path.join(output_dir, f"state_{timestamp}.csv")
        self.csv_file = open(self.csv_path, 'w', newline='')
        self.writer = csv.writer(self.csv_file)
        self.writer.writerow([
            'tick', 'timestamp_ns',
            'roll', 'pitch', 'yaw',
            'gyro_x', 'gyro_y', 'gyro_z',
            'acc_x', 'acc_y', 'acc_z',
        ])
        self.sub = self.create_subscription(
            LowState, '/lf/lowstate', self.callback, 10
        )

        # --- 摄像头 (等USB摄像头就绪后取消注释) ---
        self.enable_camera = enable_camera
        if enable_camera:
            self.img_dir = os.path.join(output_dir, 'images')
            os.makedirs(self.img_dir, exist_ok=True)
            # from sensor_msgs.msg import Image
            # self.create_subscription(Image, '/usb_cam/image_raw', self.image_cb, 10)

        # --- LiDAR点云 (等OTA后就绪后取消注释) ---
        self.enable_lidar = enable_lidar
        if enable_lidar:
            self.lidar_dir = os.path.join(output_dir, 'lidar')
            os.makedirs(self.lidar_dir, exist_ok=True)
            # from sensor_msgs.msg import PointCloud2
            # self.create_subscription(PointCloud2, '/utlidar/cloud', self.lidar_cb, 10)

        self.get_logger().info(
            f'DataLogger ready → {self.csv_path} '
            f'(camera={enable_camera}, lidar={enable_lidar})'
        )

    def callback(self, msg: LowState):
        imu = msg.imu_state
        self.writer.writerow([
            msg.tick,
            self.get_clock().now().nanoseconds,
            imu.rpy[0], imu.rpy[1], imu.rpy[2],
            imu.gyroscope[0], imu.gyroscope[1], imu.gyroscope[2],
            imu.accelerometer[0], imu.accelerometer[1], imu.accelerometer[2],
        ])
        self.csv_file.flush()

    def destroy_node(self):
        self.csv_file.close()
        super().destroy_node()


def main():
    rclpy.init()
    node = DataLogger()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
