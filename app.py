import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
import easyocr
import os

# --- 1. 移調邏輯 ---
def transpose_for_clarinet(note_str):
    try:
        if note_str.isdigit():
            val = int(note_str)
            return str((val + 2 - 1) % 7 + 1)
    except: pass
    return note_str

# --- 2. 座標參數 ---
GRID_X_START = 100   
GRID_Y_START = 222   
COL_GAP = 68.5       
ROW_GAP = 162.2      
COLS_PER_ROW = 14    

# --- 3. 網頁配置 ---
st.set_page_config(page_title="專業格式校正器", layout="centered")
st.title("🎼 豎笛轉譜：1:1 格式對應版")

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
            
            if st.button("🚀 生成 1:1 對位電子譜"):
                with st.spinner('正在分析原始格式位置...'):
                    img_cv = cv2.cvtColor(np.array(pil_input), cv2.COLOR_RGB2BGR)
                    results = reader.readtext(img_cv)
                    
                    try:
                        font = ImageFont.load_default(size=60)
                    except:
                        font = ImageFont.load_default()

                    count = 0
                    for (bbox, text, prob) in results:
                        cleaned = "".join([c for c in text if c.isdigit()])
                        if cleaned and prob > 0.15:
                            # 1. 計算在原圖中的百分比位置
                            rx = (bbox[0][0] + bbox[2][0]) / 2 / orig_w
                            ry = (bbox[0][1] + bbox[2][1]) / 2 / orig_h
                            
                            # 2. 映射到電子譜的大約座標
                            target_x_raw = rx * temp_w
                            target_y_raw = ry * temp_h
                            
                            # 3. 【核心修正】尋找最接近的格子索引
                            col_idx = round((target_x_raw - GRID_X_START) / COL_GAP)
                            row_idx = round((target_y_raw - GRID_Y_START) / ROW_GAP)
                            
                            # 限制範圍
                            row_idx = max(0, min(9, row_idx))
                            col_idx = max(0, min(COLS_PER_ROW - 1, col_idx))

                            # 4. 逐字填入，若是連寫則自動往後一格
                            for i, char in enumerate(cleaned):
                                final_col = col_idx + i
                                if final_col >= COLS_PER_ROW: break
                                
                                draw_x = GRID_X_START + (final_col * COL_GAP)
                                draw_y = GRID_Y_START + (row_idx * ROW_GAP)
                                
                                trans_note = transpose_for_clarinet(char)
                                draw.text((draw_x, draw_y), trans_note, fill=(180, 0, 0), 
                                          font=font, stroke_width=1, anchor="mm")
                                count += 1
                    
                    if count > 0:
                        st.success(f"✅ 對位完成！已依照原始位置填入 {count} 個音符。")
                        st.image(np.array(pil_temp), use_container_width=True)
                        
                        buf = io.BytesIO()
                        pil_temp.save(buf, format="PNG")
                        st.download_button("📥 下載對位修正譜", buf.getvalue(), "Accurate_Format_Score.png", "image/png")
                        
        except Exception as e:
            st.error(f"執行錯誤：{e}")
