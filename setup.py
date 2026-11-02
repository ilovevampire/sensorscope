from glob import glob

from setuptools import find_packages, setup

package_name = "sensorscope"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", glob("launch/*.launch.py")),
        ("share/" + package_name + "/config", glob("config/*.yaml")),
    ],
    install_requires=["setuptools", "numpy"],
    zip_safe=True,
    maintainer="Vishal Gaud",
    maintainer_email="uselessm61@gmail.com",
    description="Live visualisation and analysis of ROS 2 sensor data (IMU, LiDAR, GPS, odometry).",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "sensorscope = sensorscope.main:main",
            "fake_sensors = sensorscope.tools.fake_sensors:main",
        ],
    },
)
