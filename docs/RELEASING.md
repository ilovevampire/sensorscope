# Releasing SensorScope

How to publish a new version, and what is needed before the package can appear on the
[ROS Index](https://index.ros.org).

## Every release

1. `python -m pytest test -q` passes.
2. Pick the new `X.Y.Z` and set it in **all three** places (a test checks they agree):
   `package.xml`, `setup.py`, `sensorscope/__init__.py`.
3. Add a section to `CHANGELOG.rst` (`X.Y.Z (YYYY-MM-DD)`, bullet list, `Contributors:` line).
4. Commit, then tag with the plain version number, which is what `bloom` expects by default:
   ```bash
   git tag -a X.Y.Z -m "SensorScope X.Y.Z"
   git push origin main --tags
   ```
5. Create a GitHub release from that tag and paste the changelog section.

## Getting onto the ROS Index (one-time setup)

The index lists packages that are released into a ROS distribution with
[bloom](https://docs.ros.org/en/jazzy/How-To-Guides/Releasing/Releasing-a-Package.html).

1. Every `package.xml` dependency must resolve through `rosdep`. **Open item:** the GUI needs PySide6 and
   pyqtgraph, installed with pip today and not listed in `package.xml`. Before a binary release, either
   find or add rosdep keys for them (a pull request to `ros/rosdistro`), or switch the GUI to a Qt binding
   that rosdep already provides.
2. Run the ROS linters on a machine with ROS installed: `colcon test --packages-select sensorscope`
   then `colcon test-result --verbose`. Fix anything `ament_flake8`, `ament_pep257` or `ament_copyright` report.
3. Create an empty release repository, e.g. `ilovevampire/sensorscope-release`, then:
   ```bash
   sudo apt install python3-bloom python3-catkin-pkg
   bloom-release --rosdistro jazzy --track jazzy sensorscope
   ```
4. Bloom opens a pull request against `ros/rosdistro`. Once merged and the build farm succeeds, the
   package shows up on the index.
5. Optional but encouraged: add a `QUALITY_DECLARATION.md` following
   [REP-2004](https://www.ros.org/reps/rep-2004.html).
