import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw
import io
import easyocr

# --- 1. 內部邏輯整合 ---
def get_transpose_info(instrument_name):
    table = {"豎笛 (Bb)": 2, "小號 (Bb)": 2, "中音薩克斯風 (Eb)": 9, "長笛 (C)": 0}
    return table.get(instrument_name, 0)

def transpose_numbered_note(note_str, shift):
    try:
        if note_str.isdigit():
            val = int(note_str)
            new_val = (val + shift - 1) % 7 + 1
            return str(new_val)
    except: pass
    return note_str

# --- 2. 網頁配置 ---
st.set_page_config(page_title="樂譜轉調助手", layout="centered")
st.title("🎼 簡譜自動轉調助手")

@st.cache_resource
def load_ocr_reader():
    # 強制使用 CPU 模式以確保穩定性
    return easyocr.Reader(['en'], gpu=False)

reader = load_ocr_reader()

# --- 3. 介面設定 ---
target_instr = st.sidebar.selectbox(
    "選擇你的樂器", 
    ["豎笛 (Bb)", "中音薩克斯風 (Eb)", "小號 (Bb)", "長笛 (C)"],
    key="instr_select"
)

uploaded_file = st.file_uploader("請上傳樂譜照片", type=["jpg", "jpeg", "png"], key="uploader")

if uploaded_file is not None:
    try:
        # 讀取檔案內容
        file_bytes = uploaded_file.read()
        
        # 1. 建立 PIL 影像用於顯示和繪圖
        pil_img = Image.open(io.BytesIO(file_bytes)).convert('RGB')
        
        # 2. 建立 OpenCV 影像用於 OCR 辨識
        nparr = np.frombuffer(file_bytes, np.uint8)
        opencv_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # 顯示原始圖片 (使用最相容的參數)
        st.image(pil_img, caption="原始樂譜預覽", use_column_width=True)

        # --- 4. 轉換按鈕 ---
        if st.button("🚀 開始自動移調", key="process_btn"):
            with st.spinner('AI 正在處理中...'):
                shift = get_transpose_info(target_instr)
                results = reader.readtext(opencv_img)
                
                draw = ImageDraw.Draw(pil_img)
                count = 0
                
                for (bbox, text, prob) in results:
                    cleaned = "".join([c for c in text if c.isdigit()])
                    if cleaned and prob > 0.3:
                        new_text = "".join([transpose_numbered_note(c, shift) for c in cleaned])
                        
                        # 取得座標並繪製
                        p1 = tuple(map(int, bbox[0]))
                        p2 = tuple(map(int, bbox[2]))
                        draw.rectangle([p1, p2], fill="white")
                        draw.text(p1, new_text, fill=(255, 0, 0))
                        count += 1
                
                if count > 0:
                    st.success(f"完成！成功辨識並移調了 {count} 個音符。")
                    st.image(pil_img, caption="移調後的結果", use_column_width=True)
                    
                    # 下載準備
                    result_buf = io.BytesIO()
                    pil_img.save(result_buf, format="PNG")
                    st.download_button(
                        label="📥 下載結果圖片",
                        data=result_buf.getvalue(),
                        file_name="transposed.png",
                        mime="image/png"
                    )
                else:
                    st.warning("辨識不到清楚的數字，請換一張照片試試。")
                    
    except Exception as e:
        st.error(f"處理圖片時發生錯誤：{e}")
