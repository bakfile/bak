#!/usr/bin/env sh

# Dependencies:
# - asciinema (https://github.com/asciinema/asciinema)
# - svg-term (https://github.com/marionebl/svg-term-cli)
# - xsel

# Since you are here, please also look at tuterm:
#   https://github.com/veracioux/tuterm

RECORDED_COMMAND="tuterm bak.tut --mode demo"
alias copy='xsel -b'

rm -f /tmp/bakfile_bak.cast
# Record the command
asciinema rec -c "$RECORDED_COMMAND" /tmp/bakfile_bak.cast
cat /tmp/bakfile_bak.cast | svg-term --out bak_demo.svg
# Upload to asciinema.org
output="$(asciinema upload /tmp/bakfile_bak.cast)"

echo "$output"

# Copy to clipboard
echo "$output" | grep 'https:' | sed 's/^\s*//' | copy
