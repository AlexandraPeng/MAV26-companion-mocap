# PX4 外部视觉定位：安装与启动

本仓库提供 ROS 2 Jazzy bringup 包，在树莓派上运行 VRPN 客户端和 MAVROS，将动捕位姿送入 PX4 外部视觉输入；地面站通过 ROS 2 DDS 查看话题并用 RViz 显示。启动流程不会解锁、切换模式或起飞。

## 设备与连接

- 树莓派：Ubuntu 24.04、ARM64、ROS 2 Jazzy。
- 地面站：Ubuntu 24.04、ROS 2 Jazzy、RViz 2。
- 动捕 VRPN 服务：默认地址 `192.168.183.29:3883`，按现场网络修改。
- PX4 飞控串口连接树莓派 40 针排针 GPIO Pin 8/10，设备路径使用 `/dev/ttyAMA0`。Pin 8（TX）接飞控 RX，Pin 10（RX）接飞控 TX，并连接 GND；PX4 对应端口须启用 MAVLink，串口波特率须与启动参数一致。
- 两台 ROS 2 主机需设置相同的 `ROS_DOMAIN_ID`；默认使用 `0`。

## 安装依赖

在树莓派安装 ROS 2、MAVROS 和 VRPN 客户端：

```bash
sudo apt update
sudo apt install ros-jazzy-ros-base ros-jazzy-mavros ros-jazzy-mavros-extras ros-jazzy-vrpn-mocap
```

在地面站安装 ROS 2 桌面版和 RViz：

```bash
sudo apt update
sudo apt install ros-jazzy-desktop ros-jazzy-rviz2
```

## 获取并构建

将仓库放到两台主机的 `~/uav_ws/src/uav_bringup`，分别在每台主机执行：

```bash
source /opt/ros/jazzy/setup.bash
mkdir -p ~/uav_ws/src
cd ~/uav_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
```

## 启动

先在地面站启动 RViz：

```bash
cd ~/uav_ws
ROS_DOMAIN_ID=0 bash src/uav_bringup/scripts/start_groundstation_rviz.sh
```

再在树莓派启动 VRPN 与 MAVROS。将 `现场刚体名` 替换为 VRPN 服务中实际发布的刚体名；如果 PX4 端口使用其他波特率，修改 `SERIAL_BAUD`：

```bash
cd ~/uav_ws
VRPN_HOST=192.168.183.29 \
VRPN_PORT=3883 \
RIGID_BODY=现场刚体名 \
SERIAL_DEVICE=/dev/ttyAMA0 \
SERIAL_BAUD=115200 \
ROS_DOMAIN_ID=0 \
bash src/uav_bringup/scripts/start_pi.sh
```

启动程序会检查串口存在且当前用户具有写权限。若权限不足，将用户加入 `dialout` 组并重新登录：

```bash
sudo usermod -aG dialout "$USER"
```

MAVROS 使用 PX4 插件列表与配置，并加载本仓库的坐标系设置。VRPN 位姿话题 `/vrpn_mocap/<刚体名>/pose` 会重映射为 MAVROS 的 `/mavros/vision_pose/pose` 输入；默认坐标系为 `world`，ROS 接收时间作为位姿时间戳。

## 验证

在树莓派或地面站打开新终端并加载环境：

```bash
source /opt/ros/jazzy/setup.bash
source ~/uav_ws/install/setup.bash
```

检查 VRPN 位姿频率、MAVROS 飞控连接状态和 PX4 位置输出：

```bash
ros2 topic hz /vrpn_mocap/现场刚体名/pose
ros2 topic echo /mavros/state
ros2 topic echo /mavros/local_position/pose
ros2 run tf2_ros tf2_echo world base_link
```

`/mavros/state` 中 `connected` 应为 `true`。若为 `false`，检查 PX4 对应串口是否启用 MAVLink、TX/RX 是否交叉、是否共地、设备路径和波特率是否匹配，以及串口是否被其他进程占用。若 VRPN 话题无数据，检查服务地址、端口和刚体名。两台主机无法互相发现话题时，检查 `ROS_DOMAIN_ID` 和网络 DDS 通信。

RViz 的 Pose 显示订阅 `/mavros/local_position/pose`，固定坐标系为 `world`。实机测试前需先确认坐标轴约定、位姿频率与失联行为，以及急停和遥控接管有效；本配置不会发送 Offboard 设定点或执行飞行动作。
