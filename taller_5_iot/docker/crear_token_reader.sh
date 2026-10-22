#!/usr/bin/env bash
# crear_token_reader.sh — token SOLO-LECTURA de Influx para Grafana.
# La API 8086 no esta publicada al host (a proposito), usamos la CLI dentro
# del contenedor. Guarda el token en docker/.env como INFLUX_TOKEN_READER.
set -e
cd "$(dirname "$0")"
BID=$(docker exec taller5-influxdb influx bucket list --org unab | awk '/telemetria/{print $1}')
TOK=$(docker exec taller5-influxdb influx auth create --org unab \
        --read-bucket "$BID" --read-orgs 2>/dev/null \
        | grep -oE '[A-Za-z0-9_-]{40,}={0,2}' | head -1)
if [ -z "$TOK" ] || [ "${#TOK}" -lt 20 ]; then
  echo "FALLO creando token: $TOK"; exit 1
fi
sed -i "s/^INFLUX_TOKEN_READER=.*/INFLUX_TOKEN_READER=$TOK/" .env
echo "token-lectura OK (longitud ${#TOK})"
