import os
import re
import tempfile

import yaml

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, RegisterEventHandler, SetEnvironmentVariable
from launch.event_handlers import OnShutdown
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _setup(context):
    vrpn_host = LaunchConfiguration("vrpn_host").perform(context)
    vrpn_port = int(LaunchConfiguration("vrpn_port").perform(context))
    rigid_body = LaunchConfiguration("rigid_body").perform(context).strip()
    serial_device = LaunchConfiguration("serial_device").perform(context)
    serial_baud = LaunchConfiguration("serial_baud").perform(context).strip()
    domain_id = int(LaunchConfiguration("ros_domain_id").perform(context))
    frame_id = LaunchConfiguration("frame_id").perform(context)
    child_frame_id = LaunchConfiguration("child_frame_id").perform(context)
    vrpn_pose_topic = LaunchConfiguration("vrpn_pose_topic").perform(context).strip()
    mavros_vision_topic = LaunchConfiguration("mavros_vision_topic").perform(context).strip()
    transform_parameters = {
        name: float(LaunchConfiguration(name).perform(context))
        for name in (
            "translation_x",
            "translation_y",
            "translation_z",
            "world_rotation_qx",
            "world_rotation_qy",
            "world_rotation_qz",
            "world_rotation_qw",
            "body_rotation_qx",
            "body_rotation_qy",
            "body_rotation_qz",
            "body_rotation_qw",
        )
    }

    if not rigid_body or "/" in rigid_body:
        raise RuntimeError("rigid_body 必须是非空的单个 VRPN 刚体名")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", rigid_body):
        raise RuntimeError("rigid_body 必须使用 ROS 话题兼容的字母、数字和下划线")
    if not 1 <= vrpn_port <= 65535:
        raise RuntimeError("vrpn_port 必须在 1 到 65535 之间")
    if not serial_baud.isdigit() or int(serial_baud) <= 0:
        raise RuntimeError("请明确指定串口波特率，例如 serial_baud:=921600")
    if not 0 <= domain_id <= 232:
        raise RuntimeError("ros_domain_id 必须在 0 到 232 之间")
    if not serial_device.startswith("/dev/"):
        raise RuntimeError("serial_device 必须是树莓派上的 /dev/ 设备路径")
    if not __import__("os").path.exists(serial_device):
        raise RuntimeError(f"找不到 PX4 串口设备：{serial_device}")
    if not __import__("os").access(serial_device, __import__("os").W_OK):
        raise RuntimeError(f"当前用户没有串口写权限：{serial_device}（检查 dialout 组）")

    package_share = get_package_share_directory("uav_bringup")
    mavros_share = get_package_share_directory("mavros")
    if not vrpn_pose_topic:
        vrpn_pose_topic = f"/vrpn_mocap/{rigid_body}/pose"
    if not vrpn_pose_topic.startswith("/") or not mavros_vision_topic.startswith("/"):
        raise RuntimeError("位姿话题必须使用绝对话题名（以 / 开头）")

    with open(f"{mavros_share}/launch/px4_config.yaml", encoding="utf-8") as stream:
        mavros_config = yaml.safe_load(stream)
    with open(f"{package_share}/config/mavros_frames.yaml", encoding="utf-8") as stream:
        frame_overlay = yaml.safe_load(stream)
    for plugin_name, plugin_config in frame_overlay.items():
        mavros_config[plugin_name]["ros__parameters"].update(
            plugin_config["ros__parameters"]
        )
    mavros_config["/**/local_position"]["ros__parameters"].update(
        {
            "frame_id": frame_id,
            "tf.send": True,
            "tf.frame_id": frame_id,
            "tf.child_frame_id": child_frame_id,
        }
    )
    mavros_config["/**/vision_pose"]["ros__parameters"].update(
        {
            "tf.frame_id": frame_id,
            "tf.child_frame_id": "vision_estimate",
            "tf.rate_limit": 100.0,
        }
    )
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".yaml", delete=False
    ) as stream:
        yaml.safe_dump(mavros_config, stream, sort_keys=False)
        merged_config_path = stream.name

    def _remove_merged_config(_context):
        try:
            os.unlink(merged_config_path)
        except FileNotFoundError:
            pass
        return []

    return [
        Node(
            package="vrpn_mocap",
            executable="client_node",
            namespace="vrpn_mocap",
            name="vrpn_mocap_client_node",
            parameters=[
                {
                    "server": vrpn_host,
                    "port": vrpn_port,
                    "frame_id": frame_id,
                    "update_freq": 100.0,
                    "refresh_freq": 1.0,
                    "multi_sensor": False,
                    "use_vrpn_timestamps": False,
                }
            ],
            output="screen",
        ),
        Node(
            package="mavros",
            executable="mavros_node",
            name="mavros",
            parameters=[
                f"{mavros_share}/launch/px4_pluginlists.yaml",
                merged_config_path,
                {
                    "fcu_url": f"{serial_device}:{serial_baud}",
                    "gcs_url": "",
                    "tgt_system": 1,
                    "tgt_component": 1,
                    "fcu_protocol": "v2.0",
                },
            ],
            output="screen",
        ),
        Node(
            package="uav_bringup",
            executable="pose_relay",
            name="vrpn_to_mavros_pose",
            parameters=[
                {
                    "input_topic": vrpn_pose_topic,
                    "output_topic": mavros_vision_topic,
                    "frame_id": frame_id,
                    **transform_parameters,
                }
            ],
            output="screen",
        ),
        RegisterEventHandler(
            OnShutdown(on_shutdown=[OpaqueFunction(function=_remove_merged_config)])
        ),
    ]


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("vrpn_host", default_value="192.168.183.29"),
            DeclareLaunchArgument("vrpn_port", default_value="3883"),
            DeclareLaunchArgument("rigid_body", default_value="RigidBody"),
            DeclareLaunchArgument("serial_device", default_value="/dev/ttyAMA0"),
            DeclareLaunchArgument("serial_baud", default_value="115200"),
            DeclareLaunchArgument("ros_domain_id", default_value="0"),
            DeclareLaunchArgument("frame_id", default_value="world"),
            DeclareLaunchArgument("child_frame_id", default_value="base_link"),
            DeclareLaunchArgument("vrpn_pose_topic", default_value=""),
            DeclareLaunchArgument(
                "mavros_vision_topic", default_value="/mavros/vision_pose/pose"
            ),
            DeclareLaunchArgument("translation_x", default_value="0.0"),
            DeclareLaunchArgument("translation_y", default_value="0.0"),
            DeclareLaunchArgument("translation_z", default_value="0.0"),
            DeclareLaunchArgument("world_rotation_qx", default_value="0.5"),
            DeclareLaunchArgument("world_rotation_qy", default_value="0.5"),
            DeclareLaunchArgument("world_rotation_qz", default_value="0.5"),
            DeclareLaunchArgument("world_rotation_qw", default_value="0.5"),
            DeclareLaunchArgument("body_rotation_qx", default_value="0.0"),
            DeclareLaunchArgument("body_rotation_qy", default_value="0.0"),
            DeclareLaunchArgument("body_rotation_qz", default_value="0.0"),
            DeclareLaunchArgument("body_rotation_qw", default_value="1.0"),
            SetEnvironmentVariable("ROS_DOMAIN_ID", LaunchConfiguration("ros_domain_id")),
            OpaqueFunction(function=_setup),
        ]
    )
