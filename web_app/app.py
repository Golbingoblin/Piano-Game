#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Piano Games Web App - Flask Server
자동피아노 + 터치모니터 환경을 위한 웹 게임 플랫폼
"""

from flask import Flask, render_template, send_from_directory
from pathlib import Path

app = Flask(__name__)
BASE_DIR = Path(__file__).parent

@app.route('/')
def index():
    """메인 메뉴 - 4개 게임 선택"""
    return render_template('index.html')

@app.route('/conductor')
def conductor():
    """Conductor 게임 - 모션으로 MIDI BPM 조절"""
    return render_template('conductor.html')

@app.route('/airpiano')
def airpiano():
    """AirPiano 게임 - 손 제스처로 MIDI 연주"""
    return render_template('airpiano.html')

@app.route('/singing')
def singing():
    """Singing Piano 게임 - 음성 피치를 MIDI로 변환"""
    return render_template('singing.html')

@app.route('/mimipiano')
def mimipiano():
    """MimiPiano 게임 - 표정 인식으로 MIDI 변조"""
    return render_template('mimipiano.html')

@app.route('/midi-test')
def midi_test():
    """MIDI 장치 테스트 페이지"""
    return render_template('midi_test.html')

@app.route('/static/data/<path:filename>')
def serve_data(filename):
    """CSV 및 데이터 파일 제공"""
    return send_from_directory(BASE_DIR / 'static' / 'data', filename)

if __name__ == '__main__':
    # 터치 모니터에서 접속 가능하도록 0.0.0.0 바인딩
    print("=" * 50)
    print("🎹 Piano Games Web App Starting...")
    print("=" * 50)
    print("📱 메인 메뉴: http://localhost:5000")
    print("🎮 게임 목록:")
    print("   - Conductor:    http://localhost:5000/conductor")
    print("   - AirPiano:     http://localhost:5000/airpiano")
    print("   - Singing:      http://localhost:5000/singing")
    print("   - MimiPiano:    http://localhost:5000/mimipiano")
    print("🔧 MIDI 테스트:    http://localhost:5000/midi-test")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)
