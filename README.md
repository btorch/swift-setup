swift-setup
===========

Requirements
---------------
* Fabric (if not present it will pull it down with any other dependencies)


User Requirements
------------------
* The Admin/Controller system must have a user (e.g:swiftops) 
  with ssh-key access to all nodes in the cluster & sudo privileges


Contribs
------------
* There are several scripts under the contrib folder that can be helpful for pre/post swift setup


Installation
---------------
* Download the code into your local machine
* Install it : python setup.py install --prefix=/usr/local
* Content Files: /etc/swift-setup


Configuration
---------------
Once the installation is completed you will have several files under /etc/swift-setup folder 
* swift-setup.conf-sample - The sample configuration file, change what you see fit and rename it to swift-setup.conf
* hosts/ - Location of files that contains the swift hostnames, much like a DSH groups. You MUST set this up if you will be deploying servers in groups
* templates/ - Contains all the files that will be loaded into the admin system git server repo


Usage
------
* Initialize the templates
  sudo swift-setup init

* Deploy systems (see swift-setup deploy --help)
  swift-setup deploy -g storage -t storage



TODO
------
* Setup the storage drives (create partition, filesystem, fstab and mount)
