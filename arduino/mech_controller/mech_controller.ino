/*
 * MECH — Firmware del Arduino (kit "robo robo")
 *
 * Roles del Arduino:
 *   - Mover el robot (ruedas omnidireccionales).
 *   - Mover cabeza (pan/tilt) y brazos (servos).
 *   - Escuchar comandos por Serial desde la Raspberry Pi 5.
 *
 * NOTA: el robot NO lleva sensor de obstáculos (el HC-SR04 se eliminó del
 * diseño; la presencia de usuarios se detecta con la cámara C930e desde la Pi).
 * Por eso el modo AUTO no conduce solo — solo hace micro-movimientos de cabeza.
 * El movimiento de ruedas llega siempre por comandos MOVE explícitos.
 *
 * Protocolo de Serial (115200 baud, líneas terminadas en '\n'):
 *
 *   MODE:AUTO           → "vivo" en reposo (mira alrededor, sin conducir)
 *   MODE:IDLE           → pose neutral, micro-movimientos de cabeza
 *   MODE:LISTEN         → quieto, mirando al frente
 *   MODE:SPEAK          → gestos sutiles durante el habla (head bob)
 *   MODE:STOP           → todo detenido
 *
 *   HEAD:<pan>:<tilt>   → ángulos de cabeza, 0–180 cada uno
 *   ARM:L:<angle>       → brazo izquierdo, 0–180
 *   ARM:R:<angle>       → brazo derecho, 0–180
 *   MOVE:<vx>:<vy>:<w>  → velocidad omnidireccional, cada valor -100..100
 *                         vx = adelante(+)/atrás(-)
 *                         vy = derecha(+)/izquierda(-)
 *                         w  = rotación horaria(+)/antihoraria(-)
 *   STOP                → atajo para MOVE:0:0:0
 *
 * Cambia las constantes PIN_* abajo según el cableado real del kit.
 */

#include <Servo.h>

// ============================================================
// CONFIGURACIÓN DE PINES — ajusta según tu cableado
// ============================================================

// Servos
const uint8_t PIN_SERVO_HEAD_PAN  = 9;   // izquierda/derecha
const uint8_t PIN_SERVO_HEAD_TILT = 10;  // arriba/abajo
const uint8_t PIN_SERVO_ARM_L     = 11;
const uint8_t PIN_SERVO_ARM_R     = 12;

// Motores DC con driver tipo L298N o similar.
// Cada motor: 1 pin PWM (velocidad) + 2 pins de dirección (IN1/IN2).
// FL = Front-Left, FR = Front-Right, BL = Back-Left, BR = Back-Right.
const uint8_t PIN_M_FL_PWM = 3,  PIN_M_FL_IN1 = 22, PIN_M_FL_IN2 = 23;
const uint8_t PIN_M_FR_PWM = 5,  PIN_M_FR_IN1 = 24, PIN_M_FR_IN2 = 25;
const uint8_t PIN_M_BL_PWM = 6,  PIN_M_BL_IN1 = 26, PIN_M_BL_IN2 = 27;
const uint8_t PIN_M_BR_PWM = 4,  PIN_M_BR_IN1 = 28, PIN_M_BR_IN2 = 29;
// Si usas un Arduino UNO (no Mega), reasigna IN1/IN2 a pines digitales
// libres (p.ej. 2, 13, A0, A1, A2, A3, A4, A5).

// ============================================================
// PARÁMETROS DE COMPORTAMIENTO
// ============================================================

// (Sin parámetros de evasión: el robot no conduce de forma autónoma.)

// ============================================================
// ESTADO
// ============================================================

enum Mode { MODE_AUTO, MODE_IDLE, MODE_LISTEN, MODE_SPEAK, MODE_STOPPED };
Mode currentMode = MODE_IDLE;

Servo servoHeadPan, servoHeadTilt, servoArmL, servoArmR;
unsigned long lastTick = 0;

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

// Cinemática de ruedas mecanum/omnidireccionales.
// Entradas: vx (adelante), vy (lateral), w (rotación), cada uno en [-100,100].
void driveOmni(int vx, int vy, int w) {
  long fl = (long)vx + vy + w;
  long fr = (long)vx - vy - w;
  long bl = (long)vx - vy + w;
  long br = (long)vx + vy - w;

  // Escala al rango PWM [-255, 255].
  long maxMag = max(max(abs(fl), abs(fr)), max(abs(bl), abs(br)));
  long scale = 255;
  if (maxMag > 100) {
    // Normaliza si la suma excede 100 (puede pasar al mezclar componentes).
    fl = fl * 100 / maxMag;
    fr = fr * 100 / maxMag;
    bl = bl * 100 / maxMag;
    br = br * 100 / maxMag;
  }

  setMotor(PIN_M_FL_PWM, PIN_M_FL_IN1, PIN_M_FL_IN2, fl * scale / 100);
  setMotor(PIN_M_FR_PWM, PIN_M_FR_IN1, PIN_M_FR_IN2, fr * scale / 100);
  setMotor(PIN_M_BL_PWM, PIN_M_BL_IN1, PIN_M_BL_IN2, bl * scale / 100);
  setMotor(PIN_M_BR_PWM, PIN_M_BR_IN1, PIN_M_BR_IN2, br * scale / 100);
}

// ============================================================
// COMPORTAMIENTOS DE MODO
// ============================================================

void tickAuto() {
  // Sin sensor de obstáculos, AUTO no conduce a ciegas (chocaría).
  // Solo mira lentamente de lado a lado para parecer "vivo" en el stand.
  // El movimiento de ruedas se hace siempre con comandos MOVE explícitos.
  static unsigned long nextMove = 0;
  static int pan = 90;
  static int dir = 1;
  unsigned long now = millis();
  if (now > nextMove) {
    pan += dir * 15;
    if (pan >= 120) { pan = 120; dir = -1; }
    else if (pan <= 60) { pan = 60; dir = 1; }
    servoHeadPan.write(pan);
    nextMove = now + 700;
  }
}

void tickIdle() {
  // Micro-movimientos de cabeza para parecer "vivo".
  static unsigned long nextMove = 0;
  static int pan = 90;
  unsigned long now = millis();
  if (now > nextMove) {
    pan = 80 + random(0, 20);
    servoHeadPan.write(pan);
    nextMove = now + 1500 + random(0, 1500);
  }
}

void tickListen() {
  // Quieto, cabeza al frente, brazos relajados.
  servoHeadPan.write(90);
  servoHeadTilt.write(90);
}

void tickSpeak() {
  // Pequeño "bob" de cabeza mientras habla.
  static unsigned long nextBob = 0;
  static bool down = false;
  unsigned long now = millis();
  if (now > nextBob) {
    servoHeadTilt.write(down ? 85 : 95);
    down = !down;
    nextBob = now + 350;
  }
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
    int p1 = cmd.indexOf(':', 5);
    if (p1 < 0) { Serial.println("ERR:BAD_HEAD"); return; }
    int pan  = cmd.substring(5, p1).toInt();
    int tilt = cmd.substring(p1 + 1).toInt();
    servoHeadPan.write(clamp(pan, 0, 180));
    servoHeadTilt.write(clamp(tilt, 0, 180));
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
    PIN_M_FL_IN1, PIN_M_FL_IN2,
    PIN_M_FR_IN1, PIN_M_FR_IN2,
    PIN_M_BL_IN1, PIN_M_BL_IN2,
    PIN_M_BR_IN1, PIN_M_BR_IN2,
  };
  for (uint8_t p : motorPins) pinMode(p, OUTPUT);

  servoHeadPan.attach(PIN_SERVO_HEAD_PAN);
  servoHeadTilt.attach(PIN_SERVO_HEAD_TILT);
  servoArmL.attach(PIN_SERVO_ARM_L);
  servoArmR.attach(PIN_SERVO_ARM_R);

  servoHeadPan.write(90);
  servoHeadTilt.write(90);
  servoArmL.write(90);
  servoArmR.write(90);

  stopAllMotors();
  Serial.println("READY:MECH");
}

void loop() {
  readSerial();

  unsigned long now = millis();
  if (now - lastTick >= 50) {
    lastTick = now;
    switch (currentMode) {
      case MODE_AUTO:    tickAuto();   break;
      case MODE_IDLE:    tickIdle();   break;
      case MODE_LISTEN:  tickListen(); break;
      case MODE_SPEAK:   tickSpeak();  break;
      case MODE_STOPPED: /* nada */    break;
    }
  }
}
