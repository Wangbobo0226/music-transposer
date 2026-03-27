import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw
import io
import easyocr

# --- 1. 內部邏輯整合 (移調功能) ---
def get_transpose_info(instrument_name):
    table = {"豎笛 (Bb)": 2, "小號 (Bb)": 2, "中音薩克斯風 (Eb)": 9, "長笛 (C)": 0}
    return table.get(instrument_name, 0)

def transpose_numbered_note(note_str, shift):
    try:
        if note_str.isdigit():
            val = int(note_str)
            # 簡譜 1-7 循環邏輯
            new_val = (val + shift - 1) % 7 + 1
            return str(new_val)
    except: pass
    return note_str

# --- 2. 網頁配置 ---
st.set_page_config(page_title="樂譜轉調助手", layout="centered")
st.title("🎼 簡譜自動轉調助手")

# 初始化 AI 辨識器 (快取處理)
@st.cache_resource
def load_ocr_reader():
    return easyocr.Reader(['en'], gpu=False)

try:
    reader = load_ocr_reader()
except Exception as e:
    st.error("AI 引擎啟動中，請稍候。")

# --- 3. 介面設定 ---
target_instr = st.sidebar.selectbox(
    "選擇你的樂器", 
    ["豎笛 (Bb)", "中音薩克斯風 (Eb)", "小號 (Bb)", "長笛 (C)"],
    key="instr_box"
)

uploaded_file = st.file_uploader("請上傳樂譜照片", type=["jpg", "jpeg", "png"], key="file_up")

if uploaded_file is not None:
    # --- 核心修正：正確讀取圖片資料 ---
    # 獲取原始位元組資料，避免重複 read() 導致檔案變空
    img_bytes = uploaded_file.getvalue()
    
    # 轉換為 OpenCV 格式 (NumPy array)
    nparr = np.frombuffer(img_bytes, np.uint8)
    opencv_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # 轉換為 PIL 格式 (用於顯示與繪圖)
    pil_img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
    
    # 顯示原始圖片
    st.image(pil_img, caption="原始樂譜", use_container_width=True, key="view_orig")

    # --- 4. 轉換按鈕 ---
    if st.button("🚀 開始自動移調", key="run_btn"):
        with st.spinner('AI 正在辨識並計算中...'):
            
            # 獲取移調值
            shift = get_transpose_info(target_instr)
            
            # 執行辨識
            results = reader.readtext(opencv_img)
            
            draw = ImageDraw.Draw(pil_img)
            count = 0
            
            for (bbox, text, prob) in results:
                # 只處理數字
                cleaned = "".join([c for c in text if c.isdigit()])
                if cleaned and prob > 0.3:
                    new_text = "".join([transpose_numbered_note(c, shift) for c in cleaned])
                    
                    # 獲取座標
                    p1 = tuple(map(int, bbox[0]))
                    p2 = tuple(map(int, bbox[2]))
                    
                    # 覆蓋與重繪
                    draw.rectangle([p1, p2], fill="white")
                    draw.text(p1, new_text, fill=(255, 0, 0))
                    count += 1
            
            # --- 5. 顯示結果 ---
            if count > 0:
                st.success(f"轉換完成！已處理 {count} 個音符。")
                st.image(pil_img, caption=f"移調後的結果 ({target_instr})", use_container_width=True, key="view_res")
                
                # 提供下載
                buf = io.BytesIO()
                pil_img.save(buf, format="PNG")
                st.download_button(
                    label="📥 下載移調後的圖片",
                    data=buf.getvalue(),
                    file_name="transposed_score.png",
                    mime="image/png",
                    key="dl_btn"
                )
            else:
                st.warning("未能辨識到清晰數字，請嘗試上傳光線更充足的照片。")

else:
    st.info("👋 歡迎使用！請上傳一張簡譜照片來開始作業。")
