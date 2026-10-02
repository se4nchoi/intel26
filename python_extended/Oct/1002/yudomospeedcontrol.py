
from pymcprotocol import Type3E
from time import sleep
PLC_IP = "192.168.3.150"
PLC_PORT = 1026
plc = Type3E()
# PLC → Python
# M100 ~ M105
BUTTON_START = "M100"
# M100 = 정회전
# M101 = 역회전
# M102 = 정지
# M103 = 고속
# M104 = 중속
# M105 = 저속
# Python → PLC
MOTOR_CMD = "M200"
# M200 = 정회전
# M201 = 역회전
# M202 = 정지
SPEED_CMD = "M203"
# M203 = 고속
# M204 = 중속
# M205 = 저속
def motor_stop():
    plc.batchwrite_bitunits(headdevice=MOTOR_CMD,values=[0, 0, 1] )
    print("모터 정지")
def motor_forward():
    plc.batchwrite_bitunits(headdevice=MOTOR_CMD, values=[1, 0, 0] )
    print("모터 정회전")
# 역회전
def motor_reverse():
    plc.batchwrite_bitunits( headdevice=MOTOR_CMD,values=[0, 1, 0] )
    print("모터 역회전")
def speed_high():
    plc.batchwrite_bitunits(headdevice=SPEED_CMD,values=[1, 0, 0])
    print("고속 운전 : RH ON")
def speed_middle():
    plc.batchwrite_bitunits(headdevice=SPEED_CMD,values=[0, 1, 0]  )
    print("중속 운전 : RM ON")
def speed_low():
    plc.batchwrite_bitunits(headdevice=SPEED_CMD, values=[0, 0, 1] )
    print("저속 운전 : RL ON")
try:
    plc.connect(PLC_IP, PLC_PORT)
    print("PLC 연결 성공")
    # 초기 상태
    motor_stop()
    # 초기 속도 = 저속
    speed_low()
    while True:
        # M100 ~ M105 한 번에 읽기
        buttons = plc.batchread_bitunits(headdevice=BUTTON_START, readsize=6  )
        forward = buttons[0]     # M100
        reverse = buttons[1]     # M101
        stop    = buttons[2]     # M102
        high    = buttons[3]     # M103
        middle  = buttons[4]     # M104
        low     = buttons[5]     # M105
        if stop == 1:
            motor_stop()
            while plc.batchread_bitunits(headdevice="M102",readsize=1)[0] == 1:
                sleep(0.05)
        elif forward == 1:
            motor_forward()
            while plc.batchread_bitunits(headdevice="M100",readsize=1)[0] == 1:
                sleep(0.05)
        elif reverse == 1:
            motor_stop()
            sleep(1)
            motor_reverse()
            while plc.batchread_bitunits(headdevice="M101", readsize=1 )[0] == 1:
                sleep(0.05)
        elif high == 1:
            speed_high()
            while plc.batchread_bitunits(headdevice="M103",readsize=1)[0] == 1:
                sleep(0.05)
        elif middle == 1:
            speed_middle()
            while plc.batchread_bitunits(headdevice="M104",readsize=1)[0] == 1:
                sleep(0.05)
        elif low == 1:
            speed_low()
            while plc.batchread_bitunits(headdevice="M105",readsize=1)[0] == 1:
                sleep(0.05)
        sleep(0.05)
except KeyboardInterrupt:
    print("\n프로그램 종료")
    try:
        motor_stop()
    except Exception:
        pass
except Exception as e:
    print("PLC 통신 오류 :", e)
    try:
        motor_stop()
    except Exception:
        pass
finally:
    try:
        plc.close()
    except Exception:
        pass
    print("PLC 연결 종료")

#  X0
# --| |--------------------------------( M100 )
#  정회전


#  X1
# --| |--------------------------------( M101 )
#  역회전


#  X2
# --| |--------------------------------( M102 )
#  정지


#  X3
# --| |--------------------------------( M103 )
#  고속


#  X4
# --| |--------------------------------( M104 )
#  중속


#  X5
# --| |--------------------------------( M105 )

#  저속  
#  M200        M201
# --| |---------|/|--------------------( Y0 )
#  정회전       역회전                    STF


#  M201        M200
# --| |---------|/|--------------------( Y1 )
#  역회전       정회전                    STR


#  M203
# --| |--------------------------------( Y2 )
#  고속                                   RH


#  M204
# --| |--------------------------------( Y3 )
#  중속                                   RM


#  M205
# --| |--------------------------------( Y4 )
#  저속                                   RL  