# app.py
import os
from flask import Flask, render_template, request
from utils import convert_sheet_music

app = Flask(__name__)

# 設定上傳圖片的儲存資料夾
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/', methods=['GET', 'POST'])
def index():
    converted_text = ""
    original_text = ""
    upload_message = ""
    
    if request.method == 'POST':
        # 處理方式一：直接文字轉換
        if 'sheet_text' in request.form and request.form['sheet_text'].strip() != "":
            original_text = request.form['sheet_text']
            converted_text = convert_sheet_music(original_text)
            
        # 處理方式二：圖片檔案上傳
        elif 'file' in request.files:
            file = request.files['file']
            if file.filename != '':
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(filepath)
                upload_message = f"檔案 {file.filename} 已成功上傳！(註：圖片辨識功能需後續串接 OCR 模型)"
                
    return render_template('index.html', 
                           original_text=original_text, 
                           converted_text=converted_text,
                           upload_message=upload_message)

if __name__ == '__main__':
    # 啟動測試伺服器
    app.run(debug=True)
