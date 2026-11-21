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

import os
import re
import xml.etree.ElementTree as ET

import pytest

import sensorscope
from sensorscope import about

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(name):
    with open(os.path.join(ROOT, name), encoding='utf-8') as f:
        return f.read()


def test_version_strings_agree():
    pkg = ET.fromstring(_read('package.xml'))
    setup_version = re.search(r'version=["\']([^"\']+)["\']', _read('setup.py')).group(1)
    assert pkg.findtext('version') == setup_version == sensorscope.__version__ == '0.2.0'
    assert about.VERSION == sensorscope.__version__


def test_package_xml_has_ros_index_fields():
    pkg = ET.fromstring(_read('package.xml'))
    assert pkg.get('format') == '3'
    assert pkg.findtext('name') == 'sensorscope'
    assert pkg.findtext('license') == 'Apache-2.0'
    assert pkg.find('maintainer').text == 'Vishal Gaud'
    assert pkg.find('author').text == 'Vishal Gaud'
    urls = {u.get('type'): u.text for u in pkg.findall('url')}
    assert urls['repository'] == about.REPO_URL == urls['website']
    assert urls['bugtracker'] == about.ISSUES_URL
    tests = {t.text for t in pkg.findall('test_depend')}
    assert {'ament_copyright', 'ament_flake8', 'ament_pep257'} <= tests
    assert pkg.find('export/build_type').text == 'ament_python'
    assert len(pkg.findtext('description').split()) > 15


def test_changelog_top_version_matches_package():
    """Read the newest CHANGELOG.rst entry without any ROS tooling."""
    match = re.search(r'^(\d+\.\d+\.\d+) \((\d{4}-\d{2}-\d{2})\)$', _read('CHANGELOG.rst'), re.M)
    assert match, 'CHANGELOG.rst needs a heading like "0.2.0 (2026-11-03)"'
    assert match.group(1) == sensorscope.__version__


def test_ros_tooling_accepts_package_xml():
    catkin_pkg = pytest.importorskip('catkin_pkg.package')
    # the placeholder email may not be a valid address, so validate with a real-looking one
    text = _read('package.xml').replace('you@example.com', 'maintainer@example.org')
    pkg = catkin_pkg.parse_package_string(text)
    assert pkg.version == sensorscope.__version__


def test_ros_changelog_parser_reads_changelog():
    docutils = pytest.importorskip('docutils')
    catkin_pkg = pytest.importorskip('catkin_pkg')
    from catkin_pkg.changelog import get_changelog_from_path

    changelog = get_changelog_from_path(os.path.join(ROOT, 'CHANGELOG.rst'), 'sensorscope')
    versions = [v for v, _, _ in changelog.foreach_version(reverse=True)]
    assert (
        versions
    ), 'catkin_pkg found no versions in CHANGELOG.rst (catkin_pkg %s, docutils %s)' % (
        getattr(catkin_pkg, '__version__', '?'),
        docutils.__version__,
    )
    assert versions[0] == sensorscope.__version__


def test_about_constants():
    assert about.AUTHOR == 'Vishal Gaud' and about.AUTHOR_HANDLE == '@ilovevampire'
    assert about.REPO_URL == 'https://github.com/ilovevampire/sensorscope'
    assert about.ISSUES_URL.startswith(about.REPO_URL)
    assert about.AUTHOR_URL == 'https://github.com/ilovevampire'


def test_open_source_files_present():
    assert 'Apache License' in _read('LICENSE')[:200] and 'Version 2.0' in _read('LICENSE')[:200]
    for name in (
        'README.md',
        'CHANGELOG.rst',
        'CONTRIBUTING.md',
        'CODE_OF_CONDUCT.md',
        'docs/SETUP.md',
        'docs/ANALYSIS.md',
        '.github/workflows/ci.yml',
    ):
        assert os.path.getsize(os.path.join(ROOT, name)) > 100, name
    assert 'Vishal Gaud' in _read('README.md') and '0.2.0' in _read('README.md')


def test_every_python_file_has_apache_header():
    import glob

    files = [
        f
        for pat in ('sensorscope/**/*.py', 'test/*.py', 'launch/*.py', 'setup.py')
        for f in glob.glob(os.path.join(ROOT, pat), recursive=True)
    ]
    assert len(files) > 40
    for path in files:
        head = open(path, encoding='utf-8').read(700)
        assert head.startswith('# Copyright 2026 Vishal Gaud'), path
        assert 'Apache License, Version 2.0' in head, path
