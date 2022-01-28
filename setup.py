"""
Setuptools based setup module
"""
from setuptools import setup, find_packages
import versioneer


setup(
    name='pygmailfilter',
    version=versioneer.get_version(),
    description='Python interface to filter emails on Google Mail.',
    url='https://github.com/pyscioffice/pygmailfilter',
    author='Jan Janssen',
    author_email='jan.janssen@outlook.com',
    license='BSD',
    packages=find_packages(exclude=["*tests*"]),
    install_requires=[
        'google-api-python-client==2.36.0',
        'google-auth==2.5.0',
        'tqdm==4.62.3'
    ],
    cmdclass=versioneer.get_cmdclass(),
    entry_points={
        "console_scripts": [
            'pygmailfilter=pygmailfilter.__main__:load_json_tasks'
        ]
    }
)