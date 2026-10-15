from pathlib import Path
import cv2

RESOURCE_PATH = Path(__file__).resolve().parent.parent / "resources"
detector = cv2.FaceDetectorYN.create(
    str(RESOURCE_PATH / "face_detection_yunet_2026may.onnx"),
    "", (320, 320), 0.8,
)

# (Windows) Read from the first camera device
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

# (Mac) Read from the first camera device
# cap = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)

w = 640  # 1280, 1920
h = 480  # 720, 1080
cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)

# 성공적으로 video device 가 열렸으면 while 문 반복
while cap.isOpened():
    # 한 프레임을 읽어옴
    ret, frame = cap.read()
    if ret is False:
        print("Can't receive frame (stream end?). Exiting ...")
        break

    # 작은 이미지에서 얼굴 검출 후 원본 프레임 좌표로 변환
    small = cv2.resize(frame, (320, 320))
    _, faces = detector.detect(small)
    if faces is not None:
        scale_x = frame.shape[1] / 320
        scale_y = frame.shape[0] / 320
        for face in faces:
            x, y, face_w, face_h = face[:4]
            topLeft = (round(x * scale_x), round(y * scale_y))
            bottomRight = (round((x + face_w) * scale_x), round((y + face_h) * scale_y))
            cv2.rectangle(frame, topLeft, bottomRight, (0, 0, 255), 3)
            cv2.putText(
                frame, "Face", (topLeft[0], max(20, topLeft[1] - 10)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2,
            )

    # Display
    cv2.imshow("Camera", frame)

    # 1 ms 동안 대기하며 키 입력을 받고 'q' 입력 시 종료
    key = cv2.waitKey(1)
    if key & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
