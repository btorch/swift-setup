from setuptools import setup, find_packages
from swift_setup import __version__ as version
from shutil import copytree, move, rmtree
import os

name = "swift-setup"

install_requires = []
try:
    import fabric
except ImportError:
    install_requires.append("fabric")

data_files = [('/etc/swift-setup', 
               ['etc/swift-setup.conf-sample'])]
      
setup(
    name = name,
    version = version,
    author = "Joao Marcelo Martins",
    author_email = "btorch@gmail.com",
    description = "Help scripts to setup a swift cluster",
    license = "Apache License, (2.0)",
    keywords = "openstack swift",
    url = "https://github.com/btorch/swift-setup",
    packages=find_packages(exclude=['bin']),
    classifiers=[
        'Development Status :: 1 - Beta',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Environment :: Console',
        'Intended Audience :: System Administrators',
        ],
    install_requires=install_requires,
    scripts=['bin/swift-setup',],
    data_files = data_files)

src = 'templates'
dst = '/etc/swift-setup/templates'
if os.path.exists(dst):
    new_dst = dst + '.old'
    if os.path.exists(new_dst):
        rmtree(new_dst)
    move(dst, new_dst)
if os.path.exists('/etc/swift-setup'):
    copytree(src, dst) 
