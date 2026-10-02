
#2by2_1by22dan_lcd_gui_1
import threading
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from neuromeka import IndyDCP3
from pymcprotocol import Type3E
import serial
import time
running = True
# 로봇 작업 중복 실행 방지
task_lock = threading.Lock()
ROBOT_IP = "192.168.3.2"
MOVE_VEL = 10
MOVE_ACC = 10
VACUUM_DO = 2
indy = IndyDCP3(ROBOT_IP)
print("Indy7 DCP3 연결 준비 완료")
PLC_IP = "192.168.3.100"
PLC_PORT = 1026
# PLC → Python 작업 명령
PLC_OP1_BIT = "M100"
PLC_OP2_BIT = "M101"
plc = Type3E()
try:
    plc.connect(PLC_IP,  PLC_PORT )
    plc_connected = True
    print("PLC 연결 성공")
except Exception as e:
    plc_connected = False
    print("PLC 연결 실패 :", e)
ARDUINO_PORT = "COM7"
ARDUINO_BAUD = 9600
arduino = None
arduino_connected = False
try:
    arduino = serial.Serial(ARDUINO_PORT,  ARDUINO_BAUD   )
    time.sleep(2)
    arduino_connected = True
    print("Arduino 연결 성공")
except Exception as e:
    print("Arduino 연결 실패 :", e)
window = tk.Tk()
window.title("Indy7 IndyDCP3 + PLC + Arduino Control")
window.geometry( "700x650")
status_label = tk.Label(window, text="상태 : 대기중", font=("Arial", 14))
status_label.pack( pady=10)
plc_label = tk.Label(window, text=f"PLC 연결 상태 : " f"{'연결됨' if plc_connected else '연결 오류'}",
    font=("Arial", 12), fg= "green" if plc_connected   else "red" )
plc_label.pack()
arduino_label = tk.Label(window,text=f"Arduino 연결 상태 : "f"{'연결됨' if arduino_connected else '연결 오류'}",
    font=("Arial", 12), fg="green"if arduino_connected  else "red")
arduino_label.pack()
log_box = ScrolledText(window, width=85, height=26 )
log_box.pack(padx=10, pady=10)
def log(msg):
    log_box.insert(tk.END,  msg + "\n"    )
    log_box.see( tk.END)
    print(msg)
def safe_log(msg):
    if running:
        try:
            window.after( 0, log,   msg    )
        except:
            pass
def set_status(msg):
    if running:
        try:
            window.after( 0,  lambda: status_label.config( text=msg  )  )
        except:
            pass
def lcd_send(msg):
    if (arduino_connected  and arduino is not None and arduino.is_open ):
        try:
            arduino.write( (msg + "\n").encode()   )
            safe_log( f"[Arduino 송신] {msg}"       )
        except Exception as e:
            safe_log( f"[Arduino 송신 오류] {e}"     )
def result_ok(result):
    if isinstance(result, dict):
        code = result.get( "code"    )
        return str(code) == "0"
    return True
def motion_done_check():
    if not running:
        return False
    try:
        safe_log(  "로봇 이동 완료 대기..."   )
        indy.wait_for_motion_state(   "is_target_reached"    )
        safe_log( "로봇 이동 완료"   )
        return True
    except Exception as e:
        safe_log( f"이동 완료 확인 오류 : {e}"     )
        return False
def move_linear(target_position, name="MoveL"):
    if not running:
        return False
    try:
        safe_log( f"{name}"  )
        safe_log( f"Target = {target_position}"  )
        result = indy.movel(ttarget=target_position, vel_ratio=MOVE_VEL, acc_ratio=MOVE_ACC  )
        safe_log(   f"MoveL Result = {result}"        )
        if not result_ok(result):
            safe_log(  "MoveL 명령 실패"            )
            return False
        return motion_done_check()
    except Exception as e:
        safe_log( f"MoveL 오류 : {e}"        )
        return False
def robot_home():
    if not running:
        return False
    try:
        safe_log(  "HOME 이동 시작"  )
        result = indy.move_home()
        safe_log( f"HOME Result = {result}"   )
        if not result_ok(result):
            safe_log(   "HOME 명령 실패"            )
            return False
        if not motion_done_check():
            return False
        safe_log( "HOME 이동 완료" )
        return True
    except Exception as e:
        safe_log( f"HOME 이동 오류 : {e}" )
        return False
def vacuum_on():
    try:
        safe_log( "Vacuum ON"  )
        result = indy.set_do([ {  "address": VACUUM_DO,  "state": True  } ]  )
        safe_log(   f"Vacuum ON Result = {result}"    )
        if not result_ok(result):
            return False
        time.sleep( 0.5 )
        return True
    except Exception as e:
        safe_log( f"Vacuum ON 오류 : {e}"    )
        return False
def vacuum_off():
    try:
        safe_log(  "Vacuum OFF"    )
        result = indy.set_do( [ { "address": VACUUM_DO,  "state": False   }  ]  )
        safe_log( f"Vacuum OFF Result = {result}"   )
        if not result_ok(result):
            return False
        time.sleep(  0.5 )
        return True
    except Exception as e:
        safe_log(  f"Vacuum OFF 오류 : {e}"   )
        return False
def generate_grid( base, grid_x, grid_y, offset_x, offset_y, layers=1, layer_h=0):
    coords = []
    for layer in range(layers):
        z = ( base[2] + layer * layer_h   )
        for i in range( grid_y  ):
            for j in range( grid_x):
                x = (      base[0]   +  j * offset_x     )
                y = (      base[1]   +  i * offset_y     )
                coords.append( [ x,  y,  z ]  )
    return coords
def task_pick2by2_place2by2():
    if not running:
        return
    # 다른 작업 실행 중인지 검사
    if not task_lock.acquire(blocking=False ):
        safe_log( "[경고] 다른 로봇 작업이 실행 중입니다."   )
        return
    try:
        set_status(  "상태 : 작업1(OP1) 실행중"        )
        lcd_send(   "OP1_START"      )
        safe_log(      ""       )
        safe_log( "============================"  )
        safe_log( "작업1 시작"   )
        safe_log( "2 x 2 Pick → 2 x 2 Place" )
        PICK_BASE = [ 250.4689486,  333.77,    410.56    ]
        PLACE_BASE = [ 154.8543564,  326.10,  410.56     ]
        PICK_GRID_X = 2
        PICK_GRID_Y = 2
        PLACE_GRID_X = 2
        PLACE_GRID_Y = 2
        OFFSET_X = 40.0
        OFFSET_Y = 40.0
        RETRACT_Z = 50.0
        ROT_P = [ -175.85,    5.51,     169.58     ]
        ROT_R = [ 1.96,      -177.90,   3.90       ]
        pick_positions = generate_grid( PICK_BASE,  PICK_GRID_X, PICK_GRID_Y, OFFSET_X, OFFSET_Y   )
        place_positions = generate_grid( PLACE_BASE,PLACE_GRID_X, PLACE_GRID_Y, OFFSET_X, OFFSET_Y )
        safe_log(  f"Pick Positions = {pick_positions}"     )
        safe_log( f"Place Positions = {place_positions}"    )
        if not robot_home():
            return
        # 4개 물체 작업
        for i in range( len(pick_positions)   ):
            if not running:
                break
            pick = pick_positions[i]
            place = place_positions[i]
            safe_log(   ""            )
            safe_log(  f">>> STEP {i + 1}"    )
            target = [ pick[0],  pick[1],  pick[2] + RETRACT_Z,  *ROT_P   ]
            if not move_linear(  target,  "Pick Approach"    ):
                break
            target = [  pick[0],  pick[1],   pick[2],    *ROT_P     ]
            if not move_linear(target,  "Pick"      ):
                break
            if not vacuum_on():
                break
            target = [   pick[0],    pick[1],  pick[2] + RETRACT_Z,    *ROT_P     ]
            if not move_linear( target,    "Pick Retract"       ):
                break
            # PLACE APPROACH
            target = [  place[0],  place[1],   place[2] + RETRACT_Z,   *ROT_R    ]
            if not move_linear(  target,   "Place Approach"     ):
                break
            target = [ place[0],  place[1],  place[2], *ROT_R  ]
            if not move_linear(   target,  "Place"     ):
                break
            if not vacuum_off():
                break
            target = [ place[0],  place[1], place[2] + RETRACT_Z,  *ROT_R    ]
            if not move_linear(  target,   "Place Retract"    ):
                break
        if running:
            robot_home()
            lcd_send("OP1_FINISH"  )
            safe_log( "============================" )
            safe_log( "작업1 완료"  )
            safe_log( "============================"  )
            set_status(  "상태 : 작업1 완료(OP1_FINISH)"    )
    except Exception as e:
        safe_log(    f"[작업1 오류] {e}"     )
        set_status(  "상태 : 작업1 오류"     )
        try:
            vacuum_off()
        except:
            pass
    finally:
        task_lock.release()
def task_pal_1by2_2layer():
    if not running:
        return
    if not task_lock.acquire( blocking=False ):
        safe_log("[경고] 다른 로봇 작업이 실행 중입니다."  )
        return
    try:
        set_status(  "상태 : 작업2(OP2) 실행중"      )
        lcd_send(        "OP2_START"       )
        safe_log(        ""        )
        safe_log(  "============================"        )
        safe_log(         "작업2 시작"        )
        safe_log(  "1 x 2 x 2 Layer Palletizing"        )
        safe_log(  "============================"        )
        PICK_BASE = [ 250.468,   373.77,    413.56  ]
        PLACE_BASE = [ 154.85,   321.60,    410.56  ]
        GRID_X = 1
        GRID_Y = 2
        NUM_LAYERS = 2
        OFFSET_X = 40.0
        OFFSET_Y = 40.0
        LAYER_H = 30.0
        RETRACT_Z = 50.0
        ROT_P = [  -175.85,      5.51,       169.58     ]
        ROT_R = [  1.96,       -177.90,      3.90       ]
        place_positions = generate_grid(PLACE_BASE, GRID_X, GRID_Y, OFFSET_X,
            OFFSET_Y,   NUM_LAYERS,     LAYER_H     )
        safe_log( f"Place Positions = {place_positions}"    )
        if not robot_home():
            return
        for i, place in enumerate(  place_positions   ):
            if not running:
                break
            safe_log(   ""   )
            safe_log(  f">>> STEP {i + 1}"   )
            target = [ PICK_BASE[0],  PICK_BASE[1],PICK_BASE[2] + RETRACT_Z,  *ROT_P       ]
            if not move_linear(target,  "Pick Approach"   ):
                break
            # PICK
            target = [ PICK_BASE[0], PICK_BASE[1], PICK_BASE[2],   *ROT_P  ]
            if not move_linear(  target,     "Pick"        ):
                break
            if not vacuum_on():
                break
            target = [ PICK_BASE[0], PICK_BASE[1],PICK_BASE[2] + RETRACT_Z,   *ROT_P      ]
            if not move_linear(  target, "Pick Retract"    ):
                break
            target = [  place[0],  place[1],  place[2] + RETRACT_Z,   *ROT_R        ]
            if not move_linear( target,   "Place Approach"   ):
                break
            target = [ place[0],  place[1],   place[2],    *ROT_R        ]
            if not move_linear( target,   "Place"      ):
                break
            if not vacuum_off():
                break
            target = [  place[0],  place[1],   place[2] + RETRACT_Z,   *ROT_R  ]
            if not move_linear(   target, "Place Retract"   ):
                break
        if running:
            robot_home()
            lcd_send(  "OP2_FINISH"      )
            safe_log( "============================"  )
            safe_log(       "작업2 완료"            )
            safe_log( "============================"   )
            set_status(  "상태 : 작업2 완료(OP2_FINISH)"     )
    except Exception as e:
        safe_log(  f"[작업2 오류] {e}"    )
        set_status(   "상태 : 작업2 오류" )
        try:
            vacuum_off()
        except:
            pass
    finally:
        task_lock.release()
#  작업 Thread 실행 함수
def run_task1():
    if not running:
        return
    thread = threading.Thread(target=task_pick2by2_place2by2, daemon=True )
    thread.start()
def run_task2():
    if not running:
        return
    thread = threading.Thread(target=task_pal_1by2_2layer, daemon=True )
    thread.start()
#  GUI 버튼
btn1 = tk.Button(window, text="작업1 실행 (OP1)", width=25, command=run_task1 )
btn1.pack(pady=5)
btn2 = tk.Button(window, text="작업2 실행 (OP2)", width=25, command=run_task2)
btn2.pack( pady=5)
def plc_listener():
    if not plc_connected:
        safe_log("[PLC] PLC 미연결" )
        return
    prev_op1 = 0
    prev_op2 = 0
    safe_log("[PLC] Listener 시작"    )
    while running:
        try:
            op1 = plc.batchread_bitunits( headdevice=PLC_OP1_BIT,  readsize=1  )[0]
            op2 = plc.batchread_bitunits( headdevice=PLC_OP2_BIT,  readsize=1  )[0]
            if ( op1 == 1  and   prev_op1 == 0   ):
                safe_log( "[PLC] M100 OP1 수신"  )
                run_task1()
            if ( op2 == 1   and  prev_op2 == 0   ):
                safe_log( "[PLC] M101 OP2 수신"   )
                run_task2()
            prev_op1 = op1
            prev_op2 = op2
        except Exception as e:
            safe_log(  f"[PLC] 통신 오류 : {e}"  )
            time.sleep(   1  )
        time.sleep( 0.05 )
threading.Thread(target=plc_listener, daemon=True).start()
def serial_listener():
    if not arduino_connected:
        safe_log( "[Arduino] Arduino 미연결"  )
        return
    safe_log("[Arduino] Listener 시작"  )
    while running:
        try:
            if arduino.in_waiting:
                cmd = arduino.readline().decode().strip()#strip()은 문자열 앞뒤의 공백, \r, \n, 탭 등의 whitespace를 제거
                if cmd:
                    safe_log(  f"[Arduino 수신] {cmd}"     )
                if cmd == "OP1":
                    run_task1()
                elif cmd == "OP2":
                    run_task2()
        except Exception as e:
            safe_log( f"[Arduino] 수신 오류 : {e}"   )
            time.sleep(  1  )
        time.sleep( 0.05 )
threading.Thread(target=serial_listener, daemon=True).start()
def on_closing():
    global running
    running = False
    try:
        log( "프로그램 종료 중...")
    except:
        pass
    try:
        indy.set_do( [ {  "address": VACUUM_DO, "state": False     }     ]        )
    except:
        pass
    try:
        if ( arduino is not None    and    arduino.is_open     ):
            arduino.close()
    except:
        pass
    if plc_connected:
        try:
            plc.close()
        except:
            pass
    try:
        log(  "장비 연결 종료 완료"    )
    except:
        pass
    window.destroy()
window.protocol( "WM_DELETE_WINDOW",  on_closing)


log(  "======================================")
log(    "Indy7 IndyDCP3 통합 제어 프로그램"   )
log( "======================================")
log(  f"Robot IP : {ROBOT_IP}")
log(  f"PLC IP   : {PLC_IP}" )
log(  f"PLC PORT : {PLC_PORT}")
log( f"Arduino  : {ARDUINO_PORT}")
log(    f"Baudrate : {ARDUINO_BAUD}")
log(  "--------------------------------------")
log(   "PLC M100 → 작업1")
log(    "PLC M101 → 작업2")
log(    "Arduino OP1 → 작업1")
log(    "Arduino OP2 → 작업2")
log(   "GUI OP1 버튼 → 작업1")
log(   "GUI OP2 버튼 → 작업2")
log(  "======================================")
window.mainloop()