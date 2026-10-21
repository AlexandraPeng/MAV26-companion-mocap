import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.node import Node


class PoseRelay(Node):
    def __init__(self):
        super().__init__("vrpn_to_mavros_pose")
        self.declare_parameter("input_topic", "/vrpn_mocap/RigidBody/pose")
        self.declare_parameter("output_topic", "/mavros/vision_pose/pose")
        self.declare_parameter("frame_id", "world")

        input_topic = self.get_parameter("input_topic").value
        output_topic = self.get_parameter("output_topic").value
        self.frame_id = self.get_parameter("frame_id").value
        self.publisher = self.create_publisher(PoseStamped, output_topic, 10)
        self.subscription = self.create_subscription(
            PoseStamped, input_topic, self._forward, 10
        )
        self.get_logger().info(f"转发位姿：{input_topic} -> {output_topic}")

    def _forward(self, message):
        if not message.header.frame_id:
            message.header.frame_id = self.frame_id
        if message.header.stamp.sec == 0 and message.header.stamp.nanosec == 0:
            message.header.stamp = self.get_clock().now().to_msg()
        self.publisher.publish(message)


def main(args=None):
    rclpy.init(args=args)
    node = PoseRelay()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
