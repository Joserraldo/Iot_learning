# wokwi-dht22 Reference | Wokwi Docs

> Source: https://docs.wokwi.com/parts/wokwi-dht22
> Cached: 2026-09-03T18:33:27.612Z

---

- [](/)
- Diagram Reference
- wokwi-dht22

On this page# wokwi-dht22 Reference

Digital Humidity and Temperature sensor.

## Pin names[​](#pin-names)

NameDescriptionVCCPositive voltageSDADigital data pin (input/output)NCNot connectedGNDGround
## Attributes[​](#attributes)

NameDescriptionDefault valuetemperatureInitial temperature value (celsius)"24"humidityInitial relative humidity value (percentage)"40"
## Controlling the temperature[​](#controlling-the-temperature)

You can change the temperature and humidity values while the simulation is running.
Click on the DHT22 sensor and a small popup window will open. Use the temperature and
humidity sliders to change the values. Click "Hide" to close the popup window.
warningIf you are trying to read this sensor from the ESP32, use the "DHT sensor library for ESPx" library. Other DHT22 libraries may not work reliably on the ESP32. You can use this [example project](https://wokwi.com/projects/322410731508073042) as a starting point.

## Simulator examples[​](#simulator-examples)

- [DHTlib example](https://wokwi.com/projects/344892337559700051)

- [DHT-sensor-library examples](https://wokwi.com/projects/344892587898831442)

- [DHT22 on the ESP32](https://wokwi.com/projects/322410731508073042)

[Edit this page](https://github.com/wokwi/wokwi-docs/edit/main/docs/parts/wokwi-dht22.md)