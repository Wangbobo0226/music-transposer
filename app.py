# app.py
import streamlit as st
from utils import convert_sheet_music

# 設定網頁標題與圖示
st.set_page_config(page_title="簡譜移調轉換器", page_icon="🎵")

st.title("🎵 簡譜移調轉換器")
st.write("將您的簡譜進行移調。支援一般數字與高音標記（如：原譜 `1'` 轉換後會變為 `4'`）。")

st.divider()

# --- 方式一：文字輸入 ---
st.header("方式一：輸入簡譜文字")
sheet_text = st.text_area(
    "請在此輸入簡譜：", 
    placeholder="例如：3 5 2 5 | 4 4 3 5 | 1' 2' 3'",
    height=150
)

if st.button("開始轉換文字", type="primary"):
    if sheet_text.strip():
        converted = convert_sheet_music(sheet_text)
        st.success("✅ 轉換成功！")
        
        st.write("**轉換結果：**")
        # 使用 st.code 讓排版更清楚，且自帶複製按鈕
        st.code(converted, language="text") 
    else:
        st.warning("請先輸入簡譜文字喔！")

st.divider()

# --- 方式二：圖片上傳 ---
st.header("方式二：上傳樂譜圖片")
st.info("💡 提示：目前為圖片上傳介面測試，完整的圖片轉數字功能需後續串接 OCR 模型 (例如 Tesseract 或是 Google Vision API)。")

uploaded_file = st.file_uploader("請選擇樂譜圖片", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    # 顯示上傳的圖片
    st.image(uploaded_file, caption="已上傳的樂譜", use_column_width=True)
    st.success(f"檔案 {uploaded_file.name} 已成功上傳！")
