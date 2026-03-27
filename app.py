import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
import easyocr
import os

# --- 1. 移調與排版設定 ---
def transpose_for_clarinet(note_str):
    """固定為豎笛移調 (+2)"""
    try:
        if note_str.isdigit():
            val = int(note_str)
            # 簡譜 1-7 循環
            new_val = (val + 2 - 1) % 7 + 1
            return str(new_val)
    except: pass
    return note_str

# 數位專業簡譜範本的格子排版設定 (根據 Bb36e564c1fa1f3c3db.jpg 精確量測)
GRID_START_X = 50   # 第一行開頭 x 座標
GRID_START_Y = 120  # 第一行高度 y 座標
LINE_HEIGHT = 150   # 每行簡譜的高度差
NOTE_SPACING = 55   # 每個音符之間的距離 (視需求調整)
MAX_LINES = 10      # 範本上的總行數

# --- 2. 網頁介面 ---
st.set_page_config(page_title="專業數位簡譜轉譜器", layout="centered")
st.title("🎼 直排手寫稿轉橫排專業數位譜")
st.markdown("將直向手寫簡譜辨識後，自動重排並填入乾淨的橫向數位範本中 (固定豎笛 +2 調)。")

@st.cache_resource
def load_ocr_reader():
    return easyocr.Reader(['en'], gpu=False)

reader = load_ocr_reader()

# --- 3. 讀取專業簡譜範本底圖 ---
TEMPLATE_FILE = "Bb36e564c1fa1f3c3db.jpg" # 確保此檔案上傳至 GitHub

uploaded_file = st.file_uploader("第一步：上傳直排手寫簡譜照片", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    if not os.path.exists(TEMPLATE_FILE):
        st.error(f"⚠️ 找不到範本檔案 {TEMPLATE_FILE}，請確認已將該圖上傳至 GitHub 根目錄。")
    else:
        try:
            # 讀取手寫原圖
            input_bytes = uploaded_file.read()
            pil_input = Image.open(io.BytesIO(input_bytes)).convert('RGB')
            # 辨識前先將圖片轉 OpenCV 格式
            img_opencv = cv2.cvtColor(np.array(pil_input), cv2.COLOR_RGB2BGR)
            
            # 讀取專業簡譜範本底圖
            pil_temp = Image.open(TEMPLATE_FILE).convert('RGB')
            temp_w, temp_h = pil_temp.size
            
            if st.button("🚀 生成專業數位譜"):
                with st.spinner('正在精確排版並重新繪製...'):
                    # OCR 辨識
                    results = reader.readtext(img_opencv)
                    
                    all_notes = []
                    
                    # 將辨識結果依原圖高度 (Y座標) 從上到下排序
                    # 取得中心點 (x, y)
                    for (bbox, text, prob) in results:
                        cleaned = "".join([c for c in text if c.isdigit()])
                        if cleaned and prob > 0.3:
                            # 豎笛移調
                            transposed_txt = "".join([transpose_for_clarinet(c) for c in cleaned])
                            orig_y = (bbox[0][1] + bbox[2][1]) / 2
                            # 儲存音符和 Y 座標
                            all_notes.append({'text': transposed_txt, 'y': orig_y})
                    
                    # 從上到下重新排序音符
                    sorted_notes = sorted(all_notes, key=lambda n: n['y'])
                    
                    # 在新的畫布上繪製
                    draw = ImageDraw.Draw(pil_temp)
                    count = 0
                    
                    current_line = 0
                    current_x = GRID_START_X
                    
                    # 載入預設字體，並嘗試放大字體
                    try:
                        # 載入內建基礎字體，並設定較大字型
                        font = ImageFont.load_default(size=40)
                    except:
                        font = ImageFont.load_default()

                    for note in sorted_notes:
                        # 專業填譜核心邏輯：依照格子排版繪製，精確對齊並放大字體
                        # 依照格子座標排版繪製，水平對齊、垂直居中地填入
                        draw.text((current_x, GRID_START_Y + (current_line * LINE_HEIGHT)), 
                                  note['text'], fill=(255, 0, 0), font=font)
                        
                        # 移動到下一個音符位置
                        current_x += NOTE_SPACING
                        
                        # 換行檢查
                        if current_x > (temp_w - 50): # 接近右邊界
                            current_line += 1
                            current_x = GRID_START_X
                            if current_line >= MAX_LINES: # 超過總行數
                                break 
                        count += 1
                    
                    if count > 0:
                        st.success(f"✅ 完成！已數位化 {count} 個音符，並精確填入格子內。")
                        st.image(np.array(pil_temp), caption="重新排版後的專業數位簡譜", use_container_width=True)
                        
                        # 提供下載
                        buf = io.BytesIO()
                        pil_temp.save(buf, format="PNG")
                        st.download_button("📥 下載專業電子譜", buf.getvalue(), "Clarinet_Digital_Score.png", "image/png")
                    else:
                        st.warning("未能辨識到有效音符。")
                        
        except Exception as e:
            st.error(f"程式執行錯誤：{e}")
