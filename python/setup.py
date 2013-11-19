# encoding: utf-8
import os.path
try:
    from setuptools import setup
except ImportError:
    import ez_setup
    ez_setup.use_setuptools()
    from setuptools import setup


# Load the version.
__version__ = None
with open(os.path.join('src', 'pdef', 'version.py')) as f:
    exec(f.read())


setup(
    name='pdef',
    version=__version__,
    license='Apache License 2.0',
    description='Protocol definition language',
    url='http://github.com/ivan-korobkov/pdef',

    author='Ivan Korobkov',
    author_email='ivan.korobkov@gmail.com',

    packages=['pdef'],
    package_dir={'': 'src'},
    py_modules=['pdef.rpc'],

    install_requires=['requests>=1.2'],

    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: WSGI',
        'Topic :: Software Development :: Libraries'
    ]
)
