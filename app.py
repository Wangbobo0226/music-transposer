import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageOps
import io
import easyocr

# --- 內部邏輯整合 ---
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

# --- 核心安全繪圖邏輯：防止座標錯誤 ---
def safe_draw_text_and_rect(draw_obj, bbox, new_text, fill_color=(255, 0, 0), background_color="white"):
    """安全地在座標上繪製白色背景矩形和新文字，確保 y1 >= y0."""
    try:
        # 1. 提取所有座標點
        xs = [p[0] for p in bbox]
        ys = [p[1] for p in bbox]
        
        # 2. 強制找出最小與最大座標，組成完美的矩形
        min_x, max_x = int(min(xs)), int(max(xs))
        min_y, max_y = int(min(ys)), int(max(ys))
        
        # 安全性檢查 (防止 OCR 回傳單點)
        if max_x == min_x or max_y == min_y: return

        # 3. 繪製
        # 先畫一個白色矩形把舊音符完全蓋掉 (變成新譜的空白處)
        draw_obj.rectangle([min_x, min_y, max_x, max_y], fill=background_color)
        
        # 再用紅色印上新音符
        # 稍微向下偏移一點，讓新音符看起來比較居中
        offset_y = int((max_y - min_y) * 0.1)
        draw_obj.text((min_x, min_y + offset_y), new_text, fill=fill_color)
    except Exception as e:
        st.warning(f"處理某個音符座標時發生小錯誤，已跳過。錯誤: {e}")

# --- 網頁介面設定 ---
st.set_page_config(page_title="樂譜淨化移調助手", layout="centered")
st.title("🎼 簡譜自動移調與淨化助手")
st.markdown("上傳樂譜照片，AI 將移除灰暗背景，為您生成一張黑白分明的新譜，並標註移調後的紅字新音符。")

@st.cache_resource
def load_ocr_reader():
    return easyocr.Reader(['en'], gpu=False)

reader = load_ocr_reader()

target_instr = st.sidebar.selectbox("1. 選擇樂器", ["豎笛 (Bb)", "中音薩克斯風 (Eb)", "小號 (Bb)", "長笛 (C)"])
uploaded_file = st.file_uploader("2. 上傳樂譜照片", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    try:
        img_bytes = uploaded_file.read()
        pil_orig = Image.open(io.BytesIO(img_bytes)).convert('RGB')
        
        # 用於顯示預覽 (NumPy 格式)
        st.image(np.array(pil_orig), caption="原始照片預覽", use_column_width=True)

        if st.button("🚀 生成數位淨化新譜"):
            with st.spinner('正在分析並淨化譜面，請稍候...'):
                
                # --- A. 影像淨化與去背 (生成黑白線稿) ---
                # 1. 將圖片轉為 OpenCV 格式
                img_opencv = cv2.cvtColor(np.array(pil_orig), cv2.COLOR_RGB2BGR)
                
                # 2. 轉為灰階
                gray = cv2.cvtColor(img_opencv, cv2.COLOR_BGR2GRAY)
                
                # 3. 使用自適應二值化 (Adaptive Thresholding) 移除背景雜訊
                # 這是生成黑白譜的關鍵
                clean_mask = cv2.adaptiveThreshold(
                    gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                    cv2.THRESH_BINARY, 115, 20
                )
                
                # 4. 將淨化後的黑白線稿轉回 PIL 格式
                # 這就是我們的「新數位畫布」
                pil_clean = Image.fromarray(clean_mask).convert('RGB')
                
                # --- B. AI 音符提取與更新 ---
                results = reader.readtext(img_opencv)
                
                draw_new = ImageDraw.Draw(pil_clean)
                shift = get_transpose_info(target_instr)
                count = 0
                
                for (bbox, text, prob) in results:
                    cleaned_text = "".join([c for c in text if c.isdigit()])
                    if cleaned_text and prob > 0.3:
                        new_text = "".join([transpose_numbered_note(c, shift) for c in cleaned_text])
                        
                        # 使用安全的繪圖函式，將舊音符在淨化譜上「塗白」，再疊加新紅字
                        safe_draw_text_and_rect(draw_new, bbox, new_text)
                        count += 1
                
                # --- C. 顯示新生成的數位淨化新譜 ---
                st.subheader(f"✅ 生成 {target_instr} 專用乾淨新譜！")
                st.image(np.array(pil_clean), caption="生成的新譜預覽", use_column_width=True)
                
                buf = io.BytesIO()
                pil_clean.save(buf, format="PNG")
                st.download_button("📥 下載淨化新譜", buf.getvalue(), "cleaned_transposed.png", "image/png")
                
    except Exception as e:
        st.error(f"程式執行發生嚴重錯誤：{e}")

else:
    st.info("請上傳樂譜照片開始使用。照片光線充足、正拍，辨識效果越好。")
