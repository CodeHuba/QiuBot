#!/usr/bin/env python3
"""
简化版 Web Chat - 直接调用 hermes chat
"""
import subprocess
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

@app.route('/')
def index():
    return send_from_directory('.', 'web_chat.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '')
    
    if not message:
        return jsonify({'error': '消息不能为空'}), 400
    
    try:
        result = subprocess.run(
            ['hermes', 'chat', '--yolo', message],
            capture_output=True,
            text=True,
            timeout=120,
            cwd='/opt/qiubot'
        )
        
        response_text = result.stdout.strip()
        if result.returncode != 0:
            response_text = f"错误: {result.stderr}"
        
        return jsonify({'response': response_text})
    except subprocess.TimeoutExpired:
        return jsonify({'error': '请求超时'}), 504
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
