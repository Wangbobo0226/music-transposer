import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
import easyocr
import os

# --- 1. 豎笛移調邏輯 ---
def transpose_for_clarinet(note_str):
    try:
        if note_str.isdigit():
            val = int(note_str)
            return str((val + 2 - 1) % 7 + 1)
    except: pass
    return note_str

# --- 2. 專業範本座標參數 ---
GRID_ORIGIN_X = 98    # 橫向起始偏移
GRID_ORIGIN_Y = 222   # 垂直起始偏移 (讓字體往下坐)
COL_SPACING = 68.4    # 每格寬度
ROW_SPACING = 162.2   # 每行高度
TOTAL_COLS = 14       # 每行 14 格

# --- 3. 網頁配置 ---
st.set_page_config(page_title="專業級對齊轉譜器", layout="centered")
st.title("🎷 豎笛專業轉譜：徹底解決黏字版")

@st.cache_resource
def load_ocr_reader():
    return easyocr.Reader(['en'], gpu=False)

reader = load_ocr_reader()

TEMPLATE_FILE = "Bb36e564c1fa1f3c3db.jpg"

uploaded_file = st.file_uploader("上傳手寫簡譜照片", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    if not os.path.exists(TEMPLATE_FILE):
        st.error(f"找不到範本檔案 {TEMPLATE_FILE}")
    else:
        try:
            in_bytes = uploaded_file.read()
            pil_input = Image.open(io.BytesIO(in_bytes)).convert('RGB')
            orig_w, orig_h = pil_input.size
            
            pil_temp = Image.open(TEMPLATE_FILE).convert('RGB')
            temp_w, temp_h = pil_temp.size
            draw = ImageDraw.Draw(pil_temp)
            
            if st.button("🚀 執行拆解並生成數位譜"):
                with st.spinner('正在逐字拆解並精確填格...'):
                    img_cv = cv2.cvtColor(np.array(pil_input), cv2.COLOR_RGB2BGR)
                    results = reader.readtext(img_cv)
                    
                    try:
                        font = ImageFont.load_default(size=65)
                    except:
                        font = ImageFont.load_default()

                    count = 0
                    # 依據 Y 軸高度排序，避免亂序
                    sorted_results = sorted(results, key=lambda x: (x[0][0][1] // 50, x[0][0][0]))

                    for (bbox, text, prob) in sorted_results:
                        cleaned = "".join([c for c in text if c.isdigit()])
                        if cleaned and prob > 0.15:
                            # 取得這組數字在手寫稿上的起始位置
                            rx = bbox[0][0] / orig_w
                            ry = (bbox[0][1] + bbox[2][1]) / 2 / orig_h
                            
                            # 換算成範本格子座標
                            base_col = round((rx * temp_w - GRID_ORIGIN_X) / COL_SPACING)
                            row_idx = round((ry * temp_h - GRID_ORIGIN_Y) / ROW_SPACING)
                            
                            row_idx = max(0, min(9, row_idx))

                            # 【核心修正】逐字填入不同格子
                            for i, char in enumerate(cleaned):
                                current_col = base_col + i
                                if current_col >= TOTAL_COLS: break 
                                
                                # 強制將每個數字鎖定在該格的中心
                                final_x = GRID_ORIGIN_X + (current_col * COL_SPACING)
                                final_y = GRID_ORIGIN_Y + (row_idx * ROW_SPACING)
                                
                                trans_note = transpose_for_clarinet(char)
                                # 繪製紅字，確保每個字都是獨立位置
                                draw.text((final_x, final_y), trans_note, fill=(180, 0, 0), 
                                          font=font, stroke_width=1, anchor="mm")
                                count += 1
                    
                    if count > 0:
                        st.success(f"✅ 成功！已將 {count} 個音符拆解並對齊。")
                        st.image(np.array(pil_temp), use_container_width=True)
                        
                        buf = io.BytesIO()
                        pil_temp.save(buf, format="PNG")
                        st.download_button("📥 下載完美電子譜", buf.getvalue(), "Perfect_Clarinet_Score.png", "image/png")
                    else:
                        st.warning("未能辨識。")
                        
        except Exception as e:
            st.error(f"執行錯誤：{e}")
