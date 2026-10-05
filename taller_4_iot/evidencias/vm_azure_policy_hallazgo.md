# Hallazgo: pérdida de VMs y error Azure Policy al redesplegar

**Taller 4 · Lab 4 · UNAB · José Tellez**
**Fecha:** 2026-10-02

---

## 1. Contexto: pérdida de las máquinas virtuales

Durante la preparación del Taller 4 detectamos que **todas las máquinas virtuales
de la cuenta Azure se perdieron** por un error desconocido. La VM anterior del
proyecto (IP `57.156.66.112` y posterior `57.156.62.111`) dejó de responder en
todos los puertos (SSH 22, HTTP 80/443, MQTT 8883, AMQP 5671): *timeout* en todos.

No fue un problema de red local: verificamos con `socket.connect()` desde la
máquina de desarrollo contra ambas IPs en múltiples puertos y ninguna responde.
La VM simplemente ya no existía en la cuenta.

> Consecuencia adicional: al revisar la app de IoT Central `clima-salones-app-jose`
> vía su REST API, la **plantilla `consola-unab-ambiental` del Lab 2/3 y los
> dispositivos `23z8rpgm6s4` / `esp32-wokwi-01` ya no existían** (HTTP 404). La
> app fue recreada con otro `idScope` (`0ne0128155B`). Hubo que recrear la
> plantilla y crear dispositivos dedicados (ver `provision_devices.py`).

## 2. Error al redesplegar la VM

Al intentar crear una VM nueva para continuar el trabajo, el despliegue falló:

- **Excepción:** `RequestDisallowedByAzure` (`InvalidTemplateDeployment`).
- **Causa:** una **directiva de Azure Policy** de la suscripción bloqueó el
  despliegue de la VM y sus recursos (VNet, IP pública, NSG) en la región
  **Mexico Central** (`mexicocentral`), donde se intentó por defecto.

## 3. Diagnóstico (Cloud Shell / Azure CLI)

```bash
az policy assignment list --query "[].parameters" --output json
```

El resultado mostró las **únicas 5 regiones permitidas** por la directiva:

| Región | Nombre Azure |
|--------|-------------|
| Central US | `centralus` |
| East US | `eastus` |
| West US 3 | `westus3` |
| North Central US | `northcentralus` |
| Brazil South | `brazilsouth` |

Inicialmente se usaba **Central Chile** o **Mexico Central**, pero ninguna de las
dos estaba en la lista de regiones autorizadas por la política → por eso el
despliegue era bloqueado.

## 4. Solución aplicada

Se revisó la **disponibilidad del tamaño de máquina** requerido
(`Standard_B2ats_v2`) dentro de las 5 regiones autorizadas. La **única** región
que soportaba ese SKU exacto era **North Central US** (`northcentralus`).

La VM se creó entonces en **North Central US**, que además tenía el plan/SKU que
necesitábamos. Eso resolvió el problema de despliegue.

### VM resultante

| Dato | Valor |
|------|-------|
| Hostname | `vmtalleresjose` |
| IP pública | `52.237.172.24` |
| Región | North Central US (`northcentralus`) |
| SO | Ubuntu 24.04 LTS |
| Usuario SSH | `azureuser` |
| Puerto SSH | 22 (abierto) |

## 5. Verificación de conectividad IoT desde la nueva VM

Se confirmó desde la VM que tiene **salida abierta** a los puertos de Azure IoT
hacia el hub de la app (`iotc-47a415d3-...azure-devices.net`):

| Puerto | Protocolo | Estado |
|--------|-----------|--------|
| 8883 | MQTT/TLS | abierto |
| 5671 | AMQP/TLS | abierto |
| 443 | HTTPS / AMQP-WS / MQTT-WS | abierto |
| 5683 | CoAP (UDP, local VM) | local |

## 6. Lecciones para la bitácora

- La política de la suscripción **restringe regiones**: hay que consultar
  `az policy assignment list` antes de elegir región.
- El SKU de VM condiciona la región: verificar disponibilidad del tamaño en las
  regiones permitidas.
- Verificar la salida a puertos IoT (8883/5671/443) en la VM nueva antes de
  desplegar los clientes.
- Al recrear infraestructura de Azure, validar que los recursos de IoT Central
  (plantillas, dispositivos) sigan existiendo; si se perdieron, recrearlos
  (idempotente vía `provision_devices.py`).
