import cv2
import numpy as np
import base64
import os

def mat_to_base64(img_mat, extension=".png"):
    """Encodes OpenCV image matrix to base64 data URL string"""
    _, buffer = cv2.imencode(extension, img_mat)
    b64_str = base64.b64encode(buffer).decode('utf-8')
    return f"data:image/png;base64,{b64_str}"

def process_land_record_image(image_path):
    """
    OpenCV Land Record Image Processing Pipeline:
    1. Read original image
    2. Convert to Grayscale
    3. Gaussian Denoise + CLAHE Contrast Enhancement
    4. Otsu Binarization / Thresholding
    5. Deskewing Angle Calculation & Affine Transformation
    6. Grid Line Extraction (Morphological Horizontal & Vertical Operations)
    7. ROI Contour Bounding Box Overlay
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found at path: {image_path}")
        
    src_img = cv2.imread(image_path)
    if src_img is None:
        raise ValueError(f"Failed to load image matrix from {image_path}")
        
    height, width = src_img.shape[:2]
    
    # 1. Raw / Original
    raw_b64 = mat_to_base64(src_img)
    
    # 2. Grayscale Conversion
    gray = cv2.cvtColor(src_img, cv2.COLOR_BGR2GRAY)
    gray_b64 = mat_to_base64(cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR))
    
    # 3. Denoising + CLAHE (Contrast Limited Adaptive Histogram Equalization)
    denoised = cv2.GaussianBlur(gray, (5, 5), 0)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(denoised)
    
    # 4. Otsu Adaptive Thresholding / Binarization
    _, binarized = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    binarized_b64 = mat_to_base64(cv2.cvtColor(binarized, cv2.COLOR_GRAY2BGR))
    
    # 5. Deskewing / Rotation Matrix Calculation
    # Find all white pixels / non-zero points in inverted binary
    inv_bin = cv2.bitwise_not(binarized)
    non_zero = cv2.findNonZero(inv_bin)
    
    skew_angle = 0.0
    deskewed_img = src_img.copy()
    if non_zero is not None and len(non_zero) > 10:
        rect = cv2.minAreaRect(non_zero)
        angle = rect[-1]
        if angle < -45:
            angle = -(90 + angle)
        elif angle > 45:
            angle = 90 - angle
        else:
            angle = -angle
            
        # Cap skew angle for realistic land record scanning
        if abs(angle) < 15 and abs(angle) > 0.3:
            skew_angle = round(angle, 2)
            center = (width // 2, height // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            deskewed_img = cv2.warpAffine(src_img, M, (width, height), borderValue=(255, 255, 255))
            
    deskewed_b64 = mat_to_base64(deskewed_img)
    
    # 6. Grid & Table Line Detection (Morphological Operations)
    # Detect horizontal lines
    horiz_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (width // 30, 1))
    temp_h = cv2.erode(inv_bin, horiz_kernel, iterations=1)
    horiz_lines = cv2.dilate(temp_h, horiz_kernel, iterations=1)
    
    # Detect vertical lines
    vert_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, height // 30))
    temp_v = cv2.erode(inv_bin, vert_kernel, iterations=1)
    vert_lines = cv2.dilate(temp_v, vert_kernel, iterations=1)
    
    # Combine table grid mask
    table_grid = cv2.addWeighted(horiz_lines, 0.8, vert_lines, 0.8, 0.0)
    grid_bgr = cv2.cvtColor(table_grid, cv2.COLOR_GRAY2BGR)
    # Highlight grid lines in vibrant cyan
    grid_bgr[table_grid > 0] = [255, 200, 0] # BGR cyan-blue
    grid_overlay = cv2.addWeighted(src_img, 0.7, grid_bgr, 0.5, 0.0)
    grid_b64 = mat_to_base64(grid_overlay)
    
    # 7. ROI Contours Overlay
    contours, _ = cv2.findContours(table_grid, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    roi_img = src_img.copy()
    
    detected_rois = []
    roi_count = 0
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if w > 60 and h > 20 and w < width * 0.95 and h < height * 0.8:
            roi_count += 1
            detected_rois.append({"x": x, "y": y, "w": w, "h": h, "id": f"ROI-{roi_count}"})
            cv2.rectangle(roi_img, (x, y), (x + w, y + h), (0, 255, 64), 2) # Vibrant Neon Green
            cv2.putText(roi_img, f"ROI-{roi_count}", (x + 5, y + 18), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 128), 1, cv2.LINE_AA)
            
    roi_b64 = mat_to_base64(roi_img)
    
    return {
        "width": width,
        "height": height,
        "skew_angle": skew_angle,
        "roi_count": len(detected_rois),
        "rois": detected_rois,
        "stages": {
            "raw": raw_b64,
            "grayscale": gray_b64,
            "binarized": binarized_b64,
            "deskewed": deskewed_b64,
            "grid_overlay": grid_b64,
            "roi_overlay": roi_b64
        }
    }
