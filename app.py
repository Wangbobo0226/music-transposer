import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw
import io
import easyocr
# 確保你的 utils.py 檔案在同一個資料夾內
try:
    from utils import get_transpose_info, transpose_numbered_note
except ImportError:
    st.error("找不到 utils.py 檔案，請確認它已上傳至 GitHub。")

# --- 1. 網頁配置 (設定簡潔介面) ---
st.set_page_config(page_title="簡譜轉調助手", layout="centered")

st.title("🎼 簡譜自動轉調助手")
st.markdown("上傳簡譜照片，AI 將自動辨識數字並標註移調後的結果（紅字）。")

# --- 2. 初始化 AI 辨識器 (使用快取避免重複載入) ---
@st.cache_resource
def load_ocr_reader():
    # 使用英文模型辨識數字最為精準且節省記憶體
    return easyocr.Reader(['en'], gpu=False)

# 顯示載入狀態
try:
    reader = load_ocr_reader()
except Exception as e:
    st.error(f"AI 引擎啟動失敗，請重新整理網頁。錯誤原因: {e}")

# --- 3. 側邊欄設定 ---
st.sidebar.header("🔧 設定")
target_instrument = st.sidebar.selectbox(
    "選擇你的樂器",
    ["豎笛 (Bb)", "中音薩克斯風 (Eb)", "小號 (Bb)", "長笛 (C)"],
    key="instrument_select"
)

# --- 4. 檔案上傳區 ---
uploaded_file = st.file_uploader("請上傳樂譜照片 (JPG/PNG)", type=["jpg", "jpeg", "png"], key="file_up")

if uploaded_file is not None:
    # 讀取圖片並修正 np.uint8 錯誤
    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
    opencv_img = cv2.imdecode(file_bytes, 1)
    
    # 轉換為 PIL 供繪圖與顯示
    pil_img = Image.open(io.BytesIO(file_bytes)).convert('RGB')
    
    # 顯示原始圖片 (加上 key 防止渲染錯誤)
    st.image(pil_img, caption="原始樂譜", use_container_width=True, key="original_view")

    # --- 5. 轉換邏輯 ---
    if st.button("🚀 開始自動移調", key="process_btn"):
        with st.spinner('AI 正在讀取譜面數字...'):
            
            # 獲取移調數值 (來自 utils.py)
            try:
                shift = get_transpose_info(target_instrument)
            except:
                shift = 0
            
            # 執行 OCR 辨識
            results = reader.readtext(opencv_img)
            
            # 準備繪圖
            draw = ImageDraw.Draw(pil_img)
            
            count = 0
            for (bbox, text, prob) in results:
                # 過濾：只保留辨識結果中的數字
                cleaned = "".join([c for c in text if c.isdigit()])
                
                if cleaned and prob > 0.3:
                    # 計算移調後的新數字序列
                    new_text = ""
                    for char in cleaned:
                        new_text += transpose_numbered_note(char, shift)
                    
                    # 獲取座標 (左上角 p1 與 右下角 p2)
                    p1 = tuple(map(int, bbox[0]))
                    p2 = tuple(map(int, bbox[2]))
                    
                    # 先畫白色方塊遮住舊音符，再寫上紅色新音符
                    draw.rectangle([p1, p2], fill="white")
                    draw.text(p1, new_text, fill=(255, 0, 0))
                    count += 1
            
            # --- 6. 顯示結果 ---
            if count > 0:
                st.success(f"成功處理 {count} 個音符塊！")
                st.image(pil_img, caption=f"針對 {target_instrument} 移調後的結果", use_container_width=True, key="result_view")
                
                # 下載功能
                buf = io.BytesIO()
                pil_img.save(buf, format="PNG")
                st.download_button(
                    label="📥 下載移調後的樂譜",
                    data=buf.getvalue(),
                    file_name=f"transposed_{target_instrument}.png",
                    mime="image/png",
                    key="download_btn"
                )
            else:
                st.warning("未能辨識到清楚的數字，請確保照片光線充足並正對拍攝。")

else:
    st.info("👋 你好！請上傳一張簡譜照片來開始吧。")

# --- 頁尾 ---
st.divider()
st.caption("本工具由 Streamlit & EasyOCR 強力驅動。")
