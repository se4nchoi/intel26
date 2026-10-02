#include <Wire.h>
#include <LiquidCrystal_I2C.h>
LiquidCrystal_I2C lcd(0x27, 16, 2);
const int BTN_OP1 = 7;  const int BTN_OP2 = 8;
int prevOP1 = LOW;   int prevOP2 = LOW;
void setup()
{    Serial.begin(9600);     pinMode(BTN_OP1, INPUT);
    pinMode(BTN_OP2, INPUT);     lcd.init();
    lcd.backlight();      lcd.clear();
    lcd.setCursor(0, 0);     lcd.print("Indy7 Control");
    lcd.setCursor(0, 1);     lcd.print("Ready");
    Serial.println("ARDUINO_READY");}
void loop()
{    checkButtons();    checkSerial();    delay(20);}
void checkButtons()
{    int op1State = digitalRead(BTN_OP1);
    int op2State = digitalRead(BTN_OP2);
    if (op1State == HIGH && prevOP1 == LOW)
    {   delay(30);
        if (digitalRead(BTN_OP1) == HIGH)
        {   Serial.println("OP1");    lcd.clear();
            lcd.setCursor(0, 0);      lcd.print("Send Command");
            lcd.setCursor(0, 1);     lcd.print("OP1");     }
    }
    if (op2State == HIGH && prevOP2 == LOW)
    {   delay(30);
        if (digitalRead(BTN_OP2) == HIGH)
        {   Serial.println("OP2");        lcd.clear();
            lcd.setCursor(0, 0);          lcd.print("Send Command");
            lcd.setCursor(0, 1);         lcd.print("OP2");        }
    }
    prevOP1 = op1State;    prevOP2 = op2State;
}
void checkSerial()
{
    if (Serial.available() > 0)
    {
        String msg = Serial.readStringUntil('\n');
        // 문자열 앞뒤의  공백, \r, \n 등을 제거
        msg.trim();
        if (msg.length() > 0)
        {      displayMessage(msg);      }
    }
}
// Python에서 받은 메시지를 LCD에 표시
void displayMessage(String msg)
{    lcd.clear();
    if (msg == "OP1_START")
    {   lcd.setCursor(0, 0);        lcd.print("OP1");
        lcd.setCursor(0, 1);        lcd.print("RUNNING...");    }
    else if (msg == "OP1_FINISH")
    {   lcd.setCursor(0, 0);        lcd.print("OP1");
        lcd.setCursor(0, 1);        lcd.print("FINISH");    }
    else if (msg == "OP2_START")
    {   lcd.setCursor(0, 0);        lcd.print("OP2");
        lcd.setCursor(0, 1);        lcd.print("RUNNING...");
    }
    else if (msg == "OP2_FINISH")
    {   lcd.setCursor(0, 0);      lcd.print("OP2");
        lcd.setCursor(0, 1);      lcd.print("FINISH");    }
}