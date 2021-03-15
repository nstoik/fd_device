from setuptools import find_packages, setup

__version__ = '0.1'


setup(
    name='fd_device',
    version=__version__,
    packages=find_packages(exclude=['tests']),
    install_requires=[
        'click',
        'sqlalchemy',
        'alembic',
        'netifaces',
        'gpiozero',
    ],
    entry_points={
        'console_scripts': [
            'fd_device = fd_device.cli.cli:entry_point'
        ]
    }
)
