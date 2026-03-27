import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
import easyocr
# 從你建立的另一個檔案匯入邏輯
from utils import get_transpose_info, transpose_numbered_note

# --- 網頁頁面設定 ---
st.set_page_config(page_title="簡譜自動轉調助手", page_icon="🎷")

st.title("🎼 簡譜自動轉調助手")
st.markdown("""
這個工具可以幫助你將**鋼琴簡譜**快速轉換為**豎笛 (Bb)** 或 **薩克斯風 (Eb)使用**的譜！
1. 在左側選擇你的樂器。
2. 上傳簡譜圖片（如：JPG/PNG）。
3. 點擊「開始轉換」即可看到移調後的結果。
""")

# --- 側邊欄設定 ---
st.sidebar.header("🔧 轉換設定")
instrument = st.sidebar.selectbox(
    "1. 選擇你的目標樂器",
    ["豎笛 (Bb)", "中音薩克斯風 (Eb)", "小號 (Bb)", "長笛 (C)"]
)

show_original = st.sidebar.checkbox("顯示原始圖片", value=True)

# --- 初始化 EasyOCR 辨識器 (只初始化一次) ---
@st.cache_resource
def load_ocr_reader():
    # 我們設定只辨識簡譜數字與部分常用字，這會提高精準度
    return easyocr.Reader(['en', 'ch_sim'], gpu=False) # 為了免費伺服器穩健，gpu設為False

reader = load_ocr_reader()

# --- 檔案上傳 ---
uploaded_file = st.file_uploader("請上傳樂譜照片...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # 將上傳的檔案轉為 OpenCV 格式以便後續 AI 處理
    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=uint8)
    opencv_image = cv2.imdecode(file_bytes, 1)
    
    # 轉回 PIL 格式供 Streamlit 顯示與繪圖
    pil_image = Image.open(uploaded_file).convert('RGB')
    width, height = pil_image.size

    if show_original:
        st.image(pil_image, caption="你上傳的原始樂譜", use_column_width=True)

    # --- 執行按鈕 ---
    if st.button("🚀 開始自動移調"):
        with st.spinner('AI 正在分析樂譜並進行移調...'):
            
            # 獲取該樂器需要移動的半音數
            shift = get_transpose_info(instrument)
            
            # --- 核心辨識 (真實 EasyOCR) ---
            # 辨識圖片中的所有文字與座標
            results = reader.readtext(opencv_image)
            
            # 建立一個繪圖對象，在原圖上做記號
            draw = ImageDraw.Draw(pil_image)
            
            # 註：這裡我們嘗試動態設定字體大小 (約為圖片高度的 2%)
            # 為了能顯示中文調號，需要使用支援中文的字體檔路徑 (免費伺服器通用路徑)
            try:
                font_size = int(height * 0.02)
                # 這裡是一個常見的 Linux 免費中文核心字體路徑
                font = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", font_size)
            except Exception as e:
                # 若找不到字體，則回退到預設字體（不支援中文，但可顯示數字）
                font = ImageFont.load_default()
            
            count = 0
            for (bbox, text, prob) in results:
                # 清理文字：只保留簡譜數字 1~7 與升降號 #, b
                cleaned_text = "".join([c for c in text if c.isdigit() or c in ['#', 'b']])
                
                # 如果辨識到的是數字，或者是調號標註($1 = ^bE$)
                if cleaned_text and prob > 0.3: # 篩選掉低精準度的辨識
                    
                    # 計算新音符 (呼叫 utils.py 邏輯)
                    new_note = transpose_numbered_note(cleaned_text, shift)
                    
                    # 獲取原始文字的中心座標與大小
                    top_left = tuple(map(int, bbox[0]))
                    bottom_right = tuple(map(int, bbox[2]))
                    x = top_left[0]
                    y = top_left[1]
                    w = bottom_right[0] - top_left[0]
                    h = bottom_right[1] - top_left[1]
                    
                    # --- 視覺化覆蓋 ---
                    # 1. 畫一個跟原文字一樣大的白色矩形，覆蓋掉舊音符
                    # 我們稍微放大一圈白色方塊，確保覆蓋完全
                    draw.rectangle([top_left[0]-2, top_left[1]-2, bottom_right[0]+2, bottom_right[1]+2], fill=(255, 255, 255))
                    
                    # 2. 在白色方塊上印上移調後的數字 (紅色)
                    # 我們稍微調整座標，讓新的紅色數字居中
                    text_x = x + (w // 2) - (font.getsize(new_note)[0] // 2)
                    text_y = y + (h // 2) - (font.getsize(new_note)[1] // 2)
                    draw.text((text_x, text_y), new_note, font=font, fill=(255, 0, 0))
                    
                    count += 1
            
            # --- 顯示結果 ---
            st.subheader(f"✅ 針對 {instrument} 的移調完成！")
            st.success(f"已辨識並移調了 {count} 個音符。紅字為新的音符。")
            
            st.image(pil_image, caption=f"移調標註預覽 (紅字為針對 {instrument} 移調後的音符)", use_column_width=True)
            
            # --- 下載功能 ---
            buf = io.BytesIO()
            pil_image.save(buf, format="PNG")
            byte_im = buf.getvalue()
            
            st.download_button(
                label="📥 下載轉調後的圖片",
                data=byte_im,
                file_name=f"transposed_score_{instrument}.png",
                mime="image/png"
            )

else:
    st.info("💡 提示：請先在上方上傳一張清晰的簡譜照片。")

# --- 頁尾 ---
st.divider()
st.caption("Made with ❤️ for Musicians | Powered by Streamlit & Python")

# --- 頁尾 ---
st.divider()
st.caption("Made with ❤️ for Musicians | Powered by Streamlit & Python")
