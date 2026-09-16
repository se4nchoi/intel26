
from pymcprotocol import Type3E
from neuromeka import IndyDCP3
from time import sleep
PLC_IP = "192.168.3.150"
PLC_PORT = 1026
ROBOT_IP = "192.168.3.7"
plc = Type3E()
plc.connect(PLC_IP, PLC_PORT)
print("PLC 연결 성공")
indy = IndyDCP3(ROBOT_IP)
print("Indy7 DCP3 연결 성공")
BIT_INPUTS = {"BIT_CMD1": "M100",    "BIT_CMD2": "M101",
    "BIT_CMD3": "M102",    "BIT_CMD4": "M103"}
BIT_OUTPUTS = {    "BIT_CMD1": "M200",    "BIT_CMD2": "M201",
    "BIT_CMD3": "M202",    "BIT_CMD4": "M203"}
WORD_INPUTS = {    "WORD_CMD1": "D100",    "WORD_CMD2": "D101",
    "WORD_CMD3": "D102",    "WORD_CMD4": "D103"}
WORD_OUTPUTS = {    "WORD_CMD1": "D200",    "WORD_CMD2": "D201",
    "WORD_CMD3": "D202",    "WORD_CMD4": "D203"}
ZERO_JOINT = [0, 0, 0, 0, 0, 0]
MOVE_VEL = 20
MOVE_ACC = 20
VACUUM_DO = 2
def move_done_check():
    indy.wait_for_motion_state("is_target_reached")
def robot_home():
    print("로봇 HOME 이동")
    indy.move_home()
    move_done_check()
def robot_zero():
    print("로봇 ZERO 이동")
    indy.movej(jtarget=ZERO_JOINT, vel_ratio=MOVE_VEL, acc_ratio=MOVE_ACC )
    move_done_check()
def vacuum_on():
    print("진공 ON")
    indy.set_do([(VACUUM_DO, True)])
    sleep(0.5)
def vacuum_off():
    print("진공 OFF")
    indy.set_do([(VACUUM_DO, False)])
    sleep(0.5)
def pulse_bit(addr):
    plc.batchwrite_bitunits(addr, [1])
    sleep(0.3)
    plc.batchwrite_bitunits(addr, [0])
def process_bit(name):
    print(f"\n비트 명령 감지: {name}")
    if name == "BIT_CMD1":
        robot_home()
    elif name == "BIT_CMD2":
        robot_zero()
    elif name == "BIT_CMD3":
        vacuum_on()
    elif name == "BIT_CMD4":
        vacuum_off()
    out_addr = BIT_OUTPUTS[name]
    pulse_bit(out_addr)
    print(f"{name} 완료 → {out_addr} 펄스 출력")
def process_word(name, value):
    print(f"\n워드 명령 감지: {name}, 값 = {value}")
    result_value = 0
    if name == "WORD_CMD1":
        # D100 값으로 로봇 속도비 설정
        # 예: D100 = 30 → 속도비 30%
        speed = max(1, min(100, int(value)))
        indy.set_speed_ratio(speed)
        result_value = speed
    elif name == "WORD_CMD2":
        # D101 = 1 → HOME
        # D101 = 2 → ZERO
        if value == 1:
            robot_home()
            result_value = 1
        elif value == 2:
            robot_zero()
            result_value = 2
        else:
            result_value = -1
    elif name == "WORD_CMD3":
        # D102 = 1 → 진공 ON
        # D102 = 0 → 진공 OFF
        if value == 1:
            vacuum_on()
            result_value = 1
        elif value == 0:
            vacuum_off()
            result_value = 0
        else:
            result_value = -1
    elif name == "WORD_CMD4":
        # 현재 로봇 Z 위치를 D203에 기록
        state = indy.get_control_state()
        current_p = state["p"]
        result_value = int(current_p[2])
    out_addr = WORD_OUTPUTS[name]
    plc.batchwrite_wordunits(out_addr,[result_value] )
    print(f"{name} 완료 → {out_addr} = {result_value}")
print("비트 + 워드 혼합 PLC + IndyDCP3 프로그램 실행")
print("Ctrl + C 로 종료")
try:
    while True:
        try:
            for name, addr in BIT_INPUTS.items():
                bit_val = plc.batchread_bitunits(addr, 1)[0]
                if bit_val == 1:
                    process_bit(name)
                    while plc.batchread_bitunits(addr, 1)[0] == 1:
                        sleep(0.05)
            for name, addr in WORD_INPUTS.items():
                word_val = plc.batchread_wordunits(addr, 1)[0]
                if word_val != 0:
                    process_word(name, word_val)
                    plc.batchwrite_wordunits(addr, [0])
            sleep(0.05)
        except TimeoutError:
            print("PLC 통신 Timeout 발생")
            sleep(1)
        except Exception as e:
            print("오류 발생:", e)
            sleep(1)
except KeyboardInterrupt:
    print("프로그램 종료")
finally:
    try:
        vacuum_off()
    except:
        pass
    try:
        plc.close()
    except:
        pass
    print("PLC 연결 종료")

#  HOME
# X0 ------------------------ SET M100
# M200 ---------------------- RST M100
# zero
# X1 ------------------------ SET M101
# M201 ---------------------- RST M101
# Vacuum ON
# X2 ------------------------ SET M102
# M202 ---------------------- RST M102
# ; Vacuum OFF
# X3 ------------------------ SET M103
# M203 ---------------------- RST M103
#  Speed 30%
# X4 ------------------------ MOV K30 D100
#  Speed 60%
# X5 ------------------------ MOV K60 D100
#  Speed 100%
# X6 ------------------------ MOV K100 D100
#  WORD HOME
# X7 ------------------------ MOV K1 D101
#  WORD ZERO
# X10 ----------------------- MOV K2 D101
# X11 ----------------------- MOV K1 D103