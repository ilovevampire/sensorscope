# Using the Analysis tabs

Every IMU, LiDAR and GPS tab has a **Live | Analysis** switch. Live shows scrolling plots. Analysis
records a long, still capture and turns it into numbers you can put into a config file.

```
Start capture  ->  leave the sensor still  ->  Stop capture (analyses automatically)
                                                or "Analyze now" for a preview while recording
```

Try it with no hardware: `ros2 launch sensorscope demo.launch.py static:=true`.
The fake sensors print the noise values they inject, so you can check the results
(see the docstring of `sensorscope/tools/fake_sensors.py`).

## IMU

| You see | Meaning |
|---|---|
| Allan deviation plot, slope −1/2 at short τ | white noise. The value at τ = 1 s is the **noise density N** |
| Flat bottom of the curve | **bias instability B**, the best stability you can get by averaging |
| Curve rising with slope +1/2 at long τ | **rate random walk K** (the bias wanders) |
| Dashed lines | the fitted model N/√τ + B + K√(τ/3) |
| Gyro mean (bias) | constant offset to subtract; check it is small |
| Mean |a| vs 1 g | accelerometer scale and static check (within about 1 %) |

How long to capture: **10 minutes** gives N. **1–3 hours** reveals B. The tab warns when the
curve is still falling, which means you stopped too early.

Buttons: **Copy Kalibr YAML** (`gyroscope_noise_density`, `..._random_walk`, ...) and
**Copy Gazebo noise** (`<noise type="gaussian">` blocks, stddev = N·√rate).

## LiDAR

Aim at a static scene with a flat wall. SensorScope finds the nearest wall, fits a line, and reports:

- **Typical range noise**: std of each beam's range over time. Compare with the datasheet.
- **Wall noise**: spread of points around the fitted wall, over all scans.
- **Wall flatness**: rms of the *mean* scan around the line (geometry or calibration error).
- **Valid returns per beam**: dark, glossy or blocked directions show up as dips.

Set the sector by hand (untick *Auto wall sector*) to look at a different wall.

## GPS

Fix the antenna with a clear sky view, capture 10+ minutes.

- **CEP50 / CEP95**: radius containing 50 % / 95 % of fixes around their mean.
- **Measured vs reported std**: if the measured value is much larger, the driver's covariance is
  optimistic. Use the measured value (or larger) as your EKF's GPS measurement noise.
- **Error correlation time**: GPS errors are not white. If it is several seconds, an EKF that
  trusts every fix equally becomes overconfident. Inflate R or fuse fewer fixes.
- **Drift**: slow wander of the mean position in m/min.

## Timing (all sensors)

Compared on two clocks: when the message was received and the header stamp.
Header-stamp jitter is the sensor/driver's own regularity. Receive jitter also includes network and
scheduling delay. Latency (receive − stamp) is only meaningful when clocks are synchronised.
Dropped samples are estimated from gaps larger than 1.5 × the median interval.

## Offline report from a rosbag2

```bash
ros2 bag record /imu/data /scan /gps/fix /odom        # keep the sensors still for the analysis
ros2 run sensorscope report my_bag -o report.html
```

The report uses exactly the same analyzers, with figures embedded in one HTML file. It needs
`matplotlib` (`sudo apt install python3-matplotlib`). Options: `--topic /imu/data` (repeatable),
`--title "My robot, 2026-10-31"`.
