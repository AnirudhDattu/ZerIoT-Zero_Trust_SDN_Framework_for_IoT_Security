#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <time.h>

const char *ssid = "ESP32-AP";
const char *password = "12345678";
const char *controller_ip = "192.168.4.1"; // Gateway IP

String device_id = "ESP32_2"; // change for each node: ESP32_2, ESP32_3, ESP32_4
String token = "";

void setup()
{
    Serial.begin(115200);
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED)
    {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nConnected to Gateway");

    // Request token from controller (via gateway)
    if (WiFi.status() == WL_CONNECTED)
    {
        HTTPClient http;
        http.begin("http://" + String(controller_ip) + ":5000/get_token");
        http.addHeader("Content-Type", "application/json");

        String payload = "{\"device_id\":\"" + device_id + "\",\"mac_address\":\"" + WiFi.macAddress() + "\"}";
        int code = http.POST(payload);
        if (code == 200)
        {
            token = http.getString();
            Serial.println("Received token: " + token);
        }
        else
        {
            Serial.println("Token request failed");
        }
        http.end();
    }
}

void loop()
{
    if (WiFi.status() == WL_CONNECTED && token != "")
    {
        HTTPClient http;
        http.begin("http://" + String(controller_ip) + ":5000/data");
        http.addHeader("Content-Type", "application/json");

        // Random test values
        float temp = random(200, 300) / 10.0;
        int humidity = random(40, 70);

        // Build JSON
        StaticJsonDocument<200> doc;
        doc["device_id"] = device_id;
        doc["token"] = token;
        doc["timestamp"] = String(millis() / 1000);
        doc["data"] = String(temp);

        String json;
        serializeJson(doc, json);

        int code = http.POST(json);
        Serial.println("Sent: " + json + " | Response: " + String(code));
        http.end();
    }

    delay(5000);
}
