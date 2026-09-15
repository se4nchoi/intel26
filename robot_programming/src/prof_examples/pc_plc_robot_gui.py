from neuromeka import IndyDCP3
from time import sleep
ROBOT_IP = "192.168.3.7"
indy = IndyDCP3(ROBOT_IP)
from pymcprotocol import Type3E
import tkinter as tk
import threading
print("Indy7 연결 성공")
MOVE_VEL = 20
MOVE_ACC = 20
ZERO_JOINT = [ 0.0,   0.0,   0.0,   0.0,   0.0,   0.0]
PLC_IP = "192.168.3.150"
PLC_PORT = 1026
plc = Type3E()
plc.connect(PLC_IP, PLC_PORT)
print("PLC 연결 성공")
ADDR_START = "M100"  # PLC → Python (Start)
ADDR_DONE  = "M101"  # Python → PLC (Done)
def motion_done_check():
    print("이동 완료 대기...")
    indy.wait_for_motion_state( "is_target_reached"  )
    print("이동 완료!")
def move_home():
    def task():
        print("홈 위치 이동 중...")
        indy.move_home()
        motion_done_check()
        print("홈 위치 도착 완료")
    threading.Thread(  target=task  ).start()
def move_zero():
    def task():
        print("영점 위치 이동 중...")
        indy.movej(   jtarget=ZERO_JOINT,    vel_ratio=MOVE_VEL,      acc_ratio=MOVE_ACC       )
        motion_done_check()
        print("영점 위치 도착 완료")
    threading.Thread(  target=task ).start()
# PLC 감시
def plc_monitor():
    """PLC에서 Start 신호 감지 시 Indy7 동작 수행"""
    print("PLC 감시 스레드 시작")
    is_home = True
    while True:
        try:
            start_signal = plc.batchread_bitunits(  ADDR_START,   1      )[0]
            if start_signal == 1:
                if is_home:
                    print(  "[PLC] Start 신호 감지 "  "→ 로봇 영점 이동 수행"                    )
                    indy.movej( jtarget=ZERO_JOINT,   vel_ratio=MOVE_VEL,  acc_ratio=MOVE_ACC         )
                    motion_done_check()
                    is_home = False
                else:
                    print("[PLC] Start 신호 감지 " "→ 로봇 홈 이동 수행"        )
                    indy.move_home()
                    motion_done_check()
                    is_home = True
                print( "[PLC] 로봇 동작 완료 " "→ Done 신호 ON"    )
                plc.batchwrite_bitunits(  ADDR_DONE,  [1]    )
                sleep(1)
                plc.batchwrite_bitunits( ADDR_DONE,   [0]      )
                print(   "[PLC] Done 신호 초기화 완료"              )
                # Start 신호 OFF 대기
                while plc.batchread_bitunits(     ADDR_START,    1  )[0] == 1:
                    sleep(0.1)
            else:
                sleep(0.1)
        except Exception as e:
            print(
                f"[오류] PLC 감시 중 예외 발생: {e}"        )
            sleep(1)
t_plc = threading.Thread( target=plc_monitor, daemon=True)
t_plc.start()
# Tkinter GUI 구성
root = tk.Tk()
root.title("Indy7 + PLC 제어 패널")
root.geometry("350x260")
label = tk.Label( root, text="Indy7 + PLC 제어 패널", font=("Arial", 14))
label.pack( pady=10)
btn_home = tk.Button(root,text="1. 홈으로 이동", command=move_home,
    bg="lightblue",  width=25,    height=2)
btn_home.pack( pady=5)
btn_zero = tk.Button(root, text="2. 영점으로 이동",    command=move_zero,
    bg="lightgreen",  width=25,    height=2)
btn_zero.pack(    pady=5)
lbl_status = tk.Label( root,   text="PLC Start 신호 대기 중...",    fg="gray")
lbl_status.pack(    pady=10)
def on_closing():
    print("프로그램 종료 중...")

    try:
        plc.close()
        print("PLC 연결 종료")
    except Exception as e:
        print("PLC 종료 오류 :", e)
    root.destroy()
    print("프로그램 종료 완료")
root.protocol( "WM_DELETE_WINDOW", on_closing)
root.mainloop()