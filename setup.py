from setuptools import setup, find_packages
from os import path

VERSION = 0.1

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="ASCAM",
    version=VERSION,
    description="Analysis of episodic single ion channel data.",
    long_description=long_description,
    url="https://github.com/DrJohnDale/ASCAM",
    author="Nikolai Zaki",
    author_email="kol@posteo.de",
    packages=find_packages(where=here),
    python_requires=">=3.7",
    install_requires=[
        "PySide2>=5.15.2",
        "pyqtgraph>=0.12.2",
        "numpy>=1.21.2",
        "pandas>=1.1.5",
        "scipy>=1.7.1",
        "axographio>=0.3.1"
    ],
    entry_points={"console_scripts": ["ascam=src.ascam:main"]},
)
