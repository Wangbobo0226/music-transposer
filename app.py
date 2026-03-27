import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
import easyocr
# 確保你已經建立 utils.py 並包含 get_transpose_info 與 transpose_numbered_note
from utils import get_transpose_info, transpose_numbered_note

# --- 1. 網頁初始設定 ---
st.set_page_config(page_title="簡譜自動轉調助手", page_icon="🎷", layout="wide")

st.title("🎼 簡譜自動轉調助手")
st.markdown("""
本工具採用 AI 辨識技術，自動將**簡譜**移調至目標樂器音域。
1. 設定左側樂器 2. 上傳譜面照片 3. 點擊開始轉換。
""")

# --- 2. 側邊欄設定 ---
st.sidebar.header("🔧 轉換設定")
instrument = st.sidebar.selectbox(
    "選擇你的目標樂器",
    ["豎笛 (Bb)", "中音薩克斯風 (Eb)", "小號 (Bb)", "長笛 (C)"]
)

# --- 3. 初始化 AI 辨識器 (快取處理，避免重複載入) ---
@st.cache_resource
def load_ocr_reader():
    # 預載英文與簡體中文模型(簡譜常用)
    return easyocr.Reader(['en', 'ch_sim'], gpu=False)

reader = load_ocr_reader()

# --- 4. 檔案上傳區 ---
uploaded_file = st.file_uploader("請上傳樂譜照片 (JPG/PNG)...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # 修正：加上 np. 字首
    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
    opencv_image = cv2.imdecode(file_bytes, 1)
    
    # 轉換為 PIL 供顯示與繪圖
    pil_image = Image.open(io.BytesIO(file_bytes)).convert('RGB')
    draw = ImageDraw.Draw(pil_image)
    width, height = pil_image.size

    st.image(pil_image, caption="原始樂譜預覽", use_container_width=True)

    # --- 5. 執行按鈕 ---
    if st.button("🚀 開始自動移調"):
        with st.spinner('AI 正在分析譜面，請稍候 (初次執行較慢)...'):
            
            # 獲取移調數值
            shift = get_transpose_info(instrument)
            
            # 執行 OCR 辨識
            ocr_results = reader.readtext(opencv_image)
            
            # 設定字體 (嘗試使用系統字體，若無則使用預設)
            try:
                # 針對 Streamlit Cloud 的 Linux 環境常用路徑
                font_size = max(20, int(height * 0.025)) 
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
            except:
                font = ImageFont.load_default()

            count = 0
            for (bbox, text, prob) in ocr_results:
                # 只處理包含數字的文字塊 (簡譜核心)
                cleaned_text = "".join([c for c in text if c.isdigit()])
                
                if cleaned_text and prob > 0.3:
                    # 計算移調後的數字
                    new_text = ""
                    for char in cleaned_text:
                        new_text += transpose_numbered_note(char, shift)
                    
                    # 獲取座標 (左上角與右下角)
                    top_left = tuple(map(int, bbox[0]))
                    bottom_right = tuple(map(int, bbox[2]))
                    
                    # 1. 覆蓋白色背景 (遮住舊數字)
                    draw.rectangle([top_left, bottom_right], fill="white")
                    
                    # 2. 寫上紅色新數字
                    draw.text(top_left, new_text, font=font, fill=(255, 0, 0))
                    count += 1
            
            # --- 6. 顯示結果 ---
            st.success(f"轉換完成！成功處理了 {count} 個音符塊。")
            st.image(pil_image, caption=f"移調後的 {instrument} 專用譜", use_container_width=True)
            
            # 準備下載檔案
            buf = io.BytesIO()
            pil_image.save(buf, format="PNG")
            byte_im = buf.getvalue()
            
            st.download_button(
                label="📥 下載轉調後的圖片",
                data=byte_im,
                file_name=f"transposed_{instrument}.png",
                mime="image/png"
            )

else:
    st.info("👋 歡迎使用！請先上傳樂譜照片開始作業。")

# --- 頁尾 ---
st.divider()
st.caption("本工具僅供學術交流與改譜輔助使用。")
