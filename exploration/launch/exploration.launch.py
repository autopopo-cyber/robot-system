"""探索狗一期 — 一键启动 rc_bridge + data_logger"""
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='exploration',
            executable='rc_bridge',
            name='rc_bridge',
            output='screen',
        ),
        Node(
            package='exploration',
            executable='data_logger',
            name='data_logger',
            output='screen',
            parameters=[{'output_dir': '/home/unitree/exploration_data'}],
        ),
    ])
