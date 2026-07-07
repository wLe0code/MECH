/*
 * MECH — Firmware del Arduino Uno R3
 *
 * Roles del Arduino:
 *   - Mover el robot: 4 motores DC (ruedas mecanum) vía 2x driver L298N.
 *   - Mover 2 brazos (servos MG996R).
 *   - Escuchar comandos por Serial desde la Raspberry Pi 5.
 *
 * NOTA: este robot NO tiene cabeza movil ni sensor de obstaculos. El comando
 * HEAD se reconoce pero NO hace nada (no hay servos de cabeza). El movimiento
 * de ruedas llega siempre por comandos MOVE explicitos desde la Pi. Los brazos
 * se mueven solo por comandos ARM (gestos que decide la Pi).
 *
 * ALIMENTACION (importante, no quemar nada):
 *   - Logica del Arduino: por el cable USB de la Pi.
 *   - Motores: bateria -> entrada VMS/+12V de los L298N (NO desde la Pi/Arduino).
 *   - Servos MG996R: 5-6V externos desde la protoboard (NO desde el Arduino),
 *     con GND comun. El Arduino solo entrega la senal a los pines de servo.
 *   - TODOS los GND van unidos (Arduino, L298N, bateria, fuente de servos).
 *
 * Protocolo de Serial (115200 baud, lineas terminadas en '\n'):
 *
 *   MODE:{AUTO|IDLE|LISTEN|SPEAK|STOP}   estado del robot
 *   ARM:L:<angle>       brazo izquierdo, 0-180
 *   ARM:R:<angle>       brazo derecho, 0-180
 *   HEAD:<pan>:<tilt>   IGNORADO (sin cabeza fisica); responde ACK
 *   MOVE:<vx>:<vy>:<w>  velocidad mecanum, cada valor -100..100
 *                       vx = adelante(+)/atras(-)
 *                       vy = derecha(+)/izquierda(-)
 *                       w  = rotacion horaria(+)/antihoraria(-)
 *   STOP                atajo para MOVE:0:0:0
 *   LED:<patron>        aro de LEDs estilo Alexa Echo:
 *                       OFF    apagado
 *                       IDLE   respiracion azul tenue (MECH en reposo)
 *                       WAKE   barrido cian rapido (oyo "ok MECH")
 *                       LISTEN cometa cian girando (puedes hablar / grabando)
 *                       THINK  pulso rapido (transcribiendo / pensando)
 *                       SPEAK  azul-verde fijo (narrando; fijo a proposito
 *                              para no hacer temblar los servos)
 *                       ERR    3 parpadeos rojos y se apaga
 *
 * ARO DE LEDS (estilo Alexa Echo):
 *   - Hardware: aro WS2812/NeoPixel de 12 LEDs (cualquier aro "NeoPixel ring").
 *   - Libreria: "Adafruit NeoPixel" (Arduino IDE -> Library Manager).
 *   - Cableado: DIN -> pin A2 (idealmente con resistencia de ~330 ohm en
 *     serie), VCC -> 5V del Arduino, GND -> GND. Con brillo limitado (60/255)
 *     12 LEDs consumen poco y el 5V del Arduino los aguanta bien.
 *     NO los alimentes de la fuente de 6V de los servos (los quema).
 *   - Si NO tenes el aro todavia: pone MECH_LEDS en 0 abajo y el firmware
 *     compila sin la libreria (el comando LED responde ACK y no hace nada).
 */

#include <Servo.h>

// 1 = con aro NeoPixel en A2 (requiere libreria Adafruit NeoPixel).
// 0 = sin aro (no necesita la libreria; LED:... se ignora con ACK).
#define MECH_LEDS 1

#if MECH_LEDS
#include <Adafruit_NeoPixel.h>
#endif

// ============================================================
// CONFIGURACION DE PINES — Arduino Uno R3
// ============================================================

// Servos de los brazos (MG996R). La libreria Servo usa el Timer1, que en el
// Uno controla los pines 9 y 10: por eso los servos van en 9/10 y los PWM de
// motores en 3/5/6/11 (asi no chocan).
const uint8_t PIN_SERVO_ARM_L = 9;
const uint8_t PIN_SERVO_ARM_R = 10;

// Motores DC con 2x driver L298N. Los 4 PWM van en 3/5/6/11 (los unicos PWM
// usables; 9/10 los ocupa el Servo). Las direcciones en pines NO-PWM.
//
// Driver L298N #1 (motores M1=FL, M2=FR):
const uint8_t PIN_M_FL_PWM = 3,  PIN_M_FL_IN1 = 4,  PIN_M_FL_IN2 = 2;   // M1: ENA=3, IN1=4, IN2=2
const uint8_t PIN_M_FR_PWM = 5,  PIN_M_FR_IN1 = 7,  PIN_M_FR_IN2 = 8;   // M2: ENB=5, IN3=7, IN4=8
// Driver L298N #2 (motores M3=BL, M4=BR):
const uint8_t PIN_M_BL_PWM = 6,  PIN_M_BL_IN1 = 12, PIN_M_BL_IN2 = 13;  // M3: ENA=6, IN1=12, IN2=13
const uint8_t PIN_M_BR_PWM = 11, PIN_M_BR_IN1 = A0, PIN_M_BR_IN2 = A1;  // M4: ENB=11, IN3=A0, IN4=A1

// Sentido fisico de cada motor: 1 = normal, -1 = invertido.
// Si una rueda gira al reves de lo esperado, cambia AQUI su signo (no hace
// falta recablear nada). Calibrado con el robot real (jul 2026): FR y BL
// quedaron cableadas con la polaridad opuesta, por eso van en -1.
const int8_t DIR_FL = 1;
const int8_t DIR_FR = -1;
const int8_t DIR_BL = -1;
const int8_t DIR_BR = 1;

// Aro de LEDs (WS2812/NeoPixel). A2 esta libre (A0/A1 los usan los motores).
#if MECH_LEDS
const uint8_t PIN_LED_RING = A2;
const uint8_t NUM_LEDS     = 12;   // cambia si tu aro tiene 16/24 LEDs
const uint8_t LED_BRIGHT   = 60;   // 0-255; bajo para poder alimentar del 5V
Adafruit_NeoPixel ring(NUM_LEDS, PIN_LED_RING, NEO_GRB + NEO_KHZ800);
#endif

// ============================================================
// ESTADO
// ============================================================

enum Mode { MODE_AUTO, MODE_IDLE, MODE_LISTEN, MODE_SPEAK, MODE_STOPPED };
Mode currentMode = MODE_IDLE;

// Estados del aro de LEDs (se anima en loop() sin bloquear).
enum LedMode { LED_OFF, LED_IDLE, LED_WAKE, LED_LISTEN, LED_THINK, LED_SPEAK, LED_ERR };
LedMode ledMode = LED_OFF;
unsigned long ledT0 = 0;        // cuando empezo el patron actual
unsigned long ledLastFrame = 0; // ultimo refresco de animacion
bool ledStaticDone = false;     // para patrones fijos (pintar una sola vez)

Servo servoArmL, servoArmR;

String serialBuffer;

// ============================================================
// UTILIDADES
// ============================================================

int clamp(int v, int lo, int hi) {
  if (v < lo) return lo;
  if (v > hi) return hi;
  return v;
}

void setMotor(uint8_t pwm_pin, uint8_t in1, uint8_t in2, int speed) {
  // speed en [-255, 255]
  speed = clamp(speed, -255, 255);
  if (speed > 0) {
    digitalWrite(in1, HIGH);
    digitalWrite(in2, LOW);
    analogWrite(pwm_pin, speed);
  } else if (speed < 0) {
    digitalWrite(in1, LOW);
    digitalWrite(in2, HIGH);
    analogWrite(pwm_pin, -speed);
  } else {
    digitalWrite(in1, LOW);
    digitalWrite(in2, LOW);
    analogWrite(pwm_pin, 0);
  }
}

void stopAllMotors() {
  setMotor(PIN_M_FL_PWM, PIN_M_FL_IN1, PIN_M_FL_IN2, 0);
  setMotor(PIN_M_FR_PWM, PIN_M_FR_IN1, PIN_M_FR_IN2, 0);
  setMotor(PIN_M_BL_PWM, PIN_M_BL_IN1, PIN_M_BL_IN2, 0);
  setMotor(PIN_M_BR_PWM, PIN_M_BR_IN1, PIN_M_BR_IN2, 0);
}

// Cinematica de ruedas mecanum/omnidireccionales.
// Entradas: vx (adelante), vy (lateral), w (rotacion), cada uno en [-100,100].
void driveOmni(int vx, int vy, int w) {
  // Giro con SOLO 2 ruedas en diagonal (FL y BR), por pedido del equipo:
  // el término de rotación (w) se aplica únicamente a FL y BR; FR y BL no rotan.
  // (Adelante/atrás y desplazamiento lateral siguen usando las 4 ruedas.)
  long fl = (long)vx + vy + w;
  long fr = (long)vx - vy;
  long bl = (long)vx - vy;
  long br = (long)vx + vy - w;

  // Normaliza si la suma excede 100 (puede pasar al mezclar componentes).
  long maxMag = max(max(abs(fl), abs(fr)), max(abs(bl), abs(br)));
  if (maxMag > 100) {
    fl = fl * 100 / maxMag;
    fr = fr * 100 / maxMag;
    bl = bl * 100 / maxMag;
    br = br * 100 / maxMag;
  }

  // Escala [-100,100] -> PWM [-255,255], aplicando el sentido fisico de
  // cada motor (DIR_*): asi "positivo" siempre significa girar hacia
  // adelante, sin importar como quedo cableado el L298N.
  setMotor(PIN_M_FL_PWM, PIN_M_FL_IN1, PIN_M_FL_IN2, DIR_FL * fl * 255 / 100);
  setMotor(PIN_M_FR_PWM, PIN_M_FR_IN1, PIN_M_FR_IN2, DIR_FR * fr * 255 / 100);
  setMotor(PIN_M_BL_PWM, PIN_M_BL_IN1, PIN_M_BL_IN2, DIR_BL * bl * 255 / 100);
  setMotor(PIN_M_BR_PWM, PIN_M_BR_IN1, PIN_M_BR_IN2, DIR_BR * br * 255 / 100);
}

// ============================================================
// ARO DE LEDS (animaciones estilo Alexa, no bloqueantes)
// ============================================================

void setLedMode(LedMode m) {
  ledMode = m;
  ledT0 = millis();
  ledStaticDone = false;
#if MECH_LEDS
  if (m == LED_OFF) {
    ring.clear();
    ring.show();
  }
#endif
}

#if MECH_LEDS
// Pinta todo el aro de un color.
void ringFill(uint8_t r, uint8_t g, uint8_t b) {
  for (uint8_t i = 0; i < NUM_LEDS; i++) ring.setPixelColor(i, r, g, b);
  ring.show();
}

void updateLeds() {
  unsigned long now = millis();
  // Refrescar cada 40 ms es suficiente y molesta poco a los servos
  // (NeoPixel bloquea interrupciones un instante en cada show()).
  if (now - ledLastFrame < 40) return;
  ledLastFrame = now;
  unsigned long t = now - ledT0;

  switch (ledMode) {
    case LED_OFF:
      break;  // ya se apago en setLedMode

    case LED_IDLE: {
      // Respiracion azul tenue, ciclo de 4 s (MECH dormido pero presente).
      float ph = (t % 4000) / 4000.0;
      float lvl = 0.5 - 0.5 * cos(ph * 6.2832);     // 0..1
      uint8_t v = (uint8_t)(6 + lvl * 24);          // muy tenue
      ringFill(0, v / 3, v);
      break;
    }

    case LED_WAKE: {
      // Barrido de encendido: el aro se llena de cian en ~0.8 s y queda
      // lleno. Es la senal visual de "te escuche" (como el aro de Alexa).
      uint8_t lit = (uint8_t)min((unsigned long)NUM_LEDS, t / (800 / NUM_LEDS));
      for (uint8_t i = 0; i < NUM_LEDS; i++)
        if (i < lit) ring.setPixelColor(i, 0, 160, 200);
        else         ring.setPixelColor(i, 0, 0, 0);
      ring.show();
      break;
    }

    case LED_LISTEN: {
      // Cometa cian girando sobre base tenue: "puedes hablar / te escucho".
      uint8_t head = (t / 90) % NUM_LEDS;
      for (uint8_t i = 0; i < NUM_LEDS; i++) {
        uint8_t d = (head - i + NUM_LEDS) % NUM_LEDS;  // distancia detras del cometa
        if      (d == 0) ring.setPixelColor(i, 0, 180, 220);
        else if (d == 1) ring.setPixelColor(i, 0, 70, 90);
        else if (d == 2) ring.setPixelColor(i, 0, 25, 35);
        else             ring.setPixelColor(i, 0, 6, 10);
      }
      ring.show();
      break;
    }

    case LED_THINK: {
      // Pulso rapido azul-violeta (transcribiendo / pensando con Claude).
      float ph = (t % 900) / 900.0;
      float lvl = 0.5 - 0.5 * cos(ph * 6.2832);
      uint8_t v = (uint8_t)(15 + lvl * 120);
      ringFill(v / 3, 0, v);
      break;
    }

    case LED_SPEAK:
      // Fijo azul-verde mientras narra. Se pinta UNA vez: durante la
      // narracion los brazos gesticulan y no queremos show() repetidos
      // (bloquean interrupciones y hacen temblar los servos).
      if (!ledStaticDone) {
        ringFill(0, 90, 60);
        ledStaticDone = true;
      }
      break;

    case LED_ERR: {
      // 3 parpadeos rojos y se apaga solo.
      if (t > 1800) { setLedMode(LED_OFF); break; }
      bool on = (t / 300) % 2 == 0;
      if (on) ringFill(150, 0, 0); else ringFill(0, 0, 0);
      break;
    }
  }
}
#endif  // MECH_LEDS

void applyLedCommand(const String& name) {
  LedMode m;
  if      (name == "OFF")    m = LED_OFF;
  else if (name == "IDLE")   m = LED_IDLE;
  else if (name == "WAKE")   m = LED_WAKE;
  else if (name == "LISTEN") m = LED_LISTEN;
  else if (name == "THINK")  m = LED_THINK;
  else if (name == "SPEAK")  m = LED_SPEAK;
  else if (name == "ERR")    m = LED_ERR;
  else { Serial.print("ERR:UNKNOWN_LED:"); Serial.println(name); return; }
  setLedMode(m);
  Serial.print("ACK:LED:"); Serial.println(name);
}

// ============================================================
// PARSEO DE COMANDOS
// ============================================================

void applyMode(const String& m) {
  if      (m == "AUTO")   currentMode = MODE_AUTO;
  else if (m == "IDLE")   currentMode = MODE_IDLE;
  else if (m == "LISTEN") { currentMode = MODE_LISTEN; stopAllMotors(); }
  else if (m == "SPEAK")  { currentMode = MODE_SPEAK;  stopAllMotors(); }
  else if (m == "STOP")   { currentMode = MODE_STOPPED; stopAllMotors(); }
  else { Serial.print("ERR:UNKNOWN_MODE:"); Serial.println(m); return; }
  Serial.print("ACK:MODE:"); Serial.println(m);
}

void handleCommand(const String& cmd) {
  if (cmd.startsWith("MODE:")) {
    applyMode(cmd.substring(5));
    return;
  }
  if (cmd == "STOP") {
    stopAllMotors();
    Serial.println("ACK:STOP");
    return;
  }
  if (cmd.startsWith("HEAD:")) {
    // Sin cabeza fisica: se ignora, pero confirmamos para no romper la Pi.
    Serial.println("ACK:HEAD");
    return;
  }
  if (cmd.startsWith("ARM:")) {
    int p1 = cmd.indexOf(':', 4);
    if (p1 < 0) { Serial.println("ERR:BAD_ARM"); return; }
    String side = cmd.substring(4, p1);
    int angle = clamp(cmd.substring(p1 + 1).toInt(), 0, 180);
    if      (side == "L") servoArmL.write(angle);
    else if (side == "R") servoArmR.write(angle);
    else { Serial.println("ERR:BAD_ARM_SIDE"); return; }
    Serial.println("ACK:ARM");
    return;
  }
  if (cmd.startsWith("LED:")) {
    applyLedCommand(cmd.substring(4));
    return;
  }
  if (cmd.startsWith("MOVE:")) {
    int p1 = cmd.indexOf(':', 5);
    int p2 = cmd.indexOf(':', p1 + 1);
    if (p1 < 0 || p2 < 0) { Serial.println("ERR:BAD_MOVE"); return; }
    int vx = cmd.substring(5, p1).toInt();
    int vy = cmd.substring(p1 + 1, p2).toInt();
    int w  = cmd.substring(p2 + 1).toInt();
    driveOmni(vx, vy, w);
    Serial.println("ACK:MOVE");
    return;
  }
  Serial.print("ERR:UNKNOWN:");
  Serial.println(cmd);
}

void readSerial() {
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (serialBuffer.length() > 0) {
        handleCommand(serialBuffer);
        serialBuffer = "";
      }
    } else {
      serialBuffer += c;
      if (serialBuffer.length() > 64) serialBuffer = "";  // anti-overflow
    }
  }
}

// ============================================================
// SETUP / LOOP
// ============================================================

void setup() {
  Serial.begin(115200);

  uint8_t motorPins[] = {
    PIN_M_FL_PWM, PIN_M_FL_IN1, PIN_M_FL_IN2,
    PIN_M_FR_PWM, PIN_M_FR_IN1, PIN_M_FR_IN2,
    PIN_M_BL_PWM, PIN_M_BL_IN1, PIN_M_BL_IN2,
    PIN_M_BR_PWM, PIN_M_BR_IN1, PIN_M_BR_IN2,
  };
  for (uint8_t p : motorPins) pinMode(p, OUTPUT);

  servoArmL.attach(PIN_SERVO_ARM_L);
  servoArmR.attach(PIN_SERVO_ARM_R);
  servoArmL.write(90);
  servoArmR.write(90);

#if MECH_LEDS
  ring.begin();
  ring.setBrightness(LED_BRIGHT);
  ring.clear();
  ring.show();
#endif

  stopAllMotors();
  Serial.println("READY:MECH");
}

void loop() {
  // Sin comportamientos autonomos: el robot solo reacciona a comandos de la Pi.
  // (Las ruedas por MOVE, los brazos por ARM.)
  readSerial();
#if MECH_LEDS
  updateLeds();
#endif
}
