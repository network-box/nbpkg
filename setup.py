import os
from setuptools import setup, command

setup(
    name = "nbpkg",
    version = "5.0.0",
    author = "Mathieu Bridon",
    author_email = "mathieu.bridon@network-box.com",
    description = "Utility to interact with the Network Box Packaging system",
    license = "GPLv2+",
    url = "https://www.network-box.com",
    package_dir = {'': 'src'},
    packages = ['pyrpkg/nbpkg'],
    scripts = ['src/nbpkg'],
    data_files = [('/etc/bash_completion.d', ['src/nbpkg.bash']),
                  ('/etc/rpkg/', ['src/nbpkg.conf', 'src/nbpkg-nonfree.conf']),
                  ],
)
