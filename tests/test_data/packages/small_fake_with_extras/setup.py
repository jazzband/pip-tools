from setuptools import setup

setup(
    name="small_fake_with_extras",
    version=0.1,
    install_requires=["small-fake-a", "small-fake-b"],
    extras_require={
        "dev": ["small-fake-a"],
        "test": ["small-fake-b"],
    },
)
