# Contributing to SensorScope

Thanks for helping. Bug reports, sensor plugins, docs fixes and ideas are all welcome.

## Report a problem or suggest something

Open an issue: https://github.com/ilovevampire/sensorscope/issues
Please include your ROS distribution, Ubuntu version, the output of `pip list | grep -i -E "pyside6|pyqtgraph|numpy"`,
and the exact error text.

## Set up for development

Follow [docs/SETUP.md](docs/SETUP.md), then run the tests (no ROS needed for most of them):

```bash
cd ~/sensorscope_ws/src/sensorscope
pip install pytest
python -m pytest test -q
```

## Project rules

- `sensorscope/core/` and `sensorscope/analysis/` must stay free of ROS and Qt imports, so they can be tested on plain arrays.
- New analysis code needs a test against synthetic data with a **known answer** (see `test/test_analysis.py`).
- Follow the ROS 2 Python style: `ament_flake8` (max line length 99) and `ament_pep257`.
  Every source file starts with the Apache-2.0 header (see any existing file).
- Keep `package.xml`, `setup.py` and `sensorscope/__init__.py` on the same `X.Y.Z` version (a test checks this).
- Add a line to `CHANGELOG.rst` under a `Forthcoming` heading for user-visible changes.

## Add a sensor

1. Create `sensorscope/sensors/my_sensor.py` with an extractor `msg -> ({channel: value}, optional_extra)`
   and a `SensorSpec` that says which channels go in which plot.
2. Call `register(spec)` in that file and import it in `sensorscope/sensors/__init__.py`.
3. Add a test in `test/test_sensors.py` using a plain `SimpleNamespace` message.

## Pull requests

1. Fork, then create a branch: `git switch -c my-change`.
2. Keep commits focused, with messages that say what changed.
3. Make sure `python -m pytest test -q` passes.
4. Open a pull request and fill in the template.

## License

Any contribution that you make to this repository will
be under the Apache 2 License, as dictated by that
[license](http://www.apache.org/licenses/LICENSE-2.0.html):

~~~
5. Submission of Contributions. Unless You explicitly state otherwise,
   any Contribution intentionally submitted for inclusion in the Work
   by You to the Licensor shall be under the terms and conditions of
   this License, without any additional terms or conditions.
   Notwithstanding the above, nothing herein shall supersede or modify
   the terms of any separate license agreement you may have executed
   with Licensor regarding such Contributions.
~~~
