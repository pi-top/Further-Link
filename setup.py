# coding=utf-8

from setuptools import setup, find_packages

requirements = ['Flask==1.0.3', 'flask_sockets==0.2.1', 'flask_cors==3.0.8', 'flask_restplus==0.12.1']

setup(
    name='diglett',  # package name
    version='0.1',  # package version
    author='leo he',
    author_email='leo@pi-top.com',
    description='Python library for Pi-Top webide',
    keywords=['diglett'],
    url='https://www.pi-top.com/',
    package=find_packages(include=['diglett']),
    include_package_data=True,
    platforms="pi-top[4]",
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'run=run:main'
        ]
    },
    zip_safe=False
)
