"""
filefetcher -- pull GPS files

"""

from setuptools import setup, find_packages
from filefetcher import __version__

DOCSTRING = __doc__.split("\n")

setup(
    name="filefetcher",
    version=__version__,
    author="Tom Parker",
    author_email="tparker@usgs.gov",
    description=(DOCSTRING[1]),
    license="CC0",
    url="http://github.com/tparker-usgs/filefetcher",
    packages=find_packages(),
    long_description='\n'.join(DOCSTRING[3:]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Software Development :: Libraries",
        "License :: CC0 1.0 Universal (CC0 1.0) Public Domain Dedication",
    ],
    install_requires=[
        'pycurl',
        'tomputils>=1.12.4',
        'humanize',
        'multiprocessing-logging',
        'jinja2',
        'psutil',
        'single'
    ],
    entry_points={
        'console_scripts': [
            'filefetcher = filefetcher.filefetcher:main',
            'fetcherreaper = filefetcher.fetcherreaper:main'
        ]
    }
)
