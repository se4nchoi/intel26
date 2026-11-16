
import queue
import threading
import time
import paho.mqtt.client as mqtt
from neuromeka import IndyDCP3
from pymcprotocol import Type3E
BROKER_IP = "192.168.3.92"
BROKER_PORT = 1884
COMMAND_TOPIC = "indy7/command"
STATUS_TOPIC = "indy7/status"
ROBOT_IP = "192.168.3.7"
VACUUM_DO = 2
MOVE_VEL = 10
MOVE_ACC = 10
POS1 = [ 400.0, -160.0, 480.0, 179.0, 0.0, 179.0]
POS2 = [ 400.0, -100.0, 430.0, 179.0, 0.0, 179.0]
PLC_IP = "192.168.3.150"
PLC_PORT = 1026
COMMAND_ADDR = "D100"
RESULT_ADDR = "D200"
POLL_INTERVAL = 0.05
PLC_COMMANDS = {1: "HOME",2: "POS1", 3: "POS2", 4: "VACUUM_ON", 5: "VACUUM_OFF" }
VALID_COMMANDS = set(PLC_COMMANDS.values())
def publish_status(client, status):
    print("로봇 상태 :", status)
    info = client.publish(STATUS_TOPIC, status, retain=False  )
    if info.rc != mqtt.MQTT_ERR_SUCCESS:
        print("MQTT 상태 발행 요청 실패 :", info.rc)
def check_result(result, name):
    """로봇 명령 반환값 확인."""
    print(f"{name} Result =", result)
    if isinstance(result, dict) and "code" in result:
        if str(result["code"]) != "0":  
            raise RuntimeError( f"{name} 명령 실패: {result}"  )
    elif result is False:
        raise RuntimeError(  f"{name} 명령 실패: {result}"    )
def wait_move_done(indy):
    print("이동 완료 대기 중...")
    indy.wait_for_motion_state("is_target_reached")
    print("이동 완료")
def set_vacuum(indy, enabled):
    # DO 신호 목록 형식: [(출력번호, 출력상태)]
    result = indy.set_do([ (VACUUM_DO, enabled) ])
    name = "VACUUM_ON" if enabled else "VACUUM_OFF"
    check_result(result, name)
def execute_command(indy, client, command):
    if command == "HOME":
        publish_status(client, "HOME_MOVING")
        result = indy.move_home()
        check_result(result, "HOME")
        wait_move_done(indy)
        publish_status(client, "HOME_DONE")
    elif command == "POS1":
        publish_status(client, "POS1_MOVING")
        result = indy.movel(ttarget=POS1, vel_ratio=MOVE_VEL, acc_ratio=MOVE_ACC  )
        check_result(result, "POS1")
        wait_move_done(indy)
        publish_status(client, "POS1_DONE")
    elif command == "POS2":
        publish_status(client, "POS2_MOVING")
        result = indy.movel( ttarget=POS2,  vel_ratio=MOVE_VEL,  acc_ratio=MOVE_ACC   )
        check_result(result, "POS2")
        wait_move_done(indy)
        publish_status(client, "POS2_DONE")
    elif command == "VACUUM_ON":
        set_vacuum(indy, True)
        publish_status(client, "VACUUM_ON")
    elif command == "VACUUM_OFF":
        set_vacuum(indy, False)
        publish_status(client, "VACUUM_OFF")
    else:
        raise ValueError(   f"알 수 없는 명령: {command}"      )
# 3. MQTT 콜백
def on_connect(client, userdata, flags, reason_code,  properties=None):
    userdata["subscribed"].clear()
    if reason_code != 0:
        userdata["connected"].clear()
        print("MQTT 연결 실패 :", reason_code)
        return
    userdata["connected"].set()
    print("MQTT Broker 연결 완료")
    result, mid = client.subscribe(COMMAND_TOPIC,qos=0 )
    if result != mqtt.MQTT_ERR_SUCCESS:
        print("명령 Topic 구독 요청 실패 :", result)
def on_subscribe(client, userdata, mid, reason_codes, properties=None):
    if not reason_codes or any(code.is_failure for code in reason_codes ):
        userdata["subscribed"].clear()
        print("명령 Topic 구독 실패")
        return
    userdata["subscribed"].set()
    print("구독 Topic =", COMMAND_TOPIC)
    # 실제 작업 여부를 확인한 후 상태 발행
    with userdata["state_lock"]:#with는 잠금 을 잡고 블록이 끝나면 잠금을 푼다
        busy = userdata["busy"]
    status = "ROBOT_BUSY" if busy else "ROBOT_READY"
    publish_status(client, status)
def on_disconnect( client, userdata, disconnect_flags, reason_code, properties=None):
    userdata["connected"].clear()
    userdata["subscribed"].clear()
    print("MQTT 연결 해제 :", reason_code)
def on_message(client, userdata, msg):
    # 구독 직후 전달된 과거 보관 명령 무시
    if msg.retain:
        print("보관된 MQTT 명령 무시")
        return
    try:
        command = msg.payload.decode("utf-8").strip().upper()
    except UnicodeDecodeError:
        publish_status(client, "UNKNOWN_COMMAND")
        return
    print("MQTT 명령 수신 :", command)
    if command not in VALID_COMMANDS:
        publish_status(client, "UNKNOWN_COMMAND")
        return
    # PLC와 스마트폰이 동시에 로봇을 실행하지 않도록 예약
    with userdata["state_lock"]:
        accepted = not userdata["busy"]
        if accepted:
            userdata["busy"] = True
            # (명령 출처, 명령 문자열, PLC 명령 번호)
            userdata["jobs"].put_nowait( ("MQTT", command, None)   )
    if not accepted:
        publish_status(client, "ROBOT_BUSY")
def main():
    state = {
        "connected": threading.Event(),
        "subscribed": threading.Event(),
        "state_lock": threading.Lock(),
        "busy": False,
        "jobs": queue.Queue()  }
    plc = Type3E()
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="indy7_plc_panel_controller",
        userdata=state    )
    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    plc_open = False
    loop_started = False
    active_plc = None
    try:
        plc.connect(PLC_IP, PLC_PORT)
        plc_open = True
        print("PLC 연결 완료 :", PLC_IP)
        initial_command = plc.batchread_wordunits( COMMAND_ADDR,  1  )[0]
        if initial_command != 0:
            raise RuntimeError( "PLC D100을 0으로 초기화한 후 실행하세요."   )
        plc.batchwrite_wordunits( RESULT_ADDR,  [0]    )

        indy = IndyDCP3(ROBOT_IP)
        robot_state = indy.get_control_state()
        print("Indy7 통신 확인 완료 :", ROBOT_IP)
        print("로봇 상태 :", robot_state)
        # MQTT 연결
        print("MQTT Broker 연결 중 :", BROKER_IP)
        client.connect( BROKER_IP, BROKER_PORT, 60    )
        client.loop_start()
        loop_started = True
        if not state["subscribed"].wait(timeout=10):
            raise RuntimeError( "MQTT 연결 또는 구독 시간 초과"   )
        print("스마트폰 및 PLC 명령 대기")
        print("PLC 명령 주소 :"  , COMMAND_ADDR)

        while True:
            job = None
            # ① 먼저 수신되어 예약된 MQTT 명령 확인
            try:
                job = state["jobs"].get_nowait()
            except queue.Empty:
                pass
            # ② MQTT 예약 명령이 없으면 PLC 확인
            if job is None:
                value = plc.batchread_wordunits( COMMAND_ADDR,  1 )[0]
                if value != 0:
                    if value not in PLC_COMMANDS:
                        raise ValueError( f"잘못된 PLC 명령: {value}"     )
                    # PLC 읽기 중 MQTT 명령이 들어왔을 수 있음.
                    # 같은 lock으로 실행 권한을 확보한다.
                    with state["state_lock"]:
                        if not state["busy"]:
                            state["busy"] = True
                            job = ( "PLC", PLC_COMMANDS[value],  value     )
            if job is None:
                time.sleep(POLL_INTERVAL)
                continue
            source, command, plc_number = job
            print()
            print("명령 출처 :", source)
            print("실행 명령 :", command)
            active_plc = plc_number
            try:
                # PLC 명령인 경우 처리 중 결과 기록
                if source == "PLC":
                    plc.batchwrite_wordunits( RESULT_ADDR,  [10 + plc_number]  )
                # 스마트폰·PLC 모두 같은 함수로 실행
                execute_command(  indy,  client,    command    )
                # PLC 명령 완료 처리
                if source == "PLC":
                    plc.batchwrite_wordunits( RESULT_ADDR,  [100 + plc_number]  )
                    plc.batchwrite_wordunits( COMMAND_ADDR, [0]  )
                    print(  f"PLC 완료: D200={100 + plc_number}, "  "D100=0" )
                active_plc = None
            finally:
                if source == "MQTT":
                    state["jobs"].task_done()
                with state["state_lock"]:
                    state["busy"] = False
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print("프로그램 종료 요청")
        if active_plc is not None and plc_open:
            try:
                plc.batchwrite_wordunits( RESULT_ADDR, [-1]   )
            except Exception as e:
                print("PLC 오류 표시 실패 :", e)
    except Exception as e:
        print("프로그램 오류 :", e)
        if loop_started:
            publish_status(client, "ROBOT_ERROR")
        if plc_open:
            try:
                plc.batchwrite_wordunits(RESULT_ADDR,  [-1]    )
            except Exception as write_error:
                print("PLC 오류 표시 실패 :", write_error)
    finally:
        # 흡착 중인 물체의 낙하 방지를 위해
        # 종료할 때 진공 출력을 자동 OFF하지 않음.
        print("진공 출력은 자동 변경하지 않습니다.")
        try:
            client.disconnect()
        except Exception as e:
            print("MQTT 연결 종료 오류 :", e)
        if loop_started:
            try:
                client.loop_stop()
            except Exception as e:
                print("MQTT 스레드 종료 오류 :", e)
        if plc_open:
            try:
                plc.close()
            except Exception as e:
                print("PLC 연결 종료 오류 :", e)
        print("통합 프로그램 종료")
if __name__ == "__main__":
    main()
