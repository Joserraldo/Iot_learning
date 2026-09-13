// Copyright (c) Microsoft Corporation. All rights reserved.
// SPDX-License-Identifier: MIT
//
// Adapted for UNAB-Ambiental (consola-unab-ambiental):
//   Telemetry: Temperature, Humidity, Iluminance
//   Command:   setAlertLed

#include <stdarg.h>
#include <stdlib.h>

#include <az_core.h>
#include <az_iot.h>

#include <DHT.h>

#include "AzureIoT.h"
#include "Azure_IoT_PnP_Template.h"
#include "iot_configs.h"

#include <az_precondition_internal.h>

/* --- Defines --- */
#define AZURE_PNP_MODEL_ID IOT_CONFIG_MODEL_ID

// Telemetry property names
#define TELEMETRY_PROP_NAME_TEMPERATURE "Temperature"
#define TELEMETRY_PROP_NAME_HUMIDITY "Humidity"
#define TELEMETRY_PROP_NAME_ILUMINANCE "Iluminance"

// Command names (plantilla consola-unab-ambiental + compatibilidad setAlertLed)
static az_span COMMAND_NAME_SET_ALERT_LED = AZ_SPAN_FROM_STR("setAlertLed");
static az_span COMMAND_NAME_ENCENDER_HVAC = AZ_SPAN_FROM_STR("Encender_hvac");
static az_span COMMAND_NAME_FORCE_READING = AZ_SPAN_FROM_STR("force_reading");

#define COMMAND_RESPONSE_CODE_OK 200
#define COMMAND_RESPONSE_CODE_ACCEPTED 202
#define COMMAND_RESPONSE_CODE_REJECTED 404

// Writable properties (plantilla: Set_temp_hvac; patron oficial: telemetryFrequencySecs)
#define WRITABLE_PROPERTY_TELEMETRY_FREQ_SECS "telemetryFrequencySecs"
#define WRITABLE_PROPERTY_SET_TEMP_HVAC "Set_temp_hvac"
#define WRITABLE_PROPERTY_RESPONSE_SUCCESS "success"

// Reported properties (plantilla)
#define REPORTED_PROPERTY_ID_SALON "ID_salon"
#define REPORTED_PROPERTY_LED_STATE "Estado_semaforo_LED"
#define ID_SALON_VALUE "ESP32-WOKWI-01"

#define DOUBLE_DECIMAL_PLACE_DIGITS 1

/* --- Function Checks and Returns --- */
#define RESULT_OK 0
#define RESULT_ERROR __LINE__

#define EXIT_IF_TRUE(condition, retcode, message, ...) \
  do                                                   \
  {                                                    \
    if (condition)                                     \
    {                                                  \
      LogError(message, ##__VA_ARGS__);                \
      return retcode;                                  \
    }                                                  \
  } while (0)

#define EXIT_IF_AZ_FAILED(azresult, retcode, message, ...) \
  EXIT_IF_TRUE(az_result_failed(azresult), retcode, message, ##__VA_ARGS__)

/* --- Data --- */
#define DATA_BUFFER_SIZE 1024
static uint8_t data_buffer[DATA_BUFFER_SIZE];
static uint32_t telemetry_send_count = 0;

static size_t telemetry_frequency_in_seconds = 10;
static time_t last_telemetry_send_time = INDEFINITE_TIME;

static bool led_on = false;
static double set_temp_hvac = 22.0;
static uint32_t reported_prop_request_id = 1000;

// DHT sensor instance — defined in sketch.ino
extern DHT dht;

/* --- Function Prototypes --- */
static int generate_telemetry_payload(
    uint8_t* payload_buffer,
    size_t payload_buffer_size,
    size_t* payload_buffer_length);
static int generate_device_info_payload(
    az_iot_hub_client const* hub_client,
    uint8_t* payload_buffer,
    size_t payload_buffer_size,
    size_t* payload_buffer_length);
static int consume_properties_and_generate_response(
    azure_iot_t* azure_iot,
    az_span properties,
    uint8_t* buffer,
    size_t buffer_size,
    size_t* response_length);
static void read_sensors(float* temperature, float* humidity, float* iluminance);
static int send_led_state_reported(azure_iot_t* azure_iot);

/* --- Public Functions --- */
void azure_pnp_init() {}

const az_span azure_pnp_get_model_id() { return AZ_SPAN_FROM_STR(AZURE_PNP_MODEL_ID); }

void azure_pnp_set_telemetry_frequency(size_t frequency_in_seconds)
{
  telemetry_frequency_in_seconds = frequency_in_seconds;
  LogInfo("Telemetry frequency set to once every %d seconds.", telemetry_frequency_in_seconds);
}

/* Application-specific data section */

int azure_pnp_send_telemetry(azure_iot_t* azure_iot)
{
  _az_PRECONDITION_NOT_NULL(azure_iot);

  time_t now = time(NULL);

  if (now == INDEFINITE_TIME)
  {
    LogError("Failed getting current time for controlling telemetry.");
    return RESULT_ERROR;
  }
  else if (
      last_telemetry_send_time == INDEFINITE_TIME
      || difftime(now, last_telemetry_send_time) >= telemetry_frequency_in_seconds)
  {
    size_t payload_size;

    last_telemetry_send_time = now;

    if (generate_telemetry_payload(data_buffer, DATA_BUFFER_SIZE, &payload_size) != RESULT_OK)
    {
      LogError("Failed generating telemetry payload.");
      return RESULT_ERROR;
    }

    if (azure_iot_send_telemetry(azure_iot, az_span_create(data_buffer, payload_size)) != 0)
    {
      LogError("Failed sending telemetry.");
      return RESULT_ERROR;
    }
  }

  return RESULT_OK;
}

int azure_pnp_send_device_info(azure_iot_t* azure_iot, uint32_t request_id)
{
  _az_PRECONDITION_NOT_NULL(azure_iot);

  int result;
  size_t length;

  result = generate_device_info_payload(
      &azure_iot->iot_hub_client, data_buffer, DATA_BUFFER_SIZE, &length);
  EXIT_IF_TRUE(result != RESULT_OK, RESULT_ERROR, "Failed generating telemetry payload.");

  result = azure_iot_send_properties_update(
      azure_iot, request_id, az_span_create(data_buffer, length));
  EXIT_IF_TRUE(result != RESULT_OK, RESULT_ERROR, "Failed sending reported properties update.");

  return RESULT_OK;
}

int azure_pnp_handle_command_request(azure_iot_t* azure_iot, command_request_t command)
{
  _az_PRECONDITION_NOT_NULL(azure_iot);

  uint16_t response_code;
  az_span response_payload = AZ_SPAN_EMPTY;

  if (az_span_is_content_equal(command.command_name, COMMAND_NAME_SET_ALERT_LED))
  {
    // Parse payload for {"value":true} or {"value":false}
    bool new_state = false;
    char payload_buf[64];
    int plen = (az_span_size(command.payload) < 63)
        ? az_span_size(command.payload) : 63;
    memcpy(payload_buf, az_span_ptr(command.payload), plen);
    payload_buf[plen] = '\0';

    if (strstr(payload_buf, "true") != NULL || strstr(payload_buf, "\"on\"") != NULL)
    {
      new_state = true;
    }

    led_on = new_state;
    digitalWrite(PIN_LED, led_on ? HIGH : LOW);
    LogInfo("setAlertLed -> %s", led_on ? "ON" : "OFF");
    (void)send_led_state_reported(azure_iot);
    response_code = COMMAND_RESPONSE_CODE_ACCEPTED;
  }
  else if (az_span_is_content_equal(command.command_name, COMMAND_NAME_ENCENDER_HVAC))
  {
    // Comando de la plantilla: alterna el LED de alerta (GPIO2) y reporta el semaforo.
    led_on = !led_on;
    digitalWrite(PIN_LED, led_on ? HIGH : LOW);
    LogInfo("Encender_hvac -> LED %s", led_on ? "ON" : "OFF");

    (void)send_led_state_reported(azure_iot);

    az_json_writer jw;
    az_result rc = az_json_writer_init(&jw, az_span_create(data_buffer, DATA_BUFFER_SIZE), NULL);
    if (!az_result_failed(rc))
    {
      rc = az_json_writer_append_begin_object(&jw);
      rc = az_json_writer_append_property_name(&jw, AZ_SPAN_FROM_STR("resultado"));
      rc = az_json_writer_append_string(
          &jw, led_on ? AZ_SPAN_FROM_STR("HVAC encendido, LED ON")
                      : AZ_SPAN_FROM_STR("HVAC apagado, LED OFF"));
      rc = az_json_writer_append_property_name(&jw, AZ_SPAN_FROM_STR("set_temp_hvac"));
      rc = az_json_writer_append_double(&jw, set_temp_hvac, 1);
      rc = az_json_writer_append_end_object(&jw);

      if (!az_result_failed(rc))
      {
        az_span used = az_json_writer_get_bytes_used_in_destination(&jw);
        data_buffer[az_span_size(used)] = null_terminator;
        response_payload = az_span_create(data_buffer, az_span_size(used));
      }
    }
    response_code = COMMAND_RESPONSE_CODE_OK;
  }
  else if (az_span_is_content_equal(command.command_name, COMMAND_NAME_FORCE_READING))
  {
    // Fuerza una telemetria inmediata (el proximo loop la envia) + lectura en la respuesta.
    last_telemetry_send_time = INDEFINITE_TIME;

    float temperature, humidity, iluminance;
    read_sensors(&temperature, &humidity, &iluminance);

    az_json_writer jw;
    az_result rc = az_json_writer_init(&jw, az_span_create(data_buffer, DATA_BUFFER_SIZE), NULL);
    if (!az_result_failed(rc))
    {
      rc = az_json_writer_append_begin_object(&jw);
      rc = az_json_writer_append_property_name(&jw, AZ_SPAN_FROM_STR(TELEMETRY_PROP_NAME_TEMPERATURE));
      rc = az_json_writer_append_double(&jw, temperature, DOUBLE_DECIMAL_PLACE_DIGITS);
      rc = az_json_writer_append_property_name(&jw, AZ_SPAN_FROM_STR(TELEMETRY_PROP_NAME_HUMIDITY));
      rc = az_json_writer_append_double(&jw, humidity, DOUBLE_DECIMAL_PLACE_DIGITS);
      rc = az_json_writer_append_property_name(&jw, AZ_SPAN_FROM_STR(TELEMETRY_PROP_NAME_ILUMINANCE));
      rc = az_json_writer_append_double(&jw, iluminance, DOUBLE_DECIMAL_PLACE_DIGITS);
      rc = az_json_writer_append_end_object(&jw);

      if (!az_result_failed(rc))
      {
        az_span used = az_json_writer_get_bytes_used_in_destination(&jw);
        data_buffer[az_span_size(used)] = null_terminator;
        response_payload = az_span_create(data_buffer, az_span_size(used));
      }
    }
    LogInfo("force_reading -> telemetria inmediata encolada");
    response_code = COMMAND_RESPONSE_CODE_OK;
  }
  else
  {
    LogError(
        "Command not recognized (%.*s).",
        az_span_size(command.command_name),
        az_span_ptr(command.command_name));
    response_code = COMMAND_RESPONSE_CODE_REJECTED;
  }

  return azure_iot_send_command_response(
      azure_iot, command.request_id, response_code, response_payload);
}

int azure_pnp_handle_properties_update(
    azure_iot_t* azure_iot,
    az_span properties,
    uint32_t request_id)
{
  _az_PRECONDITION_NOT_NULL(azure_iot);
  _az_PRECONDITION_VALID_SPAN(properties, 1, false);

  int result;
  size_t length;

  result = consume_properties_and_generate_response(
      azure_iot, properties, data_buffer, DATA_BUFFER_SIZE, &length);
  EXIT_IF_TRUE(result != RESULT_OK, RESULT_ERROR, "Failed generating properties ack payload.");

  result = azure_iot_send_properties_update(
      azure_iot, request_id, az_span_create(data_buffer, length));
  EXIT_IF_TRUE(result != RESULT_OK, RESULT_ERROR, "Failed sending reported properties update.");

  return RESULT_OK;
}

/* --- Internal Functions --- */

static void read_sensors(float* temperature, float* humidity, float* iluminance)
{
  *temperature = dht.readTemperature();
  *humidity = dht.readHumidity();

  int raw = analogRead(PIN_POT);
  *iluminance = map(raw, 0, 4095, 100, 800);

  if (isnan(*temperature) || isnan(*humidity))
  {
    *temperature = 24.0f;
    *humidity = 50.0f;
  }

  LogInfo(
      "Sensores: T=%.1f C, H=%.1f %%, Lux=%.0f, Set_temp_hvac=%.1f C, LED=%s",
      *temperature,
      *humidity,
      *iluminance,
      set_temp_hvac,
      led_on ? "ON" : "OFF");
}

static int send_led_state_reported(azure_iot_t* azure_iot)
{
  az_json_writer jw;
  az_result rc = az_json_writer_init(&jw, az_span_create(data_buffer, DATA_BUFFER_SIZE), NULL);
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed init json writer for LED state.");

  rc = az_json_writer_append_begin_object(&jw);
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed opening LED state json.");
  rc = az_json_writer_append_property_name(&jw, AZ_SPAN_FROM_STR(REPORTED_PROPERTY_LED_STATE));
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed LED state property name.");
  rc = az_json_writer_append_string(
      &jw, led_on ? AZ_SPAN_FROM_STR("ON") : AZ_SPAN_FROM_STR("OFF"));
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed LED state property value.");
  rc = az_json_writer_append_end_object(&jw);
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed closing LED state json.");

  az_span used = az_json_writer_get_bytes_used_in_destination(&jw);
  data_buffer[az_span_size(used)] = null_terminator;

  return azure_iot_send_properties_update(
      azure_iot, reported_prop_request_id++, az_span_create(data_buffer, az_span_size(used)));
}

static int generate_telemetry_payload(
    uint8_t* payload_buffer,
    size_t payload_buffer_size,
    size_t* payload_buffer_length)
{
  az_json_writer jw;
  az_result rc;
  az_span payload_buffer_span = az_span_create(payload_buffer, payload_buffer_size);
  az_span json_span;
  float temperature, humidity, iluminance;

  read_sensors(&temperature, &humidity, &iluminance);

  rc = az_json_writer_init(&jw, payload_buffer_span, NULL);
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed initializing json writer for telemetry.");

  rc = az_json_writer_append_begin_object(&jw);
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed setting telemetry json root.");

  rc = az_json_writer_append_property_name(&jw, AZ_SPAN_FROM_STR(TELEMETRY_PROP_NAME_TEMPERATURE));
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed adding temperature property name.");
  rc = az_json_writer_append_double(&jw, temperature, DOUBLE_DECIMAL_PLACE_DIGITS);
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed adding temperature value.");

  rc = az_json_writer_append_property_name(&jw, AZ_SPAN_FROM_STR(TELEMETRY_PROP_NAME_HUMIDITY));
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed adding humidity property name.");
  rc = az_json_writer_append_double(&jw, humidity, DOUBLE_DECIMAL_PLACE_DIGITS);
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed adding humidity value.");

  rc = az_json_writer_append_property_name(&jw, AZ_SPAN_FROM_STR(TELEMETRY_PROP_NAME_ILUMINANCE));
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed adding iluminance property name.");
  rc = az_json_writer_append_double(&jw, iluminance, DOUBLE_DECIMAL_PLACE_DIGITS);
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed adding iluminance value.");

  rc = az_json_writer_append_end_object(&jw);
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed closing telemetry json payload.");

  payload_buffer_span = az_json_writer_get_bytes_used_in_destination(&jw);

  if ((payload_buffer_size - az_span_size(payload_buffer_span)) < 1)
  {
    LogError("Insufficient space for telemetry payload null terminator.");
    return RESULT_ERROR;
  }

  payload_buffer[az_span_size(payload_buffer_span)] = null_terminator;
  *payload_buffer_length = az_span_size(payload_buffer_span);

  return RESULT_OK;
}

static int generate_device_info_payload(
    az_iot_hub_client const* hub_client,
    uint8_t* payload_buffer,
    size_t payload_buffer_size,
    size_t* payload_buffer_length)
{
  az_json_writer jw;
  az_result rc;
  az_span payload_buffer_span = az_span_create(payload_buffer, payload_buffer_size);
  az_span json_span;

#define DEVINFO_COMPONENT "deviceInformation"
#define DEVINFO_MANUFACTURER "UNAB"
#define DEVINFO_MODEL "ESP32-Wokwi"
#define DEVINFO_VERSION "1.0.0"
#define DEVINFO_OS "Arduino"
#define DEVINFO_ARCH "ESP32-WROVER"
#define DEVINFO_PROC_MFR "Espressif"
#define DEVINFO_STORAGE 4096
#define DEVINFO_MEMORY 8192

  rc = az_json_writer_init(&jw, payload_buffer_span, NULL);
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed initializing json writer for device info.");

  rc = az_json_writer_append_begin_object(&jw);
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed setting device info json root.");

  // Reported properties definidas por la plantilla consola-unab-ambiental.
  rc = az_json_writer_append_property_name(&jw, AZ_SPAN_FROM_STR(REPORTED_PROPERTY_ID_SALON));
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed adding ID_salon.");
  rc = az_json_writer_append_string(&jw, AZ_SPAN_FROM_STR(ID_SALON_VALUE));
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed adding ID_salon value.");

  rc = az_json_writer_append_property_name(&jw, AZ_SPAN_FROM_STR(REPORTED_PROPERTY_LED_STATE));
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed adding Estado_semaforo_LED.");
  rc = az_json_writer_append_string(
      &jw, led_on ? AZ_SPAN_FROM_STR("ON") : AZ_SPAN_FROM_STR("OFF"));
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed adding Estado_semaforo_LED value.");

  rc = az_json_writer_append_property_name(&jw, AZ_SPAN_FROM_STR(WRITABLE_PROPERTY_SET_TEMP_HVAC));
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed adding Set_temp_hvac.");
  rc = az_json_writer_append_double(&jw, set_temp_hvac, 1);
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed adding Set_temp_hvac value.");

  rc = az_iot_hub_client_properties_writer_begin_component(
      hub_client, &jw, AZ_SPAN_FROM_STR(DEVINFO_COMPONENT));
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed writing component name.");

  rc = az_json_writer_append_property_name(&jw, AZ_SPAN_FROM_STR("manufacturer"));
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed adding manufacturer.");
  rc = az_json_writer_append_string(&jw, AZ_SPAN_FROM_STR(DEVINFO_MANUFACTURER));
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed adding manufacturer value.");

  rc = az_json_writer_append_property_name(&jw, AZ_SPAN_FROM_STR("model"));
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed adding model.");
  rc = az_json_writer_append_string(&jw, AZ_SPAN_FROM_STR(DEVINFO_MODEL));
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed adding model value.");

  rc = az_json_writer_append_property_name(&jw, AZ_SPAN_FROM_STR("swVersion"));
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed adding swVersion.");
  rc = az_json_writer_append_string(&jw, AZ_SPAN_FROM_STR(DEVINFO_VERSION));
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed adding swVersion value.");

  rc = az_json_writer_append_property_name(&jw, AZ_SPAN_FROM_STR("osName"));
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed adding osName.");
  rc = az_json_writer_append_string(&jw, AZ_SPAN_FROM_STR(DEVINFO_OS));
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed adding osName value.");

  rc = az_json_writer_append_property_name(&jw, AZ_SPAN_FROM_STR("processorArchitecture"));
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed adding processorArchitecture.");
  rc = az_json_writer_append_string(&jw, AZ_SPAN_FROM_STR(DEVINFO_ARCH));
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed adding processorArchitecture value.");

  rc = az_json_writer_append_property_name(&jw, AZ_SPAN_FROM_STR("processorManufacturer"));
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed adding processorManufacturer.");
  rc = az_json_writer_append_string(&jw, AZ_SPAN_FROM_STR(DEVINFO_PROC_MFR));
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed adding processorManufacturer value.");

  rc = az_json_writer_append_property_name(&jw, AZ_SPAN_FROM_STR("totalStorage"));
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed adding totalStorage.");
  rc = az_json_writer_append_double(&jw, DEVINFO_STORAGE, 0);
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed adding totalStorage value.");

  rc = az_json_writer_append_property_name(&jw, AZ_SPAN_FROM_STR("totalMemory"));
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed adding totalMemory.");
  rc = az_json_writer_append_double(&jw, DEVINFO_MEMORY, 0);
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed adding totalMemory value.");

  rc = az_iot_hub_client_properties_writer_end_component(hub_client, &jw);
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed closing component object.");

  rc = az_json_writer_append_end_object(&jw);
  EXIT_IF_AZ_FAILED(rc, RESULT_ERROR, "Failed closing device info json payload.");

  payload_buffer_span = az_json_writer_get_bytes_used_in_destination(&jw);

  if ((payload_buffer_size - az_span_size(payload_buffer_span)) < 1)
  {
    LogError("Insufficient space for device info payload null terminator.");
    return RESULT_ERROR;
  }

  payload_buffer[az_span_size(payload_buffer_span)] = null_terminator;
  *payload_buffer_length = az_span_size(payload_buffer_span);

  return RESULT_OK;
}

static int generate_properties_update_response(
    azure_iot_t* azure_iot,
    az_span property_name,
    double value,
    int32_t version,
    uint8_t* buffer,
    size_t buffer_size,
    size_t* response_length)
{
  az_result azrc;
  az_json_writer jw;
  az_span response = az_span_create(buffer, buffer_size);

  azrc = az_json_writer_init(&jw, response, NULL);
  EXIT_IF_AZ_FAILED(
      azrc, RESULT_ERROR, "Failed initializing json writer for properties update response.");

  azrc = az_json_writer_append_begin_object(&jw);
  EXIT_IF_AZ_FAILED(azrc, RESULT_ERROR, "Failed opening json in properties update response.");

  // This PnP Template does not have a named component,
  // so az_iot_hub_client_properties_writer_begin_component is not needed.

  azrc = az_iot_hub_client_properties_writer_begin_response_status(
      &azure_iot->iot_hub_client,
      &jw,
      property_name,
      (int32_t)AZ_IOT_STATUS_OK,
      version,
      AZ_SPAN_FROM_STR(WRITABLE_PROPERTY_RESPONSE_SUCCESS));
  EXIT_IF_AZ_FAILED(azrc, RESULT_ERROR, "Failed appending status to properties update response.");

  azrc = az_json_writer_append_double(&jw, value, 1);
  EXIT_IF_AZ_FAILED(
      azrc, RESULT_ERROR, "Failed appending frequency value to properties update response.");

  azrc = az_iot_hub_client_properties_writer_end_response_status(&azure_iot->iot_hub_client, &jw);
  EXIT_IF_AZ_FAILED(
      azrc, RESULT_ERROR, "Failed closing status section in properties update response.");

  // This PnP Template does not have a named component,
  // so az_iot_hub_client_properties_writer_end_component is not needed.

  azrc = az_json_writer_append_end_object(&jw);
  EXIT_IF_AZ_FAILED(azrc, RESULT_ERROR, "Failed closing json in properties update response.");

  *response_length = az_span_size(az_json_writer_get_bytes_used_in_destination(&jw));

  return RESULT_OK;
}

static int consume_properties_and_generate_response(
    azure_iot_t* azure_iot,
    az_span properties,
    uint8_t* buffer,
    size_t buffer_size,
    size_t* response_length)
{
  int result;
  az_json_reader jr;
  az_span component_name;
  int32_t version = 0;

  az_result azrc = az_json_reader_init(&jr, properties, NULL);
  EXIT_IF_AZ_FAILED(azrc, RESULT_ERROR, "Failed initializing json reader for properties update.");

  const az_iot_hub_client_properties_message_type message_type
      = AZ_IOT_HUB_CLIENT_PROPERTIES_MESSAGE_TYPE_WRITABLE_UPDATED;

  azrc = az_iot_hub_client_properties_get_properties_version(
      &azure_iot->iot_hub_client, &jr, message_type, &version);
  EXIT_IF_AZ_FAILED(azrc, RESULT_ERROR, "Failed writable properties version.");

  azrc = az_json_reader_init(&jr, properties, NULL);
  EXIT_IF_AZ_FAILED(
      azrc, RESULT_ERROR, "Failed re-initializing json reader for properties update.");

  while (az_result_succeeded(
      azrc = az_iot_hub_client_properties_get_next_component_property(
          &azure_iot->iot_hub_client,
          &jr,
          message_type,
          AZ_IOT_HUB_CLIENT_PROPERTY_WRITABLE,
          &component_name)))
  {
    if (az_json_token_is_text_equal(
            &jr.token, AZ_SPAN_FROM_STR(WRITABLE_PROPERTY_TELEMETRY_FREQ_SECS)))
    {
      int32_t value;
      azrc = az_json_reader_next_token(&jr);
      EXIT_IF_AZ_FAILED(azrc, RESULT_ERROR, "Failed getting writable properties next token.");

      azrc = az_json_token_get_int32(&jr.token, &value);
      EXIT_IF_AZ_FAILED(azrc, RESULT_ERROR, "Failed getting writable properties int32_t value.");

      azure_pnp_set_telemetry_frequency((size_t)value);

      result = generate_properties_update_response(
          azure_iot,
          AZ_SPAN_FROM_STR(WRITABLE_PROPERTY_TELEMETRY_FREQ_SECS),
          (double)value,
          version,
          buffer,
          buffer_size,
          response_length);
      EXIT_IF_TRUE(
          result != RESULT_OK, RESULT_ERROR, "generate_properties_update_response failed.");
    }
    else if (az_json_token_is_text_equal(
            &jr.token, AZ_SPAN_FROM_STR(WRITABLE_PROPERTY_SET_TEMP_HVAC)))
    {
      double value;
      azrc = az_json_reader_next_token(&jr);
      EXIT_IF_AZ_FAILED(azrc, RESULT_ERROR, "Failed getting Set_temp_hvac next token.");

      azrc = az_json_token_get_double(&jr.token, &value);
      EXIT_IF_AZ_FAILED(azrc, RESULT_ERROR, "Failed getting Set_temp_hvac double value.");

      set_temp_hvac = value;
      LogInfo("Set_temp_hvac -> %.1f C", value);

      result = generate_properties_update_response(
          azure_iot,
          AZ_SPAN_FROM_STR(WRITABLE_PROPERTY_SET_TEMP_HVAC),
          value,
          version,
          buffer,
          buffer_size,
          response_length);
      EXIT_IF_TRUE(
          result != RESULT_OK, RESULT_ERROR, "generate_properties_update_response failed.");
    }
    else
    {
      LogError(
          "Unexpected property received (%.*s).",
          az_span_size(jr.token.slice),
          az_span_ptr(jr.token.slice));
    }

    azrc = az_json_reader_next_token(&jr);
    EXIT_IF_AZ_FAILED(
        azrc, RESULT_ERROR, "Failed moving to next json token of writable properties.");

    azrc = az_json_reader_skip_children(&jr);
    EXIT_IF_AZ_FAILED(azrc, RESULT_ERROR, "Failed skipping children of writable properties.");

    azrc = az_json_reader_next_token(&jr);
    EXIT_IF_AZ_FAILED(
        azrc, RESULT_ERROR, "Failed moving to next json token of writable properties (again).");
  }

  return RESULT_OK;
}