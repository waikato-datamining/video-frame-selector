# setup.py
# Copyright (C) 2021 University of Waikato, Hamilton, NZ

from setuptools import setup


def _read(f):
    """
    Reads in the content of the file.
    :param f: the file to read
    :type f: str
    :return: the content
    :rtype: str
    """
    return open(f, 'rb').read()


setup(
    name="video-frame-selector",
    description="Meta-tool that presents frames from a video to image analysis frameworks and uses the predictions to determine whether to use a frame or not.",
    long_description=(
        _read('DESCRIPTION.rst') + b'\n' +
        _read('CHANGES.rst')).decode('utf-8'),
    url="https://github.com/waikato-datamining/video-frame-processor",
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Topic :: Multimedia :: Video',
        'Programming Language :: Python :: 3',
    ],
    license='MIT License',
    package_dir={
        '': 'src'
    },
    packages=[
        "vfs",
    ],
    install_requires=[
        "opencv-python",
        "pyyaml",
    ],
    version="0.0.5",
    author='Peter Reutemann',
    author_email='fracpete@waikato.ac.nz',
    entry_points={
        "console_scripts": [
            "vfs-process=vfs.process:sys_main",
        ]
    }
)
