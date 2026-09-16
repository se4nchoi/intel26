
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
MOVE_VEL = 20
MOVE_ACC = 20
VACUUM_DO = 2
ZERO_JOINT = [0, 0, 0, 0, 0, 0]
def move_done_check():
    print("이동 완료 대기...")
    indy.wait_for_motion_state("is_target_reached")
    print("이동 완료!")
def robot_home():
    print("로봇 HOME 이동")
    indy.move_home()
    move_done_check()
def robot_zero():
    print("로봇 ZERO 이동")
    indy.movej( jtarget=ZERO_JOINT, vel_ratio=MOVE_VEL, acc_ratio=MOVE_ACC    )
    move_done_check()
def vacuum_on():
    print("진공 ON")
    indy.set_do([(VACUUM_DO, True)])
    sleep(0.5)
def vacuum_off():
    print("진공 OFF")
    indy.set_do([(VACUUM_DO, False)])
    sleep(0.5)
def process_d100(cmd):
    result = 0
    if cmd == 1:
        robot_home()
        result = 1
    elif cmd == 2:
        robot_zero()
        result = 2
    elif cmd == 3:
        vacuum_on()
        result = 3
    elif cmd == 4:
        vacuum_off()
        result = 4
    elif 10 <= cmd <= 100:
        print(f"로봇 속도비 설정: {cmd}%")  
        indy.set_speed_ratio(cmd)
        result = cmd
    elif cmd == 200:
        state = indy.get_control_state()
        current_p = state["p"]
        result = int(current_p[2])
        print("현재 Z 위치 =", result)
    else:
        print("정의되지 않은 명령입니다.")
        result = -1
    plc.batchwrite_wordunits("D200", [result])
    plc.batchwrite_wordunits("D100", [0])
    print(f"D200 결과값 = {result}")
    print("D100 초기화 완료")
print("D100 + IndyDCP3 제어 프로그램 시작")
print("1=HOME, 2=ZERO, 3=진공ON, 4=진공OFF, 10~100=속도, 200=현재Z, q=종료")
try:
    while True:
        value = input("\nPLC D100에 쓸 명령 입력: ")
        if value.lower() == "q":
            break
        try:
            cmd = int(value)
        except ValueError:
            print("숫자를 입력하세요.")
            continue
        plc.batchwrite_wordunits("D100", [cmd])
        read_cmd = plc.batchread_wordunits("D100", 1)[0]
        print(f"D100 기록값: {read_cmd}")
        if read_cmd != 0:
            process_d100(read_cmd)
        sleep(0.1)
except KeyboardInterrupt:
    print("\n프로그램 수동 종료")
finally:
    try:
        vacuum_off()
    except:
        pass
    plc.close()
    print("PLC 연결 종료")

# ; ============================================
# ; X0 : HOME 명령
# ; ============================================

# X0
# ----| |------------------------[ MOV K1 D100 ]


# ; ============================================
# ; X1 : ZERO 명령
# ; ============================================

# X1
# ----| |------------------------[ MOV K2 D100 ]


# ; ============================================
# ; X2 : VACUUM ON
# ; ============================================

# X2
# ----| |------------------------[ MOV K3 D100 ]


# ; ============================================
# ; X3 : VACUUM OFF
# ; ============================================

# X3
# ----| |------------------------[ MOV K4 D100 ]


# ; ============================================
# ; X4 : 속도 20%
# ; ============================================

# X4
# ----| |------------------------[ MOV K20 D100 ]


# ; ============================================
# ; X5 : 속도 50%
# ; ============================================

# X5
# ----| |------------------------[ MOV K50 D100 ]


# ; ============================================
# ; X6 : 속도 100%
# ; ============================================

# X6
# ----| |------------------------[ MOV K100 D100 ]


# ; ============================================
# ; X7 : 현재 Z 위치 읽기
# ; ============================================

# X7
# ----| |------------------------[ MOV K200 D100 ]    