# not working code from non-robot room

from neuromeka import IndyDCP3
from time import sleep
ROBOT_IP = "192.168.3.2"
MOVE_VEL = 10
MOVE_ACC = 10
GRID_SIZE = 5
MAX_CELL = 25
CELL_PITCH = 40.0
APPROACH_HEIGHT = 50.0
VACUUM_DO = 2
indy = IndyDCP3(ROBOT_IP)
print("Indy7 DCP3 연결 성공")
def motion_done_check():
    indy.wait_for_motion_state( "is_target_reached"    )
def move_linear(target_position, name="MoveL"):
    print(name,"=", target_position    )
    result = indy.movel(ttarget=target_position, vel_ratio=MOVE_VEL,acc_ratio=MOVE_ACC )
    print( "MoveL result =",   result    )
    motion_done_check()
def vacuum_on():
    result = indy.set_do([{ "address": VACUUM_DO,  "state": True  } ])
    print( "Vacuum ON =",    result  )
    sleep(2)
def vacuum_off():
    result = indy.set_do([ { "address": VACUUM_DO, "state": False  }  ])
    print(  "Vacuum OFF =",    result    )
    sleep(1)

pos_first = [ 15.748302,  321.56088,  404.73798,  5.210189,  179.86049,  33.689323]
center = [ 108.16866, 389.27124,  471.23288,  1.4016397,  178.99274,  13.599214]
SLIDE_TARGET = [ 320.10547, 535.0671,  331.04337, -175.54137, -35.291645, 149.9351]
SLIDE_APPROACH = SLIDE_TARGET.copy()
SLIDE_APPROACH[2] += APPROACH_HEIGHT
SLIDE_RETRACT = SLIDE_TARGET.copy()
SLIDE_RETRACT[2] += APPROACH_HEIGHT
def cal_po(cell_number):
    if cell_number < 1 or cell_number > MAX_CELL:
        raise ValueError( f"잘못된 셀 번호입니다 : {cell_number}"        )
    cell_index = cell_number - 1
    row_index = ( cell_index // GRID_SIZE    )
    column_index = ( cell_index % GRID_SIZE    )
    x_distance = (  CELL_PITCH * row_index    )
    y_distance = (  CELL_PITCH * column_index    )
    selected_position = (  pos_first.copy()    )
    selected_position[0] += ( x_distance    )
    selected_position[1] += ( y_distance    )
    return selected_position
def make_approach(target_position):
    approach = (  target_position.copy()    )
    approach[2] += ( APPROACH_HEIGHT    )
    return approach
def pick_grid(cell_number):
    target = cal_po( cell_number    )
    approach = make_approach( target    )
    retract = make_approach(  target    )
    print()
    print( f"GRID PICK : {cell_number}번 셀"    )
    print("Approach =",    approach    )
    print("Target   =",  target   )
    print( "Retract  =",   retract    )
    move_linear( approach, "Pick Approach"   )
    move_linear( target, "Pick Target"    )
    vacuum_on()
    move_linear( retract, "Pick Retract"  )
def place_grid(cell_number):
    target = cal_po(cell_number    )
    approach = make_approach( target    )
    retract = make_approach(  target    )
    print()
    print(  f"GRID PLACE : {cell_number}번 셀"    )
    print(  "Approach =",  approach    )
    print(  "Target   =",   target    )
    print(  "Retract  =",   retract    )
    move_linear( approach,    "Place Approach"    )
    move_linear( target,   "Place Target"    )
    vacuum_off()
    move_linear( retract,  "Place Retract"    )
# 미끄럼틀 Pick
def pick_slide():
    print()
    print("SLIDE PICK")
    print( "Approach =",  SLIDE_APPROACH    )
    print( "Target   =",  SLIDE_TARGET    )
    print("Retract  =",   SLIDE_RETRACT    )
    move_linear( SLIDE_APPROACH,  "Slide Approach"    )
    move_linear( SLIDE_TARGET,   "Slide Target"    )
    vacuum_on()
    move_linear(SLIDE_RETRACT, "Slide Retract"    )
# 시작 셀의 행 / 열 계산
def get_row_col(cell_number):
    index = cell_number - 1
    row = (        index // GRID_SIZE    )
    col = (        index % GRID_SIZE    )
    return row, col
def row_col_to_cell(row, col):
    if row < 0 or row >= GRID_SIZE:
        raise ValueError(    "작업 위치가 5×5 작업판의 행을 초과합니다."        )
    if col < 0 or col >= GRID_SIZE:
        raise ValueError(  "작업 위치가 5×5 작업판의 열을 초과합니다."       )
    return ( row * GRID_SIZE  + col    + 1    )
# 일반 모드
def normal_grid_mode(x, y, z):
    start_row, start_col = (  get_row_col(z)    )
    if start_col + x > GRID_SIZE:
        raise ValueError(    "한 줄 작업 개수가 작업판 범위를 초과합니다."        )
    rows_needed = ( y + x - 1   ) // x
    if start_row + rows_needed > GRID_SIZE:
        raise ValueError(   "작업 범위가 25번 셀을 초과합니다."        )
    remaining = y
    for row_offset in range(  rows_needed    ):
        cells_this_row = min( x, remaining        )
        print()
        print(   f"===== {row_offset + 1}행 작업 ====="        )
        # 한 행에서x=2이면 이동은 한 번 x=3이면 두번
        for col_offset in range( cells_this_row - 1 ):
            pick_row = ( start_row + row_offset      )
            pick_col = ( start_col + col_offset            )
            place_col = (     pick_col + 1            )
            pick_cell = ( row_col_to_cell( pick_row, pick_col     )            )
            place_cell = (row_col_to_cell( pick_row,  place_col   )            )
            print()
            print(     f"{pick_cell}번 → {place_cell}번"            )
            pick_grid(                pick_cell            )
            place_grid(                place_cell            )
        remaining -= (     cells_this_row        )
def normal_slide_mode(x, y, z):
    start_row, start_col = (    get_row_col(z)    )
    # 한 줄 범위 검사
    if start_col + x > GRID_SIZE:
        raise ValueError(   "한 줄 작업 개수가 작업판 범위를 초과합니다."        )
    rows_needed = (  y + x - 1  ) // x
    if start_row + rows_needed > GRID_SIZE:
        raise ValueError(    "작업 범위가 25번 셀을 초과합니다."        )
    # 제품 하나씩
    for i in range(y):
        row_offset = (        i // x        )
        col_offset = (        i % x        )
        row = (   start_row  + row_offset        )
        col = (   start_col  + col_offset        )
        place_cell = ( row_col_to_cell( row,  col     )        )
        print()
        print(            f"제품 {i + 1} / {y}"        )
        print(   "Place Cell =",      place_cell        )
        # 미끄럼틀 Pick
        pick_slide()
        # 작업판 Place
        place_grid(      place_cell        )
# 사용자가 지정한 셀에 배치
# 모든 제품은 미끄럼틀에서 Pick
def selected_mode():
    place_info = []
    while True:
        value = int( input( "몇 번째 칸에 놓을 것입니까 " "(0 = 종료): "     )        )
        if value == 0:
            break
        if 1 <= value <= MAX_CELL:
            place_info.append(           value            )
        else:
            print(   "1~25 사이의 셀 번호를 입력하세요."      )
    print()
    print(  "선택한 셀 =",   place_info    )
    for index, cell_number in enumerate(  place_info    ):
        print()
        print( f"선택 작업 {index + 1}"    )
        print("Place Cell =", cell_number   )
        # 미끄럼틀 Pick
        pick_slide()
        # 선택한 위치 Place
        place_grid(      cell_number        )
def main():
    try:
        vacuum_off()
        select_mode = int(  input(    "일반 : 1  //  선택 : 2 : "    )     )
        if select_mode == 1:
            x = int(     input( "한 줄에 몇 개 놓을 것입니까: "       )            )
            y = int(     input( "총 몇 개 작업할 것입니까: "    )        )
            z = int(     input( "몇 번째 칸부터 시작합니까(1~25): "      )            )
            start_po = int(  input( "픽 위치 ==> " "틀 안에서 : 1 // "   "미끄럼틀에서 : 2 : "    )      )
            if x <= 0 or x > GRID_SIZE:
                raise ValueError(   "한 줄 작업 개수는 1~5 사이여야 합니다."    )
            if y <= 0:
                raise ValueError( "총 작업 개수는 1 이상이어야 합니다."     )
            if z < 1 or z > MAX_CELL:
                raise ValueError(  "시작 셀은 1~25 사이여야 합니다."      )
            # 작업판 내부 Pick
            if start_po == 1:
                normal_grid_mode(    x,     y,      z        )
            # 미끄럼틀 Pick
            elif start_po == 2:
                normal_slide_mode( x,  y,  z           )
            else:
                raise ValueError(   "픽 위치는 1 또는 2를 입력하세요."       )
        # 선택 모드
        elif select_mode == 2:
            selected_mode()
        else:
            raise ValueError( "일반 모드는 1, 선택 모드는 2입니다."     )
        # 정상 작업 완료 후 Center
        print()
        print(  "===== 작업 종료 위치 이동 ====="     )
        move_linear( center,    "Center"        )
    except KeyboardInterrupt:
        print()
        print(  "키보드 입력으로 프로그램을 종료합니다."    )
    # 기타 오류
    except Exception as e:
        print()
        print(  "프로그램 오류 :",   e     )
    finally:
        try:
            vacuum_off()
        except Exception as e:
            print( "Vacuum OFF 오류 :",      e         )
        print(  "프로그램 종료"        )
if __name__ == "__main__":

    main()