import torch
from torchvision import models, transforms
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import io

# Predefined color map for visualization (COCO dataset classes)
PALETTE = [
    (255, 182, 193), (255, 218, 185), (173, 216, 230), (255, 239, 187),
    (255, 240, 245), (221, 160, 221), (216, 191, 216), (255, 228, 196),
    (250, 250, 210), (255, 222, 173), (176, 224, 230), (244, 164, 96),
    (255, 218, 185), (218, 112, 214), (255, 240, 245), (255, 105, 180),
    (144, 238, 144), (240, 128, 128), (255, 99, 71), (255, 255, 224),
]

# COCO class labels
COCO_LABELS = [
    "background", "aeroplane", "bicycle", "bird", "boat", "bottle", "bus", "car", "cat", 
    "chair", "cow", "diningtable", "dog", "horse", "motorbike", "person", "pottedplant", 
    "sheep", "sofa", "train", "tvmonitor"
]

def segment_image(image_data: bytes) -> Image:
    # Load the pre-trained DeepLabV3 model for segmentation
    model = models.segmentation.deeplabv3_resnet101(pretrained=True)
    model.eval()  # Set the model to evaluation mode

    # Convert the bytes image data to a PIL Image
    image = Image.open(io.BytesIO(image_data))

    # Define the necessary image transformation
    transform = transforms.Compose([
        transforms.ToTensor(),  # Convert image to tensor
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),  # Normalization for pre-trained model
    ])

    # Apply the transformations
    input_tensor = transform(image)
    input_batch = input_tensor.unsqueeze(0)  # Add batch dimension

    # Check if CUDA is available and move the model and inputs to the GPU if possible
    if torch.cuda.is_available():
        model = model.cuda()
        input_batch = input_batch.cuda()

    # Perform the segmentation
    with torch.no_grad():
        output = model(input_batch)['out'][0]  # Get the output
        output_predictions = output.argmax(0)  # Get the predicted class for each pixel

    # Convert the output to a numpy array and apply the color palette
    segmented_image = Image.fromarray(output_predictions.cpu().numpy().astype(np.uint8))
    segmented_image = segmented_image.convert("P")  # Convert to "P" mode for palette-based image
    segmented_image.putpalette([x for color in PALETTE for x in color])  # Apply palette

    # Convert the segmented image back to an RGB image for better visualization
    segmented_image = segmented_image.convert("RGB")

    # Overlay labels on the segmented image
    draw = ImageDraw.Draw(segmented_image)
    font = ImageFont.load_default()  # Use a default font (you can customize this)
    
    # For each unique class in the segmented image, add the corresponding label
    for label_idx in np.unique(output_predictions.cpu().numpy()):
        if label_idx == 0:  # Skip background
            continue
        
        # Get the color for the class
        color = PALETTE[label_idx]
        
        # Find the coordinates of the top-left corner of the bounding box for the class
        y_indices, x_indices = np.where(output_predictions.cpu().numpy() == label_idx)
        
        if len(x_indices) == 0 or len(y_indices) == 0:
            continue
        
        # Draw the label on the segmented image
        label = COCO_LABELS[label_idx]
        text_position = (x_indices[0], y_indices[0])  # You can adjust this position
        draw.text(text_position, label, fill=color, font=font)

    return segmented_image
