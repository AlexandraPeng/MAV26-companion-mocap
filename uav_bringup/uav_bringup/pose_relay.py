import math

import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, qos_profile_sensor_data


def _normalize_quaternion(quaternion):
    norm = math.sqrt(sum(component * component for component in quaternion))
    if not math.isfinite(norm) or norm < 1e-12:
        raise ValueError("四元数长度必须大于 0")
    return tuple(component / norm for component in quaternion)


def _multiply_quaternions(left, right):
    lx, ly, lz, lw = left
    rx, ry, rz, rw = right
    return (
        lw * rx + lx * rw + ly * rz - lz * ry,
        lw * ry - lx * rz + ly * rw + lz * rx,
        lw * rz + lx * ry - ly * rx + lz * rw,
        lw * rw - lx * rx - ly * ry - lz * rz,
    )


def _rotate_vector(quaternion, vector):
    vector_quaternion = (vector[0], vector[1], vector[2], 0.0)
    inverse = (-quaternion[0], -quaternion[1], -quaternion[2], quaternion[3])
    rotated = _multiply_quaternions(
        _multiply_quaternions(quaternion, vector_quaternion), inverse
    )
    return rotated[:3]


class PoseRelay(Node):
    def __init__(self):
        super().__init__("vrpn_to_mavros_pose")
        self.declare_parameter("input_topic", "/vrpn_mocap/RigidBody/pose")
        self.declare_parameter("output_topic", "/mavros/vision_pose/pose")
        self.declare_parameter("frame_id", "world")
        self.declare_parameter("translation_x", 0.0)
        self.declare_parameter("translation_y", 0.0)
        self.declare_parameter("translation_z", 0.0)
        self.declare_parameter("world_rotation_qx", 0.0)
        self.declare_parameter("world_rotation_qy", 0.0)
        self.declare_parameter("world_rotation_qz", 0.0)
        self.declare_parameter("world_rotation_qw", 1.0)
        self.declare_parameter("body_rotation_qx", 0.0)
        self.declare_parameter("body_rotation_qy", 0.0)
        self.declare_parameter("body_rotation_qz", 0.0)
        self.declare_parameter("body_rotation_qw", 1.0)

        input_topic = self.get_parameter("input_topic").value
        output_topic = self.get_parameter("output_topic").value
        self.frame_id = self.get_parameter("frame_id").value
        self.translation = tuple(
            float(self.get_parameter(name).value)
            for name in ("translation_x", "translation_y", "translation_z")
        )
        self.world_rotation = _normalize_quaternion(
            tuple(
                float(self.get_parameter(f"world_rotation_q{axis}").value)
                for axis in ("x", "y", "z", "w")
            )
        )
        self.body_rotation = _normalize_quaternion(
            tuple(
                float(self.get_parameter(f"body_rotation_q{axis}").value)
                for axis in ("x", "y", "z", "w")
            )
        )
        if not all(math.isfinite(value) for value in self.translation):
            raise ValueError("坐标平移参数必须为有限数值")

        output_qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
        self.publisher = self.create_publisher(PoseStamped, output_topic, output_qos)
        self.subscription = self.create_subscription(
            PoseStamped, input_topic, self._forward, qos_profile_sensor_data
        )
        self._reported_first_pose = False
        self._reported_invalid_pose = False
        self.get_logger().info(f"位姿转接：{input_topic} -> {output_topic}")
        self.get_logger().info(
            f"输出坐标系={self.frame_id}, 平移={self.translation}, "
            f"世界旋转四元数={self.world_rotation}, "
            f"机体轴旋转四元数={self.body_rotation}"
        )
        if self.translation == (0.0, 0.0, 0.0) and self.world_rotation == (
            0.0,
            0.0,
            0.0,
            1.0,
        ):
            self.get_logger().warning(
                "当前世界坐标转换为单位变换；请根据动捕坐标标定设置平移和旋转参数"
            )

    def _forward(self, message):
        position = (
            message.pose.position.x,
            message.pose.position.y,
            message.pose.position.z,
        )
        orientation = (
            message.pose.orientation.x,
            message.pose.orientation.y,
            message.pose.orientation.z,
            message.pose.orientation.w,
        )
        try:
            if not all(math.isfinite(value) for value in position):
                raise ValueError("位置包含非有限值")
            source_orientation = _normalize_quaternion(orientation)
        except ValueError as error:
            if not self._reported_invalid_pose:
                self.get_logger().error(f"丢弃无效位姿：{error}")
                self._reported_invalid_pose = True
            return

        rotated_position = _rotate_vector(self.world_rotation, position)
        output_orientation = _normalize_quaternion(
            _multiply_quaternions(
                _multiply_quaternions(self.world_rotation, source_orientation),
                (
                    -self.body_rotation[0],
                    -self.body_rotation[1],
                    -self.body_rotation[2],
                    self.body_rotation[3],
                ),
            )
        )

        output = PoseStamped()
        output.header.stamp = message.header.stamp
        if output.header.stamp.sec == 0 and output.header.stamp.nanosec == 0:
            output.header.stamp = self.get_clock().now().to_msg()
        output.header.frame_id = self.frame_id
        output.pose.position.x = rotated_position[0] + self.translation[0]
        output.pose.position.y = rotated_position[1] + self.translation[1]
        output.pose.position.z = rotated_position[2] + self.translation[2]
        output.pose.orientation.x = output_orientation[0]
        output.pose.orientation.y = output_orientation[1]
        output.pose.orientation.z = output_orientation[2]
        output.pose.orientation.w = output_orientation[3]
        self.publisher.publish(output)

        if not self._reported_first_pose:
            self.get_logger().info("已收到并转发首个位姿")
            self._reported_first_pose = True


def main(args=None):
    rclpy.init(args=args)
    node = PoseRelay()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
