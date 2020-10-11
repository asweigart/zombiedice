from setuptools import setup, find_packages
import os
import re
import io

# Load version from module (without loading the whole module)
with io.open('src/zombiedice/__init__.py', 'r', encoding='utf-8') as fd:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
                        fd.read(), re.MULTILINE).group(1)

here = os.path.abspath(os.path.dirname(__file__))

# Get the long description from the README file
with io.open(os.path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()


setup(
    name='zombiedice',
    version=version,
    url='https://github.com/asweigart/zombiedice',
    author='Al Sweigart',
    author_email='al@inventwithpython.com',
    description=('A simulator for the dice game Zombie Dice that can run bot AI players.'),
    long_description=long_description,
    license='BSD',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    package_data={'zombiedice': ['*.png', '*.jpg', '*.js']},
    install_requires=[],
    keywords="zombie dice game ai simulator bots",
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.1',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
)