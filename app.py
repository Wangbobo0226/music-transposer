import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw
import io
import easyocr

# --- 1. 核心邏輯 ---
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
    return easyocr.Reader(['en'], gpu=False)

reader = load_ocr_reader()

# --- 3. 介面設定 ---
target_instr = st.sidebar.selectbox("選擇你的樂器", ["豎笛 (Bb)", "中音薩克斯風 (Eb)", "小號 (Bb)", "長笛 (C)"])
uploaded_file = st.file_uploader("請上傳樂譜照片", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    try:
        img_bytes = uploaded_file.read()
        pil_img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
        
        # 轉換為 NumPy 陣列顯示以解決 Python 3.14 相容性問題
        display_img = np.array(pil_img)
        st.image(display_img, caption="原始樂譜預覽")

        if st.button("🚀 開始自動移調"):
            with st.spinner('AI 正在辨識中...'):
                opencv_img = cv2.cvtColor(display_img, cv2.COLOR_RGB2BGR)
                results = reader.readtext(opencv_img)
                
                draw = ImageDraw.Draw(pil_img)
                shift = get_transpose_info(target_instr)
                count = 0
                
                for (bbox, text, prob) in results:
                    cleaned = "".join([c for c in text if c.isdigit()])
                    if cleaned and prob > 0.3:
                        new_text = "".join([transpose_numbered_note(c, shift) for c in cleaned])
                        
                        # --- 核心修正：確保 y1 >= y0, x1 >= x0 ---
                        # 提取所有座標的 x 和 y
                        xs = [p[0] for p in bbox]
                        ys = [p[1] for p in bbox]
                        
                        # 找到邊界，防止 PIL 報錯
                        min_x, max_x = int(min(xs)), int(max(xs))
                        min_y, max_y = int(min(ys)), int(max(ys))
                        
                        # 使用安全的座標繪圖
                        draw.rectangle([min_x, min_y, max_x, max_y], fill="white")
                        draw.text((min_x, min_y), new_text, fill=(255, 0, 0))
                        count += 1
                
                if count > 0:
                    st.success(f"完成！已處理 {count} 個音符。")
                    res_display = np.array(pil_img)
                    st.image(res_display, caption=f"移調後的 {target_instr} 譜")
                    
                    buf = io.BytesIO()
                    pil_img.save(buf, format="PNG")
                    st.download_button("📥 下載結果圖片", buf.getvalue(), "transposed.png", "image/png")
                else:
                    st.warning("辨識不到清楚數字。")
                    
    except Exception as e:
        st.error(f"程式執行發生錯誤：{e}")
else:
    st.info("請上傳照片開始。")
