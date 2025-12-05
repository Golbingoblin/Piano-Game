# 🔧 MIDI 장치 디버깅 가이드

Microsoft GS Wavetable Synth가 감지되지만 선택되지 않는 문제 해결 방법

---

## 🎯 빠른 진단

### 1단계: MIDI 테스트 페이지 접속

```
http://localhost:5000/midi-test
```

### 2단계: 브라우저 콘솔 열기

- **Windows**: `F12` 또는 `Ctrl + Shift + I`
- **Mac**: `Cmd + Option + I`
- **Console 탭 선택**

### 3단계: 콘솔 출력 확인

다음과 같은 로그가 표시됩니다:

```
✅ MIDI Access 획득
🎹 감지된 MIDI 출력 장치 목록:
  [0] ID: -123456789
      Name: Microsoft GS Wavetable Synth
      Manufacturer: Microsoft
      State: connected
      Connection: closed
      ---
  [1] ID: 987654321
      Name: loopMIDI Port
      Manufacturer: Tobias Erichsen
      State: connected
      Connection: closed
      ---
```

---

## ❓ 문제 시나리오별 해결

### 시나리오 1: 장치가 목록에 없음

**증상:**
```
🎹 감지된 MIDI 출력 장치 목록:
  (비어있음)
❌ MIDI 출력 장치가 연결되지 않았습니다.
```

**원인:**
- Windows MIDI 서비스 비활성화
- 브라우저 권한 문제

**해결:**

1. **Windows 서비스 확인**
   ```
   Win + R → services.msc
   → "Windows Audio" 서비스 확인
   → 실행 중이 아니면 시작
   ```

2. **장치 관리자 확인**
   ```
   Win + X → 장치 관리자
   → 소프트웨어 장치
   → "Microsoft GS Wavetable Synth" 확인
   → 비활성화되어 있으면 활성화
   ```

3. **브라우저 관리자 권한 실행**
   ```
   Chrome/Edge 우클릭
   → "관리자 권한으로 실행"
   → 테스트 페이지 다시 접속
   ```

---

### 시나리오 2: 장치가 목록에 있지만 선택 안 됨

**증상:**
```
🎹 감지된 MIDI 출력 장치 목록:
  [0] ID: -123456789
      Name: Microsoft GS Wavetable Synth
      ...
🔍 자동 선택 시도 중...
   "Microsoft GS Wavetable Synth" 패턴 매칭 실패
   "MIDIOUT2" 패턴 매칭 실패
   ...
✅ "loopMIDI" 패턴으로 장치 선택됨: loopMIDI Port
```

**원인:**
- 장치 이름이 예상과 다름 (예: "Microsoft GS Wavetable Synth 0")
- 다른 장치가 우선 선택됨

**해결:**

**방법 1: 저장된 설정 초기화**
1. MIDI 테스트 페이지에서 "🗑️ 저장된 MIDI 설정 초기화" 버튼 클릭
2. 페이지 새로고침 (`F5`)
3. 콘솔에서 자동 선택 로그 확인

**방법 2: 수동으로 localStorage 초기화**
```javascript
// 브라우저 콘솔에 입력:
localStorage.removeItem('preferredMidiOutput')
location.reload()
```

**방법 3: 메인 페이지에서 직접 선택**
1. `http://localhost:5000` 접속
2. "🎹 MIDI 출력 장치 선택" 드롭다운에서 Microsoft GS Wavetable Synth 선택
3. 게임 시작

---

### 시나리오 3: 장치 이름이 다름

**증상:**
```
  [0] ID: -123456789
      Name: Microsoft GS Wavetable Synth 0  ← 숫자 추가됨
      ...
```

**원인:**
- Windows가 장치 이름 뒤에 번호 추가

**해결:**

현재 코드는 부분 일치 검색을 사용하므로 자동으로 처리되어야 합니다:
```javascript
output.name.toLowerCase().includes('microsoft gs wavetable synth')
```

그래도 안 되면:
1. 콘솔에서 정확한 이름 확인
2. 메인 페이지에서 수동 선택

---

### 시나리오 4: State가 'disconnected'

**증상:**
```
  [0] ID: -123456789
      Name: Microsoft GS Wavetable Synth
      State: disconnected  ← 문제!
```

**원인:**
- 다른 프로그램이 독점 사용 중
- MIDI 드라이버 충돌

**해결:**

1. **다른 MIDI 프로그램 종료**
   - DAW (FL Studio, Ableton 등)
   - MIDI 플레이어
   - 가상 MIDI 라우터

2. **Windows 재시작**

3. **가상 MIDI 포트 사용**
   - loopMIDI 설치
   - 새 포트 생성
   - 해당 포트 사용

---

### 시나리오 5: 테스트 버튼 눌러도 소리 없음

**증상:**
- 장치 선택됨 (State: connected)
- 테스트 버튼 클릭
- "테스트 완료" 메시지 표시
- 소리 안 남

**원인:**
- 시스템 볼륨 음소거
- MIDI 볼륨 설정 낮음
- 스피커/헤드폰 연결 문제

**해결:**

1. **Windows 볼륨 확인**
   ```
   작업 표시줄 → 스피커 아이콘 우클릭
   → 볼륨 믹서 열기
   → Chrome/Edge 볼륨 확인
   ```

2. **MIDI 볼륨 확인**
   ```
   설정 → 시스템 → 사운드
   → 앱 볼륨 및 장치 기본 설정
   → Chrome/Edge 출력 장치 확인
   ```

3. **다른 장치로 테스트**
   - MIDI 테스트 페이지에서 "🎵 모든 장치 테스트" 클릭
   - 어떤 장치에서 소리가 나는지 확인

---

## 📊 콘솔 로그 해석

### 정상 케이스

```javascript
✅ MIDI Access 획득
🎹 감지된 MIDI 출력 장치 목록:
  [0] ID: -123456789
      Name: Microsoft GS Wavetable Synth
      Manufacturer: Microsoft
      State: connected
      Connection: closed
      ---
🔍 자동 선택 시도 중...
✅ "Microsoft GS Wavetable Synth" 패턴으로 장치 선택됨: Microsoft GS Wavetable Synth (ID: -123456789)
✅ 최종 선택된 MIDI 출력: Microsoft GS Wavetable Synth
   ID: -123456789
   Manufacturer: Microsoft
   State: connected
```

### 저장된 장치 사용

```javascript
✅ MIDI Access 획득
🎹 감지된 MIDI 출력 장치 목록:
  ...
✅ 저장된 MIDI 출력 사용: Microsoft GS Wavetable Synth (ID: -123456789)
```

### 저장된 장치 없음 (자동 선택)

```javascript
⚠️ 저장된 장치를 찾을 수 없음 (ID: 12345), 자동 선택으로 전환
🔍 자동 선택 시도 중...
...
```

---

## 🛠️ 고급 디버깅

### localStorage 직접 확인

```javascript
// 브라우저 콘솔에서:

// 저장된 장치 ID 확인
console.log('저장된 ID:', localStorage.getItem('preferredMidiOutput'));

// 모든 MIDI 장치 ID 확인
navigator.requestMIDIAccess().then(access => {
    access.outputs.forEach((output, id) => {
        console.log('장치 ID:', id, '→ 이름:', output.name);
    });
});
```

### 강제로 특정 장치 선택

```javascript
// 브라우저 콘솔에서:

// 1. 모든 장치 목록 확인
navigator.requestMIDIAccess().then(access => {
    const outputs = Array.from(access.outputs.values());
    outputs.forEach((output, idx) => {
        console.log(idx, ':', output.name, '/ ID:', output.id);
    });
});

// 2. 원하는 장치의 ID 복사 후 저장
localStorage.setItem('preferredMidiOutput', '-123456789');  // 실제 ID로 변경

// 3. 페이지 새로고침
location.reload();
```

---

## 🔍 실시간 모니터링

테스트 페이지를 열어두고 다음을 모니터링:

1. **장치 추가/제거 감지**
   - USB MIDI 장치 연결/해제
   - 가상 MIDI 포트 활성화/비활성화
   - "🔄 장치 새로고침" 버튼 클릭

2. **State 변화 확인**
   - connected ↔ disconnected
   - 다른 프로그램 실행 시 영향

3. **Connection 상태**
   - open: 현재 사용 중
   - closed: 대기 상태

---

## 📝 로그 저장

문제가 지속되면 콘솔 로그를 저장하여 공유:

1. 콘솔에서 우클릭
2. "Save as..." 선택
3. 로그 파일 저장 (txt 형식)
4. 파일 공유

---

## ✅ 체크리스트

문제 해결 전 확인:

- [ ] MIDI 테스트 페이지 접속 (`/midi-test`)
- [ ] 브라우저 콘솔 열기 (F12)
- [ ] 장치 목록에 Microsoft GS Wavetable Synth 있음
- [ ] State가 "connected"임
- [ ] 저장된 설정 확인 (💾 표시)
- [ ] 필요 시 설정 초기화
- [ ] 수동 선택 시도
- [ ] 테스트 버튼으로 소리 확인
- [ ] 볼륨 설정 확인

---

## 🚑 긴급 해결법

아무것도 안 되면:

```javascript
// 1. 완전 초기화
localStorage.clear();
location.reload();

// 2. 브라우저 데이터 삭제
// 설정 → 개인정보 및 보안 → 인터넷 사용 기록 삭제
// → 쿠키 및 기타 사이트 데이터 체크

// 3. 브라우저 재시작

// 4. Windows 재시작
```

그래도 안 되면:
- **가상 MIDI 포트 사용 (loopMIDI)** - 100% 작동 보장
- 또는 Chrome Canary/Beta 버전 시도

---

**문제가 해결되지 않으면 콘솔 로그를 공유해주세요!** 🙏
