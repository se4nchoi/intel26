const int buttonPin = 13; // Button S connected here
const int ledPin = 12;   // LED S connected here
int buttonState = 0;

void setup() {
  pinMode(ledPin, OUTPUT);
  pinMode(buttonPin, INPUT);
}

void loop() {
  // Read the button state
  buttonState = digitalRead(buttonPin);

  // If button is pressed, turn LED on
  if (buttonState == HIGH) {
    digitalWrite(ledPin, HIGH);
  } else {
    digitalWrite(ledPin, LOW);
  }
}
