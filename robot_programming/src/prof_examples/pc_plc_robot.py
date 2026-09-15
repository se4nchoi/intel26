
from neuromeka import IndyDCP3
from time import sleep
ROBOT_IP = "192.168.3.7"
indy = IndyDCP3(ROBOT_IP)
from pymcprotocol import Type3E
print("Indy7 연결 성공")
MOVE_VEL = 20
MOVE_ACC = 20
ZERO_JOINT = [ 0.0,   0.0,    0.0,    0.0,    0.0,    0.0]
PLC_IP = "192.168.3.150"
PLC_PORT = 1026
plc = Type3E()
plc.connect( PLC_IP, PLC_PORT)
print("PLC 연결 성공")
ADDR_START = "M100"  # PLC → Python : Start
ADDR_DONE  = "M101"  # Python → PLC : Done
def motion_done_check():
    print("이동 완료 대기...")
    indy.wait_for_motion_state( "is_target_reached"   )
    print("이동 완료!")
def move_home():
    print("홈 위치 이동 중...")
    indy.move_home()
    motion_done_check()
    print("홈 위치 도착 완료")
def move_zero():
    print("영점 위치 이동 중...")
    indy.movej(jtarget=ZERO_JOINT, vel_ratio=MOVE_VEL, acc_ratio=MOVE_ACC )
    motion_done_check()
    print("영점 위치 도착 완료")
def plc_monitor():
    print("PLC 감시 시작")
    # 시작할 때 로봇이 HOME 위치에 있다고 가정
    is_home = True
    while True:
        try:
            start_signal = plc.batchread_bitunits( ADDR_START, 1  )[0]
            if start_signal == 1:
                print(   "[PLC] M100 Start 신호 감지"         )
                if is_home:
                    print(  "[PLC] 로봇 ZERO 이동 수행"      )
                    move_zero()
                    is_home = False
                # 현재 ZERO 상태이면 HOME 이동
                else:
                    print(  "[PLC] 로봇 HOME 이동 수행"      )
                    move_home()
                    is_home = True
                print( "[PLC] 로봇 동작 완료"    )
                print( "[PLC] M101 Done 신호 ON"   )
                plc.batchwrite_bitunits( ADDR_DONE,  [1]   )
                sleep(1)
                plc.batchwrite_bitunits(  ADDR_DONE,  [0]  )
                print(   "[PLC] M101 Done 신호 OFF"       )
                print(   "[PLC] M100 OFF 대기..."         )
                while plc.batchread_bitunits( ADDR_START,  1 )[0] == 1:
                    sleep(0.1)
                print(  "[PLC] M100 OFF 확인"      )
            else:
                sleep(0.1)
        except KeyboardInterrupt:
            print()
            print( "프로그램 종료 요청"    )
            break
        except Exception as e:
            print( "[오류] PLC 감시 중 예외 발생 :",    e    )
            sleep(1)
try:
    plc_monitor()
except KeyboardInterrupt:
    print( "프로그램을 종료합니다."  )
finally:
    try:
        plc.batchwrite_bitunits( ADDR_DONE,  [0]        )
    except Exception as e:
        print(  "Done 신호 초기화 오류 :",    e    )
    try:
        plc.close()
        print(   "PLC 연결 종료"     )
    except Exception as e:
        print( "PLC 종료 오류 :",   e    )
    print( "프로그램 종료 완료"    )
    
# signals = plc.batchread_bitunits(ADDR_START, 3)
# m100 = signals[0]
# m101 = signals[1]
# m102 = signals[2]
# start_signal = plc.batchread_bitunits(ADDR_START, 3)[0]
# start_signal = plc.batchread_bitunits(ADDR_START, 3)[2]#m102
# signals = plc.batchread_bitunits("M100", 3)
# switch1 = signals[0]    # M100
# switch2 = signals[1]    # M101
# switch3 = signals[2]    # M102
# print("M100 =", switch1)
# print("M101 =", switch2)
# print("M102 =", switch3)

#여러개의 값을 출력을 내려면 다음처럼 합니다.
# plc.batchwrite_bitunits("M101", [1, 1, 1])