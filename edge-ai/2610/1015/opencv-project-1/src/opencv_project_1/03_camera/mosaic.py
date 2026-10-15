from pathlib import Path
import cv2

RESOURCE_PATH = Path(__file__).resolve().parent.parent / "resources"
BLOCK_SIZE = 20  # 값이 클수록 모자이크가 거칠어짐
detector = cv2.FaceDetectorYN.create(
    str(RESOURCE_PATH / "face_detection_yunet_2026may.onnx"),
    "", (320, 320), 0.8,
)

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

try:
    if not cap.isOpened():
        raise RuntimeError("Could not open camera")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # 얼굴을 검출하고 원본 프레임 좌표로 변환
        height, width = frame.shape[:2]
        _, faces = detector.detect(cv2.resize(frame, (320, 320)))
        if faces is not None:
            for face in faces:
                x, y, w, h = face[:4]
                # 얼굴 주변까지 덮도록 10% 여유를 두고 화면 경계에 맞춤
                x1 = max(0, round((x - w * 0.1) * width / 320))
                y1 = max(0, round((y - h * 0.1) * height / 320))
                x2 = min(width, round((x + w * 1.1) * width / 320))
                y2 = min(height, round((y + h * 1.1) * height / 320))
                if x2 <= x1 or y2 <= y1:
                    continue

                # 얼굴 영역을 작게 줄였다가 최근접 보간으로 확대
                roi = frame[y1:y2, x1:x2]
                tiny = cv2.resize(
                    roi,
                    (max(1, (x2 - x1) // BLOCK_SIZE),
                     max(1, (y2 - y1) // BLOCK_SIZE)),
                    interpolation=cv2.INTER_AREA,
                )
                frame[y1:y2, x1:x2] = cv2.resize(
                    tiny, (x2 - x1, y2 - y1),
                    interpolation=cv2.INTER_NEAREST,
                )

        cv2.imshow("Face Mosaic", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
finally:
    cap.release()
    cv2.destroyAllWindows()
