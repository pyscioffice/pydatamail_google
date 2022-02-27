"""
Setuptools based setup module
"""
from setuptools import setup, find_packages
import versioneer


setup(
    name='pydatamail_google',
    version=versioneer.get_version(),
    description='Python interface to filter emails on Google Mail.',
    url='https://github.com/pyscioffice/pydatamail_google',
    author='Jan Janssen',
    author_email='jan.janssen@outlook.com',
    license='BSD',
    packages=find_packages(exclude=["*tests*"]),
    install_requires=[
        'google-api-python-client==2.38.0',
        'google-auth==2.6.0',
        'google-auth-oauthlib==0.4.6',
        'tqdm==4.62.3',
        'pandas==1.4.1',
        'sqlalchemy==1.4.31',
        'numpy==1.22.2',
        'matplotlib==3.5.1',
        'pydatamail==0.0.3'
    ],
    extras_require={
        'archive': [
            'pypdf3==1.0.6',
            'email2pdf==0.9.9.0'
        ]
    },
    cmdclass=versioneer.get_cmdclass(),
    entry_points={
        "console_scripts": [
            'pydatamail_google=pydatamail_google.__main__:command_line_parser'
        ]
    }
)
