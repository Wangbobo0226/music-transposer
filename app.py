import streamlit as st
import cv2
import numpy as np
from PIL import Image
import pytesseract
from utils import process_jianpu_ocr
import re

# 如果是用戶的本機環境，可能需要指定 tesseract 路徑。
# 請根據您的 Tesseract 安裝位置修改此路徑，如果是部署到 Streamlit Cloud 則無需此行。
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def preprocess_image(pil_image):
    """對影像進行高級前處理以提高 OCR 辨識率。"""
    # 將 PIL Image 轉為 OpenCV 格式 (numpy array)。
    # PIL 使用 RGB，OpenCV 使用 BGR。
    img_cv = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

    # 1. 調整大小以提高 OCR 性能 (放大)。
    height, width = img_cv.shape[:2]
    new_size = (width * 2, height * 2) # 放大 2 倍。
    img_cv = cv2.resize(img_cv, new_size, interpolation=cv2.INTER_CUBIC)

    # 2. 轉為灰階。
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

    # 3. 自適應二值化，以處理不均勻的光照。
    # 使用 ADAPTIVE_THRESH_GAUSSIAN_C，一個鄰域。
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    
    # 4. 中值濾波去除噪點和細小的水印/歌詞行。
    median = cv2.medianBlur(binary, 3)

    # 5. Otsu 二值化。
    _, final_thresh = cv2.threshold(median, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 6. 形態學操作 (移除小的噪音點，可選)。
    # kernel = np.ones((1, 1), np.uint8)
    # final_thresh = cv2.morphologyEx(final_thresh, cv2.MORPH_OPEN, kernel)
    
    return final_thresh

# Streamlit 介面。
st.title("🎵 簡譜轉換器")
st.write("上傳樂譜圖片，自動轉換為移調後的簡譜。")

uploaded_file = st.file_uploader("請選擇樂譜圖片", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    # 1. 顯示原始圖片。
    st.image(uploaded_file, caption="原始樂譜", use_container_width=True)
    
    # 增加一個前處理結果顯示按鈕，方便偵錯。
    with st.expander("查看前處理結果 (可選)", expanded=False):
        # 影像前處理。
        pil_image = Image.open(uploaded_file)
        preprocessed_img = preprocess_image(pil_image)
        # 將 OpenCV 影像轉回 PIL 影像以顯示。
        preprocessed_pil = Image.fromarray(preprocessed_img)
        st.image(preprocessed_pil, caption="前處理後的影像", use_container_width=True)
    
    with st.spinner('🔍 正在辨識樂譜...'):
        # 影像前處理。
        pil_image = Image.open(uploaded_file)
        preprocessed_img = preprocess_image(pil_image)
        
        # 3. 執行 OCR。
        # 對於稀疏文字，psm 11。對於多行多列，psm 3。
        custom_config = r'--oem 3 --psm 3' # 嘗試 psm 3 或是 psm 11。
        detected_text = pytesseract.image_to_string(preprocessed_img, config=custom_config)
        
        # 4. 清理、移調並再次清理。
        cleaned_original, final_converted = process_jianpu_ocr(detected_text)
        
        st.success("✅ 辨識完成！")
        
        # 5. 顯示結果。
        st.write("**OCR 擷取出的原譜：**")
        st.code(cleaned_original, language="text")

        st.write("**自動移調後的結果：**")
        # 預防性地清理最後的結果，移除 OCR 生成的不尋常符號。
        final_cleaned = re.sub(r"[^1-7'\s\|]", "", final_converted)
        st.code(final_cleaned, language="text")
