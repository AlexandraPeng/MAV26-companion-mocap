from glob import glob
from setuptools import find_packages, setup

package_name = "uav_bringup"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", glob("launch/*")),
        ("share/" + package_name + "/config", glob("config/*")),
        ("share/" + package_name + "/rviz", glob("rviz/*")),
        ("share/" + package_name + "/scripts", glob("scripts/*")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="无人机工作区维护者",
    maintainer_email="maintainer@example.com",
    description="VRPN 到 MAVROS 的 PX4 外部视觉定位启动配置",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "pose_relay = uav_bringup.pose_relay:main",
        ],
    },
)
