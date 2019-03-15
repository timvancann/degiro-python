import sys

from setuptools import setup

with open("README.md", "r") as f:
    long_description = f.read()

if {"pytest", "test"}.intersection(sys.argv):
    setup_dependencies = ["pytest-runner==4.2"]

setup(
    name="DeGiro API",
    author="Tim van Cann",
    long_description=long_description,
    author_email="timvancann@godatadriven.com",
    packages=["degiro"],
    include_package_data=True,
    install_requires=["PyFunctional==1.2.0", "requests==2.21.0"],
    tests_require=["requests==2.21.0"],
    classifiers=["Programming Language :: Python :: 3", "License :: OSI Approved :: MIT License"],
)
