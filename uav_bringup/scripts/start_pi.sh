#!/usr/bin/env bash
set -eo pipefail

source /opt/ros/jazzy/setup.bash
source "${UAV_WS:-$HOME/uav_ws}/install/setup.bash"
set -u

export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-0}"
export RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-rmw_fastrtps_cpp}"

exec ros2 launch uav_bringup fleet_bringup.launch.py \
  vrpn_host:="${VRPN_HOST:-192.168.183.29}" \
  vrpn_port:="${VRPN_PORT:-3883}" \
  rigid_body:="${RIGID_BODY:-RigidBody}" \
  serial_device:="${SERIAL_DEVICE:-/dev/ttyAMA0}" \
  serial_baud:="${SERIAL_BAUD:-115200}" \
  ros_domain_id:="$ROS_DOMAIN_ID" \
  frame_id:="${WORLD_FRAME:-world}" \
  child_frame_id:="${BODY_FRAME:-base_link}" \
  vrpn_pose_topic:="${VRPN_POSE_TOPIC:-}" \
  mavros_vision_topic:="${MAVROS_VISION_TOPIC:-/mavros/vision_pose/pose}" \
  translation_x:="${POSE_TRANSLATION_X:-0.0}" \
  translation_y:="${POSE_TRANSLATION_Y:-0.0}" \
  translation_z:="${POSE_TRANSLATION_Z:-0.0}" \
  world_rotation_qx:="${POSE_WORLD_QX:-0.5}" \
  world_rotation_qy:="${POSE_WORLD_QY:-0.5}" \
  world_rotation_qz:="${POSE_WORLD_QZ:-0.5}" \
  world_rotation_qw:="${POSE_WORLD_QW:-0.5}" \
  body_rotation_qx:="${POSE_BODY_QX:-0.0}" \
  body_rotation_qy:="${POSE_BODY_QY:-0.0}" \
  body_rotation_qz:="${POSE_BODY_QZ:-0.0}" \
  body_rotation_qw:="${POSE_BODY_QW:-1.0}"
