from setuptools import setup, find_packages
setup(
    name="unbound-ec2",
    version="0.2",
    packages=find_packages(),
    install_requires=[
        'vaurien==1.9',
        'dnspython',
        'boto'
    ],
    dependency_links = [
        'http://github.com/mwhooker/vaurien/tarball/master#egg=vaurien-1.9'
    ]
)
