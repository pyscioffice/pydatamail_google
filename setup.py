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
        'google-api-python-client==2.37.0',
        'google-auth==2.6.0',
        'google-auth-oauthlib==0.4.6',
        'tqdm==4.62.3',
        'pandas==1.4.0',
        'sqlalchemy==1.4.31',
        'numpy==1.22.2',
        'matplotlib==3.5.1',
        'pydatamail==0.0.1'
    ],
    extras_require={
        'archive': [
            'pypdf2==1.26.0',
            'email2pdf==0.9.9.0'
        ]
    },
    cmdclass=versioneer.get_cmdclass(),
    entry_points={
        "console_scripts": [
            'pygmailfilter=pygmailfilter.__main__:command_line_parser'
        ]
    }
)