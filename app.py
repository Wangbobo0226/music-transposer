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

# --- 2. 數位範本精密座標 ---
GRID_X_START = 100   # 第一格中心
GRID_Y_START = 222   # 第一行中心
COL_GAP = 68.5       # 格子間距
ROW_GAP = 162.2      # 行間距
COLS_PER_ROW = 14    # 每行格數

# --- 3. 網頁配置 ---
st.set_page_config(page_title="專業格式對位轉譜器", layout="centered")
st.title("🎼 豎笛專業轉譜：行對行精準校正版")

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
            draw = ImageDraw.Draw(pil_temp)
            
            if st.button("🚀 執行格式對位生成"):
                with st.spinner('正在分析行間距並校正格式...'):
                    img_cv = cv2.cvtColor(np.array(pil_input), cv2.COLOR_RGB2BGR)
                    results = reader.readtext(img_cv)
                    
                    try:
                        font = ImageFont.load_default(size=60)
                    except:
                        font = ImageFont.load_default()

                    # 1. 將辨識結果依照 Y 座標分行 (容許 80 像素內的誤差視為同一行)
                    raw_data = []
                    for (bbox, text, prob) in results:
                        cleaned = "".join([c for c in text if c.isdigit()])
                        if cleaned and prob > 0.15:
                            cx = (bbox[0][0] + bbox[2][0]) / 2
                            cy = (bbox[0][1] + bbox[2][1]) / 2
                            raw_data.append({'text': cleaned, 'x': cx, 'y': cy})
                    
                    if not raw_data:
                        st.warning("辨識不到數字，請確保光線充足且字跡清晰。")
                    else:
                        # 核心邏輯：依照高度排序後，人為判斷行號
                        raw_data.sort(key=lambda k: k['y'])
                        
                        rows = []
                        if raw_data:
                            current_row = [raw_data[0]]
                            for i in range(1, len(raw_data)):
                                # 如果跟上一個音符的高度差小於原圖高度的 8%，視為同一行
                                if raw_data[i]['y'] - raw_data[i-1]['y'] < (orig_h * 0.08):
                                    current_row.append(raw_data[i])
                                else:
                                    rows.append(sorted(current_row, key=lambda k: k['x']))
                                    current_row = [raw_data[i]]
                            rows.append(sorted(current_row, key=lambda k: k['x']))

                        # 2. 填入範本 (行對行)
                        count = 0
                        for row_idx, row_content in enumerate(rows):
                            if row_idx >= 10: break # 範本只有 10 行
                            
                            current_col_ptr = 0
                            for item in row_content:
                                for char in item['text']:
                                    if current_col_ptr >= COLS_PER_ROW: break
                                    
                                    # 計算該行該格的精確中心
                                    draw_x = GRID_X_START + (current_col_ptr * COL_GAP)
                                    draw_y = GRID_Y_START + (row_idx * ROW_GAP)
                                    
                                    trans_note = transpose_for_clarinet(char)
                                    draw.text((draw_x, draw_y), trans_note, fill=(180, 0, 0), 
                                              font=font, stroke_width=1, anchor="mm")
                                    current_col_ptr += 1
                                    count += 1
                        
                        st.success(f"✅ 對位完成！已根據手寫行數排版 {count} 個音符。")
                        st.image(np.array(pil_temp), use_container_width=True)
                        
                        buf = io.BytesIO()
                        pil_temp.save(buf, format="PNG")
                        st.download_button("📥 下載對位修正譜", buf.getvalue(), "Aligned_Clarinet_Score.png", "image/png")
                        
        except Exception as e:
            st.error(f"執行錯誤：{e}")
