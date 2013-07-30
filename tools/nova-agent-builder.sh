#!/bin/bash
##### NOVA AGENT BUILDER
##### how_to:$ sh nova-agent-builder.sh help
##### W.I.P. works fine for most of cases,
#####   needs some updates for RHEL & OpenSuse support

##### Var
INSTALL_PIP='easy_install pip'
PIP='pip'

NOVA_AGENT_REPO='git://github.com/rackerlabs/openstack-guest-agents-unix.git'
BASE_DIR="/tmp/test_nova_agent"
REPO_DIR='nova-agent'

##### Functions
shout(){
  echo "***************************************************"
  echo $1
  echo "***************************************************"
}

patchelf_git(){
  shout "installing PatchElf from Git"
  PATCHELF_DIR='/tmp/patchelf'
  CURR_DIR=`pwd`
  if [ -f $PATCHELF_DIR ]; then
    cd $PATCHELF_DIR
    git checkout .
    git pull
  else
    git clone https://github.com/NixOS/patchelf.git $PATCHELF_DIR
    cd $PATCHELF_DIR
  fi
  sh bootstrap.sh
  ./configure
  make
  make install
  cd $CURR_DIR
}

python_module_installer()
{
  shout "Install required modules"

  if [ `which pip > /dev/null 2>&1 ; echo $?` -ne 0 ]; then
    `$INSTALL_PIP`
  fi

  `$PIP install pycrypto`
  `$PIP install pyxenstore`
  `$PIP install unittest2`
  `$PIP install mox`
}

major_version(){
  export OS_VERSION=`cat $RELEASE_FILE | sed 's/[^0-9.]*//g'`
  export OS_VERSION_MAJOR=`echo $OS_VERSION | awk -F'.' '{print $1}'`
}

get_epel_repo(){
  shout "enabling EPEL repo"
  major_version
  EPEL_URI='http://epel.mirror.net.in/epel'
  if [ $OS_VERSION_MAJOR -eq 6 ]; then
    EPEL_URI=$EPEL_URI"/6/i386/epel-release-6-8.noarch.rpm"
  elif [ $OS_VERSION_MAJOR -eq 5 ]; then
    EPEL_URI=$EPEL_URI"/5/i386/epel-release-5-4.noarch.rpm"
  else
    shout "This version isn't supported." && exit 1
  fi

  curl -L -o /tmp/epel-6.8.rpm $EPEL_URI
  `rpm -ivh /tmp/epel-6.8.rpm && yum repolist`
}

# for distros: RedHat, CentOS, Fedora
install_pre_requisite_redhat(){
  export RELEASE_FILE='/etc/redhat-release'
  cat $RELEASE_FILE

  get_epel_repo

  yum -y install git autoconf gcc gcc-c++ automake libtool
  yum -y install python-crypto python-devel

  yum install -y centos-release-xen.x86_64 &&  yum repolist
  yum install -y xen-devel
  patchelf_git

  INSTALL_PIP='yum -y install python-pip'
  PIP='python-pip'
  python_module_installer
}

# for distros: Debian, Ubuntu
install_pre_requisite_debian(){
  export RELEASE_FILE='/etc/debian_version'
  cat $RELEASE_FILE

  apt-get -y install git curl
  apt-get -y install autoconf build-essential python-cjson libxen-dev
  apt-get -y install python-anyjson python-pip python-crypto libtool python-dev
  patchelf_git

  INSTALL_PIP='apt-get install -y python-pip'
  python_module_installer
}

# for distros: Gentoo
install_pre_requisite_gentoo(){
  export RELEASE_FILE='/etc/gentoo-release'
  cat $RELEASE_FILE

  emerge git autoconf
  emerge patchelf

  INSTALL_PIP='emerge dev-python/pip'
  python_module_installer
}

# for distros: ArchLinux
install_pre_requisite_archlinux(){
  export RELEASE_FILE='/etc/arch-release'
  cat $RELEASE_FILE

  pacman -Sc --noconfirm
  pacman -Sy --noconfirm git autoconf patchelf python-pip

  python_module_installer
}

# for distros: FreeBSD
install_pre_requisite_freebsd(){
    uname -a

    pkg_add -r git autogen automake wget
    pkg_add -r py27-unittest2 py27-cryptkit py27-pycrypto

    # re-install xen-tool :: required for pyxenstore install
    cd /usr/ports/sysutils/xen-tools
    make reinstall
    cp  /usr/ports/sysutils/xen-tools/work/xen-4.1.3/tools/xenstore/libxenstore.so  /usr/lib
    cp /usr/ports/sysutils/xen-tools/work/xen-4.1.3/tools/xenstore/xs.h /usr/local/include/python2.7/
    cp /usr/ports/sysutils/xen-tools/work/xen-4.1.3/tools/xenstore/xs_lib.h /usr/local/include/python2.7/
    mkdir -p /usr/local/include/python2.7/xen/io
    cp /usr/ports/sysutils/xen-tools/work/xen-4.1.3/xen/include/public/io/xs_wire.h /usr/local/include/python2.7/xen/io/
    cd -

    # installing pyxenstore
    cd /tmp
    wget https://pypi.python.org/packages/source/p/pyxenstore/pyxenstore-0.0.2.tar.gz
    tar -zvxf pyxenstore-0.0.2.tar.gz
    cd pyxenstore-0.0.2
    python setup.py install
    cd -

    alias make='gmake' # patchelf and nova-agent require 'gmake' instead of 'make'
    patchelf_git
}

install_pre_requisite(){
  if [ -f /etc/redhat-release ]; then
    install_pre_requisite_redhat

  elif [ -f /etc/debian_version ]; then
    install_pre_requisite_debian

  elif [ -f /etc/gentoo-release ]; then
    install_pre_requisite_gentoo

  elif [ -f /etc/arch-release ]; then
    install_pre_requisite_archlinux

  elif [ `uname -s` == 'FreeBSD' ] ; then
    install_pre_requisite_freebsd

  else
    echo 'Un-Managed Distro.' && exit 1

  fi
}

branch_nova_agent(){
  if [ ! -z $NOVA_AGENT_BRANCH ]; then
    git checkout $NOVA_AGENT_BRANCH
  fi
}

patch_nova_agent(){
  PATCH_FILE='/tmp/nova_agent.patch'
  # if create patch from a pull request
  if [ ! -z $NOVA_AGENT_PULL_REQUEST ]; then
    PATCH_URL_BASE='http://github.com/rackerlabs/openstack-guest-agents-unix/pull/'
    export NOVA_AGENT_PATCH_URL="$PATCH_URL_BASE""$NOVA_AGENT_PULL_REQUEST"".patch"
  fi

  # apply patch if env NOVA_AGENT_PULL_REQUEST or NOVA_AGENT_PATCH_URL present
  if [ ! -z $NOVA_AGENT_PATCH_URL]; then
    shout "downloading nova-agent patch from: "$NOVA_AGENT_PATCH_URL
    curl -L -o $PATCH_FILE $NOVA_AGENT_PATCH_URL
    git apply $PATCH_FILE
  fi
}

clone_nova_agent(){
  #Clone Nova agent code from the repo.
  shout "cloning NovaAgent"
  mkdir -p $BASE_DIR
  cd $BASE_DIR

  if [ -f $BASE_DIR/$REPO_DIR ]; then
    cd $REPO_DIR
    git checkout .
    git pull
  else
    git clone $NOVA_AGENT_REPO $REPO_DIR
    cd $REPO_DIR
  fi
  branch_nova_agent
  patch_nova_agent
}

make_nova_agent(){
  install_pre_requisite

  clone_nova_agent

  sh autogen.sh && ./configure && make
}

check_nova_agent(){
  make_nova_agent
  make check
}

bintar_nova_agent(){
  check_nova_agent
  make bintar
  cp $BASE_DIR/$REPO_DIR/nova-agent*.tar.gz $NOVA_AGENT_BINTAR
}

bintar_nova_agent_without_test(){
  make_nova_agent
  make bintar
  cp $BASE_DIR/$REPO_DIR/nova-agent*.tar.gz $NOVA_AGENT_BINTAR
}

##### MAIN

help="$(cat <<'SYNTAX'
++++++++++++++++++++++++++++++++++++++++++++++++++\n
 [HELP] NOVA AGENT Builder\n
++++++++++++++++++++++++++++++++++++++++++++++++++\n
\n
 To just run the test 'make check' for latest pull:\n
   $ sh nova-agent-builder.sh test\n
\n
 To create a bintar for nova-agent with tests run:\n
   $ sh nova-agent-builder.sh bintar\n
\n
 To create a bintar for nova-agent without tests:\n
   $ sh nova-agent-builder.sh bintar_no_test\n
\n
 To apply a Git Patch before running tests/bintar:\n
   provide environment var NOVA_AGENT_PULL_REQUEST\n
   with URL to download the Patch.\n
\n
 To apply Pull Request before running tests/bintar:\n
   provide environment var NOVA_AGENT_PULL_REQUEST\n
   with Pull Request NUMBER to refer.\n
\n
 To perform test/bintar action on another branch:\n
   provide environment var NOVA_AGENT_BRANCH\n
   with Name of the Git Branch to checkout.\n
\n
 ++++++++++++++++++++++++++++++++++++++++++++++++++\n
SYNTAX
)"

if [ $# -eq 0 ]; then
  shout "Running create Bin tar"
  bintar_nova_agent
elif [ $# -gt 1 ]; then
  shout "Help"
  echo $help && exit 1
elif [ "$1" = "test" ]; then
  shout "Running Checks"
  check_nova_agent
elif [ "$1" = "bintar" ]; then
  shout "Running create Bin tar"
  bintar_nova_agent
elif [ "$1" = "bintar_no_test" ]; then
  shout "Running create Bin tar without tests"
  bintar_nova_agent_without_test
else
  echo $help && exit 1
fi
