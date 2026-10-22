#!/bin/bash
# instalar_nginx.sh — inserta el bloque /taller5/ del snippet ANTES de
# "location /" del sitio iotcentraljose, sin tocar el resto. Corre como root.
set -e
BASE=/home/azureuser/taller_5_iot/docker
F=/etc/nginx/sites-available/iotcentraljose
if grep -q 'taller5/grafana' "$F"; then
  echo "nginx: bloque /taller5/ YA estaba — nada que hacer"
else
  cp "$F" "$F.bak-$(date +%s)"
  awk -v snip="$BASE/nginx-taller5.conf.snippet" '
    !done && /^    location \/ \{/ { while ((getline l < snip) > 0) print l; done=1 }
    { print }' "$F" > "$F.new" && mv "$F.new" "$F"
  echo "nginx: bloque /taller5/ insertado"
fi
nginx -t && systemctl reload nginx && echo "nginx recargado OK"
