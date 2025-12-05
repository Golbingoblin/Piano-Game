# 🎹 Piano Games - 설치 가이드

## 📋 목차
1. [시스템 요구사항](#시스템-요구사항)
2. [Conda 환경 설치](#conda-환경-설치)
3. [데이터 파일 확인](#데이터-파일-확인)
4. [MimiPiano 모델 변환 (선택사항)](#mimipiano-모델-변환-선택사항)
5. [서버 실행](#서버-실행)
6. [문제 해결](#문제-해결)

---

## 시스템 요구사항

### 필수 사항
- **운영체제**: Windows 10/11, macOS 10.15+, Linux
- **Python**: 3.8 이상 (3.9 권장)
- **브라우저**: Chrome 80+ 또는 Edge 80+ (Web MIDI API 지원)
- **MIDI 장치**: 자동피아노 또는 가상 MIDI 포트
- **웹캠**: 카메라 기반 게임용 (Conductor, AirPiano, MimiPiano)
- **마이크**: Singing Piano용

### 권장 사항
- **메모리**: 4GB RAM 이상
- **네트워크**: 초기 로딩 시 CDN 접근 필요 (MediaPipe, TensorFlow.js 다운로드)

---

## Conda 환경 설치

### 방법 1: environment.yml 사용 (권장)

```bash
# 1. 웹 앱 디렉토리로 이동
cd F:\idea\games\web_app

# 2. Conda 환경 생성 및 패키지 설치
conda env create -f environment.yml

# 3. 환경 활성화
conda activate piano-games

# 4. 설치 확인
python --version  # Python 3.9.x 출력되어야 함
flask --version   # Flask 버전 출력되어야 함
```

### 방법 2: 수동 설치

```bash
# 1. Conda 환경 생성
conda create -n piano-games python=3.9 -y

# 2. 환경 활성화
conda activate piano-games

# 3. Flask 설치
conda install -c conda-forge flask=2.3.0 -y

# 4. TensorFlowJS 변환 도구 설치 (선택사항)
pip install tensorflowjs==4.10.0
```

### 방법 3: pip만 사용 (Conda 없이)

```bash
# 1. 가상환경 생성
python -m venv venv

# 2. 가상환경 활성화
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 3. 패키지 설치
pip install -r requirements.txt
```

---

## 데이터 파일 확인

웹 앱 실행 전에 다음 파일들이 있는지 확인하세요:

```
web_app/static/data/
├── chord.CSV           ✅ (AirPiano용)
├── progression.CSV     ✅ (AirPiano용)
└── expression.csv      ✅ (MimiPiano용)
```

### 파일이 없는 경우

기존 Python 게임 폴더에서 복사:

```bash
# Windows
copy ..\airpiano\chord.CSV static\data\
copy ..\airpiano\progression.CSV static\data\
copy ..\mimipiano\expression.csv static\data\

# macOS/Linux
cp ../airpiano/chord.CSV static/data/
cp ../airpiano/progression.CSV static/data/
cp ../mimipiano/expression.csv static/data/
```

---

## MimiPiano 모델 변환 (선택사항)

MimiPiano에서 표정 인식 기능을 사용하려면 CNN 모델을 변환해야 합니다.

### 변환하지 않으면?
- 얼굴 감지만 수행 (MediaPipe Face Detection)
- 표정 인식 없음 (행복/슬픔 점수 수동 조절)

### 변환 방법

#### 1. 원본 모델 확인

```bash
# mimipiano 폴더에 모델 파일이 있는지 확인
ls ../mimipiano/checkPoint_model.h5
# 또는 Windows:
dir ..\mimipiano\checkPoint_model.h5
```

파일이 없으면 MimiPiano 표정 인식을 사용할 수 없습니다.

#### 2. TensorFlow.js 변환

```bash
# Conda 환경 활성화 (아직 안 했으면)
conda activate piano-games

# 모델 변환 (시간이 좀 걸릴 수 있음)
tensorflowjs_converter \
  --input_format=keras \
  ../mimipiano/checkPoint_model.h5 \
  static/data/tfjs_model

# Windows (한 줄로):
tensorflowjs_converter --input_format=keras ..\mimipiano\checkPoint_model.h5 static\data\tfjs_model
```

#### 3. 변환 결과 확인

```bash
ls static/data/tfjs_model/
# 다음 파일들이 생성되어야 함:
# - model.json
# - group1-shard1of1.bin (또는 여러 shard 파일)
```

### 변환 실패 시

TensorFlow 관련 오류가 발생하면:

```bash
# TensorFlow 설치 (변환에만 필요, 서버 실행엔 불필요)
pip install tensorflow==2.13.0

# 다시 변환 시도
tensorflowjs_converter --input_format=keras ..\mimipiano\checkPoint_model.h5 static\data\tfjs_model
```

---

## 서버 실행

### 1. Conda 환경 활성화

```bash
conda activate piano-games
```

### 2. 서버 시작

```bash
# web_app 디렉토리에서
python app.py
```

### 3. 출력 확인

다음과 같이 출력되면 성공:

```
==================================================
🎹 Piano Games Web App Starting...
==================================================
📱 메인 메뉴: http://localhost:5000
🎮 게임 목록:
   - Conductor:    http://localhost:5000/conductor
   - AirPiano:     http://localhost:5000/airpiano
   - Singing:      http://localhost:5000/singing
   - MimiPiano:    http://localhost:5000/mimipiano
==================================================
 * Serving Flask app 'app'
 * Debug mode: on
WARNING: This is a development server. Do not use it in a production deployment.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://192.168.x.x:5000
Press CTRL+C to quit
```

### 4. 브라우저 접속

Chrome 또는 Edge에서 열기:
```
http://localhost:5000
```

---

## 문제 해결

### "ModuleNotFoundError: No module named 'flask'"

```bash
# 환경이 활성화되지 않은 경우
conda activate piano-games

# Flask 재설치
conda install -c conda-forge flask -y
```

### "Address already in use" (포트 5000이 이미 사용 중)

**방법 1**: 다른 프로그램 종료
```bash
# Windows: 5000 포트 사용 중인 프로그램 찾기
netstat -ano | findstr :5000

# 해당 PID 종료 (작업 관리자에서)
```

**방법 2**: 다른 포트 사용
```bash
# app.py 마지막 줄 수정:
app.run(host='0.0.0.0', port=8080, debug=True)

# 접속: http://localhost:8080
```

### "MIDI 출력 장치가 연결되지 않았습니다"

**먼저 MIDI 테스트 페이지로 확인:**
```
http://localhost:5000/midi-test
```
이 페이지에서 모든 MIDI 장치를 확인하고 테스트할 수 있습니다.

**Windows**: 가상 MIDI 포트 설치
1. [loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html) 다운로드
2. 설치 및 실행
3. 가상 포트 생성 (예: "loopMIDI Port")
4. 브라우저 새로고침

**macOS**: IAC Driver 활성화
1. Audio MIDI Setup 열기
2. MIDI Studio 열기 (Cmd+2)
3. IAC Driver 더블클릭
4. "Device is online" 체크
5. Apply

**Microsoft GS Wavetable Synth가 안 보이는 경우:**
1. MIDI 테스트 페이지 접속 (`http://localhost:5000/midi-test`)
2. 브라우저 개발자 도구 (F12) → Console 탭 확인
3. 장치 목록과 상태 정보 확인
4. Windows 장치 관리자 → 소프트웨어 장치 확인
5. 필요시 브라우저를 관리자 권한으로 실행

### "카메라 접근 실패"

1. 브라우저 설정에서 카메라 권한 허용
2. 다른 프로그램이 카메라를 사용 중이면 종료
3. HTTPS가 아닌 경우 localhost만 카메라 접근 가능

### MediaPipe/TensorFlow.js 로딩 실패

1. 인터넷 연결 확인 (CDN 접근 필요)
2. 방화벽/백신 소프트웨어 확인
3. 브라우저 캐시 삭제 후 재시도

### Conda 환경 삭제 및 재설치

```bash
# 환경 비활성화
conda deactivate

# 환경 삭제
conda env remove -n piano-games

# 처음부터 다시 설치
conda env create -f environment.yml
conda activate piano-games
```

---

## 🎓 추가 정보

### 개발 모드로 실행

Flask 개발 서버는 코드 변경 시 자동으로 재시작됩니다:

```bash
# app.py의 debug=True가 활성화되어 있음
python app.py
```

### 프로덕션 배포

실제 서비스로 배포할 때는 Gunicorn 사용 권장:

```bash
pip install gunicorn

gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### 네트워크 환경에서 실행

같은 Wi-Fi의 다른 기기에서 접속:

1. 서버 컴퓨터 IP 확인:
   ```bash
   # Windows
   ipconfig
   # macOS/Linux
   ifconfig
   ```

2. 다른 기기에서 접속:
   ```
   http://<서버IP>:5000
   ```
   예: `http://192.168.1.100:5000`

**⚠️ 주의**: HTTP 환경에서는 localhost 외의 접근 시 카메라/마이크 권한이 제한될 수 있습니다.

---

## ✅ 설치 체크리스트

설치 완료 전 확인 사항:

- [ ] Conda 환경 생성됨 (`conda env list`로 확인)
- [ ] Flask 설치됨 (`flask --version`)
- [ ] 데이터 파일 존재 (`ls static/data/*.csv`)
- [ ] (선택) MimiPiano 모델 변환 완료
- [ ] 서버 실행 성공
- [ ] 브라우저에서 메인 페이지 접속 가능
- [ ] MIDI 출력 장치 연결 및 선택
- [ ] 최소 1개 게임 정상 작동 확인

모든 항목이 완료되면 준비 완료입니다! 🎉

---

## 📞 도움이 필요하신가요?

- 에러 메시지를 정확히 복사해주세요
- 브라우저 개발자 도구 (F12) 콘솔의 에러 확인
- `conda list` 출력 공유

**즐거운 연주 되세요! 🎹✨**
