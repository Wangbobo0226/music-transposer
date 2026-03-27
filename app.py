import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
import easyocr
import os

# --- 1. 豎笛移調邏輯 (+2) ---
def transpose_for_clarinet(note_str):
    try:
        if note_str.isdigit():
            val = int(note_str)
            return str((val + 2 - 1) % 7 + 1)
    except: pass
    return note_str

# --- 2. 專業範本 Bb36e564c1fa1f3c3db.jpg 的極精密座標定義 ---
# 根據你上傳的 image_f37efd，我將 Y 座標從 190 修正到 215，讓它更往下移一點
GRID_ORIGIN_X = 95   # 稍微往右移
GRID_ORIGIN_Y = 215  # 顯著下調，確保進入格線中心
COL_SPACING = 68.5   
ROW_SPACING = 162    
TOTAL_COLS = 14      

# --- 3. 網頁配置 ---
st.set_page_config(page_title="專業級對齊轉譜器", layout="centered")
st.title("🎷 豎笛專業轉譜：精密置中最終版")

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
            
            if st.button("🚀 生成精密置中電子譜"):
                with st.spinner('正在進行最終座標對位...'):
                    img_cv = cv2.cvtColor(np.array(pil_input), cv2.COLOR_RGB2BGR)
                    results = reader.readtext(img_cv)
                    
                    try:
                        # 字體維持在 62，能清楚在格子內顯現
                        font = ImageFont.load_default(size=62)
                    except:
                        font = ImageFont.load_default()

                    count = 0
                    for (bbox, text, prob) in results:
                        cleaned = "".join([c for c in text if c.isdigit()])
                        if cleaned and prob > 0.2:
                            rx = (bbox[0][0] + bbox[2][0]) / 2 / orig_w
                            ry = (bbox[0][1] + bbox[2][1]) / 2 / orig_h
                            
                            raw_tx = rx * temp_w
                            raw_ty = ry * temp_h
                            
                            col_idx = round((raw_tx - GRID_ORIGIN_X) / COL_SPACING)
                            row_idx = round((raw_ty - GRID_ORIGIN_Y) / ROW_SPACING)
                            
                            col_idx = max(0, min(TOTAL_COLS - 1, col_idx))
                            row_idx = max(0, min(9, row_idx))

                            for i, char in enumerate(cleaned):
                                current_col = col_idx + i
                                if current_col >= TOTAL_COLS: break 
                                
                                final_x = GRID_ORIGIN_X + (current_col * COL_SPACING)
                                final_y = GRID_ORIGIN_Y + (row_idx * ROW_SPACING)
                                
                                trans_note = transpose_for_clarinet(char)
                                # 使用深紅色、置中對齊
                                draw.text((final_x, final_y), trans_note, fill=(180, 0, 0), 
                                          font=font, stroke_width=1, anchor="mm")
                                count += 1
                    
                    if count > 0:
                        st.success(f"✅ 生成完畢！音符已精密對準格位中心。")
                        st.image(np.array(pil_temp), use_container_width=True)
                        
                        buf = io.BytesIO()
                        pil_temp.save(buf, format="PNG")
                        st.download_button("📥 下載完美電子譜", buf.getvalue(), "Perfect_Clarinet_Score.png", "image/png")
                    else:
                        st.warning("未能辨識。")
                        
        except Exception as e:
            st.error(f"執行錯誤：{e}")
