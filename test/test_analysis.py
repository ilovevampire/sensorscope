# Copyright 2026 Vishal Gaud
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import math

from helpers import (
    ACC_K,
    ACC_SIGMA,
    FS,
    gps_capture,
    GYRO_K,
    GYRO_SIGMA,
    imu_capture,
    lidar_capture,
)
import numpy as np
import pytest
from sensorscope.analysis.allan import allan_deviation, analyze_allan
from sensorscope.analysis.export import gazebo_imu_sdf, kalibr_yaml
from sensorscope.analysis.gps import analyze_gps
from sensorscope.analysis.imu import analyze_imu, datasheet_lines
from sensorscope.analysis.lidar import analyze_lidar
from sensorscope.analysis.spectrum import autocorr_time, histogram_fit, welch_psd
from sensorscope.core.timing import analyze_timing


def test_allan_white_noise_slope_and_level():
    rng = np.random.default_rng(0)
    x = rng.normal(0, 0.005, 200_000)
    taus, adev, err = allan_deviation(x, 100.0)
    i1, i10 = np.argmin(abs(taus - 1.0)), np.argmin(abs(taus - 10.0))
    assert adev[i1] == pytest.approx(0.005 * math.sqrt(0.01), rel=0.05)  # N = sigma * sqrt(dt)
    assert adev[i10] / adev[i1] == pytest.approx(10**-0.5, rel=0.1)  # slope -1/2
    assert np.all(err > 0)


def test_allan_fit_recovers_N_and_K():
    r = analyze_allan(imu_capture().channels['gx'], FS)
    assert r.N == pytest.approx(GYRO_SIGMA * math.sqrt(1 / FS), rel=0.05)
    assert r.K == pytest.approx(GYRO_K, rel=0.4)  # long-tau statistics are noisy
    assert not r.min_at_edge
    assert 10 < r.tau_B < 120  # V-shape minimum near 30 s


def test_allan_short_input_rejected():
    with pytest.raises(ValueError):
        allan_deviation(np.arange(5.0), 100.0)


def test_spectrum_tools():
    rng = np.random.default_rng(3)
    fs = 200.0
    t = np.arange(40_000) / fs
    f, p = welch_psd(np.sin(2 * np.pi * 12.5 * t) + rng.normal(0, 0.1, t.size), fs)
    assert f[np.argmax(p)] == pytest.approx(12.5, abs=0.5)
    f, p = welch_psd(rng.normal(0, 0.005, 200_000), 100.0)
    assert p[5:-5].mean() == pytest.approx(2 * 0.005**2 / 100.0, rel=0.05)  # one-sided level
    h = histogram_fit(rng.normal(3.0, 2.0, 50_000))
    assert h.mean == pytest.approx(3.0, abs=0.05) and abs(h.excess_kurtosis) < 0.1
    e = np.zeros(20_000)
    w = rng.normal(size=e.size)
    for k in range(1, e.size):
        e[k] = 0.95 * e[k - 1] + math.sqrt(1 - 0.95**2) * w[k]
    assert autocorr_time(e, 1.0) == pytest.approx(-1 / math.log(0.95), rel=0.3)


def test_imu_analysis_end_to_end():
    res = analyze_imu(imu_capture())
    assert res.fs == pytest.approx(FS, rel=0.01)
    assert abs(res.gravity_error_pct) < 1.0
    gN = res.mean_param(('gx', 'gy', 'gz'), 'N')
    aN = res.mean_param(('ax', 'ay', 'az'), 'N')
    assert gN == pytest.approx(GYRO_SIGMA * math.sqrt(1 / FS), rel=0.05)
    assert aN == pytest.approx(ACC_SIGMA * math.sqrt(1 / FS), rel=0.05)
    assert res.mean_param(('ax', 'ay', 'az'), 'K') == pytest.approx(ACC_K, rel=0.5)
    assert res.timing.has_stamps and res.timing.latency_mean_ms == pytest.approx(2.0, abs=0.01)
    assert any('1–3 hours' in w for w in res.warnings)  # 50 min capture
    assert not any('still falling' in w for w in res.warnings)  # minimum was reached
    assert len(datasheet_lines(res)) == 2


def test_imu_warnings_for_moving_sensor_and_short_capture():
    cap = imu_capture(n=2000)
    cap.channels['gz'] = cap.channels['gz'] + 0.5  # rotating at 0.5 rad/s
    res = analyze_imu(cap)
    assert any('Gyro mean' in w for w in res.warnings)
    assert any('only 20 s' in w for w in res.warnings)
    with pytest.raises(ValueError):
        analyze_imu(imu_capture(n=100))


def test_export_snippets():
    res = analyze_imu(imu_capture(n=60_000))
    y = kalibr_yaml(res, '/imu/data')
    for key in (
        'accelerometer_noise_density',
        'gyroscope_random_walk',
        'rostopic: /imu/data',
        'update_rate',
    ):
        assert key in y and 'nan' not in y
    sdf = gazebo_imu_sdf(res)
    assert sdf.count('<noise type="gaussian">') == 6 and 'nan' not in sdf


def test_gps_analysis_cep_and_covariance_hint():
    res = analyze_gps(gps_capture(n=20_000, sigma=2.5, reported=1.5))
    # 2-D Gaussian: CEP50 = 1.1774 sigma, CEP95 = 2.4477 sigma (correlated errors, so loose)
    assert res.cep50 == pytest.approx(1.1774 * 2.5, rel=0.2)
    assert res.cep95 == pytest.approx(2.4477 * 2.5, rel=0.2)
    assert res.covariance_ratio == pytest.approx(2.5 / 1.5, rel=0.15)
    assert any('Optimistic covariance' in w for w in res.warnings)
    assert any('time-correlated' in w for w in res.warnings)
    assert res.availability_pct == 100.0


def test_gps_analysis_needs_fixes():
    cap = gps_capture(n=50)
    cap.channels['status'][:] = -1.0
    with pytest.raises(ValueError):
        analyze_gps(cap)


def test_lidar_analysis_static_wall():
    res = analyze_lidar(lidar_capture())
    assert res.n_scans == 60 and res.n_beams == 360
    assert res.valid_pct == pytest.approx(98.0, abs=1.0)
    assert res.median_beam_std == pytest.approx(0.02, rel=0.15)
    assert res.wall_noise_std == pytest.approx(0.02, rel=0.15)
    assert res.wall_distance == pytest.approx(3.0, abs=0.05)  # nearest wall is 3 m away
    assert abs(abs(res.sector_center_deg) - 90.0) <= 2.0
    manual = analyze_lidar(lidar_capture(), sector_center_deg=0.0, sector_width_deg=20.0)
    assert manual.wall_distance == pytest.approx(4.0, abs=0.05)
    with pytest.raises(ValueError):
        analyze_lidar(lidar_capture(n_scans=2))


def test_timing_stats_detect_drops_and_latency():
    t = np.arange(0, 10, 0.01)
    stamp = t - 0.003
    keep = np.ones(t.size, bool)
    keep[[200, 201, 500]] = False  # 3 missing messages
    s = analyze_timing(t[keep], stamp[keep])
    assert s.has_stamps and s.dropped_est == 3
    assert s.latency_mean_ms == pytest.approx(3.0, abs=0.01)
    assert s.rate_hz == pytest.approx(100.0, rel=0.02)
    no = analyze_timing(t, np.full(t.size, np.nan))
    assert not no.has_stamps and no.rate_hz == pytest.approx(100.0, rel=0.01)


def test_allan_flags_curve_that_never_reaches_a_minimum():
    x = np.random.default_rng(5).normal(0, 0.005, 120_000)  # pure white noise: always falling
    r = analyze_allan(x, 100.0)
    assert r.min_at_edge
