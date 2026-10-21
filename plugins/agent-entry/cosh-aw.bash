# Apache-2.0; see LICENSE, NOTICE and ORIGIN.md.
# Loaded only in this plugin's cosh backend, never installed as an aw executable.
export ANOLISA_COSH_WORKSPACE="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/workspace.py"
aw() {
    if [[ ${1:-} == run ]]; then
        /usr/bin/python3 "$ANOLISA_COSH_WORKSPACE" aw "$@"
    else
        /usr/bin/aw "$@"
    fi
}
export -f aw
