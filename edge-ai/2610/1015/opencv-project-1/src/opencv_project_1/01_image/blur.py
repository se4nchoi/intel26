from pathlib import Path
import cv2

RESOURCE_PATH = Path(__file__).resolve().parent.parent / "resources"
image = cv2.imread(RESOURCE_PATH / "jang.jpg", cv2.IMREAD_COLOR)

dst1 = cv2.blur(image, (10, 10), anchor=(-1, -1), borderType=cv2.BORDER_DEFAULT)
dst2 = cv2.blur(image, (10, 10), anchor=(-1, -1), borderType=cv2.BORDER_REFLECT)

dst3 = cv2.blur(image, (30, 30), anchor=(-1, -1), borderType=cv2.BORDER_DEFAULT)
dst4= cv2.blur(image, (1, 50), anchor=(-1, -1), borderType=cv2.BORDER_DEFAULT)

height, width = image.shape[:2]
for window_name in ("src", "dst1", "dst2", "dst3", "dst4"):
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, max(1, width // 2), max(1, height // 2))

cv2.imshow("src", image)
cv2.imshow("dst1", dst1)
cv2.imshow("dst2", dst2)
cv2.imshow("dst3", dst3)
cv2.imshow("dst4", dst4)

cv2.waitKey(0)
cv2.destroyAllWindows()
