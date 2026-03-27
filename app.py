import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw
import io
import easyocr

# --- 1. 核心邏輯 (移調計算) ---
def get_transpose_info(instrument_name):
    table = {"豎笛 (Bb)": 2, "小號 (Bb)": 2, "中音薩克斯風 (Eb)": 9, "長笛 (C)": 0}
    return table.get(instrument_name, 0)

def transpose_numbered_note(note_str, shift):
    try:
        if note_str.isdigit():
            val = int(note_str)
            # 簡譜 1-7 循環
            new_val = (val + shift - 1) % 7 + 1
            return str(new_val)
    except: pass
    return note_str

# --- 2. 網頁配置 ---
st.set_page_config(page_title="樂譜轉調助手", layout="centered")
st.title("🎼 簡譜自動轉調助手")

@st.cache_resource
def load_ocr_reader():
    # 強制使用 CPU 模式
    return easyocr.Reader(['en'], gpu=False)

reader = load_ocr_reader()

# --- 3. 介面設定 ---
target_instr = st.sidebar.selectbox(
    "選擇你的樂器", 
    ["豎笛 (Bb)", "中音薩克斯風 (Eb)", "小號 (Bb)", "長笛 (C)"]
)

uploaded_file = st.file_uploader("請上傳樂譜照片", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    try:
        # 讀取檔案
        img_bytes = uploaded_file.read()
        
        # 轉換為 PIL 並確保是 RGB 格式
        pil_img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
        
        # --- 關鍵修正：將影像轉換為 NumPy 陣列以解決 TypeError ---
        display_img = np.array(pil_img)

        # 顯示原始圖片 (改用最基礎的顯示方式)
        st.image(display_img, caption="原始樂譜預覽")

        # --- 4. 轉換按鈕 ---
        if st.button("🚀 開始自動移調"):
            with st.spinner('AI 正在辨識中...'):
                # 準備 OpenCV 格式供 OCR 使用
                opencv_img = cv2.cvtColor(display_img, cv2.COLOR_RGB2BGR)
                results = reader.readtext(opencv_img)
                
                # 重新建立繪圖物件
                draw = ImageDraw.Draw(pil_img)
                shift = get_transpose_info(target_instr)
                count = 0
                
                for (bbox, text, prob) in results:
                    cleaned = "".join([c for c in text if c.isdigit()])
                    if cleaned and prob > 0.3:
                        new_text = "".join([transpose_numbered_note(c, shift) for c in cleaned])
                        
                        # 取得座標
                        p1 = tuple(map(int, bbox[0]))
                        p2 = tuple(map(int, bbox[2]))
                        
                        # 覆蓋舊數字並填上紅字
                        draw.rectangle([p1, p2], fill="white")
                        draw.text(p1, new_text, fill=(255, 0, 0))
                        count += 1
                
                if count > 0:
                    st.success(f"完成！已處理 {count} 個音符。")
                    # 同樣轉換為 NumPy 陣列顯示結果
                    res_display = np.array(pil_img)
                    st.image(res_display, caption=f"移調後的 {target_instr} 譜")
                    
                    # 下載功能
                    buf = io.BytesIO()
                    pil_img.save(buf, format="PNG")
                    st.download_button("📥 下載結果圖片", buf.getvalue(), "transposed.png", "image/png")
                else:
                    st.warning("辨識不到清楚數字，請換一張照片。")
                    
    except Exception as e:
        st.error(f"程式執行發生錯誤：{e}")

else:
    st.info("請上傳樂譜照片開始使用。")
