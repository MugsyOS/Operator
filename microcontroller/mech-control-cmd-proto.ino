#include <CmdMessenger.h>
#include <AccelStepper.h>

// 1,2000,1000;
// 1,1000,1500,0;1,1000,1500,1;1,3000,1500,0;1,1000,1000,1;
// 2,30,3000;2,-30,3000;
// 2,20,3000;2,-20,3000;2,20,3000;2,-20,3000;2,20,3000;2,-20,3000;2,20,3000;2,-20,3000;2,20,3000;2,0,3000;

// 3,1000,1000,0,30;
// 3,1000,1000,0,8; 3,-1000,1000,0,-8;
// all
// 2,-0,3000;1,2000,1000;2,10,3000;2,-10,3000;2,10,3000;2,-10,3000;2,-0,3000;3,1000,1000,1,8; 3,-1000,1000,1,-8;


3,1000,1000,1,8; 3,-1000,1000,1,-8;3,1000,1000,1,3; 3,-1000,1000,1,-3;3,1000,1000,1,8; 3,-1000,1000,1,-8; 3,-1000,1000,1,0;


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
  long arg1;
  int arg2;
  int direction; // 0 for clockwise, 1 for counter-clockwise
  long arg3;
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
  // Initialize Serial
  Serial.begin(115200);
  
  // Attach command callbacks
  cmdMessenger.attach(1, moveConeCommand);
  cmdMessenger.attach(2, moveSpoutCommand);
  cmdMessenger.attach(3, moveBothCommand);
  
  // Stepper initialization
  coneStepper.setEnablePin(CONE_ENABLE_PIN);
  spoutStepper.setEnablePin(SPOUT_ENABLE_PIN);
  coneStepper.setMaxSpeed(1000);                    // Adjust speed as needed
  coneStepper.setAcceleration(10000);               // Adjust acceleration as needed
  spoutStepper.setMaxSpeed(3000);                    // Adjust speed as needed
  spoutStepper.setAcceleration(10000);  
  coneStepper.setPinsInverted(false, false, true);  // Invert enable pin
  spoutStepper.setPinsInverted(false, false, true);  // Invert enable pin

  // Set up the microstepping pins as outputs and configure for 1/32 microstepping
  pinMode(M0, OUTPUT);  
  pinMode(M1, OUTPUT);
  pinMode(M2, OUTPUT);
  digitalWrite(M0, HIGH);  // Set M0 to HIGH for 1/32 microstepping
  digitalWrite(M1, HIGH);  // Set M1 to HIGH for 1/32 microstepping
  digitalWrite(M2, HIGH);  // Set M2 to HIGH for 1/32 microstepping

  // Set up the limit switch pin as input
  pinMode(LIMIT_SWITCH_PIN, INPUT_PULLUP);

  // Disable steppers initially
  coneStepper.disableOutputs();
  spoutStepper.disableOutputs();

  Serial.println("Ready for commands");

  // Zero the spout stepper motor
  zeroSpoutStepper();
}

void loop() {
  // Process incoming serial commands
  cmdMessenger.feedinSerialData();

  // Execute commands from the queue
  if (!isQueueEmpty() && !coneStepper.isRunning() && !spoutStepper.isRunning()) {
    Command cmd = dequeueCommand();
    switch (cmd.commandId) {
      case 1:
        executeMoveConeCommand(cmd.arg1, cmd.arg2, cmd.direction);
        break;
      case 2:
        executeMoveSpoutCommand(cmd.arg1, cmd.arg2, cmd.direction);
        break;
      case 3:
        executeMoveBothCommand(cmd.arg1, cmd.arg2, cmd.direction, cmd.arg3);
        break;
    }
  }

  // Run steppers
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

// Command function to enqueue move cone command
void moveConeCommand() {
  long steps = cmdMessenger.readInt32Arg();
  int speed = cmdMessenger.readInt16Arg();
  int direction = cmdMessenger.readInt16Arg();
  Command cmd = {1, steps, speed, direction};
  enqueueCommand(cmd);
  // Serial.print("Queued command: ID=");
  // Serial.print(cmd.commandId);
  // Serial.print(", Arg1=");
  // Serial.print(cmd.arg1);
  // Serial.print(", Arg2=");
  // Serial.print(cmd.arg2);
  // Serial.print(", Direction=");
  // Serial.println(cmd.direction);
}

// Command function to enqueue move spout command
void moveSpoutCommand() {
  long degrees = cmdMessenger.readInt32Arg();
  int speed = cmdMessenger.readInt16Arg();
  int direction = cmdMessenger.readInt16Arg();
  Command cmd = {2, degrees, speed, direction};
  enqueueCommand(cmd);
}

// Command function to enqueue move both command
void moveBothCommand() {
  long coneSteps = cmdMessenger.readInt32Arg();
  int coneSpeed = cmdMessenger.readInt16Arg();
  int direction = cmdMessenger.readInt16Arg();
  int spoutDegrees = cmdMessenger.readInt32Arg();
  // long spoutDegrees = cmdMessenger.readInt32Arg();
  // int spoutSpeed = cmdMessenger.readInt16Arg();
  Command cmd = {3, coneSteps, coneSpeed, direction, spoutDegrees};
  enqueueCommand(cmd);
}

// Execute move cone command
void executeMoveConeCommand(long steps, int speed, int direction) {
  coneStepper.setMaxSpeed(abs(speed));
  coneStepper.setPinsInverted(direction == 1, false, true); // Set direction
  coneStepper.move(steps);
  Serial.print("Moving cone: ");
  Serial.print(steps);
  Serial.print(" steps at speed ");
  Serial.print(speed);
  Serial.print(" in direction ");
  Serial.println(direction == 0 ? "clockwise" : "counter-clockwise");
}

// Execute move spout command
void executeMoveSpoutCommand(long degrees, int speed, int direction) {
  if (!isZeroed) {
    Serial.println("Error: Spout stepper is not zeroed.");
    return;
  }
  spoutStepper.setMaxSpeed(abs(speed));
  spoutStepper.setPinsInverted(direction == 1, false, true); // Set direction
  spoutStepper.moveTo(degrees * SPOUT_STEPS_PER_DEGREE);
  Serial.print("Moving spout: ");
  Serial.print(degrees);
  Serial.print(" degrees at speed ");
  Serial.print(speed);
  Serial.print(" in direction ");
  Serial.println(direction == 0 ? "clockwise" : "counter-clockwise");

  // Wait until movement is complete before marking as done
  
}

// Execute move both command
void executeMoveBothCommand(long coneSteps, int speed, int direction, long spoutDegrees) {
  coneStepper.setMaxSpeed(abs(speed));
  spoutStepper.setMaxSpeed(abs(3000));
  coneStepper.setPinsInverted(direction == 1, false, true); // Set direction
  spoutStepper.setPinsInverted(direction == 1, false, true); // Set direction
  coneStepper.move(coneSteps);
  spoutStepper.moveTo(spoutDegrees * SPOUT_STEPS_PER_DEGREE);
  Serial.print("Moving cone: ");
  Serial.print(coneSteps);
  Serial.print(" steps, spout at speed ");
  Serial.print(speed);
  Serial.print(" in direction ");
  Serial.println(direction == 0 ? "clockwise" : "counter-clockwise");
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

  testMovement(44);  // return to center
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
