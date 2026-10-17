#!/bin/sh
# Preserve pacman's ownership of the installed native executable.
if [ "${1-}" = update ]; then
  printf '%s\n' 'Qoder CLI is managed by pacman. Update the qodercli-bin package through your package manager.' >&2
  exit 1
fi
# Official CLI settings merge this with user/project preferences. An explicit
# user --settings argument may replace this startup setting; see README.md.
exec /opt/qodercli/qodercli --settings /usr/share/qodercli/pacman-settings.json "$@"
