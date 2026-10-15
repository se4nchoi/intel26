from pathlib import Path
import cv2

img_file_name = "artist_caught.png"

RESOURCE_PATH = Path(__file__).resolve().parent.parent / "resources"
image = cv2.imread(RESOURCE_PATH / img_file_name, cv2.IMREAD_COLOR)

# Crop 300x400 from original image from (100, 50)=(x,y)
cropped = image[50:450, 100:400]

# Resize cropped image from 300x400 to 400x200
resized = cv2.resize(cropped, (400, 200))

# Display all
cv2.imshow("Original", image)
cv2.imshow("Cropped image", cropped)
cv2.imshow("Resized image", resized)

cv2.waitKey(0)
cv2.destroyAllWindows()
