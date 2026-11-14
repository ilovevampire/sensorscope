# SensorScope

[![tests](https://github.com/ilovevampire/sensorscope/actions/workflows/ci.yml/badge.svg)](https://github.com/ilovevampire/sensorscope/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

Live visualisation and analysis of ROS 2 sensor data. SensorScope auto-discovers IMU, LiDAR, GPS and
odometry topics, shows them live with statistics, and analyses timed captures to give you real
numbers for tuning sensors and filters.

- **Author / maintainer:** Vishal Gaud ([@ilovevampire](https://github.com/ilovevampire))
- **Version:** 0.2.0
- **ROS distribution:** Jazzy (Ubuntu 24.04)
- **License:** Apache-2.0

## Features

| Sensor | Message type | Live view | Analysis tab |
|---|---|---|---|
| IMU | `sensor_msgs/msg/Imu` | acceleration, gyro, orientation | Allan deviation, noise density N, bias instability B, random walk K, PSD, Kalibr/Gazebo export |
| LiDAR | `sensor_msgs/msg/LaserScan` | range statistics, top-down scan | per-beam noise, dropout map, static-wall fit |
| GPS | `sensor_msgs/msg/NavSatFix` | local position, accuracy, fix status, track | CEP50/95, RMS, drift, measured vs reported covariance, error correlation time |
| Odometry | `nav_msgs/msg/Odometry` | position, yaw, velocities, track | none yet |

Every sensor also gets header-stamp timing (jitter, latency, dropped samples) and CSV export.
Recorded bags can be analysed offline with the `report` executable.

## Installation

See [docs/SETUP.md](docs/SETUP.md). In short:

```bash
git clone https://github.com/ilovevampire/sensorscope.git ~/sensorscope_ws/src/sensorscope
pip install PySide6 pyqtgraph        # GUI dependencies, inside a venv (see SETUP.md)
cd ~/sensorscope_ws && python3 -m colcon build --packages-select sensorscope --symlink-install
```

## Usage

```bash
ros2 launch sensorscope sensorscope.launch.py          # your robot
ros2 launch sensorscope demo.launch.py static:=true    # fake sensors, no hardware needed
```

Open **Help > Quick start** (F1) in the app, and read [docs/ANALYSIS.md](docs/ANALYSIS.md) to learn
how to read the analysis results.

## Executables

### `sensorscope` (node name: `sensorscope`)

Opens the GUI. Subscribes automatically to every topic of a supported type, including topics that
appear later. QoS: `sensor_data` (best effort), which connects to both reliable and best-effort publishers.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `buffer_size` | int | `20000` | samples kept per channel for the live plots |
| `discovery_period_s` | double | `2.0` | how often to look for new sensor topics |
| `use_sim_time` | bool | `false` | follow `/clock` (Gazebo, `ros2 bag play --clock`) |

### `fake_sensors` (node name: `fake_sensors`)

Synthetic sensors with documented, injected noise (see the file's docstring) for trying and testing.

| Published topic | Type | Rate |
|---|---|---|
| `/imu/data` | `sensor_msgs/msg/Imu` | 100 Hz |
| `/scan` | `sensor_msgs/msg/LaserScan` | 10 Hz |
| `/gps/fix` | `sensor_msgs/msg/NavSatFix` | 5 Hz |
| `/odom` | `nav_msgs/msg/Odometry` | 30 Hz |

| Parameter | Type | Default | Description |
|---|---|---|---|
| `static` | bool | `false` | publish still sensors (needed for meaningful Analysis) |

### `report`

```bash
ros2 run sensorscope report my_bag -o report.html [--topic /imu/data] [--title "My robot"]
```

Writes one self-contained HTML report from a rosbag2. Needs `matplotlib`.

## Launch files

| File | Arguments | Description |
|---|---|---|
| `sensorscope.launch.py` | `use_sim_time` (false), `buffer_size` (20000) | start the GUI |
| `demo.launch.py` | `static` (false) | start `fake_sensors` and the GUI |

## Package layout

```
sensorscope/
  core/      ring buffers, capture, timing, stats (numpy only)
  analysis/  Allan, spectrum, IMU / LiDAR / GPS analyzers, exports (numpy only)
  sensors/   one small plugin file per message type
  ros/       topic discovery, node, background spin thread
  ui/        PySide6 + pyqtgraph window, live tabs, analysis tabs, help dialogs
  report/    rosbag2 reader and HTML report builder
  tools/     fake_sensors
```

## Development

```bash
python -m pytest test -q
```

`core/` and `analysis/` never import ROS or Qt, and are tested against synthetic data with known
ground truth. See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add a sensor.

## Roadmap

- [x] Live viewer, statistics, auto-discovery
- [x] IMU / LiDAR / GPS analysis, timing, tuning export, rosbag2 report, Help menu
- [ ] EKF tools: innovation, NIS consistency, covariance trace, raw vs filtered, Q/R hints
- [ ] Docs site, Docker image, Gazebo demo, ROS CI, ROS Index release
- [ ] More sensors: camera, depth, encoders, battery

## Support and contributing

- Bugs and ideas: https://github.com/ilovevampire/sensorscope/issues
- [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), [CHANGELOG.rst](CHANGELOG.rst)

## License

Apache License 2.0, see [LICENSE](LICENSE). Copyright 2026 Vishal Gaud.
