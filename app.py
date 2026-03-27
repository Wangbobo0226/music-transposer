import streamlit as st
import cv2
import numpy as np
from PIL import Image
import easyocr
from utils import convert_sheet_music, process_jianpu_ocr
import re

st.set_page_config(page_title="簡譜移調轉換器 (AI 升級版)", page_icon="🎵", layout="wide")

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
    y_threshold = 15 # 容差值
    
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
        
        # 4. 濾網：合併多餘的小節線 (例如 "| |" 變成 "|")
        line = re.sub(r'\|\s*\|', '|', line)
        
        # 5. 濾網：刪除夾在小節線中無意義的孤單雜訊 (例如 "| 6 |" 變成 "|")
        line = re.sub(r'\|\s*[\d\.\-]\s*\|', '|', line)
        
        # 6. 智慧補齊頭尾小節線
        chars = [c for c in line if c.strip()]
        if chars:
            music_char_count = sum(1 for c in chars if c.isdigit() or c in '-·|')
            if music_char_count / len(chars) > 0.3: 
                if not line.startswith('|'):
                    line = '| ' + line
                if not line.endswith('|'):
                    line = line + ' |'
        
        # 7. 最後終極美化：再次確保 | 兩側絕對是一個空格，而且頭尾乾淨
        line = line.replace('|', ' | ')
        line = re.sub(r'\s+', ' ', line).strip()
        
        # 如果經過過濾後，這行只剩下小節線而沒有音符，就直接刪掉這一行
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
st.sidebar.info("💡 **升級提示**：已開啟「純黑白安全模式」與「完美間距排版整形器」，格式更嚴格整齊！")

if menu_option == "📝 文字輸入轉換":
    st.title("📝 簡譜文字轉換")
    st.write("請在下方輸入框貼上或手打您的簡譜，系統將自動為您移調。")
    
    sheet_text = st.text_area(
        "輸入簡譜：", 
        placeholder="例如：\n| 3 5 2 5 | 4 4 3 5 | 1' 2' 3' |",
        height=300
    )

    if st.button("開始轉換", type="primary"):
        if sheet_text.strip():
            converted = convert_sheet_music(sheet_text)
            st.success("✅ 轉換成功！")
            st.code(converted, language="text") 
        else:
            st.warning("請先輸入簡譜文字喔！")

elif menu_option == "🖼️ 圖片 AI 智慧辨識 (EasyOCR)":
    st.title("🖼️ 樂譜圖片 AI 智慧偵測")
    st.write("上傳樂譜圖片，AI 將自動辨識數字、過濾雜訊，並重構排版進行移調！")

    uploaded_file = st.file_uploader("請選擇樂譜圖片", type=["png", "jpg", "jpeg"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        
        col1, col2 = st.columns(2)
        with col1:
            # 使用最新語法 width="stretch" 避免黃色警告
            st.image(image, caption="已上傳的樂譜", width="stretch")
            
        with col2:
            if st.button("🚀 開始啟動 AI 掃描", type="primary"):
                with st.spinner('📦 正在喚醒 AI 視覺模型...'):
                    try:
                        ocr = load_ocr_model()
                    except Exception as e:
                        st.error(f"❌ 模型載入失敗：{str(e)}")
                        st.stop()
                
                with st.spinner('🔍 正在進行極速黑白強化與強制排版美化...'):
                    try:
                        img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                        
                        # 記憶體安全模式：不放大，僅轉灰階
                        gray_img = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
                        
                        # Otsu 二值化：把背景變純白、字體變純黑，大幅降低雜訊干擾
                        _, binary_img = cv2.threshold(gray_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                        
                        # 進行辨識 (內部放大率設為安全的 1.2)
                        result = ocr.readtext(binary_img, mag_ratio=1.2, contrast_ths=0.1, adjust_contrast=0.5)
                        
                        # 核心處理流程：重構座標 -> 強制整形排版 -> 移調處理
                        structured_text = reconstruct_layout(result)
                        beautified_text = format_jianpu_text(structured_text)
                        cleaned_original, final_converted = process_jianpu_ocr(beautified_text)
                        
                        if cleaned_original.strip():
                            st.success("✅ 辨識與轉換完成！")
                            st.write("**(1) 根據座標重構並強制格式化的乾淨原譜：**")
                            st.code(cleaned_original, language="text")
                            
                            st.write("**(2) 自動移調後的結果：**")
                            st.code(final_converted, language="text")
                        else:
                            st.error("⚠️ AI 無法從圖片中解析出清晰的音符，建議裁切圖片只保留樂譜部分。")
                            
                    except Exception as e:
                        st.error(f"❌ 處理圖片時發生錯誤：{str(e)}")
