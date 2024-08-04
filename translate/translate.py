from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
from flask_cors import CORS
from functools import wraps
import requests
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)
app.config['TEMPLATES_AUTO_RELOAD'] = True

# 비밀번호 설정
PASSWORD = 'dark20109'  

def check_auth(password):
    """비밀번호가 유효한지 확인하는 함수."""
    return password == PASSWORD

def authenticate():
    """비밀번호 인증을 요구하는 페이지로 리디렉션합니다."""
    return redirect(url_for('login'))

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not request.cookies.get('authenticated'):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form['password']
        if check_auth(password):
            resp = redirect(url_for('index'))
            resp.set_cookie('authenticated', 'true')
            return resp
        else:
            return jsonify({'message': '비밀번호가 잘못되었습니다.'}), 401
    return render_template('login.html')

@app.route('/logout')
def logout():
    resp = redirect(url_for('login'))
    resp.delete_cookie('authenticated')
    return resp

@app.route('/')
@requires_auth
def index():
    return render_template('index.html')

@app.route('/translate', methods=['POST'])
@requires_auth
def translate():
    text = request.json['text']
    
    try:
        chunks = split_text(text)
        translated_chunks = []
        
        for chunk in chunks:
            preprocessed_chunk = preprocess_with_llm(chunk)
            translated_chunk = translate_with_deepl(preprocessed_chunk)
            postprocessed_chunk = postprocess_with_llm(translated_chunk)
            translated_chunks.append(postprocessed_chunk)
        
        final_translation = ' '.join(translated_chunks)
        filename = save_translation(final_translation)
        
        return jsonify({'translatedText': final_translation, 'filename': filename})
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        # 이메일 전송 로직 추가
        return jsonify({'message': '비밀번호 재설정 링크가 이메일로 전송되었습니다.'})
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    # 토큰 검증 로직 추가
    if request.method == 'POST':
        new_password = request.form['password']
        global PASSWORD
        PASSWORD = new_password
        return jsonify({'message': '비밀번호가 성공적으로 재설정되었습니다.'})
    return render_template('reset_password.html')

def split_text(text, max_length=3000):
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0
    
    for word in words:
        if current_length + len(word) + 1 > max_length:
            chunks.append(' '.join(current_chunk))
            current_chunk = [word]
            current_length = len(word)
        else:
            current_chunk.append(word)
            current_length += len(word) + 1
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks

def preprocess_with_llm(text):
    prompt = f"다음 텍스트를 번역하기 좋게 전처리해주세요. 내용을 축약하지 말고 모든 문장을 유지해주세요: {text}"
    response = requests.post('http://localhost:1234/v1/chat/completions', json={
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 3000
    })
    return response.json()['choices'][0]['message']['content']

def translate_with_deepl(text):
    params = {
        'auth_key': '4750ceae-2799-439f-9ccf-bad6142bf7da:fx',
        'text': text,
        'source_lang': 'KO',
        'target_lang': 'EN'
    }
    response = requests.post('https://api-free.deepl.com/v2/translate', data=params)
    return response.json()['translations'][0]['text']

def postprocess_with_llm(text):
    prompt = f"다음 번역 결과를 자연스럽게 다듬어주세요. 모든 문장을 유지하고 내용을 축약하지 마세요: {text}"
    response = requests.post('http://localhost:1234/v1/chat/completions', json={
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 3000
    })
    return response.json()['choices'][0]['message']['content']

def save_translation(text):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"translation_{timestamp}.txt"
    filepath = os.path.join('translations', filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(text)
    return filename

@app.route('/download/<filename>')
@requires_auth
def download_file(filename):
    return send_file(os.path.join('translations', filename), as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003, debug=False)
