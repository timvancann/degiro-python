from setuptools import setup

with open("README.md", "r") as f:
    long_description = f.read()

setup(
    name="DeGiro API",
    author="Tim van Cann",
    long_description=long_description,
    author_email="timvancann@godatadriven.com",
    packages=["degiro"],
    include_package_data=True,
    install_requires=["PyFunctional==1.2.0"],
    tests_require={"pytest==4.3.1"},
    classifiers=["Programming Language :: Python :: 3", "License :: OSI Approved :: MIT License"],
)
