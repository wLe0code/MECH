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
 */

#include <Servo.h>

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
// Si una rueda gira al reves, intercambia sus 2 cables de motor (OUT) o sus IN.

// ============================================================
// ESTADO
// ============================================================

enum Mode { MODE_AUTO, MODE_IDLE, MODE_LISTEN, MODE_SPEAK, MODE_STOPPED };
Mode currentMode = MODE_IDLE;

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
  long fl = (long)vx + vy + w;
  long fr = (long)vx - vy - w;
  long bl = (long)vx - vy + w;
  long br = (long)vx + vy - w;

  // Normaliza si la suma excede 100 (puede pasar al mezclar componentes).
  long maxMag = max(max(abs(fl), abs(fr)), max(abs(bl), abs(br)));
  if (maxMag > 100) {
    fl = fl * 100 / maxMag;
    fr = fr * 100 / maxMag;
    bl = bl * 100 / maxMag;
    br = br * 100 / maxMag;
  }

  // Escala [-100,100] -> PWM [-255,255].
  setMotor(PIN_M_FL_PWM, PIN_M_FL_IN1, PIN_M_FL_IN2, fl * 255 / 100);
  setMotor(PIN_M_FR_PWM, PIN_M_FR_IN1, PIN_M_FR_IN2, fr * 255 / 100);
  setMotor(PIN_M_BL_PWM, PIN_M_BL_IN1, PIN_M_BL_IN2, bl * 255 / 100);
  setMotor(PIN_M_BR_PWM, PIN_M_BR_IN1, PIN_M_BR_IN2, br * 255 / 100);
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

  stopAllMotors();
  Serial.println("READY:MECH");
}

void loop() {
  // Sin comportamientos autonomos: el robot solo reacciona a comandos de la Pi.
  // (Las ruedas por MOVE, los brazos por ARM.)
  readSerial();
}
