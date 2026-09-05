import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "sample_docs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_font(size=18):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        return ImageFont.load_default()

def create_sample_712_maharashtra():
    """Generates Form 7/12 (Satbara) Land Record Sample - Clean Record (High Confidence)"""
    width, height = 900, 1200
    img = Image.new("RGB", (width, height), color=(250, 248, 240))
    draw = ImageDraw.Draw(img)
    
    font_title = get_font(24)
    font_header = get_font(18)
    font_body = get_font(15)
    font_bold = get_font(16)
    
    # Outer border
    draw.rectangle([20, 20, width - 20, height - 20], outline="#1e293b", width=3)
    draw.rectangle([25, 25, width - 25, height - 25], outline="#334155", width=1)
    
    # Header Banner
    draw.rectangle([30, 30, width - 30, 90], fill="#0f172a")
    draw.text((width // 2 - 180, 45), "GOVERNMENT OF MAHARASHTRA", fill="#f8fafc", font=font_title)
    
    draw.text((width // 2 - 180, 100), "VILLAGE FORM NO. 7/12 ( अधिकार अभिलेख पत्रक )", fill="#1e293b", font=font_header)
    
    # Location Metadata Block
    draw.rectangle([40, 140, width - 40, 210], outline="#64748b", width=2, fill="#f1f5f9")
    draw.text((60, 155), "District (जिल्हा): Pune", fill="#0f172a", font=font_bold)
    draw.text((320, 155), "Taluka (तालुका): Haveli", fill="#0f172a", font=font_bold)
    draw.text((580, 155), "Village (गावाचे नाव): Wagholi", fill="#0f172a", font=font_bold)
    draw.text((60, 180), "Survey / Khasra No (सर्व्हे / गट क्र.): 142/3A", fill="#0f172a", font=font_bold)
    draw.text((450, 180), "Khata No (खाता क्रमांक): 8842", fill="#0f172a", font=font_bold)
    
    # Main Table (Form 7 - Owners & Land Details)
    y_start = 230
    draw.rectangle([40, y_start, width - 40, y_start + 40], fill="#334155")
    draw.text((50, y_start + 10), "Occupant Name (खातेदाराचे नाव)", fill="#ffffff", font=font_bold)
    draw.text((340, y_start + 10), "Share (हिस्सा)", fill="#ffffff", font=font_bold)
    draw.text((450, y_start + 10), "Area (क्षेत्रफळ - H.R.)", fill="#ffffff", font=font_bold)
    draw.text((640, y_start + 10), "Assessment (आकारणी ₹)", fill="#ffffff", font=font_bold)
    
    rows = [
        ("1. Rameshwar Laxman Patil", "0.50 (50%)", "0.82.00 Hectares (2.02 Acres)", "₹ 14.50"),
        ("2. Sunita Rameshwar Patil", "0.50 (50%)", "0.82.00 Hectares (2.02 Acres)", "₹ 14.50"),
    ]
    
    curr_y = y_start + 40
    for r in rows:
        draw.rectangle([40, curr_y, width - 40, curr_y + 40], outline="#cbd5e1", fill="#ffffff")
        draw.text((50, curr_y + 10), r[0], fill="#0f172a", font=font_body)
        draw.text((340, curr_y + 10), r[1], fill="#0f172a", font=font_body)
        draw.text((450, curr_y + 10), r[2], fill="#0f172a", font=font_body)
        draw.text((640, curr_y + 10), r[3], fill="#0f172a", font=font_body)
        curr_y += 40
        
    # Total Summary Block
    draw.rectangle([40, curr_y, width - 40, curr_y + 35], fill="#e2e8f0")
    draw.text((50, curr_y + 8), "TOTAL AREA (एकूण क्षेत्रफळ): 1.64.00 Hectares (4.05 Acres)", fill="#0f172a", font=font_bold)
    draw.text((550, curr_y + 8), "Land Use: Jirayat (Dry Agricultural)", fill="#0f172a", font=font_bold)
    curr_y += 50
    
    # Encumbrances & Other Rights (Form 12)
    draw.rectangle([40, curr_y, width - 40, curr_y + 35], fill="#1e293b")
    draw.text((50, curr_y + 8), "OTHER RIGHTS & ENCUMBRANCES (इतर अधिकार व बोजे)", fill="#ffffff", font=font_bold)
    curr_y += 35
    
    draw.rectangle([40, curr_y, width - 40, curr_y + 100], outline="#cbd5e1", fill="#ffffff")
    draw.text((50, curr_y + 15), "• Bank Charge: Mortgage registered with Bank of Maharashtra, Wagholi Branch", fill="#1e293b", font=font_body)
    draw.text((50, curr_y + 40), "  Loan Reference: BOM/AGRI/2023/9912 | Amount: ₹ 4,50,000", fill="#475569", font=font_body)
    draw.text((50, curr_y + 65), "• Mutation Entry No (फेरफार क्र.): 12480 (Date: 14-Nov-2023)", fill="#1e293b", font=font_body)
    curr_y += 120
    
    # Official Stamp & QR Code Placeholder
    draw.rectangle([60, curr_y, 240, curr_y + 120], outline="#2563eb", width=2, fill="#eff6ff")
    draw.text((70, curr_y + 20), "DIGITALLY SIGNED", fill="#1d4ed8", font=font_bold)
    draw.text((75, curr_y + 45), "Tahsil Office, Haveli", fill="#1e40af", font=font_body)
    draw.text((75, curr_y + 65), "Ref ID: MH712-8842-X9", fill="#1e40af", font=font_body)
    draw.text((75, curr_y + 85), "Date: 22-Aug-2026", fill="#1e40af", font=font_body)
    
    # Government Circular Seal
    draw.ellipse([650, curr_y + 5, 760, curr_y + 115], outline="#dc2626", width=3)
    draw.text((665, curr_y + 40), "SEAL OF TAHSILLAR", fill="#dc2626", font=font_bold)
    draw.text((680, curr_y + 60), "HAVELI, PUNE", fill="#dc2626", font=font_body)
    
    filepath = os.path.join(OUTPUT_DIR, "maharashtra_712_clean.png")
    img.save(filepath)
    print(f"Saved: {filepath}")
    return filepath

def create_sample_rtc_karnataka():
    """Generates RTC / Pahani Land Record (Karnataka) - Low Confidence due to Noise & Rotated Scan"""
    width, height = 900, 1200
    img = Image.new("RGB", (width, height), color=(245, 240, 230))
    draw = ImageDraw.Draw(img)
    
    font_title = get_font(22)
    font_header = get_font(17)
    font_body = get_font(14)
    font_bold = get_font(15)
    
    # Border
    draw.rectangle([20, 20, width - 20, height - 20], outline="#451a03", width=3)
    
    # Header Banner
    draw.rectangle([30, 30, width - 30, 90], fill="#7c2d12")
    draw.text((width // 2 - 240, 45), "GOVERNMENT OF KARNATAKA - REVENUE DEPARTMENT", fill="#fef3c7", font=font_title)
    
    draw.text((width // 2 - 180, 100), "RECORD OF RIGHTS, TENANCY AND CROPS (RTC / Pahani)", fill="#451a03", font=font_header)
    
    # Location Metadata Block
    draw.rectangle([40, 140, width - 40, 210], outline="#9a3412", width=2, fill="#ffedd5")
    draw.text((60, 155), "District (ಜಿಲ್ಲೆ): Bengaluru Rural", fill="#431407", font=font_bold)
    draw.text((340, 155), "Taluk (ತಾಲೂಕು): Devanahalli", fill="#431407", font=font_bold)
    draw.text((600, 155), "Hobli/Village: Vijayapura", fill="#431407", font=font_bold)
    draw.text((60, 180), "Survey No (ಸರ್ವೇ ನಂಬರ್): 89/1B", fill="#431407", font=font_bold)
    draw.text((340, 180), "Khata No: 4021", fill="#431407", font=font_bold)
    draw.text((600, 180), "Valid Year: 2025-2026", fill="#431407", font=font_bold)
    
    # Owners Table (Intentionally includes share discrepancy to trigger Rule engine flag)
    y_start = 230
    draw.rectangle([40, y_start, width - 40, y_start + 40], fill="#9a3412")
    draw.text((50, y_start + 10), "Owner Name (ಖಾತೆದಾರರ ಹೆಸರು)", fill="#ffffff", font=font_bold)
    draw.text((340, y_start + 10), "Extent (Acre-Gunta)", fill="#ffffff", font=font_bold)
    draw.text((520, y_start + 10), "Recorded Share", fill="#ffffff", font=font_bold)
    draw.text((680, y_start + 10), "Soil Type", fill="#ffffff", font=font_bold)
    
    # Share fractions sum to 0.70 instead of 1.0 (Anomalous share sum!)
    rows = [
        ("1. Venkatachalapathy Gowda", "1 Acre 20 Gunta", "0.40 (40%)", "Red Soil (Kari)"),
        ("2. Krishnappa Gowda (Co-owner)", "1 Acre 00 Gunta", "0.30 (30%)", "Red Soil (Kari)"),
    ]
    
    curr_y = y_start + 40
    for r in rows:
        draw.rectangle([40, curr_y, width - 40, curr_y + 45], outline="#fdba74", fill="#ffffff")
        draw.text((50, curr_y + 12), r[0], fill="#431407", font=font_body)
        draw.text((340, curr_y + 12), r[1], fill="#431407", font=font_body)
        draw.text((520, curr_y + 12), r[2], fill="#431407", font=font_body)
        draw.text((680, curr_y + 12), r[3], fill="#431407", font=font_body)
        curr_y += 45
        
    draw.rectangle([40, curr_y, width - 40, curr_y + 35], fill="#fed7aa")
    draw.text((50, curr_y + 8), "TOTAL EXTENT: 2 Acres 20 Gunta (Discrepancy in recorded shares: Sum = 70%)", fill="#7c2d12", font=font_bold)
    curr_y += 50
    
    # Encumbrances
    draw.rectangle([40, curr_y, width - 40, curr_y + 35], fill="#7c2d12")
    draw.text((50, curr_y + 8), "MUTATION & LIEN DETAILS (ರೂಪಾಂತರ ಹಾಗೂ ಸಾಲದ ವಿವರ)", fill="#ffffff", font=font_bold)
    curr_y += 35
    
    draw.rectangle([40, curr_y, width - 40, curr_y + 90], outline="#fdba74", fill="#ffffff")
    draw.text((50, curr_y + 15), "• MR No: MR-109/2022-23 (Inheritance Partition)", fill="#431407", font=font_body)
    draw.text((50, curr_y + 40), "• Encumbrance Flag: Active dispute notice filed under Section 136(2) of KLR Act", fill="#991b1b", font=font_bold)
    curr_y += 110
    
    # Add simulated scan degradation (noise / angle skew via OpenCV)
    filepath_temp = os.path.join(OUTPUT_DIR, "karnataka_rtc_temp.png")
    img.save(filepath_temp)
    
    # Read with OpenCV to apply slight rotation & noise
    cv_img = cv2.imread(filepath_temp)
    h, w = cv_img.shape[:2]
    center = (w // 2, h // 2)
    # Rotate by 2.5 degrees skew
    M = cv2.getRotationMatrix2D(center, 2.5, 1.0)
    rotated = cv2.warpAffine(cv_img, M, (w, h), borderValue=(245, 240, 230))
    
    # Add slight noise to simulate aged scan
    noise = np.random.normal(0, 8, rotated.shape).astype(np.uint8)
    noisy_img = cv2.add(rotated, noise)
    
    filepath = os.path.join(OUTPUT_DIR, "karnataka_rtc_low_conf.png")
    cv2.imwrite(filepath, noisy_img)
    if os.path.exists(filepath_temp):
        os.remove(filepath_temp)
    print(f"Saved degraded RTC: {filepath}")
    return filepath

def create_sample_khasra_up():
    """Generates Khasra-Khatauni Sample (Uttar Pradesh) - Hindi Devanagari Record"""
    width, height = 900, 1200
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    font_title = get_font(24)
    font_header = get_font(18)
    font_body = get_font(15)
    font_bold = get_font(16)
    
    draw.rectangle([20, 20, width - 20, height - 20], outline="#166534", width=3)
    
    # Header Banner
    draw.rectangle([30, 30, width - 30, 90], fill="#14532d")
    draw.text((width // 2 - 220, 45), "UTTAR PRADESH REVENUE CODE - KHASRA / KHATAUNI", fill="#f0fdf4", font=font_title)
    
    draw.text((width // 2 - 160, 100), "उद्धरण खतौनी (भूलेख उत्तर प्रदेश ऑनलाइन अभिलेख)", fill="#166534", font=font_header)
    
    # Metadata Block
    draw.rectangle([40, 140, width - 40, 210], outline="#22c55e", width=2, fill="#f0fdf4")
    draw.text((60, 155), "District (जनपद): Varanasi", fill="#14532d", font=font_bold)
    draw.text((340, 155), "Tehsil (तहसील): Pindra", fill="#14532d", font=font_bold)
    draw.text((600, 155), "Pargana/Village: Phulpur", fill="#14532d", font=font_bold)
    draw.text((60, 180), "Khasra No (खसरा संख्या): 512/1", fill="#14532d", font=font_bold)
    draw.text((340, 180), "Khatauni Account No: 00319", fill="#14532d", font=font_bold)
    
    # Owners Table
    y_start = 230
    draw.rectangle([40, y_start, width - 40, y_start + 40], fill="#166534")
    draw.text((50, y_start + 10), "Khatedar Name (खातेदार का नाम)", fill="#ffffff", font=font_bold)
    draw.text((360, y_start + 10), "Share Ratio", fill="#ffffff", font=font_bold)
    draw.text((500, y_start + 10), "Area (Hectares)", fill="#ffffff", font=font_bold)
    draw.text((680, y_start + 10), "Lagaan (₹)", fill="#ffffff", font=font_bold)
    
    rows = [
        ("1. Shivkumar Nath Tiwari s/o Ramswaroop", "1.00 (100% Sole Owner)", "0.5420 Hectares (1.34 Acres)", "₹ 28.00"),
    ]
    
    curr_y = y_start + 40
    for r in rows:
        draw.rectangle([40, curr_y, width - 40, curr_y + 40], outline="#bbf7d0", fill="#ffffff")
        draw.text((50, curr_y + 10), r[0], fill="#14532d", font=font_body)
        draw.text((360, curr_y + 10), r[1], fill="#14532d", font=font_body)
        draw.text((500, curr_y + 10), r[2], fill="#14532d", font=font_body)
        draw.text((680, curr_y + 10), r[3], fill="#14532d", font=font_body)
        curr_y += 40
        
    draw.rectangle([40, curr_y, width - 40, curr_y + 35], fill="#dcfce7")
    draw.text((50, curr_y + 8), "TOTAL SANCTIONED AREA: 0.5420 Hectares | Land Category: Irrigated Single Crop", fill="#14532d", font=font_bold)
    curr_y += 50
    
    # Encumbrances
    draw.rectangle([40, curr_y, width - 40, curr_y + 35], fill="#14532d")
    draw.text((50, curr_y + 8), "REVENUE REMARKS & ORDERS (विवरण एवं आदेश)", fill="#ffffff", font=font_bold)
    curr_y += 35
    
    draw.rectangle([40, curr_y, width - 40, curr_y + 90], outline="#bbf7d0", fill="#ffffff")
    draw.text((50, curr_y + 15), "• Order No: 881/Tehsildar Pindra dt 10-Jan-2024", fill="#14532d", font=font_body)
    draw.text((50, curr_y + 40), "• Encumbrance: Clear Record (No Bank Lien or Encumbrance registered)", fill="#166534", font=font_bold)
    curr_y += 110
    
    # Stamp
    draw.rectangle([60, curr_y, 240, curr_y + 100], outline="#16a34a", width=2, fill="#f0fdf4")
    draw.text((70, curr_y + 20), "VERIFIED BHULEKH UP", fill="#15803d", font=font_bold)
    draw.text((75, curr_y + 45), "Digital Cert: UP-2026-88192", fill="#166534", font=font_body)
    
    filepath = os.path.join(OUTPUT_DIR, "up_khasra_clean.png")
    img.save(filepath)
    print(f"Saved: {filepath}")
    return filepath

if __name__ == "__main__":
    create_sample_712_maharashtra()
    create_sample_rtc_karnataka()
    create_sample_khasra_up()
    print("All sample land record documents generated successfully.")
