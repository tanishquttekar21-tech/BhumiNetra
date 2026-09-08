import cv2
import numpy as np
import base64
import os

def mat_to_base64(img_mat, extension=".png"):
    """Encodes OpenCV image matrix to base64 data URL string"""
    if img_mat is None or img_mat.size == 0:
        return ""
    _, buffer = cv2.imencode(extension, img_mat)
    b64_str = base64.b64encode(buffer).decode('utf-8')
    return f"data:image/png;base64,{b64_str}"

def correct_illumination(gray_img):
    """
    Equalizes uneven background illumination and scanner shadows 
    using morphological background estimation.
    """
    try:
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25))
        background = cv2.morphologyEx(gray_img, cv2.MORPH_CLOSE, kernel)
        background = np.maximum(background, 1) # Prevent divide-by-zero
        normalized = cv2.divide(gray_img, background, scale=255)
        return cv2.convertScaleAbs(normalized)
    except Exception:
        return gray_img

def remove_noise(gray_img, use_fast_nlm=False):
    """
    Applies Gaussian Blur or Fast Non-Local Means Denoising 
    to reduce scan grain while preserving document text edges.
    """
    if use_fast_nlm and hasattr(cv2, 'fastNlMeansDenoising'):
        try:
            return cv2.fastNlMeansDenoising(gray_img, h=10, templateWindowSize=7, searchWindowSize=21)
        except Exception:
            pass
    return cv2.GaussianBlur(gray_img, (5, 5), 0)

def upscale_if_low_res(img_mat, target_min_dim=1200):
    """
    Upscales low-resolution scans to boost OCR accuracy on small Devanagari text.
    """
    h, w = img_mat.shape[:2]
    min_dim = min(h, w)
    if min_dim < target_min_dim and min_dim > 0:
        scale = target_min_dim / float(min_dim)
        if scale <= 3.0: # Limit max 3x upscale for performance
            new_w = int(w * scale)
            new_h = int(h * scale)
            return cv2.resize(img_mat, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
    return img_mat

def clean_border_margins(bin_img, margin_px=10):
    """
    Cleans up scanner shadow borders around document edges.
    """
    h, w = bin_img.shape[:2]
    cleaned = bin_img.copy()
    cleaned[0:margin_px, :] = 255
    cleaned[h-margin_px:h, :] = 255
    cleaned[:, 0:margin_px] = 255
    cleaned[:, w-margin_px:w] = 255
    return cleaned

def process_land_record_image(image_path, options=None):
    """
    OpenCV Land Record Image Processing Pipeline:
    1. Read original image (never modified on disk)
    2. Convert to Grayscale & Illumination Background Correction
    3. Noise Removal (Gaussian / Fast NLM) + CLAHE Contrast Enhancement
    4. Adaptive Otsu Thresholding / Binarization & Margin Cleanup
    5. Deskewing Angle Calculation & Affine Transformation
    6. Grid Line Extraction (Morphological Horizontal & Vertical Operations)
    7. ROI Contour Bounding Box Overlay & Low-Res Upscaling
    
    Supports optional configuration via `options` dict while remaining 
    100% backward compatible with existing caller interface.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found at path: {image_path}")
        
    src_img = cv2.imread(image_path)
    if src_img is None:
        raise ValueError(f"Failed to load image matrix from {image_path}")
        
    opts = options or {}
    clahe_clip = opts.get("clahe_clip", 2.5)
    enable_upscale = opts.get("upscale", True)
    
    # Upscale low-res scans if requested
    if enable_upscale:
        src_img = upscale_if_low_res(src_img, target_min_dim=1200)
        
    height, width = src_img.shape[:2]
    
    # 1. Raw / Original
    raw_b64 = mat_to_base64(src_img)
    
    # 2. Grayscale & Illumination Correction
    gray = cv2.cvtColor(src_img, cv2.COLOR_BGR2GRAY)
    gray_illum = correct_illumination(gray)
    gray_b64 = mat_to_base64(cv2.cvtColor(gray_illum, cv2.COLOR_GRAY2BGR))
    
    # 3. Denoising + CLAHE (Contrast Limited Adaptive Histogram Equalization)
    denoised = remove_noise(gray_illum, use_fast_nlm=opts.get("fast_nlm", False))
    clahe = cv2.createCLAHE(clipLimit=clahe_clip, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)
    
    # 4. Otsu Adaptive Thresholding & Margin Cleanup
    _, binarized = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    binarized_clean = clean_border_margins(binarized, margin_px=opts.get("margin_px", 8))
    binarized_b64 = mat_to_base64(cv2.cvtColor(binarized_clean, cv2.COLOR_GRAY2BGR))
    
    # 5. Deskewing / Rotation Matrix Calculation
    inv_bin = cv2.bitwise_not(binarized_clean)
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
    horiz_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(width // 30, 1), 1))
    temp_h = cv2.erode(inv_bin, horiz_kernel, iterations=1)
    horiz_lines = cv2.dilate(temp_h, horiz_kernel, iterations=1)
    
    vert_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(height // 30, 1)))
    temp_v = cv2.erode(inv_bin, vert_kernel, iterations=1)
    vert_lines = cv2.dilate(temp_v, vert_kernel, iterations=1)
    
    table_grid = cv2.addWeighted(horiz_lines, 0.8, vert_lines, 0.8, 0.0)
    grid_bgr = cv2.cvtColor(table_grid, cv2.COLOR_GRAY2BGR)
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
            cv2.rectangle(roi_img, (x, y), (x + w, y + h), (0, 255, 64), 2)
            cv2.putText(roi_img, f"ROI-{roi_count}", (x + 5, y + 18), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 128), 1, cv2.LINE_AA)
            
    roi_b64 = mat_to_base64(roi_img)
    
    return {
        "image_path": image_path,
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

