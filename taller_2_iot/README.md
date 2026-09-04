# Taller 2: Sistema IoT conectado a Azure

## Descripción

El Taller 2 consistió en construir y poner en funcionamiento una solución IoT para monitorear las condiciones ambientales de un salón mediante **Azure IoT Central**. La solución integra dispositivos simulados en Azure, un nodo Python ejecutándose en una máquina virtual y un ESP32 simulado con Wokwi.

El sistema registra y envía telemetría de temperatura, humedad e iluminación. También permite consultar el estado del sistema desde un dashboard web y ejecutar acciones sobre los dispositivos.

## Componentes

- Dispositivos simulados nativamente en Azure IoT Central.
- Nodo Python ejecutándose en una VM de Azure.
- Dashboard web desarrollado con Flask.
- ESP32 simulado localmente con Wokwi for VS Code.
- Sensor DHT22 para temperatura y humedad.
- Potenciómetro para simular la iluminación.
- LED para representar el estado del sistema.
- Aprovisionamiento mediante Azure Device Provisioning Service (DPS).
- Comunicación mediante MQTT sobre TLS.

## Funcionalidades implementadas

- Envío periódico de `Temperature`, `Humidity` e `Iluminance` a Azure IoT Central.
- Visualización de lecturas, historial y estado del sistema en el dashboard Flask.
- Actualización de la propiedad `Set_temp_hvac`.
- Comando `Encender_hvac` para alternar el LED del ESP32.
- Comando `force_reading` para solicitar una lectura inmediata.
- Regla de alerta en Azure IoT Central que envía un correo cuando la temperatura supera los 27 °C.
- Verificación de la comunicación entre Azure IoT Central, la VM y el ESP32 simulado.

## Resultado

El taller fue completado y verificado satisfactoriamente. Se confirmó que:

- El nodo Python se conecta a Azure IoT Central desde la VM.
- La VM envía telemetría periódicamente.
- El dashboard Flask funciona y permite consultar y controlar el sistema.
- El ESP32 simulado se conecta a Azure IoT Central mediante Wokwi.
- El ESP32 envía telemetría y responde a los comandos configurados.
- La regla de alerta de temperatura queda configurada en IoT Central.

## Documentación

- [Bitácora del taller](docs/bitacora.md)
- [Guía para encender y operar la VM de Azure](docs/guia-vm-azure.md)
- [Documentación del proyecto Wokwi](wokwi/README.md)
- [Código del nodo Python](python-vm-01.py)

## Informe

El informe final en PDF todavía se encuentra en elaboración. Cuando esté terminado, se agregará directamente en esta carpeta junto con las evidencias finales.

> No se deben subir contraseñas, claves de dispositivos ni otros secretos al repositorio. Las credenciales deben mantenerse fuera de los archivos versionados.
