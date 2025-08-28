FROM python:3.13-bookworm AS builder

# automode
ARG AUTOMODE="OFF"
ARG CONFIG=""
ARG AUTOUPDATE="OFF"
ENV AUTOMODE=$AUTOMODE CONFIG=$CONFIG AUTOUPDATE=$AUTOUPDATE

# we need non-free
RUN printf "\ndeb https://deb.debian.org/debian bookworm contrib non-free" >> "/etc/apt/sources.list.d/debian-extended.list"

# apt
# install packages before copying mediaforge so docker can save the state and make debugging this quicker
RUN apt-get -y update
RUN apt-get -y upgrade

# prep for new node
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash -

RUN apt-get --no-install-recommends install -y  \
# most packages
    nano nodejs npm libgif-dev lsb-release \
# ffmpeg
# https://trac.ffmpeg.org/wiki/CompilationGuide/Ubuntu#FFmpeg
    # build deps
  autoconf automake build-essential cmake git-core libass-dev libfreetype6-dev libgnutls28-dev libmp3lame-dev libsdl2-dev libtool libva-dev libvdpau-dev libvorbis-dev libxcb1-dev libxcb-shm0-dev libxcb-xfixes0-dev meson ninja-build pkg-config texinfo wget yasm zlib1g-dev \
    # build deps "for ubuntu 20.04"
  libunistring-dev libaom-dev libdav1d-dev \
    # deps not listed in the build guide grrr \
  libsvtav1enc-dev \
    # optional deps
  libdav1d-dev libopus-dev libfdk-aac-dev libvpx-dev libx265-dev libnuma-dev libx264-dev nasm \
# libvips
# https://www.libvips.org/install.html#building-libvips-from-source
    # build deps
    ninja-build build-essential pkg-config bc \
    # other deps
    libcgif-dev libfftw3-dev libopenexr-dev libgsf-1-dev libglib2.0-dev liborc-dev libopenslide-dev libmatio-dev libwebp-dev libjpeg-dev libexpat1-dev libexif-dev libtiff5-dev libcfitsio-dev libpoppler-glib-dev librsvg2-dev libpango1.0-dev libopenjp2-7-dev libimagequant-dev \
# imagemagick
     fuse libfuse2 \
# fonts
    fonts-noto

RUN apt-get remove fonts-noto-color-emoji
# python packages
RUN python -m pip install --user --upgrade --no-warn-script-location --root-user-action=ignore  \
    pip poetry \
# libvips
    meson

RUN apt-get -y autoremove

# copy mediaforge code to container
COPY . mediaforge
RUN chmod +x /mediaforge/docker/*

RUN bash -c /mediaforge/docker/installbgpot.sh
RUN bash -c /mediaforge/docker/buildffmpeg.sh
RUN bash -c /mediaforge/docker/buildvips.sh
RUN bash -c /mediaforge/docker/installimagemagick.sh

WORKDIR mediaforge
RUN python -m poetry install

RUN cp config.example.py config.py
# so mediaforge knows to prompt with nano
ENV AM_I_IN_A_DOCKER_CONTAINER Yes

ENTRYPOINT ["/bin/bash", "/mediaforge/docker/dockerentry.sh"]
#CMD ["/bin/bash", "./dockerentry.sh"]



