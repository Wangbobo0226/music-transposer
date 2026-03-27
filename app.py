import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
import easyocr
import os

# --- 1. 豎笛移調與專業排版參數 ---
def transpose_for_clarinet(note_str):
    """固定為豎笛移調 (+2)"""
    try:
        if note_str.isdigit():
            val = int(note_str)
            new_val = (val + 2 - 1) % 7 + 1
            return str(new_val)
    except: pass
    return note_str

# 根據 Bb36e564c1fa1f3c3db.jpg 調整的座標參數
GRID_START_X = 65    # 第一格起始 X
GRID_START_Y = 135   # 第一列起始 Y
LINE_GAP = 162       # 每列行距
NOTE_GAP = 68        # 每個音符間距
NOTES_PER_LINE = 14  # 每行預計填入的音符數

# --- 2. 網頁設定 ---
st.set_page_config(page_title="專業簡譜生成器", layout="centered")
st.title("🎷 豎笛專用：數位專業簡譜排版")

@st.cache_resource
def load_ocr_reader():
    return easyocr.Reader(['en'], gpu=False)

reader = load_ocr_reader()

TEMPLATE_FILE = "Bb36e564c1fa1f3c3db.jpg"

uploaded_file = st.file_uploader("上傳手寫簡譜照片", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    if not os.path.exists(TEMPLATE_FILE):
        st.error(f"找不到範本檔案 {TEMPLATE_FILE}，請確認檔案已在 GitHub 根目錄中。")
    else:
        try:
            # 處理手寫原圖
            in_bytes = uploaded_file.read()
            nparr = np.frombuffer(in_bytes, np.uint8)
            img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # 準備數位畫布
            pil_temp = Image.open(TEMPLATE_FILE).convert('RGB')
            draw = ImageDraw.Draw(pil_temp)
            
            if st.button("🚀 生成專業放大版數位譜"):
                with st.spinner('正在進行 AI 辨識與精確排版...'):
                    results = reader.readtext(img_cv)
                    
                    # 1. 收集並排序音符 (先依高度 Y 排序分行，再依 X 排序)
                    raw_data = []
                    for (bbox, text, prob) in results:
                        cleaned = "".join([c for c in text if c.isdigit()])
                        if cleaned and prob > 0.2:
                            tx = (bbox[0][0] + bbox[2][0]) / 2
                            ty = (bbox[0][1] + bbox[2][1]) / 2
                            raw_data.append({'text': cleaned, 'x': tx, 'y': ty})
                    
                    # 排序邏輯：容許 30 像素內的誤差視為同一行
                    sorted_notes = sorted(raw_data, key=lambda k: (k['y'] // 30, k['x']))
                    
                    # 2. 載入字體並設定放大倍率
                    try:
                        # 嘗試載入較大的字體 (Streamlit 環境預設路徑)
                        font = ImageFont.load_default(size=45) 
                    except:
                        font = ImageFont.load_default()

                    # 3. 填入畫布
                    count = 0
                    for i, note in enumerate(sorted_notes):
                        trans_text = "".join([transpose_for_clarinet(c) for c in note['text']])
                        
                        line = i // NOTES_PER_LINE
                        col = i % NOTES_PER_LINE
                        
                        # 計算畫布座標
                        draw_x = GRID_START_X + (col * NOTE_GAP)
                        draw_y = GRID_START_Y + (line * LINE_GAP)
                        
                        # 繪製放大紅字，增加 stroke_width 讓字體更明顯
                        draw.text((draw_x, draw_y), trans_text, fill=(220, 20, 60), 
                                  font=font, stroke_width=1, anchor="mm") # anchor="mm" 確保中心對齊
                        count += 1
                        if line >= 9: break # 防止超過範本行數
                    
                    if count > 0:
                        st.success(f"✅ 成功生成！已排版 {count} 個音符。")
                        st.image(np.array(pil_temp), caption="生成的專業電子簡譜", use_container_width=True)
                        
                        # 提供下載
                        buf = io.BytesIO()
                        pil_temp.save(buf, format="PNG")
                        st.download_button("📥 下載專業電子譜", buf.getvalue(), "Clarinet_Sheet_Pro.png", "image/png")
                    else:
                        st.warning("辨識失敗，請上傳更清晰的照片。")
                        
        except Exception as e:
            st.error(f"執行錯誤：{e}")
