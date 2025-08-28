#!/bin/bash

updategit() {
  # remote isnt set up by default when container is set up
  echo "Updating MediaForge Code..."
  if [ ! -d ".git" ]; then
    git init . --initial-branch=master
    git remote add origin https://github.com/machineonamission/mediaforge.git
  fi
  git fetch --all
  git reset --hard origin/master
}
updateapt() {
  echo "Updating APT Packages..."
  apt-get update -y
  apt-get upgrade -y
  apt autoremove -y
  echo "Done!"
}
updatepip() {
  # remote isnt set up by default when container is set up
  echo "Updating PIP Packages..."
  pip install --upgrade --user pip poetry --no-warn-script-location --root-user-action=ignore
  python -m poetry install
}
updateffmpeg(){
  # for backwards compatability
  chmod +x /mediaforge/docker/*
  /mediaforge/docker/buildffmpeg.sh
}
updatevips(){
  # for backwards compatability
  chmod +x /mediaforge/docker/*
  /mediaforge/docker/buildvips.sh
}
updateimagemagick(){
  # for backwards compatability
  chmod +x /mediaforge/docker/*
  /mediaforge/docker/installimagemagick.sh
}
updatebgpot(){
  # for backwards compatability
  chmod +x /mediaforge/docker/*
  /mediaforge/docker/installbgpot.sh
}

run() {
  # remote isnt set up by default when container is set up
  echo "Running..."
  cd /mediaforge
  python -m poetry run python src/main.py
}

# mediaforge ascii art :3
cat "media/active/braillebanner.txt"
printf "\n\n"

if [ "$AUTOMODE" == "ON" ] && [ "$CONFIG" != "" ]; then
  echo "We're in automode. Running MediaForge"
  if [ "$AUTOUPDATE" == "ON" ]; then
    updategit
    updateapt
    updatepip
    updateffmpeg
    updatevips
    updatebgpot
  fi
  echo "$CONFIG" | base64 -d >config.py
  run
  exit
fi

read -t 10 -p "Press Enter to view options, or MediaForge will automatically start in 10 seconds." RESP
if [[ $? -gt 128 ]] ; then
    run
else
  # weird variable name thing for prompt
  PS3='What would you like to do? '
  choices=("Run MediaForge" "Edit Config" "Update/Rebuild All And Run" "Update MediaForge Code" "Rebuild FFmpeg" "Rebuild libvips" "Update bgutil-pot" "Update ImageMagick" "Update APT Packages" "Update PIP Packages" "Debug Shell" "Quit")
  select fav in "${choices[@]}"; do
    case $fav in
    "Run MediaForge")
      run
      ;;
    "Edit Config")
      nano config.py
      ;;
    "Update/Rebuild All And Run")
      updategit
      updateapt
      updatepip
      updateffmpeg
      updatevips
      updateimagemagick
      updatebgpot
      run
      ;;
    "Update MediaForge Code")
      updategit
      ;;
    "Rebuild FFmpeg")
      updateffmpeg
    ;;
    "Rebuild libvips")
      updatevips
    ;;
    "Update ImageMagick")
      updateimagemagick
    ;;
    "Update bgutil-pot")
      updatebgpot
    ;;
    "Update APT Packages")
      updateapt
      ;;
    "Update PIP Packages")
      updatepip
      ;;
    "Debug Shell")
      /bin/bash
      ;;
    "Quit")
      echo "Goodbye!"
      exit
      ;;
    *) echo "invalid option $REPLY" ;;
    esac
  done
fi

