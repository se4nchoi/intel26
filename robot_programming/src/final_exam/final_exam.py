# 20261116
# 22번 최예현
# 로봇프로그래밍 기말시험

"""
기말 프로젝트 - Indy7 미끄럼틀(피더) -> 5x5 팔레트 Pick & Place (흡착 DO 2)
=====================================================================

위치: neuromeka-digitaltwin 티치 펜던트에서 마지막으로 기록한 조그 포인트
(data/positions.csv, 2026-11-16 10:18 저장, 로봇 192.168.3.7):
    pick-feed, place-1, place-2, place-6

궤적은 디지털 트윈 팔레타이징 셀과 같은 방식:
    홈              MoveJ  (관절 이동)
    피더 접근       MoveJ  -> 접근 위치의 IK (pick-feed 관절값을 시드로 사용)
    피더 픽         MoveL  기울어진 툴 축을 따라 100 mm 진입,
                           마지막 6 mm는 저속
    피더 후퇴       MoveL  처음 6 mm는 저속, 이후 같은 직선으로 빠져나옴
    팔레트 접근     MoveJ  -> 슬롯 접근 위치의 IK (place-1 관절값을 시드로 사용)
    팔레트 놓기     MoveL  수직으로 100 mm 하강
    팔레트 후퇴     MoveL

동작 순서
--------
1) 홈 위치 이동
2) 미끄럼틀(피더) pick 접근 위치
3) pick 위치 이동
   3-1) 매거진 포인트에서 흡착 ON (DO 2)
4) pick 후퇴 위치
5) 팔레트 #N place 접근 위치
6) place 위치 이동
7) 흡착 OFF (DO 2)   (+ place 후퇴)
8) 2-7을 팔레트 #4, #8, #10 에 반복   ->  놓는 위치: 2, 4, 8, 10
마지막으로 홈 복귀.

팔레트 번호 (약 40 mm 간격, 3점 티칭: place-1, place-2, place-6)
--------------------------------------------------------------------------
     1   2   3   4   5        열 -> (place-2 - place-1)  약 -Y 40.8 mm
     6   7   8   9  10        행 -> (place-6 - place-1)  약 -X 41.0 mm
    11  12  13  14  15
    16  17  18  19  20
    21  22  23  24  25

사용법
-----
    uv run python final_exam.py            # 실제 로봇에서 실행
    uv run python final_exam.py --dry-run  # 모든 목표 좌표 출력 (로봇 연결 안 함)
    uv run python final_exam.py --teach    # 현재 q / p 출력 (재티칭용)
    uv run python final_exam.py --release  # 중단 후 흡착 해제 (먼저 확인을 받음)

오류 / Ctrl-C 시 로봇은 정지하지만 흡착은 끄지 않는다. 잡고 있는 제품이
자동으로 떨어지는 일은 없다.
"""

import math
import sys
import time
from typing import Dict, List

from neuromeka import IndyDCP3, JointBaseType, OpState, TaskBaseType

# ==============================================================================
# 로봇 / IO 설정
# ==============================================================================
ROBOT_IP = "192.168.3.7"
ROBOT_INDEX = 0

VACUUM_DO = 2                  # 흡착 on/off -> 로봇 디지털 출력 d2

# 최고 속도는 높이고(+60 %) 가속 비율은 낮춤: 충분히 빠르게 속도를 올리되
# 긴 구간에 걸쳐 감속하므로, 접근 / 후퇴 지점에 급정지하지 않고 부드럽게 도착한다.
TRANSIT_VEL, TRANSIT_ACC = 40, 20   # 접근 지점까지의 MoveJ 이동 (이전 25 / 25)
ACTION_VEL, ACTION_ACC = 25, 12     # MoveL 진입 / 후퇴 (이전 15 / 15)

APPROACH_DIST = 100.0          # 접근 / 후퇴 시 툴 축 방향으로 물러나는 거리 (mm)
VACUUM_DWELL = 0.5             # 팔레트에서 흡착이 풀릴 때까지 대기 시간 (s)
PICK_VACUUM_DWELL = 0.9        # 피더에서 들어올리기 전에 흡착이 완전히 붙을 때까지 대기 (s)

# 피더 픽업: 미끄럼틀 안에서 제품이 움직일 여유가 있으므로, 매거진 포인트
# 직전 / 직후 몇 mm는 저속으로 움직여 매번 같은 자세로 집고 들어올린다.
FEED_CREEP_DIST = 6.0          # 툴 축 방향 거리 mm (이전 15)
FEED_CREEP_VEL, FEED_CREEP_ACC = 12, 20   # 이전 6 / 6 (총 약 6 s) -> 총 약 1 s
MOVE_TIMEOUT = 60.0            # 동작 하나당 제한 시간 (s)

# ==============================================================================
# 티칭한 조그 포인트  (neuromeka-digitaltwin data/positions.csv, 2026-11-16)
# 태스크 [X, Y, Z (mm), U, V, W (deg)] / 관절 [q1..q6 (deg)]
# ==============================================================================
# 미끄럼틀(피더) 매거진 포인트 - 툴이 미끄럼틀에 맞춰 약 20도 기울어짐
PICK_FEED = [202.96, 487.47, 149.46, -0.36, -159.86, 0.17]
PICK_FEED_Q = [70.99, -32.2, -67.85, 19.13, -86.66, 68.62]

# 팔레트 3점 티칭
PLACE_1 = [196.08, 335.98, 195.56, 0.09, -179.96, 0.01]
PLACE_1_Q = [88.33, -1.55, -107.83, 0.04, -70.71, 88.3]
PLACE_2 = [196.18, 295.19, 197.93, 0.14, -179.95, 0.01]   # 다음 열
PLACE_6 = [155.11, 335.57, 195.87, 0.28, -179.95, 0.05]   # 다음 행

# 그리드 형상: 티칭한 점들로부터 측정한 간격
PALLET_COLS = 5
PALLET_ROWS = 5
COL_STEP = [PLACE_2[i] - PLACE_1[i] for i in range(3)]   # (dx, dy, dz) 1 -> 2
ROW_STEP = [PLACE_6[i] - PLACE_1[i] for i in range(3)]   # (dx, dy, dz) 1 -> 6

# 슬롯별 미세 보정 (dx, dy, dz) mm, 실제 셀에서 확인한 값
#   #4  +0 일 때 약 4 mm 베이스 쪽으로 가까움, +4 일 때 2-4 mm 멀어짐 -> +1
#   #10 +0 일 때 약 8 mm 베이스 쪽으로 가까움, +8 일 때 2-4 mm 멀어짐 -> +4
SLOT_CORRECTION = {
    4: (0.0, 1.0, 0.0),
    10: (0.0, 4.0, 0.0),
}

# 놓는 순서: 먼저 #2, 이후 #4, #8, #10 반복
PLACE_SEQUENCE = [2, 4, 8, 10]


# ==============================================================================
# 팔레트 맵 (1-25 -> (접근, 놓기))
# ==============================================================================
def build_pallet_map() -> Dict[int, List[float]]:
    """슬롯 n 놓기 자세 = place-1 + 열 * COL_STEP + 행 * ROW_STEP (자세 각도는 place-1 사용)."""
    pallet = {}
    for n in range(1, PALLET_COLS * PALLET_ROWS + 1):
        row, col = divmod(n - 1, PALLET_COLS)
        fix = SLOT_CORRECTION.get(n, (0.0, 0.0, 0.0))
        xyz = [PLACE_1[i] + col * COL_STEP[i] + row * ROW_STEP[i] + fix[i] for i in range(3)]
        pallet[n] = [*xyz, *PLACE_1[3:]]
    return pallet


PALLET = build_pallet_map()


def approach_of(pose: List[float], dist: float = APPROACH_DIST) -> List[float]:
    """툴 -Z 축 방향으로 `dist` mm 물러난 위치 (툴이 기울어져 있어도 똑바로 진입 / 후퇴)."""
    u, v, w = (math.radians(a) for a in pose[3:6])
    cu, su = math.cos(u), math.sin(u)
    cv, sv = math.cos(v), math.sin(v)
    cw, sw = math.cos(w), math.sin(w)
    # 베이스 좌표계에서의 툴 Z 축: Rz(w) * Ry(v) * Rx(u) 의 세 번째 열
    zx = cw * sv * cu + sw * su
    zy = sw * sv * cu - cw * su
    zz = cv * cu
    return [pose[0] - dist * zx, pose[1] - dist * zy, pose[2] - dist * zz, *pose[3:6]]


def fmt(pose: List[float]) -> str:
    return "[" + ", ".join(f"{v:8.2f}" for v in pose) + "]"


# ==============================================================================
# 동작 / IO 헬퍼
# ==============================================================================
class MotionError(RuntimeError):
    pass


def wait_move_done(indy: IndyDCP3, timeout: float = MOVE_TIMEOUT) -> None:
    """동작이 끝나고 컨트롤러가 IDLE 이 될 때까지 대기. 오류 / 시간 초과 시 예외 발생."""
    start = time.time()

    while time.time() - start < 0.5:
        if indy.get_motion_data().get("is_in_motion", False):
            break
        time.sleep(0.02)

    while time.time() - start < timeout:
        m_data = indy.get_motion_data()
        op_state = indy.get_robot_data().get("op_state")

        if op_state in (OpState.VIOLATE, OpState.VIOLATE_HARD,
                        OpState.COLLISION, OpState.STOP_AND_OFF):
            raise MotionError(f"Robot fault during motion (op_state={op_state})")

        if not m_data.get("is_in_motion", False) and op_state == OpState.IDLE:
            print("\r    progress [100%]")
            return

        print(f"\r    progress [{m_data.get('traj_progress', 0):>3}%]", end="", flush=True)
        time.sleep(0.05)

    raise MotionError("Motion timeout")


def check(result, name: str) -> None:
    if isinstance(result, dict) and result.get("code") not in (0, "0", None):
        raise MotionError(f"{name} rejected: {result}")


def move_home(indy: IndyDCP3) -> None:
    print("\n[HOME] move_home()")
    check(indy.move_home(), "move_home")
    wait_move_done(indy)


def move_j(indy: IndyDCP3, q: List[float], label: str,
           vel: int = TRANSIT_VEL, acc: int = TRANSIT_ACC) -> None:
    print(f"  {label:<26} J{fmt(q)}")
    check(indy.movej(jtarget=list(q), base_type=JointBaseType.ABSOLUTE,
                     vel_ratio=vel, acc_ratio=acc), label)
    wait_move_done(indy)


def move_j_to_pose(indy: IndyDCP3, pose: List[float], seed_q: List[float], label: str) -> None:
    """태스크 자세로 MoveJ: 티칭한 관절값을 IK 시드로 써서 같은 팔 자세(configuration)를 유지."""
    res = indy.inverse_kin(tpos=list(pose), init_jpos=list(seed_q))
    q = res.get("jpos") if isinstance(res, dict) else None
    if not q or len(q) != 6:
        raise MotionError(f"IK failed for {label} {fmt(pose)}: {res}")
    if max(abs(a - b) for a, b in zip(q, seed_q)) > 60.0:
        raise MotionError(f"IK for {label} jumped to another arm config: {fmt(q)}")
    move_j(indy, q, label)


def move_l(indy: IndyDCP3, pose: List[float], label: str,
           vel: int = ACTION_VEL, acc: int = ACTION_ACC) -> None:
    print(f"  {label:<26} L{fmt(pose)}")
    check(indy.movel(ttarget=list(pose), base_type=TaskBaseType.ABSOLUTE,
                     vel_ratio=vel, acc_ratio=acc), label)
    wait_move_done(indy)


def vacuum(indy: IndyDCP3, on: bool, dwell: float = VACUUM_DWELL) -> None:
    print(f"  VACUUM {'ON ' if on else 'OFF'} (DO{VACUUM_DO})")
    check(indy.set_do([{"address": VACUUM_DO, "state": 1 if on else 0}]), "set_do")
    time.sleep(dwell)


def vacuum_is_on(indy: IndyDCP3) -> bool:
    """컨트롤러에서 DO2 상태를 다시 읽어옴 (DigitalState.ON == 1)."""
    signals = indy.get_do().get("signals", [])
    return any(s.get("address") == VACUUM_DO and s.get("state") in (1, "ON_STATE")
               for s in signals)


def confirm(prompt: str) -> bool:
    return input(f"{prompt} [y/N] ").strip().lower() == "y"


# ==============================================================================
# PICK & PLACE 사이클
# ==============================================================================
def pick_and_place(indy: IndyDCP3, slot: int) -> None:
    place = PALLET[slot]
    place_app = approach_of(place)
    feed_app = approach_of(PICK_FEED)
    feed_near = approach_of(PICK_FEED, FEED_CREEP_DIST)   # 같은 직선 위, 저속 구간 시작점

    # 2) 피더 pick 접근 (관절 이동, pick-feed 팔 자세)
    move_j_to_pose(indy, feed_app, PICK_FEED_Q, "2) pick approach (J)")
    # 3) pick 위치: 툴 축을 따라 빠르게 내려간 뒤 마지막 몇 mm는 저속
    move_l(indy, feed_near, "3) pick near")
    move_l(indy, PICK_FEED, "3) pick location (creep)", FEED_CREEP_VEL, FEED_CREEP_ACC)
    # 3-1) 매거진 포인트에서 흡착 ON, 완전히 붙을 때까지 대기
    vacuum(indy, True, PICK_VACUUM_DWELL)
    # 4) pick 후퇴: 처음 몇 mm는 저속, 이후 일반 속도
    move_l(indy, feed_near, "4) pick lift (creep)", FEED_CREEP_VEL, FEED_CREEP_ACC)
    move_l(indy, feed_app, "4) pick retract")
    # 5) 팔레트 place 접근 (관절 이동, place-1 팔 자세)
    move_j_to_pose(indy, place_app, PLACE_1_Q, f"5) place approach #{slot} (J)")
    # 6) place 위치
    move_l(indy, place, f"6) place location #{slot}")
    # 7) 흡착 OFF
    vacuum(indy, False)
    # 다음 이동 전에 수직으로 후퇴
    move_l(indy, place_app, "   place retract")


def run(indy: IndyDCP3) -> None:
    r = indy.get_robot_data()
    print(f"Connected. op_state={r.get('op_state')}  p={fmt(r.get('p', []))}")
    if r.get("op_state") != OpState.IDLE:
        raise MotionError(f"Robot not IDLE (op_state={r.get('op_state')}). "
                          "Recover / servo-on from the teach pendant first.")

    # 자동으로 흡착을 해제하지 않음: 이전에 중단된 실행에서 제품이 아직
    # 흡착되어 있을 수 있고, 팔이 있는 현재 위치에서 떨어뜨리면 위험하다.
    if vacuum_is_on(indy):
        print(f"\n[WARN] Vacuum DO{VACUUM_DO} is ON - a part may still be held "
              f"at p={fmt(r.get('p', []))}.")
        if not confirm("Is it safe to release it HERE (part will drop)?"):
            raise MotionError("Aborted with vacuum still ON. Jog the part to a safe "
                              "spot, then run with --release.")
        vacuum(indy, False)

    move_home(indy)                # 1) 홈

    for i, slot in enumerate(PLACE_SEQUENCE, start=1):
        print(f"\n===== Cycle {i}/{len(PLACE_SEQUENCE)} : feeder -> pallet #{slot} =====")
        pick_and_place(indy, slot)

    move_home(indy)
    print("\n[DONE] Placed on pallet slots:", PLACE_SEQUENCE)


def safe_stop(indy: IndyDCP3) -> None:
    """
    동작만 정지한다. 흡착은 일부러 그대로 둔다: 제품을 잡고 있는 상태에서
    DO2를 끄면 팔이 멈춘 위치에서 제품이 떨어진다. 해제는 작업자가
    판단해서 한다 (--release).
    """
    print("\n[SAFE STOP] stopping motion (vacuum left as is)")
    try:
        indy.stop_motion()
    except Exception as e:
        print("  -> stop_motion failed:", e)

    try:
        if vacuum_is_on(indy):
            print(f"[WARN] Vacuum DO{VACUUM_DO} is still ON - the part is being held.")
            print("       Jog it to a safe spot on the pendant, then release with:")
            print("         uv run python final_exam.py --release")
    except Exception as e:
        print("  -> could not read vacuum state:", e)


def release() -> None:
    """중단된 실행 이후, 작업자 확인을 받고 흡착을 해제."""
    indy = IndyDCP3(robot_ip=ROBOT_IP, index=ROBOT_INDEX)
    if not vacuum_is_on(indy):
        print(f"Vacuum DO{VACUUM_DO} is already OFF.")
        return
    p = indy.get_robot_data().get("p", [])
    print(f"Vacuum DO{VACUUM_DO} is ON at p={fmt(p)}.")
    if confirm("Release now (part will drop)?"):
        vacuum(indy, False)
        print("Released.")
    else:
        print("Left ON.")


# ==============================================================================
# 진입점
# ==============================================================================
def dry_run() -> None:
    print("PICK-FEED        ", fmt(PICK_FEED))
    print("PICK-FEED approach", fmt(approach_of(PICK_FEED)))
    print(f"COL step (1->2)  {fmt(COL_STEP)}  |{math.dist(PLACE_1[:3], PLACE_2[:3]):.2f} mm|")
    print(f"ROW step (1->6)  {fmt(ROW_STEP)}  |{math.dist(PLACE_1[:3], PLACE_6[:3]):.2f} mm|")
    print("\nPallet map (place / approach xyz):")
    for n, pose in PALLET.items():
        mark = "  <-- place" if n in PLACE_SEQUENCE else ""
        print(f"  #{n:<2} {fmt(pose)}  app {fmt(approach_of(pose)[:3])}{mark}")


def teach() -> None:
    indy = IndyDCP3(robot_ip=ROBOT_IP, index=ROBOT_INDEX)
    r = indy.get_robot_data()
    print("q (deg):", [round(v, 2) for v in r.get("q", [])])
    print("p      :", [round(v, 3) for v in r.get("p", [])])


def main() -> int:
    if "--dry-run" in sys.argv:
        dry_run()
        return 0
    if "--teach" in sys.argv:
        teach()
        return 0
    if "--release" in sys.argv:
        release()
        return 0

    dry_run()
    input(f"\nRobot {ROBOT_IP}: keep clear of the cell, hand on E-stop. ENTER to start...")

    indy = IndyDCP3(robot_ip=ROBOT_IP, index=ROBOT_INDEX)
    try:
        run(indy)
        return 0
    except KeyboardInterrupt:
        print("\n[ABORT] user interrupt")
        safe_stop(indy)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        safe_stop(indy)
    return 1


if __name__ == "__main__":
    sys.exit(main())
