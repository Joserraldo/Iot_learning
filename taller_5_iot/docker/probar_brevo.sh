#!/bin/bash
# probar_brevo.sh — prueba de autenticacion SMTP contra Brevo SIN imprimir secretos.
# Corre en la VM:  bash ~/taller_5_iot/docker/probar_brevo.sh
# Esperado: LOGIN_OK. Si sale 535: la BREVO_SMTP_KEY del .env no es la "SMTP key"
# del panel de Brevo (las "API key" NO sirven para SMTP) o el BREVO_EMAIL no es
# el email de acceso de esa cuenta Brevo.
cd "$(dirname "$0")"
K=$(awk -F= '/^BREVO_SMTP_KEY=/{print $2}' .env | tr -d '\r')
E=$(awk -F= '/^BREVO_EMAIL=/{print $2}' .env)
echo "key_longitud=${#K} email=$E"
python3 - <<PYEOF
import smtplib
try:
    s = smtplib.SMTP("smtp-relay.brevo.com", 587, timeout=20)
    s.starttls(); s.login("$E", "$K"); s.quit()
    print("LOGIN_OK")
except Exception as e:
    print("LOGIN_FAIL", e)
PYEOF
