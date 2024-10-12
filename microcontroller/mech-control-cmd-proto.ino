#include <CmdMessenger.h>
#include <AccelStepper.h>

// 1,2000,750;
// 1,1000,750,0;1,1000,750,1;1,3000,750,0;1,1000,750,1;
// 2,30,3000;2,-30,3000;
// 2,20,3000;2,-20,3000;2,20,3000;2,-20,3000;2,20,3000;2,-20,3000;2,20,3000;2,-20,3000;2,20,3000;2,0,3000;
// 3,2000,30,750;
// 3, 1000, 10, 1000, 3000;3, -1000, -10, 1000, 3000;

// Stepper definitions
#define CONE_STEP_PIN 3
#define CONE_DIR_PIN 2
#define CONE_ENABLE_PIN 4
#define SPOUT_STEP_PIN 6
#define SPOUT_DIR_PIN 5
#define SPOUT_ENABLE_PIN 7

// Define the microstepping pins for the spout stepper
#define M0 11
#define M1 10
#define M2 9

// Define the limit switch pin for zeroing the spout stepper
#define LIMIT_SWITCH_PIN 8

AccelStepper coneStepper(AccelStepper::DRIVER, CONE_STEP_PIN, CONE_DIR_PIN);
AccelStepper spoutStepper(AccelStepper::DRIVER, SPOUT_STEP_PIN, SPOUT_DIR_PIN);

const float STEP_ANGLE = 0.9;            // Step angle in degrees for the spout stepper
const int MICROSTEPS = 32;               // Number of microsteps for the spout stepper
const float PULLEY_RATIO = 40.0 / 20.0;  // Ratio of spout pulley to motor pulley
const float SPOUT_STEPS_PER_DEGREE = (1.0 / STEP_ANGLE) * MICROSTEPS * PULLEY_RATIO;

// Track zeroing state for the spout stepper
bool isZeroed = false;

// Instantiate CmdMessenger object
CmdMessenger cmdMessenger = CmdMessenger(Serial);

// Command queue to handle sequential execution
struct Command {
  int commandId;
  long coneSteps;
  long spoutDegrees;
  int coneSpeed;
  int spoutSpeed;
  int direction;
};

Command commandQueue[20];
int queueFront = 0;
int queueRear = 0;

bool isQueueEmpty() {
  return queueFront == queueRear;
}

bool isQueueFull() {
  return (queueRear + 1) % 20 == queueFront;
}

void enqueueCommand(Command cmd) {
  if (!isQueueFull()) {
    commandQueue[queueRear] = cmd;
    queueRear = (queueRear + 1) % 20;
  }
}

Command dequeueCommand() {
  Command cmd = commandQueue[queueFront];
  queueFront = (queueFront + 1) % 20;
  return cmd;
}

void setup() {
  Serial.begin(115200);
  
  cmdMessenger.attach(1, moveConeCommand);
  cmdMessenger.attach(2, moveSpoutCommand);
  cmdMessenger.attach(3, moveBothCommand);
  
  coneStepper.setEnablePin(CONE_ENABLE_PIN);
  spoutStepper.setEnablePin(SPOUT_ENABLE_PIN);
  coneStepper.setMaxSpeed(1000);
  coneStepper.setAcceleration(10000);
  spoutStepper.setMaxSpeed(2000);
  spoutStepper.setAcceleration(10000);
  coneStepper.setPinsInverted(false, false, true);
  spoutStepper.setPinsInverted(false, false, true);

  pinMode(M0, OUTPUT);  
  pinMode(M1, OUTPUT);
  pinMode(M2, OUTPUT);
  digitalWrite(M0, HIGH);
  digitalWrite(M1, HIGH);
  digitalWrite(M2, HIGH);

  pinMode(LIMIT_SWITCH_PIN, INPUT_PULLUP);

  coneStepper.disableOutputs();
  spoutStepper.disableOutputs();

  Serial.println("Ready for commands");
  zeroSpoutStepper();
}

void loop() {
  cmdMessenger.feedinSerialData();

  if (!isQueueEmpty() && !coneStepper.isRunning() && !spoutStepper.isRunning()) {
    Command cmd = dequeueCommand();
    switch (cmd.commandId) {
      case 1:
        executeMoveConeCommand(cmd.coneSteps, cmd.coneSpeed, cmd.direction);
        break;
      case 2:
        executeMoveSpoutCommand(cmd.spoutDegrees, cmd.spoutSpeed, cmd.direction);
        break;
      case 3:
        executeMoveBothCommand(cmd.coneSteps, cmd.spoutDegrees, cmd.coneSpeed, cmd.spoutSpeed, cmd.direction);
        break;
    }
  }

  if (coneStepper.isRunning()) {
    coneStepper.enableOutputs();
    coneStepper.run();
  } else {
    coneStepper.disableOutputs();
  }

  if (spoutStepper.isRunning()) {
    spoutStepper.enableOutputs();
    spoutStepper.run();
  } else {
    spoutStepper.disableOutputs();
  }
}

void moveConeCommand() {
  long steps = cmdMessenger.readInt32Arg();
  int speed = cmdMessenger.readInt16Arg();
  int direction = cmdMessenger.readInt16Arg();
  Command cmd = {1, steps, 0, speed, 0, direction};
  enqueueCommand(cmd);
}

void moveSpoutCommand() {
  long degrees = cmdMessenger.readInt32Arg();
  int speed = cmdMessenger.readInt16Arg();
  int direction = cmdMessenger.readInt16Arg();
  Command cmd = {2, 0, degrees, 0, speed, direction};
  enqueueCommand(cmd);
}

void moveBothCommand() {
  long coneSteps = cmdMessenger.readInt32Arg();
  long spoutDegrees = cmdMessenger.readInt32Arg();
  int coneSpeed = cmdMessenger.readInt16Arg();
  int spoutSpeed = cmdMessenger.readInt16Arg();
  int direction = cmdMessenger.readInt16Arg();
  Command cmd = {3, coneSteps, spoutDegrees, coneSpeed, spoutSpeed, direction};
  enqueueCommand(cmd);
}

void executeMoveConeCommand(long steps, int speed, int direction) {
  coneStepper.setMaxSpeed(abs(speed));
  coneStepper.setPinsInverted(direction == 1, false, true);
  coneStepper.move(steps);
}

void executeMoveSpoutCommand(long degrees, int speed, int direction) {
  if (!isZeroed) {
    Serial.println("Error: Spout stepper is not zeroed.");
    return;
  }
  spoutStepper.setMaxSpeed(abs(speed));
  spoutStepper.setPinsInverted(direction == 1, false, true);
  spoutStepper.moveTo(degrees * SPOUT_STEPS_PER_DEGREE);
}

void executeMoveBothCommand(long coneSteps, long spoutDegrees, int coneSpeed, int spoutSpeed, int direction) {
  coneStepper.setMaxSpeed(abs(coneSpeed));
  spoutStepper.setMaxSpeed(abs(spoutSpeed));
  coneStepper.setPinsInverted(direction == 1, false, true);
  spoutStepper.setPinsInverted(direction == 1, false, true);
  coneStepper.move(coneSteps);
  spoutStepper.moveTo(spoutDegrees * SPOUT_STEPS_PER_DEGREE);
}

void zeroSpoutStepper() {
  // Enable the motor
  digitalWrite(SPOUT_ENABLE_PIN, LOW);

  // Rotate counterclockwise until the limit switch is hit
  spoutStepper.setSpeed(-3000);  // Negative speed for counterclockwise
  Serial.println("Zeroing spout stepper...");
  while (digitalRead(LIMIT_SWITCH_PIN) == LOW) {
    spoutStepper.runSpeed();
  }

 
  testMovement(44);  //Move to center
  // Set current position as zero
  spoutStepper.setCurrentPosition(0);
  isZeroed = true;

  // Disable the motor after reaching the center position
  spoutStepper.disableOutputs();
  Serial.println("Spout stepper zeroed and moved to center position.");
}

void testMovement(float angle) {
  long stepsToMove = (long)(angle * SPOUT_STEPS_PER_DEGREE);
  Serial.print("Test movement - Angle: ");
  Serial.print(angle);
  Serial.print(" degrees, Steps: ");
  Serial.println(stepsToMove);

  spoutStepper.move(stepsToMove);

  while (spoutStepper.distanceToGo() != 0) {
    spoutStepper.run();
  }

  Serial.print("Final position: ");
  Serial.println(spoutStepper.currentPosition());
}
