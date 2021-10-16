#!/usr/bin/env sh

# NOTE: Change this to suit your needs

TERM_WIDTH=110
TERM_HEIGHT=30
RECORDED_COMMAND="tuterm bak.tut --mode demo"
alias copy='xsel -b'

# Dependencies:
# - asciinema (https://github.com/asciinema/asciinema)
# - svg-term (https://github.com/marionebl/svg-term-cli)
# - xsel

# Since you are here, please also look at tuterm:
#   https://github.com/veracioux/tuterm

rm -f /tmp/bakfile_bak.cast

# Record the command
asciinema rec -c "$RECORDED_COMMAND" /tmp/bakfile_bak.cast

# Change terminal width and height
# NOTE: for some reason the yes command prints Broken pipe; this is a workaround
sed -e "1 s/\(\"width\": \)[0-9]\+/\1$TERM_WIDTH/" \
    -e "1 s/\(\"height\": \)[0-9]\+/\1$TERM_HEIGHT/" \
    -e '/Broken pipe/d' \
    -i /tmp/bakfile_bak.cast

# Upload to asciinema.org
output="$(asciinema upload /tmp/bakfile_bak.cast)"
echo "$output"

# Copy URL to clipboard
echo "$output" | grep 'https:' | sed 's/^\s*//' | copy

# Create local SVG animation
cat /tmp/bakfile_bak.cast | svg-term --out bak_demo.svg

echo "SVG animation saved as 'bak_demo.svg'"
