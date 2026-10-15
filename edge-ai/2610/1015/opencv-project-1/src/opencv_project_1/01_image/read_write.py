from pathlib import Path
import cv2

img_file_name = "goodkoko.jpg"

# 이미지 파일을 Read
RESOURCE_PATH = Path(__file__).resolve().parent.parent / "resources"
img = cv2.imread(RESOURCE_PATH / img_file_name, cv2.IMREAD_COLOR)

# Image 란 이름의 Display 창 생성
cv2.namedWindow("image", cv2.WINDOW_AUTOSIZE)

# Numpy ndarray H/W/C order
print(img.shape)

# Read 한 이미지 파일을 Display
cv2.imshow("image", img)

# 별도 키 입력이 있을때 까지 대기
key = cv2.waitKey(0) & 0xFF

# output.png 로 읽은 이미지 파일을 저장
# cv2.imwrite("output.png", img)
if key == ord("s") or key == ord("S"):
    cv2.imwrite(f'{RESOURCE_PATH}/output_img/output_{img_file_name}', img)


# Destroy all windows
cv2.destroyAllWindows()