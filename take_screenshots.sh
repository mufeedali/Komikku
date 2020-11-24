#!/bin/bash

meson . _build
meson configure -Dprefix=$PWD/_build/testdir _build
ninja -C _build
ninja -C _build install
GTK_THEME=Adwaita:dark ninja -C _build run &

sleep 5
wmctrl -F -r Komikku -e 0,0,0,412,838
wmctrl -F -r Komikku -N "Komikku main"

sleep 5
gnome-screenshot -w -f screenshots/main-window.png

xdotool key --delay 100 Return
sleep 1
wmctrl -F -r Komikku -e 0,0,0,412,838
sleep 1
gnome-screenshot -w -f screenshots/add-servers.png
sleep 3

xdotool key --delay 100 Shift+Tab Return
xdotool key --delay 100 Tab Tab Return
xdotool key --delay 100 Tab Tab Return
sleep 1
wmctrl -F -r Preferences -e 0,0,0,412,838
sleep 1
gnome-screenshot -w -f screenshots/preferences.png
sleep 3

xdotool key --delay 100 Escape Tab Return Return
sleep 0.5
gnome-screenshot -w -f screenshots/card-info.png
sleep 3

xdotool key --delay 100 Tab Return
sleep 0.5
gnome-screenshot -w -f screenshots/card-chapters.png
sleep 3

xdotool key --delay 100 Tab Return
# xdotool mousemove -sync 200 500 click 1
sleep 2
gnome-screenshot -w -f screenshots/reader.png
sleep 3

xdotool key Alt+F4
