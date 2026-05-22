#!/usr/bin/env python3
"""探索狗平台 — 一期: 遥控 + 数据收集"""

from setuptools import setup

package_name = 'exploration'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    entry_points={
        'console_scripts': [
            'rc_bridge = exploration.rc_bridge:main',
            'data_logger = exploration.data_logger:main',
        ],
    },
)
