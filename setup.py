from setuptools import setup, find_packages
from pkg_resources import parse_requirements

def get_requirements(filename):
    with open(filename) as f:
        requirements = [str(req) for req in parse_requirements(f)]
    return requirements

setup(
    name="gen_ai",
    version="0.1.0",
    packages=find_packages(include=['gen_ai']),
    install_requires=get_requirements("requirements.txt"),
    author="Google LLC",
    author_email="chertushkin@google.com",
    description="This is pipeline code for accelerating solution accelerators",
    long_description=open("README.md").read(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache 2.0 License",
        "Operating System :: OS Independent",
    ],
)