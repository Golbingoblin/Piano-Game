# 🎹 Piano Games - 웹 앱

자동피아노와 터치모니터 환경을 위한 인터랙티브 음악 게임 플랫폼

## 📋 게임 목록

### 1. 🎵 Conductor
- **설명**: 카메라 앞에서 움직이면 MIDI 재생 속도가 변합니다
- **기술**: OpenCV 모션 감지, Web MIDI API
- **난이도**: ⭐ (매우 간단)

### 2. ✋ AirPiano
- **설명**: 손가락으로 공중 피아노를 연주하세요
- **기술**: MediaPipe Hands, 코드 진행, 파티클 이펙트
- **난이도**: ⭐⭐⭐ (보통)

### 3. 🎤 Singing Piano
- **설명**: 노래하거나 허밍하면 목소리가 MIDI로 변환됩니다
- **기술**: Web Audio API, Autocorrelation 피치 감지, 블루스 스케일
- **난이도**: ⭐⭐⭐ (보통)

### 4. 😊 MimiPiano
- **설명**: 얼굴 표정으로 음악의 분위기를 바꾸세요
- **기술**: TensorFlow.js CNN, MediaPipe Face Detection
- **난이도**: ⭐⭐⭐⭐ (복잡 - 모델 변환 필요)

---

## 🚀 시작하기

**📖 자세한 설치 가이드는 [INSTALL.md](INSTALL.md)를 참조하세요!**

### 빠른 시작 (Conda)

```bash
# 1. Conda 환경 생성 및 활성화
conda env create -f environment.yml
conda activate piano-games

# 2. 서버 실행
python app.py

# 3. 브라우저에서 접속
# http://localhost:5000
```

### 빠른 시작 (pip)

```bash
# 1. 필요한 패키지 설치
pip install -r requirements.txt

# 2. 서버 실행
python app.py
```

### 서버 실행

```bash
cd F:\idea\games\web_app
python app.py
```

서버가 시작되면 다음과 같이 표시됩니다:

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
```

### 4. 브라우저 접속

Chrome 또는 Edge에서 `http://localhost:5000` 으로 접속하세요.

---

## 🎮 게임별 사용법

### 🎹 MIDI 출력 장치 선택

모든 게임 페이지에서 MIDI 출력 장치를 선택할 수 있습니다:

1. 페이지 상단의 "🎹 MIDI 출력 장치" 드롭다운 메뉴
2. 연결된 모든 MIDI 장치가 표시됩니다
3. 원하는 장치를 선택하면 자동으로 저장됩니다
4. 다음에 접속하면 저장된 장치가 자동으로 선택됩니다

### Conductor

1. MIDI 출력 장치를 선택하세요 (위 참조)
2. **(선택사항)** MIDI 파일 업로드 - 모션으로 템포 조절
   - 파일 선택 후 취소를 눌러도 기존 파일 유지됨
   - MIDI 파일 없이도 실시간 비트 재생
3. "시작" 버튼 클릭
4. 카메라 권한 허용
5. 카메라 앞에서 움직이면 모션 강도에 따라 BPM이 변합니다
6. 민감도와 반응 속도를 조절할 수 있습니다

**MIDI 파일 재생:**
- MIDI 파일을 선택하면 움직임에 따라 재생 속도가 조절됩니다
- 움직임이 많을수록 빠르게, 적을수록 느리게 재생
- 파일이 끝나면 자동으로 루프 재생

### AirPiano

1. MIDI 출력 장치를 선택하세요
2. "시작" 버튼 클릭
3. 카메라 권한 허용
4. 양손을 카메라에 보여주세요
5. 손가락을 구부리면 코드가 연주됩니다
6. "분위기 전환" 버튼으로 코드 진행을 변경할 수 있습니다

### Singing Piano

1. MIDI 출력 장치를 선택하세요
2. "시작" 버튼 클릭
3. 마이크 권한 허용
4. 노래하거나 허밍하세요
5. 목소리의 피치가 실시간으로 MIDI 노트로 변환됩니다
6. 블루스 스케일로 자동 보정됩니다

### MimiPiano

**⚠️ 주의**: MimiPiano를 사용하려면 먼저 CNN 모델을 변환해야 합니다.

#### 모델 변환 (최초 1회만)

```bash
# mimipiano 폴더에 checkPoint_model.h5 파일이 있는지 확인
cd F:\idea\games

# TensorFlow.js 형식으로 변환
tensorflowjs_converter \
  --input_format=keras \
  mimipiano/checkPoint_model.h5 \
  web_app/static/data/tfjs_model
```

변환이 완료되면 `web_app/static/data/tfjs_model/` 폴더에 다음 파일들이 생성됩니다:
- `model.json`
- `group1-shard1of1.bin` (또는 여러 shard 파일)

#### 게임 실행

1. MIDI 출력 장치를 선택하세요
2. "시작" 버튼 클릭
3. 카메라 권한 허용
4. 얼굴을 카메라에 보여주세요
5. 표정에 따라 happiness와 special 점수가 변합니다
6. MIDI 파일을 선택하고 재생하면 표정에 따라 음악이 변조됩니다

---

## 🔧 문제 해결

### MIDI 장치 테스트 페이지

MIDI 장치가 제대로 인식되지 않을 때 전용 테스트 페이지를 사용하세요:

```
http://localhost:5000/midi-test
```

**기능:**
- 연결된 모든 MIDI 출력/입력 장치 표시
- 각 장치의 상세 정보 (ID, 제조사, 상태 등)
- 장치별 개별 테스트 (C4 음 재생)
- 브라우저 콘솔에 디버그 정보 출력

**Microsoft GS Wavetable Synth가 안 보이는 경우:**
1. Windows 설정 → 시스템 → 사운드 → 고급 사운드 옵션 확인
2. 장치 관리자 → 소프트웨어 장치 확인
3. 브라우저를 관리자 권한으로 실행 시도
4. MIDI 테스트 페이지에서 콘솔 확인 (F12)

### "MIDI 출력 장치가 연결되지 않았습니다"

1. 자동피아노(또는 가상 MIDI 포트)가 연결되어 있는지 확인
2. Windows의 경우: 장치 관리자에서 MIDI 장치 확인
3. 가상 MIDI 포트 설치:
   - Windows: loopMIDI
   - Mac: IAC Driver
4. **MIDI 테스트 페이지로 장치 상태 확인**: http://localhost:5000/midi-test

### "Web MIDI API를 지원하지 않는 브라우저입니다"

- Chrome 또는 Edge 브라우저를 사용하세요
- Firefox와 Safari는 Web MIDI API를 지원하지 않습니다

### "카메라 접근 실패"

1. 브라우저 권한 설정 확인
2. HTTPS 환경이 아닌 경우 localhost만 허용됩니다
3. 다른 프로그램이 카메라를 사용 중인지 확인

### "마이크 접근 실패" (Singing Piano)

1. 브라우저 마이크 권한 허용
2. 시스템 마이크 설정 확인
3. 마이크가 올바르게 연결되어 있는지 확인

### MimiPiano 모델 로드 실패

1. 모델 변환이 완료되었는지 확인
2. `web_app/static/data/tfjs_model/model.json` 파일이 존재하는지 확인
3. 브라우저 개발자 도구 콘솔에서 에러 메시지 확인

---

## 📁 프로젝트 구조

```
web_app/
├── app.py                 # Flask 서버
├── static/
│   ├── css/
│   │   └── style.css      # 공통 스타일
│   ├── js/
│   │   ├── common.js      # 공통 유틸리티 (Web MIDI API)
│   │   ├── conductor.js   # Conductor 게임
│   │   ├── airpiano.js    # AirPiano 게임
│   │   ├── singing.js     # Singing Piano 게임
│   │   └── mimipiano.js   # MimiPiano 게임
│   └── data/
│       ├── chord.CSV      # AirPiano 코드 테이블
│       ├── progression.CSV # AirPiano 진행
│       ├── expression.csv # MimiPiano 표현 맵
│       └── tfjs_model/    # MimiPiano CNN 모델 (변환 후 생성)
└── templates/
    ├── index.html         # 메인 메뉴
    ├── conductor.html     # Conductor 페이지
    ├── airpiano.html      # AirPiano 페이지
    ├── singing.html       # Singing Piano 페이지
    └── mimipiano.html     # MimiPiano 페이지
```

---

## 🎨 터치 인터페이스 최적화

모든 게임은 터치 모니터 환경에 최적화되어 있습니다:

- ✅ 큰 터치 버튼
- ✅ 제스처 인식
- ✅ 더블탭 줌 방지
- ✅ 텍스트 선택 방지
- ✅ 반응형 디자인

---

## 🌐 네트워크 환경에서 실행

같은 네트워크의 다른 기기에서 접속하려면:

1. 서버 컴퓨터의 IP 주소 확인:
   ```bash
   # Windows
   ipconfig

   # Mac/Linux
   ifconfig
   ```

2. 다른 기기에서 접속:
   ```
   http://<서버IP>:5000
   ```

   예: `http://192.168.1.100:5000`

**⚠️ 주의**: HTTPS가 아닌 경우 localhost 외의 환경에서는 카메라/마이크 접근이 제한될 수 있습니다.

---

## 📊 기술 스택

### 프론트엔드
- **HTML5 Canvas**: 비디오 렌더링, 파티클 이펙트
- **JavaScript (ES6+)**: 게임 로직
- **Web MIDI API**: 자동피아노 제어
- **Web Audio API**: 오디오 입력 및 피치 감지
- **MediaPipe**: 손/얼굴 감지
- **TensorFlow.js**: CNN 표정 인식

### 백엔드
- **Flask**: 웹 서버
- **Python 3**: 서버 로직

---

## 🐛 알려진 이슈

1. **AirPiano**: MediaPipe Hands의 손가락 각도 계산이 때때로 부정확할 수 있음
2. **Singing Piano**: Autocorrelation 알고리즘이 복잡한 음향에서 오작동 가능
3. **MimiPiano**: 모델 변환 후 정확도가 약간 떨어질 수 있음
4. **모든 게임**: 저사양 기기에서 프레임 드롭 발생 가능

---

## 📝 라이선스

이 프로젝트는 교육 및 개인 용도로 자유롭게 사용할 수 있습니다.

---

## 🙏 크레딧

- **MediaPipe**: Google
- **TensorFlow.js**: Google
- **Web MIDI API**: W3C Standard
- **Flask**: Pallets Project

---

## 📧 문의

문제가 발생하거나 질문이 있으시면 이슈를 생성해주세요.

**즐거운 연주 되세요! 🎹✨**
