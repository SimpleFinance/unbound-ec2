from setuptools import setup, find_packages
setup(
    name="unbound-ec2",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'vaurien',
        'dnspython'
    ]
)
