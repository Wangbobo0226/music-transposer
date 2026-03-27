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

# --- 2. 針對範本 Bb36e564c1fa1f3c3db.jpg 的最終極精密參數 ---
# 根據最新回饋，Y 軸再往下修正一點點
GRID_ORIGIN_X = 96   
GRID_ORIGIN_Y = 220  # 從 215 降到 220，讓數字更穩定地待在格子中央
COL_SPACING = 68.5   
ROW_SPACING = 162    
TOTAL_COLS = 14      

# --- 3. 網頁配置 ---
st.set_page_config(page_title="專業級對齊轉譜器", layout="centered")
st.title("🎷 豎笛專業轉譜：終極校正版")

@st.cache_resource
def load_ocr_reader():
    return easyocr.Reader(['en'], gpu=False)

reader = load_ocr_reader()

TEMPLATE_FILE = "Bb36e564c1fa1f3c3db.jpg"

uploaded_file = st.file_uploader("上傳手寫簡譜照片 (請盡量拍正、不要斜拍)", type=["jpg", "jpeg", "png"])

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
            
            if st.button("🚀 生成最終校正電子譜"):
                with st.spinner('正在進行極精密對位...'):
                    img_cv = cv2.cvtColor(np.array(pil_input), cv2.COLOR_RGB2BGR)
                    results = reader.readtext(img_cv)
                    
                    try:
                        # 使用更顯眼的粗體感
                        font = ImageFont.load_default(size=64)
                    except:
                        font = ImageFont.load_default()

                    count = 0
                    # 先將所有音符收集起來，進行初步排序防止跳格
                    found_notes = []
                    for (bbox, text, prob) in results:
                        cleaned = "".join([c for c in text if c.isdigit()])
                        if cleaned and prob > 0.15: # 稍微調低閾值，避免漏字
                            rx = (bbox[0][0] + bbox[2][0]) / 2 / orig_w
                            ry = (bbox[0][1] + bbox[2][1]) / 2 / orig_h
                            found_notes.append({'text': cleaned, 'rx': rx, 'ry': ry})
                    
                    # 依高度排序
                    found_notes = sorted(found_notes, key=lambda x: x['ry'])

                    for item in found_notes:
                        raw_tx = item['rx'] * temp_w
                        raw_ty = item['ry'] * temp_h
                        
                        # 格點吸附邏輯 (加入微調)
                        col_idx = round((raw_tx - GRID_ORIGIN_X) / COL_SPACING)
                        row_idx = round((raw_ty - GRID_ORIGIN_Y) / ROW_SPACING)
                        
                        col_idx = max(0, min(TOTAL_COLS - 1, col_idx))
                        row_idx = max(0, min(9, row_idx))

                        for i, char in enumerate(item['text']):
                            current_col = col_idx + i
                            if current_col >= TOTAL_COLS: break 
                            
                            final_x = GRID_ORIGIN_X + (current_col * COL_SPACING)
                            final_y = GRID_ORIGIN_Y + (row_idx * ROW_SPACING)
                            
                            trans_note = transpose_for_clarinet(char)
                            # 使用稍微更深的紅色，增加 stroke_width=1 讓它更扎實
                            draw.text((final_x, final_y), trans_note, fill=(160, 0, 0), 
                                      font=font, stroke_width=1, anchor="mm")
                            count += 1
                    
                    if count > 0:
                        st.success(f"✅ 校正完畢！已排版 {count} 個音符。")
                        st.image(np.array(pil_temp), use_container_width=True)
                        
                        buf = io.BytesIO()
                        pil_temp.save(buf, format="PNG")
                        st.download_button("📥 下載最終版電子譜", buf.getvalue(), "Final_Clarinet_Score.png", "image/png")
                    else:
                        st.warning("未能識別有效音符。")
                        
        except Exception as e:
            st.error(f"執行錯誤：{e}")
