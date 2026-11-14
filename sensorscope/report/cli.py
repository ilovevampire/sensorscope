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

"""Command line entry point: ros2 run sensorscope report <bag> -o report.html."""

from __future__ import annotations

import argparse
import os
import sys


def main(argv=None) -> None:
    p = argparse.ArgumentParser(
        prog='report', description='Generate an HTML sensor-analysis report from a rosbag2.'
    )
    p.add_argument('bag', help='path to the rosbag2 directory (or .mcap / .db3 file)')
    p.add_argument('-o', '--output', default='sensorscope_report.html', help='output HTML file')
    p.add_argument('--topic', action='append', help='only analyse this topic (repeatable)')
    p.add_argument('--title', default='SensorScope report')
    args = p.parse_args(sys.argv[1:] if argv is None else argv)

    from .bag_reader import read_captures
    from .builder import build_report

    try:
        print(f'Reading {args.bag} ...')
        captures = read_captures(args.bag, args.topic)
    except RuntimeError as exc:
        sys.exit(str(exc))
    for c in captures:
        print(
            f'  {c.topic}: {c.n:,} messages, {c.duration_s:.1f} s'
            + ('  (buffer full, truncated)' if c.truncated else '')
        )
    try:
        doc = build_report(captures, args.title, source=os.path.abspath(args.bag))
    except ImportError:
        sys.exit(
            'The report needs matplotlib: sudo apt install python3-matplotlib  (or pip '
            'install matplotlib)'
        )
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(doc)
    print(f'Wrote {os.path.abspath(args.output)}')


if __name__ == '__main__':
    main()
