import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
import easyocr
import os

# --- 1. 專業移調邏輯 ---
def transpose_for_clarinet(note_str):
    """固定為豎笛移調 (+2)，並處理 1-7 循環"""
    try:
        if note_str.isdigit():
            val = int(note_str)
            new_val = (val + 2 - 1) % 7 + 1
            return str(new_val)
    except: pass
    return note_str

# --- 2. 針對範本 Bb36e564c1fa1f3c3db.jpg 的精確座標參數 ---
GRID_START_X = 60    # 第一格中心 X
GRID_START_Y = 160   # 第一列中心 Y
LINE_GAP = 162       # 每列垂直行距
NOTE_GAP = 68        # 每個單獨數字的水平間距
NOTES_PER_LINE = 14  # 每行橫向能容納的數字數量

# --- 3. 網頁配置 ---
st.set_page_config(page_title="專業數位轉譜系統", layout="centered")
st.title("🎷 豎笛專業簡譜排版 (修正重疊版)")

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
            nparr = np.frombuffer(in_bytes, np.uint8)
            img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            pil_temp = Image.open(TEMPLATE_FILE).convert('RGB')
            draw = ImageDraw.Draw(pil_temp)
            
            if st.button("🚀 生成清晰專業譜"):
                with st.spinner('正在分析並逐字排版中...'):
                    results = reader.readtext(img_cv)
                    
                    # 1. 提取音符並記錄座標
                    raw_list = []
                    for (bbox, text, prob) in results:
                        cleaned = "".join([c for c in text if c.isdigit()])
                        if cleaned and prob > 0.2:
                            # 記錄這組數字的中心 Y 座標用於分行排序
                            cy = (bbox[0][1] + bbox[2][1]) / 2
                            cx = (bbox[0][0] + bbox[2][0]) / 2
                            raw_list.append({'text': cleaned, 'x': cx, 'y': cy})
                    
                    # 2. 排序：先分行，行內由左至右
                    sorted_raw = sorted(raw_list, key=lambda k: (k['y'] // 40, k['x']))
                    
                    # 3. 拆解字串：將 "3321" 拆成 ['3','3','2','1']
                    final_notes = []
                    for item in sorted_raw:
                        for char in item['text']:
                            final_notes.append(transpose_for_clarinet(char))
                    
                    # 4. 字體設定 (較大且清晰)
                    try:
                        font = ImageFont.load_default(size=60)
                    except:
                        font = ImageFont.load_default()

                    # 5. 填入範本格子
                    count = 0
                    for i, note in enumerate(final_notes):
                        line_idx = i // NOTES_PER_LINE
                        col_idx = i % NOTES_PER_LINE
                        
                        if line_idx >= 10: break # 超過範本行數
                        
                        # 計算每個「獨立數字」的精確座標
                        target_x = GRID_START_X + (col_idx * NOTE_GAP)
                        target_y = GRID_START_Y + (line_idx * LINE_GAP)
                        
                        # 繪製：深紅色、置中對齊
                        draw.text((target_x, target_y), note, fill=(180, 0, 0), 
                                  font=font, stroke_width=1, anchor="mm")
                        count += 1
                    
                    if count > 0:
                        st.success(f"✅ 完成！已排版 {count} 個音符。")
                        st.image(np.array(pil_temp), caption="生成的專業電子譜", use_container_width=True)
                        
                        buf = io.BytesIO()
                        pil_temp.save(buf, format="PNG")
                        st.download_button("📥 下載此專業電子譜", buf.getvalue(), "Pro_Clarinet_Sheet.png", "image/png")
                    else:
                        st.warning("未能辨識音符。")
                        
        except Exception as e:
            st.error(f"執行錯誤：{e}")
