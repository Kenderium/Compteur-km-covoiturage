#!/usr/bin/env bash
# Copie le firmware sur un Pico W branché en USB (nécessite `pip install mpremote`).
# Usage : firmware/tools/deploy.sh
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f config.py ]; then
  echo "Créez d'abord firmware/config.py à partir de config_example.py" >&2
  exit 1
fi

mpremote mkdir :lib 2>/dev/null || true
mpremote mkdir :carpox 2>/dev/null || true
mpremote mkdir :carpox_core 2>/dev/null || true

mpremote cp lib/*.py :lib/
mpremote cp carpox/*.py :carpox/
# La logique partagée vit dans core/ ; on la copie telle quelle.
mpremote cp ../core/carpox_core/__init__.py ../core/carpox_core/geo.py :carpox_core/
mpremote cp config.py main.py :
mpremote reset
echo "Firmware installé."
