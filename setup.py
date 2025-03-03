"""
setup.py
Usage: python setup.py py2app
"""
from setuptools import setup

APP = ['app.py']  # replace with your filename
DATA_FILES = []
OPTIONS = {
    'alias': True,              # uses symlinks instead of copying resources
    'iconfile': 'icon.icns',    # use a proper .icns file for the macOS app icon
}

setup(
    name="DexcomNavBarIcon",
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
