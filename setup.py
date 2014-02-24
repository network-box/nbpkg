import os
from setuptools import setup, command

setup(
    name = "nbpkg",
    version = "5.0.4",
    author = "Mathieu Bridon",
    author_email = "mathieu.bridon@network-box.com",
    description = ("Network Box plugin to rpkg to manage "
                   "package sources in a git repository"),
    license = "GPLv2+",
    url = "https://github.com/network-box/nbpkg",
    package_dir = {'': 'src'},
    packages = ['nbpkg'],
    scripts = ['src/bin/nbpkg'],
    data_files = [('/etc/bash_completion.d', ['src/nbpkg.bash']),
                  ('/etc/rpkg', ['src/nbpkg.conf', 'src/nbpkg-nonfree.conf']),
                  ],
)
