#!/bin/bash
# Keep this on a separate line so that if GPG pass is cancelled
# the rest of the script won't continue
# TODO: is this a bug or expected behaviour on -e bash scripts?
entry="$1"
password="$(pass generate --force "$entry" | tail -1)"

echo "$password" | head -1 | xclip -selection c

notify-send --app-name=password-store \
    "$entry 🔑" \
    "Password generated and copied to clipboard. Password will only paste ONCE"
