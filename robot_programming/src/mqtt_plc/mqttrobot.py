
import paho.mqtt.client as mqtt
from neuromeka import IndyDCP3
import time
BROKER_IP = "192.168.3.92"
BROKER_PORT = 1884
COMMAND_TOPIC = "indy7/command"
STATUS_TOPIC  = "indy7/status"
ROBOT_IP = "192.168.3.7"
indy = IndyDCP3(ROBOT_IP)
print("Indy7 연결 완료")
POS1 = [400.0, -160.0, 480.0, 179.0, 0.0, 179.0]
POS2 = [ 400.0,-100.0, 430.0, 179.0, 0.0, 179.0]
def wait_move_done():
    print("이동 완료 대기 중...")
    indy.wait_for_motion_state("is_target_reached")
    print("이동 완료")
def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code != 0:
        print("MQTT 연결 실패 :", reason_code)
        return

    print("MQTT Broker 연결 완료")
    
    # 명령 Topic 구독
    client.subscribe(COMMAND_TOPIC)
    print("구독 Topic =", COMMAND_TOPIC  )
    client.publish(STATUS_TOPIC,   "ROBOT_READY" )
# MQTT 메시지 수신
def on_message(client, userdata, msg):
    try:
        command = msg.payload.decode("utf-8").strip().upper()
        print("MQTT 명령 수신")
        print("Topic   :", msg.topic)
        print("Command :", command)
        if command == "HOME":
            print("HOME 이동 시작")
            client.publish(  STATUS_TOPIC,  "HOME_MOVING"     )
            result = indy.move_home()
            if isinstance(result, dict) and "code" in result and str(result["code"]) != "0":
                raise RuntimeError(f"HOME 명령 실패: {result}")
            wait_move_done()
            client.publish( STATUS_TOPIC,  "HOME_DONE"   )
        elif command == "POS1":
            print("POS1 이동 시작")
            client.publish( STATUS_TOPIC,  "POS1_MOVING"    )
            result = indy.movel(  ttarget=POS1   )
            print("MoveL Result =", result      )
            if isinstance(result, dict) and "code" in result and str(result["code"]) != "0":
                raise RuntimeError(f"POS1 명령 실패: {result}")
            wait_move_done()
            client.publish( STATUS_TOPIC,   "POS1_DONE"   )
        # POS2
        elif command == "POS2":
            print("POS2 이동 시작")
            client.publish( STATUS_TOPIC,  "POS2_MOVING"    )
            result = indy.movel(  ttarget=POS2  )
            print( "MoveL Result =",    result        )
            if isinstance(result, dict) and "code" in result and str(result["code"]) != "0":
                raise RuntimeError(f"POS2 명령 실패: {result}")
            wait_move_done()
            client.publish( STATUS_TOPIC,   "POS2_DONE"      )
        elif command == "VACUUM_ON":
            print("Vacuum ON")
            result = indy.set_do([(2, True)])
            if isinstance(result, dict) and "code" in result and str(result["code"]) != "0":
                raise RuntimeError(f"VACUUM_ON 명령 실패: {result}")
            client.publish( STATUS_TOPIC,  "VACUUM_ON"    )
        # Vacuum OFF
        elif command == "VACUUM_OFF":
            print("Vacuum OFF")
            result = indy.set_do([(2, False)])
            if isinstance(result, dict) and "code" in result and str(result["code"]) != "0":
                raise RuntimeError(f"VACUUM_OFF 명령 실패: {result}")
            client.publish( STATUS_TOPIC,  "VACUUM_OFF"  )
        else:
            print("알 수 없는 명령 :",command            )
            client.publish( STATUS_TOPIC, "UNKNOWN_COMMAND"   )
    except Exception as e:
        print( "Robot Error :",     e        )
        client.publish(  STATUS_TOPIC,  "ROBOT_ERROR"      )
# MQTT Client 생성
mqtt_client = mqtt.Client( mqtt.CallbackAPIVersion.VERSION2)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
# Broker 연결
print( "MQTT Broker 연결 중 :",   BROKER_IP)
# MQTT 실행
try:
    mqtt_client.connect(BROKER_IP, BROKER_PORT, 60)
    print("Indy7 MQTT 프로그램 실행")
    mqtt_client.loop_forever()
except KeyboardInterrupt:
    print("프로그램 종료")
except Exception as e:
    print("MQTT 실행 오류 :", e)
finally:
    try:
        indy.set_do([ (2, False) ])
    except Exception:
        pass
    mqtt_client.disconnect()
    print("MQTT 연결 종료")
