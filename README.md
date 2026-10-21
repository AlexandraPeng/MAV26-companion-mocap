# PX4 外部视觉定位：安装与启动

本仓库提供 ROS 2 Jazzy bringup 包，在树莓派上运行 VRPN 客户端和 MAVROS，并将动捕位姿转接到 PX4 外部视觉输入；地面站通过 ROS 2 DDS 订阅树莓派上的 MAVROS 话题。启动流程不会解锁、切换模式或起飞。

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

先在地面站启动 ROS 2 环境（当前暂不启动 RViz）：

```bash
cd ~/uav_ws
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=0
```

再在树莓派启动 VRPN、MAVROS 和位姿转接。刚体名可通过 `RIGID_BODY` 设置，串口波特率为 `115200`：

```bash
cd ~/uav_ws
VRPN_HOST=192.168.183.29 \
VRPN_PORT=3883 \
RIGID_BODY=RigidBody \
SERIAL_DEVICE=/dev/ttyAMA0 \
SERIAL_BAUD=115200 \
ROS_DOMAIN_ID=0 \
bash src/uav_bringup/scripts/start_pi.sh
```

启动程序会检查串口存在且当前用户具有写权限。若权限不足，将用户加入 `dialout` 组并重新登录：

```bash
sudo usermod -aG dialout "$USER"
```

MAVROS 使用 PX4 插件列表与配置，并加载本仓库的坐标系设置。树莓派上的 `pose_relay` 以 best-effort 兼容 QoS 订阅 `/vrpn_mocap/<刚体名>/pose`，再以 reliable QoS 发布到 `/mavros/vision_pose/pose`。它对位置应用世界系四元数旋转和平移，并对姿态应用世界系旋转和机体系旋转。按 NOKOV X=北、Y=天（上）、Z=东配置时，默认世界旋转四元数为 `(0.5, 0.5, 0.5, 0.5)`，将 NOKOV 北天东转换到 MAVROS 所需的 ROS ENU；MAVROS 再负责转换到 PX4 NED。平移默认零。启动脚本用 `POSE_WORLD_QX/QY/QZ/QW` 和 `POSE_TRANSLATION_X/Y/Z` 覆盖世界系变换，用 `POSE_BODY_QX/QY/QZ/QW` 设置机体系旋转；四元数顺序为 x、y、z、w，平移单位为米。当前默认不改变刚体自身轴向，若 NOKOV 刚体坐标与 ROS `base_link` 不一致，还需标定机体系旋转。输入时间戳会保留，只有零时间戳才补当前 ROS 时间。日志会在首个位姿成功转发后报告。

地面站要订阅树莓派的话题，需两台主机的 ROS 2 DDS 网络发现正常且 `ROS_DOMAIN_ID` 相同。地面站 source ROS 环境后可直接检查：

```bash
ros2 topic list
ros2 topic echo /mavros/state
ros2 topic echo /mavros/local_position/pose
```

本机 relay 不会代替 DDS 跨机传输。如果地面站看不到 `/mavros/*`，先检查两机网络和 DDS 发现；`ros2 topic relay` 也要求运行 relay 的主机能同时发现源和目标节点。

MAVROS 的 `VER: unicast request timeout` 表示飞控版本请求超时；`TM: RTT too high for timesync` 表示该串口往返时间样本过高，时间同步未采用该样本。这些告警本身不表示 DDS 局域网故障。截图中 MAVROS 仍收到飞控事件和任务消息，说明串口链路至少存在双向通信。若持续出现，检查 PX4 串口的 MAVLink 实例、波特率和串口负载；它们与 relay 是否收到 VRPN 位姿需分别检查。

## 验证

在树莓派或地面站打开新终端并加载环境：

```bash
source /opt/ros/jazzy/setup.bash
source ~/uav_ws/install/setup.bash
```

检查 VRPN 位姿频率、MAVROS 飞控连接状态和 PX4 位置输出：

```bash
ros2 topic hz /vrpn_mocap/RigidBody/pose
ros2 topic hz /mavros/vision_pose/pose
ros2 topic echo /mavros/state
ros2 topic echo /mavros/local_position/pose
ros2 run tf2_ros tf2_echo world base_link
```

`/mavros/state` 中 `connected` 应为 `true`。若为 `false`，检查 PX4 对应串口是否启用 MAVLink、TX/RX 是否交叉、是否共地、设备路径和波特率是否匹配，以及串口是否被其他进程占用。若 VRPN 话题无数据，检查服务地址、端口和刚体名。两台主机无法互相发现话题时，检查 `ROS_DOMAIN_ID` 和网络 DDS 通信。

实机测试前需先确认坐标轴约定、位姿频率与失联行为，以及急停和遥控接管有效；本配置不会发送 Offboard 设定点或执行飞行动作。
