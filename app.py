import streamlit as st
import cv2
import numpy as np
from PIL import Image
import pytesseract
from utils import convert_sheet_music, process_jianpu_ocr
import re

# 如果是用戶的本機環境 (Windows)，可能需要指定 tesseract 路徑
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def preprocess_image(img_cv):
    """對影像進行高級前處理以提高 OCR 辨識率"""
    # 1. 調整大小以提高 OCR 性能 (放大)
    height, width = img_cv.shape[:2]
    new_size = (width * 2, height * 2) 
    img_cv = cv2.resize(img_cv, new_size, interpolation=cv2.INTER_CUBIC)

    # 2. 轉為灰階
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

    # 3. 自適應二值化，以處理不均勻的光照
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    
    # 4. 中值濾波去除噪點
    median = cv2.medianBlur(binary, 3)

    # 5. Otsu 二值化
    _, final_thresh = cv2.threshold(median, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    return final_thresh

# 設定網頁標題與圖示
st.set_page_config(page_title="簡譜移調轉換器", page_icon="🎵", layout="centered")

# --- 建立側邊欄選單 ---
st.sidebar.title("⚙️ 功能選單")
menu_option = st.sidebar.radio(
    "請選擇您要使用的轉換方式：",
    ("📝 文字輸入轉換", "🖼️ 圖片上傳轉換")
)

st.sidebar.divider()
st.sidebar.info("💡 **提示**：圖片轉換功能目前使用基礎 OCR，建議上傳背景乾淨、對比度高的樂譜以獲得最佳效果。")

# --- 根據選單顯示不同的內容 ---

if menu_option == "📝 文字輸入轉換":
    st.title("📝 簡譜文字轉換")
    st.write("請在下方輸入框貼上或手打您的簡譜，系統將自動為您移調。")
    
    sheet_text = st.text_area(
        "輸入簡譜：", 
        placeholder="例如：3 5 2 5 | 4 4 3 5 | 1' 2' 3'",
        height=150
    )

    if st.button("開始轉換", type="primary"):
        if sheet_text.strip():
            converted = convert_sheet_music(sheet_text)
            st.success("✅ 轉換成功！")
            
            st.write("**轉換結果：**")
            st.code(converted, language="text") 
        else:
            st.warning("請先輸入簡譜文字喔！")

elif menu_option == "🖼️ 圖片上傳轉換":
    st.title("🖼️ 樂譜圖片 AI 偵測")
    st.write("上傳樂譜圖片，系統將自動過濾雜訊、抓取數字並進行移調！")

    uploaded_file = st.file_uploader("請選擇樂譜圖片", type=["png", "jpg", "jpeg"])

    if uploaded_file is not None:
        # 顯示原始圖片
        image = Image.open(uploaded_file)
        st.image(image, caption="已上傳的樂譜", use_container_width=True)
        
        # 建立一個隱藏區塊，讓想看除錯畫面的人可以展開
        with st.expander("🛠️ 查看 AI 影像前處理結果 (除錯用)", expanded=False):
            img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            preprocessed_img = preprocess_image(img_cv)
            st.image(preprocessed_img, caption="黑白高對比處理後的影像", use_container_width=True)
        
        if st.button("🔍 開始掃描與轉換", type="primary"):
            with st.spinner('AI 正在努力閱讀樂譜中，請稍候...'):
                try:
                    # 執行 OCR 辨識 (psm 6 通常對統一區塊文字較好，也可視情況改為 psm 3 或 11)
                    custom_config = r'--oem 3 --psm 6'
                    detected_text = pytesseract.image_to_string(preprocessed_img, config=custom_config)
                    
                    # 呼叫 utils.py 中的完整處理流程
                    cleaned_original, final_converted = process_jianpu_ocr(detected_text)
                    
                    if cleaned_original.strip():
                        st.success("✅ 辨識與轉換完成！")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write("**OCR 擷取出的原譜：**")
                            st.code(cleaned_original, language="text")
                            
                        with col2:
                            st.write("**自動移調後的結果：**")
                            st.code(final_converted, language="text")
                    else:
                        st.error("⚠️ 無法從圖片中偵測到清晰的數字，可能圖片太模糊或雜訊過多。")
                        
                except Exception as e:
                    st.error(f"❌ 處理圖片時發生錯誤：{str(e)}")
                    st.info("請確認雲端環境是否已正確安裝 Tesseract 引擎 (packages.txt)。")
