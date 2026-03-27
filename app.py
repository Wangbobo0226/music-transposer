import streamlit as st
import cv2
import numpy as np
from PIL import Image
import pytesseract
from utils import convert_sheet_music, process_jianpu_ocr
import re

# 若在 Windows 本機執行，請取消註解並設定正確路徑
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def preprocess_image(img_cv):
    """進階影像前處理，嘗試保留更多結構特徵"""
    height, width = img_cv.shape[:2]
    # 放大影像以利辨識
    new_size = (width * 2, height * 2) 
    img_cv = cv2.resize(img_cv, new_size, interpolation=cv2.INTER_CUBIC)

    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

    # 稍微調整自適應二值化的參數，試圖減少雜訊對排版的影響
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 5)
    
    # 稍微輕量一點的中值濾波
    median = cv2.medianBlur(binary, 3)

    return median

st.set_page_config(page_title="簡譜移調轉換器", page_icon="🎵", layout="wide") # 改用 wide layout 讓排版有更多空間

st.sidebar.title("⚙️ 功能選單")
menu_option = st.sidebar.radio(
    "請選擇您要使用的轉換方式：",
    ("📝 文字輸入轉換", "🖼️ 圖片上傳轉換")
)

st.sidebar.divider()
st.sidebar.info("💡 **提示**：由於樂譜排版複雜，OCR 可能無法 100% 還原原始空白與對齊，但會盡力保留行與小節線的結構。")

if menu_option == "📝 文字輸入轉換":
    st.title("📝 簡譜文字轉換")
    st.write("請在下方輸入框貼上或手打您的簡譜，系統將自動為您移調。")
    
    sheet_text = st.text_area(
        "輸入簡譜：", 
        placeholder="例如：\n3 5 2 5 | 4 4 3 5 | 1' 2' 3'",
        height=300
    )

    if st.button("開始轉換", type="primary"):
        if sheet_text.strip():
            converted = convert_sheet_music(sheet_text)
            st.success("✅ 轉換成功！")
            st.code(converted, language="text") 
        else:
            st.warning("請先輸入簡譜文字喔！")

elif menu_option == "🖼️ 圖片上傳轉換":
    st.title("🖼️ 樂譜圖片 AI 偵測")
    st.write("上傳樂譜圖片，系統將嘗試抓取數字並保留原始排版進行移調。")

    uploaded_file = st.file_uploader("請選擇樂譜圖片", type=["png", "jpg", "jpeg"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        
        col1, col2 = st.columns(2)
        with col1:
            st.image(image, caption="已上傳的樂譜", use_container_width=True)
            
            with st.expander("🛠️ 查看 AI 影像前處理結果 (除錯用)", expanded=False):
                img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                preprocessed_img = preprocess_image(img_cv)
                st.image(preprocessed_img, caption="處理後的影像", use_container_width=True)
        
        with col2:
            # 讓使用者可以微調 OCR 模式
            st.write("🔧 **OCR 微調選項**")
            psm_mode = st.selectbox(
                "選擇版面分析模式 (PSM)：",
                ("PSM 6: 假設單一統一文字區塊 (推薦)", "PSM 4: 假設單欄可變大小文字", "PSM 11: 稀疏文字尋找 (盡量保留空白)")
            )
            
            psm_val = psm_mode.split(":")[0].replace("PSM ", "")

            if st.button("🔍 開始掃描與轉換", type="primary"):
                with st.spinner('正在分析樂譜排版中...'):
                    try:
                        # 將 psm 參數帶入，並加入 preserve_interword_spaces 嘗試保留空白
                        custom_config = f'--oem 3 --psm {psm_val} -c
