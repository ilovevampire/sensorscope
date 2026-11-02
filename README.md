# SensorScope

Live visualisation and analysis of ROS 2 sensor data: IMU, LiDAR, GPS and odometry
(more to come), with graphs **and** numbers, in one window, with zero configuration.

```bash
ros2 launch sensorscope sensorscope.launch.py
```

It auto-discovers supported topics and opens one tab per sensor. See [docs/SETUP.md](docs/SETUP.md)
for installation (Ubuntu 24.04, ROS 2 Jazzy).

## Phase 1 features

- Auto-discovery of `sensor_msgs/Imu`, `LaserScan`, `NavSatFix` and `nav_msgs/Odometry` topics
- Live scrolling plots with a selectable time window (1 to 120 s), pause, clear
- Numeric stats per channel over the visible window: last, mean, std, min, max, RMS
- Message rate, jitter and a "NO DATA" warning per topic
- LiDAR top-down scan view, GPS and odometry track view (GPS shown in local metres from the first fix)
- Export the buffered data to CSV
- `fake_sensors` node: try everything without hardware (`ros2 launch sensorscope demo.launch.py`)

## Layout

```
sensorscope/
  core/      pure numpy: ring buffers, rate and stats, SensorStream (no ROS, no Qt)
  sensors/   one small plugin file per message type (extractor + plot layout)
  ros/       topic discovery, node, background spin thread
  ui/        PySide6 + pyqtgraph window, tabs and plots (depends on core only)
  tools/     fake_sensors demo publisher
```

## Adding a sensor (3 steps)

1. Create `sensorscope/sensors/my_sensor.py` with an extractor
   (`msg -> ({channel: value}, optional_extra)`) and a `SensorSpec` listing which channels go in which plot.
2. Call `register(spec)` in that file.
3. Import the module in `sensorscope/sensors/__init__.py`.

Extractors only read message attributes, so you can unit-test them with plain objects (see `test/test_sensors.py`).

## License

Apache-2.0
