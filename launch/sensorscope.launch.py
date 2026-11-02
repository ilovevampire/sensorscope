from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("use_sim_time", default_value="false",
                              description="Use /clock (set true with Gazebo or bag --clock)"),
        DeclareLaunchArgument("buffer_size", default_value="20000",
                              description="Samples kept per channel"),
        Node(
            package="sensorscope",
            executable="sensorscope",
            name="sensorscope",
            output="screen",
            parameters=[{
                "use_sim_time": LaunchConfiguration("use_sim_time"),
                "buffer_size": LaunchConfiguration("buffer_size"),
            }],
        ),
    ])
