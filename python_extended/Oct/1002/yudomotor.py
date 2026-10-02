
from pymcprotocol import Type3E
from time import sleep
PLC_IP = "192.168.3.10"
PLC_PORT = 1026
plc = Type3E()
# PLC → Python
FORWARD_BUTTON = "M100"     # X0 → M100 : 정회전 버튼
REVERSE_BUTTON = "M101"     # X1 → M101 : 역회전 버튼
STOP_BUTTON    = "M102"     # X2 → M102 : 정지 버튼
# Python → PLC
FORWARD_CMD = "M200"        # 정회전 명령
REVERSE_CMD = "M201"        # 역회전 명령
STOP_CMD    = "M202"        # 정지 상태 표시
motor_state = "STOP"
def motor_stop():
    global motor_state
    plc.batchwrite_bitunits(headdevice=FORWARD_CMD,values=[0, 0, 1] )
    motor_state = "STOP"
    print("모터 정지")
def motor_forward():
    global motor_state
    # 이미 정회전 중이면 아무것도 하지 않음
    if motor_state == "FORWARD":
        return
    # 역회전 중이라면 먼저 정지
    if motor_state == "REVERSE":
        print("역회전 → 정회전 방향 변경")
        plc.batchwrite_bitunits(headdevice=FORWARD_CMD, values=[0, 0, 1] )
        print("모터 정지 후 방향 전환 대기")
        sleep(1)
    plc.batchwrite_bitunits(headdevice=FORWARD_CMD, values=[1, 0, 0]  )
    motor_state = "FORWARD"
    print("모터 정회전")
def motor_reverse():
    global motor_state
    # 이미 역회전 중이면 아무것도 하지 않음
    if motor_state == "REVERSE":
        return
    # 정회전 중이라면 먼저 정지
    if motor_state == "FORWARD":
        print("정회전 → 역회전 방향 변경")
        plc.batchwrite_bitunits(headdevice=FORWARD_CMD, values=[0, 0, 1]  )
        print("모터 정지 후 방향 전환 대기")
        sleep(1)
    plc.batchwrite_bitunits( headdevice=FORWARD_CMD,     values=[0, 1, 0] )
    motor_state = "REVERSE"
    print("모터 역회전")
try:
    plc.connect(PLC_IP, PLC_PORT)
    print("PLC 연결 성공")
    motor_stop()
    while True:
        # M100 ~ M102 한 번에 읽기
        buttons = plc.batchread_bitunits(headdevice=FORWARD_BUTTON, readsize=3)
        forward = buttons[0]     # M100
        reverse = buttons[1]     # M101
        stop    = buttons[2]     # M102
        # 정지 버튼 최우선
        if stop == 1:
            motor_stop()
            # 버튼을 놓을 때까지 대기
            while plc.batchread_bitunits(headdevice=STOP_BUTTON, readsize=1)[0] == 1:
                sleep(0.05)
        # 정회전 버튼
        elif forward == 1:
            motor_forward()
            # 버튼을 놓을 때까지 대기
            while plc.batchread_bitunits(headdevice=FORWARD_BUTTON,readsize=1)[0] == 1:
                sleep(0.05)
        # 역회전 버튼
        elif reverse == 1:
            motor_reverse()
            # 버튼을 놓을 때까지 대기
            while plc.batchread_bitunits(headdevice=REVERSE_BUTTON,readsize=1)[0] == 1:
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
# PLC 연결 종료
finally:
    try:
        plc.close()
    except Exception:
        pass
    print("PLC 연결 종료")

# |----[ X0 ]----------------------------( M100 )----|
# |          정회전 버튼

# |----[ X1 ]----------------------------( M101 )----|
# |          역회전 버튼

# |----[ X2 ]----------------------------( M102 )----|
# |----[ M200 ]----[/ M201 ]--------------( Y0 )----|
# |     정회전       역회전 인터록           정회전 MC


# |----[ M201 ]----[/ M200 ]--------------( Y1 )----|
# |     역회전       정회전 인터록           역회전 MC
# |          정지 버튼    