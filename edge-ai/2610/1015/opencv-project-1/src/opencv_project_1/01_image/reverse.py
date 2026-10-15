from pathlib import Path
import cv2


RESOURCE_PATH = Path(__file__).resolve().parent.parent / "resources" / "jang.jpg"
image = cv2.imread(RESOURCE_PATH, cv2.IMREAD_COLOR)

dst = cv2.bitwise_not(image)

cv2.imshow("src", image)
cv2.imshow("dst", dst)

cv2.waitKey(0)
cv2.destroyAllWindows()