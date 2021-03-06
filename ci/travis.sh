#!/usr/bin/env bash

export VIRTUALENVWRAPPER_PYTHON=`which python3`
export VIRTUALENVWRAPPER_VIRTUALENV=`which virtualenv`
export VIRTUALENV_WRAPPER_SH=`which virtualenvwrapper.sh`

# Create a basic .jhbuildrc
echo "import os"                                   > ~/.jhbuildrc
echo "prefix='${PREFIX}'"                         >> ~/.jhbuildrc
echo "checkoutroot='${JHBUILD}'"                  >> ~/.jhbuildrc
echo "moduleset = 'gnome-world'"                  >> ~/.jhbuildrc
echo "interact = False"                           >> ~/.jhbuildrc
echo "makeargs = '${MAKEFLAGS}'"                  >> ~/.jhbuildrc
echo "os.environ['CFLAGS'] = '${CFLAGS}'"         >> ~/.jhbuildrc
echo "os.environ['PYTHON'] = 'python${PYTHON_VERSION_MAJOR}'"           >> ~/.jhbuildrc
echo "os.environ['GSTREAMER'] = '1.0'"            >> ~/.jhbuildrc
echo "os.environ['ENABLE_PYTHON3'] = 'yes'"       >> ~/.jhbuildrc
echo "os.environ['ENABLE_GTK'] = 'yes'"           >> ~/.jhbuildrc
echo "os.environ['PYTHON_VERSION'] = '${PYTHON_VERSION}'"       >> ~/.jhbuildrc
echo "os.environ['CFLAGS'] = '-fPIC -O0 -ggdb -fno-inline -fno-omit-frame-pointer'" >> ~/.jhbuildrc
echo "os.environ['MAKEFLAGS'] = '-j4'"            >> ~/.jhbuildrc
echo "os.environ['PREFIX'] = '${HOME}/jhbuild'"   >> ~/.jhbuildrc
echo "os.environ['JHBUILD'] = '${HOME}/gnome'"    >> ~/.jhbuildrc
echo "os.environ['PATH'] = '${PREFIX}/bin:${PREFIX}/sbin:${PATH}'" >> ~/.jhbuildrc
echo "os.environ['LD_LIBRARY_PATH'] = '${PREFIX}/lib:${LD_LIBRARY_PATH}'" >> ~/.jhbuildrc
echo "os.environ['PYTHONPATH'] = '${PREFIX}/lib/python$PYTHON_VERSION/site-packages:/usr/lib/python$PYTHON_VERSION/site-packages'" >> ~/.jhbuildrc
echo "os.environ['PKG_CONFIG_PATH'] = '${PREFIX}/lib/pkgconfig:${PREFIX}/share/pkgconfig:/usr/lib/pkgconfig'" >> ~/.jhbuildrc
echo "os.environ['XDG_DATA_DIRS'] = '${PREFIX}/share:/usr/share'" >> ~/.jhbuildrc
echo "os.environ['XDG_CONFIG_DIRS'] = '${PREFIX}/etc/xdg'"        >> ~/.jhbuildrc
echo "os.environ['CC'] = 'gcc'"                                   >> ~/.jhbuildrc
echo "os.environ['WORKON_HOME'] = '${HOME}/.virtualenvs'"                           >> ~/.jhbuildrc
echo "os.environ['PROJECT_HOME'] = '${HOME}/dev'"                                   >> ~/.jhbuildrc
echo "os.environ['VIRTUALENVWRAPPER_PYTHON'] = '$VIRTUALENVWRAPPER_PYTHON'"                  >> ~/.jhbuildrc
echo "os.environ['VIRTUALENVWRAPPER_VIRTUALENV'] = '$VIRTUALENVWRAPPER_VIRTUALENV'"     >> ~/.jhbuildrc
# source /usr/local/bin/virtualenvwrapper.sh
echo "os.environ['PYTHONSTARTUP'] = '$HOME/.pythonrc'"                              >> ~/.jhbuildrc
echo "os.environ['PIP_DOWNLOAD_CACHE'] = '$HOME/.pip/cache'"                        >> ~/.jhbuildrc

mkdir -p "${PREFIX}"
mkdir -p "${JHBUILD}"

sudo apt-get install -qq gnome-common
sudo apt-get install -qq gtk-doc-tools
sudo apt-get install -qq libgtk-3-dev
sudo apt-get install -qq libgirepository1.0-dev
sudo apt-get install -qq --no-install-recommends \
    build-essential docbook-xsl flex bison cvs gperf cmake valac g++ \
    lib{pam0g,iw,db,gdbm,png12,ffi,tiff,boost-signals,ldap2}-dev \
    lib{vorbis,gl1-mesa,unistring,quvi,icu,neon27,usb-1.0-0,sasl2}-dev \
    lib{asound2,ncurses5,nss3,udev,usb,acl1,polkit-gobject-1,cairo}-dev \
    lib{oauth,nl-route-3,nl-genl-3,cups2,rsvg2,systemd-login}-dev \
    lib{dvdread,soundtouch,wnck-3,avahi-gobject}-dev \
    libtasn1-3-bin \
    libx{cb-util0,composite,randr,damage,ft2,i,t}-dev \
    {uuid,ppp,python-cairo}-dev \
    icc-profiles-free libxml-simple-perl subversion ruby gnome-doc-utils \
    yelp-tools apt-file

if [ "x${ENABLE_DISTCHECK}" == "xyes" ]; then
  sudo apt-get install -qq yelp-tools;
  sudo apt-get install -qq libgladeui-dev;
fi

if [ "x${ENABLE_LUA51}" == "xyes" ]; then
  sudo apt-get install -qq lua5.1;
  sudo apt-get install -qq liblua5.1-0-dev;
fi

if [ "x${ENABLE_LUAJIT}" == "xyes" ]; then
  sudo apt-get install -qq luajit;
  sudo apt-get install -qq luajit-5.1-dev;
fi

# Must be done after Lua has been installed.
# Fix Lua's package.path and package.cpath and
# add the variables to the JHBuild enviroment
if [ "x${ENABLE_LUA51}" == "xyes" ]; then
  LUA_PATH="`lua5.1 -e 'print(package.path)'`";
  LUA_PATH="${PREFIX}/share/lua/5.1/?/init.lua;${LUA_PATH}";
  LUA_PATH="${PREFIX}/share/lua/5.1/?.lua;${LUA_PATH}";
  LUA_CPATH="`lua5.1 -e 'print(package.cpath)'`";
  LUA_CPATH="${PREFIX}/lib/lua/5.1/?.so;${LUA_CPATH}";

  echo "os.environ['LUA_PATH']  = '${LUA_PATH}'"  >> ~/.jhbuildrc;
  echo "os.environ['LUA_CPATH'] = '${LUA_CPATH}'" >> ~/.jhbuildrc;
fi

if [ "x${ENABLE_PYTHON2}" == "xyes" ]; then
  sudo apt-get install -qq python-dev;
  sudo apt-get install -qq python-cairo-dev;
  sudo apt-get install -qq python-gi-dev;
fi

if [ "x${ENABLE_PYTHON3}" == "xyes" ]; then
  sudo apt-get install -qq python3-dev;
  sudo apt-get install -qq python3-cairo-dev;
  sudo apt-get install -qq python3-gi;
fi

sudo apt-get install yasm nasm -qq

# Get JHBuild
# source: https://github.com/GNOME/jhbuild/commit/86d958b6778da649b559815c0a0dbe6a5d1a8cd4
(cd "${JHBUILD}" &&
 if test ! -d "${JHBUILD}/jhbuild"; then git clone https://github.com/GNOME/jhbuild.git && cd jhbuild; else echo "exists" && cd jhbuild; fi &&
 git checkout 86d958b6778da649b559815c0a0dbe6a5d1a8cd4 &&
 ./autogen.sh --prefix=/usr/local > /dev/null &&
 make > /dev/null &&
 sudo make install > /dev/null )

# Need a gtk-doc that can handle virtual/rename-to function annotations
if [ "x${ENABLE_DISTCHECK}" == "xyes" ]; then
  (cd "${JHBUILD}" &&
   git clone https://github.com/GNOME/gtk-doc.git &&
   jhbuild buildone -n gtk-doc);
fi

# Need at least glib version 2.38
(cd "${JHBUILD}" &&
 git clone https://github.com/GNOME/glib.git &&
 cd glib &&
 git checkout eaca4f4116801f99e30e42a857559e19a1e6f4ce &&
 jhbuild buildone -n glib)

# Need at least gobject-introspection version 1.39
(cd "${JHBUILD}" &&
 git clone https://github.com/GNOME/gobject-introspection.git &&
 cd gobject-introspection &&
 git checkout cee2a4f215d5edf2e27b9964d3cfcb28a9d4941c &&
 jhbuild buildone -n gobject-introspection);

# Need LGI from git master
if [ "x${ENABLE_LUA51}" == "xyes" ]; then
  (cd "${JHBUILD}" &&
   git clone https://github.com/pavouk/lgi.git &&
   cd lgi &&
   jhbuild run make PREFIX="${PREFIX}"
                    CFLAGS="${CFLAGS} -I/usr/include/lua5.1" &&
   jhbuild run make install PREFIX="${PREFIX}");
fi


if [ "x${ENABLE_PYTHON2}" == "xyes" ] || [ "x${ENABLE_PYTHON3}" == "xyes" ]; then
  (cd "${JHBUILD}" &&
   git clone https://github.com/GNOME/pygobject.git);
fi

# Need PyGObject built for Python 2
if [ "x${ENABLE_PYTHON2}" == "xyes" ]; then
  (cd "${JHBUILD}" && cd pygobject && git checkout fb1b8fa8a67f2c7ea7ad4b53076496a8f2b4afdb &&
   jhbuild run ./autogen.sh --prefix="${PREFIX}" --with-python=python2 > /dev/null &&
   jhbuild run make install > /dev/null &&
   jhbuild run git clean -xdf > /dev/null);
fi

# Need PyGObject built for Python 3
if [ "x${ENABLE_PYTHON3}" == "xyes" ]; then
  (cd "${JHBUILD}" &&
   cd pygobject &&
   git checkout fb1b8fa8a67f2c7ea7ad4b53076496a8f2b4afdb &&
   jhbuild run ./autogen.sh --prefix="${PREFIX}" --with-python=python3 > /dev/null &&
   jhbuild run make install > /dev/null);
fi


cd "${JHBUILD}" && \
curl -L "https://gstreamer.freedesktop.org/src/gstreamer/gstreamer-1.8.2.tar.xz" > gstreamer-1.8.2.tar.xz && \
tar -xJf gstreamer-1.8.2.tar.xz && \
cd gstreamer-1.8.2 && \
jhbuild run ./configure --prefix="${PREFIX}" > /dev/null && \
jhbuild run make -j4  > /dev/null && \
jhbuild run make install > /dev/null

cd "${JHBUILD}" && \
curl -L "https://gstreamer.freedesktop.org/src/orc/orc-0.4.25.tar.xz" > orc-0.4.25.tar.xz && \
tar -xJf orc-0.4.25.tar.xz && \
cd orc-0.4.25 && \
jhbuild run ./configure --prefix="${PREFIX}" > /dev/null && \
jhbuild run make -j4  > /dev/null && \
jhbuild run make install > /dev/null

cd "${JHBUILD}" && \
curl -L "http://gstreamer.freedesktop.org/src/gst-plugins-base/gst-plugins-base-1.8.2.tar.xz" > gst-plugins-base-1.8.2.tar.xz && \
tar -xJf gst-plugins-base-1.8.2.tar.xz && \
cd gst-plugins-base-1.8.2 && \
jhbuild run ./configure --prefix="${PREFIX}" --enable-orc --with-x > /dev/null && \
jhbuild run make -j4  > /dev/null && \
jhbuild run make install > /dev/null

cd "${JHBUILD}" && \
curl -L "http://gstreamer.freedesktop.org/src/gst-plugins-good/gst-plugins-good-1.8.2.tar.xz" > gst-plugins-good-1.8.2.tar.xz && \
tar -xJf gst-plugins-good-1.8.2.tar.xz && \
cd gst-plugins-good-1.8.2 && \
jhbuild run ./configure --prefix="${PREFIX}" --enable-orc --with-libv4l2 --with-x  > /dev/null && \
jhbuild run make -j4  > /dev/null && \
jhbuild run make install > /dev/null

cd "${JHBUILD}" && \
curl -L "http://gstreamer.freedesktop.org/src/gst-plugins-ugly/gst-plugins-ugly-1.8.2.tar.xz" > gst-plugins-ugly-1.8.2.tar.xz && \
tar -xJf gst-plugins-ugly-1.8.2.tar.xz && \
cd gst-plugins-ugly-1.8.2 && \
jhbuild run ./configure --prefix="${PREFIX}" --enable-orc  > /dev/null && \
jhbuild run make -j4  > /dev/null && \
jhbuild run make install > /dev/null

cd "${JHBUILD}" && \
curl -L "http://gstreamer.freedesktop.org/src/gst-plugins-bad/gst-plugins-bad-1.8.2.tar.xz" > gst-plugins-bad-1.8.2.tar.xz && \
tar -xJf gst-plugins-bad-1.8.2.tar.xz && \
cd gst-plugins-bad-1.8.2 && \
jhbuild run ./configure --prefix="${PREFIX}" --enable-orc  > /dev/null && \
jhbuild run make -j4  > /dev/null && \
jhbuild run make install > /dev/null

cd "${JHBUILD}" && \
curl -L "http://gstreamer.freedesktop.org/src/gst-libav/gst-libav-1.8.2.tar.xz" > gst-libav-1.8.2.tar.xz && \
tar -xJf gst-libav-1.8.2.tar.xz && \
cd gst-libav-1.8.2 && \
jhbuild run ./configure --prefix="${PREFIX}" --enable-orc  > /dev/null && \
jhbuild run make -j4  > /dev/null && \
jhbuild run make install > /dev/null

( cd $JHBUILD &&
curl -L "https://github.com/bossjones/bossjones-gst-plugins-espeak-0-4-0/archive/v0.4.1.tar.gz" > gst-plugins-espeak-0.4.0.tar.gz &&
tar xvf gst-plugins-espeak-0.4.0.tar.gz &&
rm -rfv gst-plugins-espeak-0.4.0 &&
mv -fv bossjones-gst-plugins-espeak-0-4-0-0.4.1 gst-plugins-espeak-0.4.0 &&
cd gst-plugins-espeak-0.4.0 &&
jhbuild run ./configure --prefix="${PREFIX}" > /dev/null &&
jhbuild run make > /dev/null &&
jhbuild run make install > /dev/null);

( cd $JHBUILD &&
git clone https://github.com/cmusphinx/sphinxbase.git &&
cd sphinxbase &&
git checkout 74370799d5b53afc5b5b94a22f5eff9cb9907b97 &&
cd $JHBUILD/sphinxbase &&
jhbuild run ./autogen.sh --prefix="${PREFIX}" > /dev/null &&
jhbuild run ./configure --prefix="${PREFIX}" > /dev/null &&
jhbuild run make clean all > /dev/null &&
jhbuild run make install > /dev/null);

( cd $JHBUILD &&
git clone https://github.com/cmusphinx/pocketsphinx.git &&
cd pocketsphinx &&
git checkout 68ef5dc6d48d791a747026cd43cc6940a9e19f69 &&
jhbuild run ./autogen.sh --prefix="${PREFIX}" > /dev/null &&
jhbuild run ./configure --prefix="${PREFIX}" > /dev/null &&
jhbuild run make clean all > /dev/null &&
jhbuild run make install > /dev/null );


if [[ "${SKIP_ON_TRAVIS}" == 'yes' ]]; then
   echo "[ THIS IS A TRAVIS BUILD SKIPPING ... ]"
else
    export WORKON_HOME=${HOME}/.virtualenvs
    export PROJECT_HOME=${HOME}/dev
    export VIRTUALENVWRAPPER_PYTHON=`which python3`
    export VIRTUALENVWRAPPER_VIRTUALENV=`which virtualenv`
    source $VIRTUALENV_WRAPPER_SH
    export PYTHONSTARTUP=$HOME/.pythonrc
    export PIP_DOWNLOAD_CACHE=$HOME/.pip/cache
    workon scarlett_os

    mkdir -p $HOME/dev/bossjones-github/
    git clone https://github.com/bossjones/scarlett_os $HOME/dev/bossjones-github/scarlett_os
    cd $HOME/dev/bossjones-github/scarlett_os
    jhbuild run python3 setup.py install
    jhbuild run pip3 install -U coveralls sphinx numpy ipython
    jhbuild run python3 setup.py test
fi
