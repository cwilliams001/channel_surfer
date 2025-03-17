from setuptools import setup, find_packages

setup(
    name="channel-surfer",
    version="0.1.4",
    packages=find_packages(),
    install_requires=[
        "rich",
        "requests",
    ],
    entry_points={
        "console_scripts": [
            "channel-surfer=channel_surfer.main:main",
        ],
    },
    author="CWilliams",
    author_email="williamsct1@gmail.com",
    description="A TUI for managing channel endpoints with ease.",
    url="https://github.com/cwilliams001/channel_surfer",
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
)
