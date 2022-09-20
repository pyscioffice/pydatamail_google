"""
Setuptools based setup module
"""
from setuptools import setup, find_packages
from pathlib import Path
import versioneer


setup(
    name='pydatamail_google',
    version=versioneer.get_version(),
    description='Python interface to filter emails on Google Mail.',
    long_description=Path("README.md").read_text(),
    long_description_content_type='text/markdown',
    url='https://github.com/pyscioffice/pydatamail_google',
    author='Jan Janssen',
    author_email='jan.janssen@outlook.com',
    license='BSD',
    packages=find_packages(exclude=["*tests*"]),
    install_requires=[
        'google-api-python-client==2.61.0',
        'google-auth==2.11.1',
        'google-auth-oauthlib==0.5.3',
        'tqdm==4.64.1',
        'pandas==1.5.0',
        'sqlalchemy==1.4.41',
        'numpy==1.23.3',
        'pydatamail==0.0.10',
    ],
    extras_require={
        'archive': [
            'pypdf3==1.0.6',
            'email2pdf==0.9.9.0'
        ],
        'machinelearning': [
            'pydatamail_ml==0.0.3'
        ]
    },
    cmdclass=versioneer.get_cmdclass(),
    entry_points={
        "console_scripts": [
            'pydatamail_google=pydatamail_google.__main__:command_line_parser'
        ]
    }
)
