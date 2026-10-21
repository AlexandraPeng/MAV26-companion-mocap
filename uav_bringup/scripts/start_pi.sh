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
  child_frame_id:="${BODY_FRAME:-base_link}"
