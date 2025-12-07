#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Piano Games Web App - Flask Server
자동피아노 + 터치모니터 환경을 위한 웹 게임 플랫폼
"""

from flask import Flask, render_template, send_from_directory, jsonify, request
from pathlib import Path
import os
import json

app = Flask(__name__)
BASE_DIR = Path(__file__).parent
MUSIC_ROOT = BASE_DIR.parent / 'mimipiano' / 'MusicRoot'
MAESTRO_ROOT = BASE_DIR.parent / 'maestro-v3.0.0'

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

@app.route('/touch-piano')
def touch_piano():
    """Touch Piano 게임 - 멀티터치 피아노"""
    return render_template('touch_piano.html')

@app.route('/rhythm-game')
def rhythm_game():
    """Rhythm Game - 5버튼 리듬게임"""
    return render_template('rhythm_game.html')

@app.route('/midi-test')
def midi_test():
    """MIDI 장치 테스트 페이지"""
    return render_template('midi_test.html')

@app.route('/static/data/<path:filename>')
def serve_data(filename):
    """CSV 및 데이터 파일 제공"""
    return send_from_directory(BASE_DIR / 'static' / 'data', filename)

@app.route('/api/midi-files')
def get_midi_files():
    """MusicRoot 폴더의 모든 MIDI 파일 목록 반환"""
    midi_files = {}

    if not MUSIC_ROOT.exists():
        return jsonify({'error': 'MusicRoot folder not found'}), 404

    # 각 키 폴더 순회
    for key_folder in sorted(MUSIC_ROOT.iterdir()):
        if key_folder.is_dir():
            key_name = key_folder.name
            # 해당 키 폴더의 모든 .mid 파일 찾기
            files = sorted([f.name for f in key_folder.glob('*.mid')])
            if files:
                midi_files[key_name] = files

    return jsonify(midi_files)

@app.route('/api/midi-file/<key>/<filename>')
def serve_midi_file(key, filename):
    """특정 MIDI 파일 제공"""
    file_path = MUSIC_ROOT / key / filename
    if not file_path.exists():
        return jsonify({'error': 'File not found'}), 404
    return send_from_directory(MUSIC_ROOT / key, filename, mimetype='audio/midi')

# ===== Draw to Music Routes =====

@app.route('/draw-to-music')
def draw_to_music():
    """그림 그리기 페이지"""
    return render_template('draw_to_music.html')

@app.route('/api/compose-from-image', methods=['POST'])
def compose_from_image():
    """그림을 분석하여 MIDI 생성"""
    import base64
    from io import BytesIO

    data = request.get_json()
    image_data = data.get('image')

    # TODO: AI 분석 및 이미지 생성 (나중에 구현)
    # 일단 더미 응답

    # 분석 결과 (더미)
    analysis = {
        'description': 'A beautiful sunset over mountains with vibrant orange and purple colors',
        'mood': 'peaceful and contemplative',
        'suggested_genre': 'ambient classical'
    }

    # 테스트 MIDI 파일 경로 (MAESTRO에서 하나 가져오기)
    test_midi = '2004/MIDI-Unprocessed_XP_06_R1_2004_03_ORIG_MID--AUDIO_06_R1_2004_03_Track03_wav.midi'

    return jsonify({
        'success': True,
        'analysis': analysis,
        'generated_image_url': '/static/images/placeholder_generated.jpg',  # TODO: 실제 생성 이미지
        'midi_path': test_midi
    })

# ===== Classical Library Routes =====

@app.route('/classical-library')
def classical_library():
    """클래식 음악 라이브러리 - 작곡가 목록"""
    return render_template('classical_library.html')

@app.route('/composer/<composer_name>')
def composer_detail(composer_name):
    """작곡가 상세 페이지"""
    return render_template('composer_detail.html', composer_name=composer_name)

@app.route('/piece/<path:midi_path>')
def piece_player(midi_path):
    """곡 재생 페이지"""
    return render_template('piece_player.html', midi_path=midi_path)

@app.route('/api/composers')
def get_composers():
    """작곡가 목록 및 곡 데이터 반환"""
    composers_file = BASE_DIR / 'static' / 'data' / 'composers.json'
    if not composers_file.exists():
        return jsonify({'error': 'Composers data not found'}), 404

    with open(composers_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return jsonify(data)

@app.route('/api/composer-info/<composer_name>')
def get_composer_info(composer_name):
    """특정 작곡가의 Wikipedia 정보 반환"""
    info_file = BASE_DIR / 'static' / 'data' / 'composer_info.json'
    if not info_file.exists():
        return jsonify({'error': 'Composer info not found'}), 404

    with open(info_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if composer_name not in data:
        return jsonify({'error': 'Composer not found'}), 404

    return jsonify(data[composer_name])

@app.route('/api/maestro-midi/<path:filepath>')
def serve_maestro_midi(filepath):
    """MAESTRO MIDI 파일 제공"""
    file_path = MAESTRO_ROOT / filepath
    if not file_path.exists():
        return jsonify({'error': 'File not found'}), 404

    directory = file_path.parent
    filename = file_path.name
    return send_from_directory(directory, filename, mimetype='audio/midi')

if __name__ == '__main__':
    # 터치 모니터에서 접속 가능하도록 0.0.0.0 바인딩
    print("=" * 50)
    print("Piano Games Web App Starting...")
    print("=" * 50)
    print("Main Menu: http://localhost:5000")
    print("Games:")
    print("   - Conductor:    http://localhost:5000/conductor")
    print("   - AirPiano:     http://localhost:5000/airpiano")
    print("   - Singing:      http://localhost:5000/singing")
    print("   - MimiPiano:    http://localhost:5000/mimipiano")
    print("   - Touch Piano:  http://localhost:5000/touch-piano")
    print("   - Rhythm Game:  http://localhost:5000/rhythm-game")
    print("Other Features:")
    print("   - Classical Library: http://localhost:5000/classical-library")
    print("   - Draw to Music:     http://localhost:5000/draw-to-music")
    print("MIDI Test:              http://localhost:5000/midi-test")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)
