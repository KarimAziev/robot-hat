from setuptools import find_packages, setup
from io import open
from setuptools import setup


def read_file(fname, encoding='utf-8'):
    with open(fname, encoding=encoding) as r:
        return r.read()


README = read_file('README.md')

setup(
    name="robot_hat",
    use_scm_version=True,
    setup_requires=["setuptools_scm"],
    packages=find_packages(),
    include_package_data=True,
    keywords=['python', 'i2c', 'raspberrypi'],
    url="https://github.com/KarimAziev/robot_hat",
    description="Rewritten version of Sunfounder's Robot Hat Python library for Raspberry Pi",
    long_description=README,
    long_description_content_type="text/markdown",
    license='GNU',
    zip_safe=False,
    author="Karim Aziiev",
    author_email="karim.aziiev@gmail.com",
    install_requires=["pygame", "smbus2", 'gpiozero', "RPi.GPIO", "platformdirs"],
    extras_require={
        "dev": [
            "black",
            "pre-commit",
            "isort",
        ],
    },
)
