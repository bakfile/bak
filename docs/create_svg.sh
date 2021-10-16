#!/usr/bin/env sh

RECORDED_COMMAND="tuterm bak.tut --mode demo"

rm -f /tmp/bakfile_bak.cast
asciinema rec -c "$RECORDED_COMMAND" /tmp/bakfile_bak.cast
cat /tmp/bakfile_bak.cast | svg-term --out bak_demo.svg
