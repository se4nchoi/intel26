// 4개 LED 제어 아두이노 펌웨어
// 확장 핀: 11(LED1), 12(LED2), 13(LED3), 14(LED4 / A0)

const int LEDpin1 = 8;    // LED 1 (OK)
const int LEDpin2 = 9;    // LED 2 (NG)
const int LEDpin3 = 10;    // LED 3 (확장 1 - 13번 핀)
const int LEDpin4 = 11;    // LED 4 (확장 2 - 14번 핀 / A0)

void setup() {
  Serial.begin(9600);      // 시리얼 통신 시작 (9600 보레이트)
  
  pinMode(LEDpin1, OUTPUT);
  pinMode(LEDpin2, OUTPUT);
  pinMode(LEDpin3, OUTPUT);
  pinMode(LEDpin4, OUTPUT);

  // 초기 상태: 모든 LED OFF
  digitalWrite(LEDpin1, LOW);
  digitalWrite(LEDpin2, LOW);
  digitalWrite(LEDpin3, LOW);
  digitalWrite(LEDpin4, LOW);
}

void loop() {
  if (Serial.available()) {
    char c = Serial.read();  // PC로부터 문자 수신
    
    // LED 1 제어 (11번 핀)
    if (c == 'A') {
      digitalWrite(LEDpin1, HIGH);  
      Serial.print("led1on\n");
    }
    else if (c == 'B') {
      digitalWrite(LEDpin1, LOW); 
      Serial.print("led1off\n");
    }
    // LED 2 제어 (12번 핀)
    else if (c == 'C') {
      digitalWrite(LEDpin2, HIGH); 
      Serial.print("led2on\n");
    }
    else if (c == 'D') {
      digitalWrite(LEDpin2, LOW);    
      Serial.print("led2off\n");
    }
    // LED 3 제어 (13번 핀 확장)
    else if (c == 'E') {
      digitalWrite(LEDpin3, HIGH); 
      Serial.print("led3on\n");
    }
    else if (c == 'F') {
      digitalWrite(LEDpin3, LOW);    
      Serial.print("led3off\n");
    }
    // LED 4 제어 (14번 / A0 핀 확장)
    else if (c == 'G') {
      digitalWrite(LEDpin4, HIGH); 
      Serial.print("led4on\n");
    }
    else if (c == 'H') {
      digitalWrite(LEDpin4, LOW);    
      Serial.print("led4off\n");
    }
  }
}
