"""Package setup for cronwatcher."""

from setuptools import setup, find_packages

with open("README.md", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", encoding="utf-8") as fh:
    requirements = [
        line.strip()
        for line in fh
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="cronwatcher",
    version="0.1.0",
    author="cronwatcher contributors",
    description="Lightweight daemon that monitors cron job execution and sends alerts on failures.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(exclude=["tests*"]),
    python_requires=">=3.11",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "cronwatcher=cronwatcher.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX",
        "Topic :: System :: Monitoring",
        "Topic :: Utilities",
    ],
)
