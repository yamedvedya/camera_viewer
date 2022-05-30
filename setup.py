#!/usr/bin/python3
import io
import os
from petra_camera.version import __version__

from setuptools import setup, find_packages

# Package meta-data.
NAME = 'petra_camera'
DESCRIPTION = 'Simple viewer for cameras, used at PETRA III source'
EMAIL = 'yury.matveev@desy.de'
AUTHOR = 'Yury Matveyev'
REQUIRES_PYTHON = '>=3.7'

# What packages are required for this module to be executed?
REQUIRED = ['pyqtgraph', 'psutil', 'numpy', 'scipy',
]

EXTRA_REQUIRED = {'LAMBDA': ['watchdog'],
                  'PEAK': ['scikit-image']
                  }

# Import the README and use it as the long-description.
# Note: this will only work if 'README.md' is present in your MANIFEST.in file!
here = os.path.abspath(os.path.dirname(__file__))
try:
    with io.open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
        long_description = '\n' + f.read()
except IOError:
    long_description = DESCRIPTION

# Load the package's __version__.py module as a dictionary.
about = {}
about['__version__'] = __version__

# Where the magic happens:
setup(
    name=NAME,
    version=about['__version__'],
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type='text/markdown',
    author=AUTHOR,
    author_email=EMAIL,
    python_requires=REQUIRES_PYTHON,
    packages=find_packages(),
    package_dir={'petra_camera': 'petra_camera',},
    package_data={'petra_camera': ['petra_camera/*.py', 'petra_camera/*.xml' ],},
    install_requires=REQUIRED,
    extras_require=EXTRA_REQUIRED,
    include_package_data=True,
    license='GPLv3',
    entry_points={'console_scripts': ['petra_camera = petra_camera:main',],},
    scripts=['petra_camera/petra_camera.sh'],
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Development Status :: 5 - Production/Stable'
    ],
)
