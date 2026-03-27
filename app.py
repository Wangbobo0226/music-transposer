import streamlit as st
import cv2
import numpy as np
from PIL import Image
import pytesseract
from utils import convert_sheet_music
import re

# 設定網頁標題與圖示
st.set_page_config(page_title="簡譜移調轉換器", page_icon="🎵")

st.title("🎵 簡譜移調轉換器 (含 AI 偵測)")
st.write("手動輸入簡譜，或上傳簡譜圖片，系統將自動偵測數字並進行移調！")

st.divider()

# --- 方式一：文字輸入 ---
st.header("方式一：手動輸入簡譜")
sheet_text = st.text_area(
    "請在此輸入簡譜：", 
    placeholder="例如：3 5 2 5 | 4 4 3 5 | 1' 2' 3'",
    height=100
)

if st.button("開始轉換文字", type="primary"):
    if sheet_text.strip():
        converted = convert_sheet_music(sheet_text)
        st.success("✅ 轉換成功！")
        
        st.write("**轉換結果：**")
        st.code(converted, language="text") 
    else:
        st.warning("請先輸入簡譜文字喔！")

st.divider()

# --- 方式二：圖片上傳與偵測系統 ---
st.header("方式二：AI 樂譜圖片偵測")
st.info("💡 提示：此功能使用基礎 OCR 技術。為獲得最佳效果，請上傳背景乾淨、對比度高的黑白樂譜圖片。")

uploaded_file = st.file_uploader("請選擇樂譜圖片", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    # 1. 顯示原始圖片
    image = Image.open(uploaded_file)
    st.image(image, caption="已上傳的樂譜", use_container_width=True)
    
    with st.spinner('🔍 正在使用 OCR 掃描樂譜中，請稍候...'):
        try:
            # 2. 影像前處理 (OpenCV) 幫助提高辨識率
            # 將 PIL Image 轉為 OpenCV 格式 (numpy array)
            img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            # 轉為灰階圖片
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            # 影像二值化 (黑白對比最大化)
            _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
            
            # 3. 執行 Tesseract OCR 偵測
            # 雲端環境中不需要指定 tesseract_cmd 路徑，系統會自動找到
            custom_config = r'--oem 3 --psm 6'
            detected_text = pytesseract.image_to_string(thresh, config=custom_config)
            
            # 4. 資料清理 (過濾掉中文歌詞或非樂譜相關的雜訊)
            # 只保留數字 1-7、單引號 '、空格和 | 符號
            clean_text = re.sub(r'[^1-7\'\s\|]', '', detected_text)
            # 移除過多的空白行
            clean_text = '\n'.join([line.strip() for line in clean_text.split('\n') if line.strip()])

            if clean_text:
                st.success("✅ 掃描完成！")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**OCR 擷取出的原譜：**")
                    st.code(clean_text, language="text")
                    
                with col2:
                    st.write("**自動移調後的結果：**")
                    final_converted = convert_sheet_music(clean_text)
                    st.code(final_converted, language="text")
            else:
                st.error("⚠️ 無法從圖片中偵測到清晰的數字，請嘗試上傳更清晰、對比度更高的圖片，或改用手動輸入。")
                
        except Exception as e:
            st.error(f"❌ 處理圖片時發生錯誤：{str(e)}")
            st.info("如果您是在 Streamlit Cloud 執行，請確認您的 GitHub 專案中是否已加入正確的 `packages.txt` 與 `requirements.txt`。")
