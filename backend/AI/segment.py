import io
import cv2
from PIL import Image
import numpy as np

def segment_image(image_data: bytes) -> Image:
    # Convert the byte data to a NumPy array
    nparr = np.frombuffer(image_data, np.uint8)

    # Decode the image
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Image not found or unable to read")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, binary = cv2.threshold(blurred, 127, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    segmented_image = image.copy()
    cv2.drawContours(segmented_image, contours, -1, (0, 255, 0), 2)
    segmented_pil_image = Image.fromarray(segmented_image)

    return segmented_pil_image
