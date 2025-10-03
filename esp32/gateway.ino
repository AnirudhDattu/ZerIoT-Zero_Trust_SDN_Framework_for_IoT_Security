#include <WiFi.h>
#include <HTTPClient.h>

const char *ap_ssid = "ESP32-AP"; // Gateway AP
const char *ap_password = "12345678";

const char *sta_ssid = "YourWiFi"; // Connects to laptop WiFi
const char *sta_password = "YourWiFiPassword";

const char *controller_ip = "192.168.1.100"; // Laptop IP where controller.py runs
WiFiServer server(80);

void setup()
{
    Serial.begin(115200);

    // Dual mode: AP + STA
    WiFi.mode(WIFI_AP_STA);

    // Start AP for nodes
    WiFi.softAP(ap_ssid, ap_password);
    Serial.println("Gateway AP Started");

    // Connect to STA WiFi
    WiFi.begin(sta_ssid, sta_password);
    while (WiFi.status() != WL_CONNECTED)
    {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nConnected to WiFi");

    server.begin();
}

void loop()
{
    WiFiClient client = server.available();
    if (client)
    {
        String request = client.readStringUntil('\r');
        client.flush();
        Serial.println("Received from node: " + request);

        if (WiFi.status() == WL_CONNECTED)
        {
            HTTPClient http;
            http.begin("http://" + String(controller_ip) + ":5000/data");
            http.addHeader("Content-Type", "application/json");
            int code = http.POST(request);
            Serial.println("Forwarded to controller, response: " + String(code));
            http.end();
        }

        client.println("HTTP/1.1 200 OK");
        client.println("Content-Type: text/plain");
        client.println();
        client.println("Gateway received");
        client.stop();
    }
}
