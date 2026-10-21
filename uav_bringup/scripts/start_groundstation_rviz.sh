#!/usr/bin/env bash
set -eo pipefail

source /opt/ros/jazzy/setup.bash
source "${UAV_WS:-$HOME/uav_ws}/install/setup.bash"
set -u

export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-0}"
export RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-rmw_fastrtps_cpp}"

exec rviz2 -d "$(ros2 pkg prefix uav_bringup)/share/uav_bringup/rviz/uav.rviz"
