import streamlit as st
import cv2
import numpy as np
from PIL import Image
import easyocr
from utils import convert_sheet_music, process_jianpu_ocr
import re

st.set_page_config(page_title="簡譜移調轉換器 (AI 最終強化版)", page_icon="🎵", layout="wide")

# --- 網頁記憶體 (Session State) 初始化 ---
if 'ocr_scanned_text' not in st.session_state:
    st.session_state.ocr_scanned_text = None

# --- 初始化 EasyOCR 模型 ---
@st.cache_resource
def load_ocr_model():
    # 載入模型，關閉 GPU 節省資源，適合雲端環境
    return easyocr.Reader(['ch_tra', 'en'], gpu=False)

def reconstruct_layout(ocr_results):
    """根據 EasyOCR 的座標結果重構初步排版"""
    if not ocr_results:
        return ""
    blocks = []
    for res in ocr_results:
        bbox = res[0]
        text = res[1]
        min_y = min([p[1] for p in bbox])
        max_y = max([p[1] for p in bbox])
        center_y = (min_y + max_y) / 2
        min_x = min([p[0] for p in bbox])
        blocks.append({'text': text, 'center_y': center_y, 'min_x': min_x})
        
    blocks.sort(key=lambda b: b['center_y'])
    lines = []
    current_line = []
    y_threshold = 15 
    for block in blocks:
        if not current_line:
            current_line.append(block)
        else:
            avg_y = sum([b['center_y'] for b in current_line]) / len(current_line)
            if abs(block['center_y'] - avg_y) < y_threshold:
                current_line.append(block)
            else:
                lines.append(current_line)
                current_line = [block]
    if current_line:
        lines.append(current_line)
        
    final_text = ""
    for line in lines:
        line.sort(key=lambda b: b['min_x'])
        line_text = "  ".join([b['text'] for b in line])
        final_text += line_text + "\n"
    return final_text

def format_jianpu_text(text):
    """將文字強制格式化為絕對標準的簡譜樣式： | 3 5 2 5 | 4 4 3 5 | """
    lines = text.split('\n')
    formatted_lines = []
    for line in lines:
        if not line.strip():
            continue
            
        # 1. 將常被誤認的字母轉為小節線 |
        line = re.sub(r'[Il]', '|', line)
        
        # 2. 先在所有小節線兩側強制加空格
        line = line.replace('|', ' | ')
        
        # 3. 將所有「多個連續空白」全部壓縮成「剛好一個空白」
        line = re.sub(r'\s+', ' ', line).strip()
        
        # 4. 濾網：合併多餘的小節線
        line = re.sub(r'\|\s*\|', '|', line)
        
        # 5. 濾網：刪除夾在小節線中無意義的孤單雜訊
        line = re.sub(r'\|\s*[\d\.\-]\s*\|', '|', line)
        
        # 6. 智慧補齊頭尾小節線
        chars = [c for c in line if c.strip()]
        if chars:
            music_char_count = sum(1 for c in chars if c.isdigit() or c in "-·|")
            if music_char_count / len(chars) > 0.3: 
                if not line.startswith('|'):
                    line = '| ' + line
                if not line.endswith('|'):
                    line = line + ' |'
        
        # 7. 再次確保格式對齊
        line = line.replace('|', ' | ')
        line = re.sub(r'\s+', ' ', line).strip()
        
        if line.replace('|', '').strip() == '':
            continue
        formatted_lines.append(line)
    return '\n'.join(formatted_lines)

# --- 側邊欄選單 ---
st.sidebar.title("⚙️ 功能選單")
menu_option = st.sidebar.radio(
    "請選擇您要使用的轉換方式：",
    ("📝 文字輸入轉換", "🖼️ 圖片 AI 智慧辨識 (EasyOCR)")
)

st.sidebar.divider()
st.sidebar.info("🎯 **最新更新**：已啟動「數字偵測白名單」，AI 將自動過濾非樂譜文字，大幅提升精準度！")

if menu_option == "📝 文字輸入轉換":
    st.title("📝 簡譜文字轉換")
    st.write("請直接輸入或貼上簡譜文字。")
    sheet_text = st.text_area("輸入簡譜：", placeholder="例如：| 3 5 2 5 | 4 4 3 5 |", height=300)
    if st.button("開始轉換", type="primary"):
        if sheet_text.strip():
            converted = convert_sheet_music(sheet_text)
            st.success("✅ 轉換成功！")
            st.code(converted, language="text") 
        else:
            st.warning("請先輸入簡譜文字。")

elif menu_option == "🖼️ 圖片 AI 智慧辨識 (EasyOCR)":
    st.title("🖼️ 樂譜圖片 AI 智慧偵測")
    st.write("上傳樂譜圖片，AI 將專注辨識數字與符號。")

    uploaded_file = st.file_uploader("請選擇樂譜圖片", type=["png", "jpg", "jpeg"])

    if uploaded_file is None:
        st.session_state.ocr_scanned_text = None

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        
        col1, col2 = st.columns(2)
        with col1:
            st.image(image, caption="已上傳的樂譜", width="stretch")
            
        with col2:
            if st.button("🚀 開始啟動 AI 掃描"):
                with st.spinner('📦 正在啟動數字專用辨識模型...'):
                    try:
                        ocr = load_ocr_model()
                    except Exception as e:
                        st.error(f"❌ 模型載入失敗：{str(e)}")
                        st.stop()
                
                with st.spinner('🔍 偵測數字中...'):
                    try:
                        img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                        gray_img = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
                        _, binary_img = cv2.threshold(gray_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                        
                        # 【核心改進】使用 allowlist 只偵測數字、小節線與基本符號
                        result = ocr.readtext(binary_img, 
                                            allowlist='0123456789|.-Il\'·', 
                                            mag_ratio=1.2, 
                                            contrast_ths=0.1, 
                                            adjust_contrast=0.5)
                        
                        structured_text = reconstruct_layout(result)
                        beautified_text = format_jianpu_text(structured_text)
                        
                        if beautified_text.strip():
                            st.session_state.ocr_scanned_text = beautified_text
                        else:
                            st.error("⚠️ 無法從圖中解析出數字。")
                            
                    except Exception as e:
                        st.error(f"❌ 發生錯誤：{str(e)}")
            
            # --- 人工校對與最終移調 ---
            if st.session_state.ocr_scanned_text is not None:
                st.success("✅ 掃描完成！")
                edited_text = st.text_area(
                    "✏️ 人工校對 (若 AI 看錯數字可在此修正)：", 
                    value=st.session_state.ocr_scanned_text, 
                    height=200
                )
                
                if st.button("✨ 確認無誤，開始移調", type="primary"):
                    cleaned_original, final_converted = process_jianpu_ocr(edited_text)
                    st.divider()
                    st.write("🎉 **移調結果：**")
                    st.code(final_converted, language="text")
