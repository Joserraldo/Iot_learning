#!/bin/bash
# prep_env.sh — crea docker/.env con secretos nuevos en una VM limpia.
#
# Los secretos propios (Grafana, Influx) se generan aqui con openssl.
# Los de Brevo son EXTERNOS y no se pueden generar: llegan por el entorno
# (o por stdin). Nunca se escriben en el repo.
set -e
cd "$(dirname "$0")"
mkdir -p ../evidencias
G=$(openssl rand -hex 12)
IPW=$(openssl rand -hex 24)
KS=$(openssl rand -hex 24)

# Brevo: usuario relay asignado (GET /v3/account -> relay.data.userName) y la
# "SMTP key" del panel SMTP & SMTP API (xsmtpsib-...), NO la API key REST.
BREVO_EMAIL="${BREVO_EMAIL:-}"
BREVO_SMTP_KEY="${BREVO_SMTP_KEY:-}"
BREVO_FROM="${BREVO_FROM:-}"
ALERT_TO_EMAIL="${ALERT_TO_EMAIL:-}"
if [ -z "$BREVO_EMAIL" ] || [ -z "$BREVO_SMTP_KEY" ]; then
  echo "Faltan BREVO_EMAIL y BREVO_SMTP_KEY."
  echo "  export BREVO_EMAIL=<usuario-relay-smtp-brevo-com>"
  echo "  export BREVO_SMTP_KEY=<smtp-key-del-panel>"
  echo "  (opcional) export BREVO_FROM=... ALERT_TO_EMAIL=..."
  echo "y vuelve a ejecutar este script. Ver docker/.env.example."
  exit 1
fi

cat > .env <<EOF
GRAFANA_ADMIN_PASSWORD=$G
INFLUX_ORG=unab
INFLUX_BUCKET=telemetria
INFLUX_USERNAME=iot
INFLUX_PASSWORD=$IPW
INFLUX_API_TOKEN=$KS
INFLUX_TOKEN_READER=PLACEHOLDER
BREVO_EMAIL=$BREVO_EMAIL
BREVO_SMTP_KEY=$BREVO_SMTP_KEY
BREVO_FROM=$BREVO_FROM
ALERT_TO_EMAIL=$ALERT_TO_EMAIL
EOF
echo "ENV_LISTO $(wc -l < .env) lineas"
