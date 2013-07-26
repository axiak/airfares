#!/usr/bin/python
from setuptools import setup, find_packages

requirements = [
    'selenium',
    'splinter',
    'requests<=1.1'
]


setup(name='flight-scraping',
      version='0.1',
      zip_safe=False,
      packages=find_packages(),
      platforms=["any"],
      include_package_data=True,
      install_requires=requirements,
      entry_points={
          'console_scripts': ['load_flights=load_data:main']
      })
