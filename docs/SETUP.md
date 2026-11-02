# SensorScope setup (Ubuntu 24.04 + ROS 2 Jazzy)

## 1. Install system packages

Install ROS 2 Jazzy first: https://docs.ros.org/en/jazzy/Installation.html

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip libxcb-cursor0 python3-colcon-common-extensions
```

## 2. Create a workspace and a Python environment

```bash
mkdir -p ~/sensorscope_ws/src
cd ~/sensorscope_ws
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install PySide6 pyqtgraph
```

## 3. Get the package

```bash
git clone https://github.com/ilovevampire/sensorscope.git ~/sensorscope_ws/src/sensorscope
```

## 4. Build

Use `python3 -m colcon` (not plain `colcon`) so the launcher uses the venv's Python, which has PySide6.

```bash
cd ~/sensorscope_ws
source /opt/ros/jazzy/setup.bash
python3 -m colcon build --packages-select sensorscope --symlink-install
source install/setup.bash
```

## 5. Run

In every new terminal, first activate the environment:

```bash
cd ~/sensorscope_ws
source .venv/bin/activate
source /opt/ros/jazzy/setup.bash
source install/setup.bash
```

Demo with synthetic sensors (no hardware needed):

```bash
ros2 launch sensorscope demo.launch.py
```

Your own robot:

```bash
ros2 launch sensorscope sensorscope.launch.py
```

Gazebo or a bag played with `--clock`:

```bash
ros2 launch sensorscope sensorscope.launch.py use_sim_time:=true
```

SensorScope finds `Imu`, `LaserScan`, `NavSatFix` and `Odometry` topics by itself and opens one tab per topic.

## Troubleshooting

| Problem | Fix |
|---|---|
| `Could not load the Qt platform plugin "xcb"` | `sudo apt install libxcb-cursor0`. On Wayland, also try `QT_QPA_PLATFORM=xcb` before the launch command. |
| `No module named PySide6` when launching | The build used system Python. Rebuild with the venv active: `rm -rf build/sensorscope install/sensorscope`, then repeat step 4. |
| `error: option --editable not recognized` during build | `pip install "setuptools<80"` in the venv, then rebuild. |
| Window stays on "Waiting for sensor topics" | Run `ros2 topic list -t` to check a supported type is publishing. In simulation, add `use_sim_time:=true`. |
