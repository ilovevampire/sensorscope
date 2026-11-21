^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Changelog for package sensorscope
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

0.2.0 (2026-11-03)
------------------
* Live viewer: auto-discovery of Imu, LaserScan, NavSatFix and Odometry topics, scrolling
  plots, per-channel statistics, rate/jitter/stale-topic indicators, LiDAR scan view,
  GPS/odometry track view, CSV export.
* Analysis tabs (IMU, LiDAR, GPS): timed captures analysed on a background thread.

  * IMU: Allan deviation, noise density, bias instability, random walk, PSD, histogram,
    gravity check, Kalibr YAML and Gazebo noise export.
  * LiDAR: per-beam noise, dropout map, static-wall fit and residuals.
  * GPS: CEP50/CEP95, RMS, drift, measured-versus-reported covariance, error correlation time.

* Header-stamp timing for every sensor: stamp jitter, latency, dropped-sample estimate.
* ``report`` executable: HTML report from a rosbag2 using the same analyzers.
* ``fake_sensors`` demo publisher with a ``static`` mode and documented injected noise.
* Help menu: quick start, About (version, author, links, licences), GitHub and issue links.
* Contributors: Vishal Gaud
