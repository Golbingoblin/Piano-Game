# ⚡ Quick Start Guide

복사-붙여넣기로 바로 시작하세요!

## 🔥 Conda 환경 설치 및 실행 (한 번에)

```bash
# 웹 앱 디렉토리로 이동
cd F:\idea\games\web_app

# Conda 환경 생성 및 패키지 설치
conda env create -f environment.yml

# 환경 활성화
conda activate piano-games

# 서버 실행
python app.py
```

그 다음 Chrome/Edge에서 접속:
```
http://localhost:5000
```

---

## 🎯 다음 실행할 때 (환경 이미 설치됨)

```bash
cd F:\idea\games\web_app
conda activate piano-games
python app.py
```

---

## 🛠️ MimiPiano 모델 변환 (선택사항)

```bash
# 환경 활성화 (아직 안 했으면)
conda activate piano-games

# 모델 변환
tensorflowjs_converter --input_format=keras ..\mimipiano\checkPoint_model.h5 static\data\tfjs_model
```

---

## 🔧 문제 해결

### Flask 모듈 없음

```bash
conda activate piano-games
conda install -c conda-forge flask -y
```

### 포트 5000 사용 중

app.py 마지막 줄을 다음으로 변경:
```python
app.run(host='0.0.0.0', port=8080, debug=True)
```

접속: `http://localhost:8080`

### 환경 재설치

```bash
conda env remove -n piano-games
conda env create -f environment.yml
```

---

## 📦 패키지 목록

설치되는 것들:
- **Flask 2.3.0**: 웹 서버
- **TensorFlowJS 4.10.0**: 모델 변환 (선택)
- **Python 3.9**: 런타임

JavaScript 라이브러리 (CDN 자동 로드):
- MediaPipe Hands/Face Detection
- TensorFlow.js
- Web MIDI API (브라우저 내장)

---

**끝! 이제 http://localhost:5000 접속하세요 🎹**
