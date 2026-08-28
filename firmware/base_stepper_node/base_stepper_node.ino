#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// --- PIN DRIVER ULN2003 (AGGIORNATI) ---
const int IN1 = 25;
const int IN2 = 27;
const int IN3 = 14;
const int IN4 = 26;

// --- SPECIFICHE STEPPER (Half-Step 28BYJ-48) ---
const int STEPS_PER_REV = 4096; // 4096 passi per un giro completo di 360°
const int stepLookup[8] = {
  B01000,
  B01100,
  B00100,
  B00110,
  B00010,
  B00011,
  B00001,
  B01001
};

// --- BLE UUIDs (Allineati a config.py) ---
#define BASE_SERVICE_UUID      "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define BASE_AZIMUTH_CHAR_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"

BLECharacteristic *pAzimuthCharacteristic;
bool deviceConnected = false;
bool rotating = false;

long currentStep = 0;
int stepIndex = 0;
unsigned long lastStepTime = 0;
const unsigned long stepIntervalMicros = 2200; // ~9 secondi a giro completo

class BaseServerCallbacks: public BLEServerCallbacks {
  void onConnect(BLEServer* pServer) {
    deviceConnected = true;
    rotating = true;
    Serial.println("[BASE] Controller connesso, rotazione avviata");
  }
  void onDisconnect(BLEServer* pServer) {
    deviceConnected = false;
    rotating = false;
    // Disattiva tutte le bobine per evitare riscaldamento del motore a riposo
    digitalWrite(IN1, LOW);
    digitalWrite(IN2, LOW);
    digitalWrite(IN3, LOW);
    digitalWrite(IN4, LOW);
    Serial.println("[BASE] Controller disconnesso, motore fermato");
    pServer->startAdvertising();
  }
};

void setStepPins(int mask) {
  digitalWrite(IN1, (mask & B00001) ? HIGH : LOW);
  digitalWrite(IN2, (mask & B00010) ? HIGH : LOW);
  digitalWrite(IN3, (mask & B00100) ? HIGH : LOW);
  digitalWrite(IN4, (mask & B01000) ? HIGH : LOW);
}

void setup() {
  Serial.begin(115200);

  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);

  // Inizializzazione BLE
  BLEDevice::init("ESP32-Stepper-Base");
  BLEServer *pServer = BLEDevice::createServer();
  pServer->setCallbacks(new BaseServerCallbacks());

  BLEService *pService = pServer->createService(BASE_SERVICE_UUID);

  pAzimuthCharacteristic = pService->createCharacteristic(
    BASE_AZIMUTH_CHAR_UUID,
    BLECharacteristic::PROPERTY_NOTIFY
  );
  pAzimuthCharacteristic->addDescriptor(new BLE2902());

  pService->start();
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(BASE_SERVICE_UUID);
  pAdvertising->setScanResponse(true);
  pAdvertising->start();

  Serial.println("Base Stepper pronta (Pin D25, D27, D14, D26) in advertising...");
}

void loop() {
  if (rotating && deviceConnected) {
    unsigned long nowMicros = micros();
    if (nowMicros - lastStepTime >= stepIntervalMicros) {
      lastStepTime = nowMicros;

      // Avanzamento di 1 step
      stepIndex = (stepIndex + 1) % 8;
      setStepPins(stepLookup[stepIndex]);
      currentStep = (currentStep + 1) % STEPS_PER_REV;

      // Invia pacchetto BLE ogni 16 step (~1.4° di risoluzione)
      if (currentStep % 16 == 0) {
        float thetaDeg = (float(currentStep) / STEPS_PER_REV) * 360.0f;
        uint16_t thetaEnc = (uint16_t)(thetaDeg * 10.0f); // 0.0° - 360.0° -> 0 - 3600
        uint32_t nowMs = millis();

        // Pacchetto Base (6 Byte): [Theta_H, Theta_L, Time_B3, Time_B2, Time_B1, Time_B0]
        uint8_t packet[6];
        packet[0] = (thetaEnc >> 8) & 0xFF;
        packet[1] = thetaEnc & 0xFF;
        packet[2] = (nowMs >> 24) & 0xFF;
        packet[3] = (nowMs >> 16) & 0xFF;
        packet[4] = (nowMs >> 8) & 0xFF;
        packet[5] = nowMs & 0xFF;

        pAzimuthCharacteristic->setValue(packet, 6);
        pAzimuthCharacteristic->notify();
      }
    }
  } else {
    delay(20);
  }
}