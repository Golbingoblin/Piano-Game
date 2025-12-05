/**
 * Singing Piano - 음성 피치를 MIDI로 변환
 * 기존 singing.py의 JavaScript 버전
 */

// ============ 설정 ============
const SAMPLE_RATE = 44100;
const BLOCK_SIZE = 2048;
const MIN_FREQ = 80.0;
const MAX_FREQ = 1000.0;

let rmsThreshold = 0.02;
let octaveShift = 1;
let velocityScale = 200.0;
let velocityOffset = 20.0;
let scaleName = 'blues';
let accompEnabled = false;

// ============ 상태 ============
let audioContext = null;
let analyser = null;
let microphone = null;
let scriptProcessor = null;
let isRunning = false;

let currentNote = null;
let noteHistory = [];
const WINDOW_SIZE = 3;
const DEBOUNCE_COUNT = 2;

let scaleNotes = [];

// 블루스 스케일
const BLUES_ROOT = 60; // C4
const BLUES_STEPS = [0, 3, 5, 6, 7, 10];

// 반주
const CHORD_STEPS = [0,0,0,0, 5,5, 0,0, 7,5,0,7];
const CHORD_INTERVALS = [0, 4, 7, 10];
let accompChordIdx = 0;
let lastAccompTime = 0;

// ============ 초기화 ============

window.addEventListener('load', async () => {
    // MIDI 초기화
    const midiResult = await initMIDI();
    if (!midiResult.success) {
        showError(midiResult.error);
        return;
    }

    // MIDI 출력 선택 UI 업데이트
    const midiSelect = document.getElementById('midiOutputSelect');
    if (midiSelect) {
        populateMidiSelect(midiSelect, midiResult.outputs, midiResult.selected);
    }

    // 스케일 생성
    generateScaleNotes();

    // UI 이벤트
    document.getElementById('scaleSelect').addEventListener('change', (e) => {
        scaleName = e.target.value;
        generateScaleNotes();
        showSuccess(`스케일: ${scaleName}`);
    });

    document.getElementById('threshold').addEventListener('input', (e) => {
        rmsThreshold = parseFloat(e.target.value);
        document.getElementById('thresholdValue').textContent = rmsThreshold.toFixed(3);
    });

    document.getElementById('octave').addEventListener('input', (e) => {
        octaveShift = parseInt(e.target.value);
        const sign = octaveShift >= 0 ? '+' : '';
        document.getElementById('octaveValue').textContent = `${sign}${octaveShift}`;
    });

    document.getElementById('velScale').addEventListener('input', (e) => {
        velocityScale = parseFloat(e.target.value);
        document.getElementById('velScaleValue').textContent = velocityScale;
    });

    document.getElementById('accompEnabled').addEventListener('change', (e) => {
        accompEnabled = e.target.checked;
    });

    showSuccess('준비 완료! 시작 버튼을 눌러주세요.');
});

// ============ 스케일 생성 ============

function generateScaleNotes() {
    scaleNotes = [];

    if (scaleName === 'blues') {
        for (let base = 0; base < 128; base += 12) {
            BLUES_STEPS.forEach(step => {
                const note = base + (BLUES_ROOT % 12) + step;
                if (note >= 0 && note <= 127) {
                    scaleNotes.push(note);
                }
            });
        }
    } else {
        // 크로매틱 (모든 노트)
        for (let i = 0; i <= 127; i++) {
            scaleNotes.push(i);
        }
    }

    scaleNotes.sort((a, b) => a - b);
    console.log('✅ Scale notes:', scaleNotes.length);
}

// ============ 오디오 시작 ============

async function startSinging() {
    if (isRunning) return;

    try {
        // 오디오 컨텍스트 생성
        audioContext = new (window.AudioContext || window.webkitAudioContext)({
            sampleRate: SAMPLE_RATE
        });

        // 마이크 접근
        const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: false,
                noiseSuppression: false,
                autoGainControl: false
            }
        });

        microphone = audioContext.createMediaStreamSource(stream);
        analyser = audioContext.createAnalyser();
        analyser.fftSize = BLOCK_SIZE * 2;
        analyser.smoothingTimeConstant = 0;

        // ScriptProcessor (deprecated하지만 간단함)
        scriptProcessor = audioContext.createScriptProcessor(BLOCK_SIZE, 1, 1);
        scriptProcessor.onaudioprocess = processAudio;

        microphone.connect(analyser);
        analyser.connect(scriptProcessor);
        scriptProcessor.connect(audioContext.destination);

        isRunning = true;
        document.getElementById('startBtn').disabled = true;
        document.getElementById('stopBtn').disabled = false;

        showSuccess('🎤 노래하세요!');

    } catch (error) {
        showError('마이크 접근 실패: ' + error.message);
    }
}

function stopSinging() {
    if (!isRunning) return;

    isRunning = false;

    // 현재 노트 끄기
    if (currentNote !== null) {
        sendNoteOff(currentNote, 0);
        currentNote = null;
    }

    // 오디오 정리
    if (scriptProcessor) {
        scriptProcessor.disconnect();
        scriptProcessor = null;
    }

    if (analyser) {
        analyser.disconnect();
        analyser = null;
    }

    if (microphone) {
        microphone.disconnect();
        microphone.mediaStream.getTracks().forEach(track => track.stop());
        microphone = null;
    }

    if (audioContext) {
        audioContext.close();
        audioContext = null;
    }

    allNotesOff();

    document.getElementById('startBtn').disabled = false;
    document.getElementById('stopBtn').disabled = true;
    document.getElementById('pitchDisplay').textContent = '--';
    document.getElementById('noteDisplay').textContent = '대기 중...';
    document.getElementById('frequencyDisplay').textContent = '--';

    showStatus('정지됨');
}

// ============ 오디오 처리 ============

function processAudio(event) {
    const inputData = event.inputBuffer.getChannelData(0);

    // RMS 계산
    let sumSquares = 0;
    for (let i = 0; i < inputData.length; i++) {
        sumSquares += inputData[i] * inputData[i];
    }
    const rms = Math.sqrt(sumSquares / inputData.length);

    // 노이즈 게이트
    if (rms < rmsThreshold) {
        noteHistory.push(null);
        if (noteHistory.length > WINDOW_SIZE) {
            noteHistory.shift();
        }
        handleNoteChange(rms);
        return;
    }

    // 피치 감지 (Autocorrelation)
    const freq = detectPitchAutocorr(inputData, SAMPLE_RATE);

    if (freq && freq >= MIN_FREQ && freq <= MAX_FREQ) {
        // MIDI 노트 변환
        let rawNote = frequencyToMidi(freq) + (octaveShift * 12);
        rawNote = clamp(rawNote, 0, 127);

        // 스케일에 맞춤
        const mappedNote = findClosestScaleNote(rawNote);

        noteHistory.push(mappedNote);
        if (noteHistory.length > WINDOW_SIZE) {
            noteHistory.shift();
        }

        // 디스플레이 업데이트
        document.getElementById('pitchDisplay').textContent = midiToNoteName(mappedNote);
        document.getElementById('noteDisplay').textContent = `MIDI: ${mappedNote}`;
        document.getElementById('frequencyDisplay').textContent = `${freq.toFixed(1)} Hz (RMS: ${rms.toFixed(3)})`;

        // 반주 트리거
        if (accompEnabled && scaleName === 'blues') {
            triggerAccompaniment();
        }

    } else {
        noteHistory.push(null);
        if (noteHistory.length > WINDOW_SIZE) {
            noteHistory.shift();
        }
    }

    handleNoteChange(rms);
}

// ============ 피치 감지 (Autocorrelation) ============

function detectPitchAutocorr(buffer, sampleRate) {
    // 평균 제거
    let sum = 0;
    for (let i = 0; i < buffer.length; i++) {
        sum += buffer[i];
    }
    const mean = sum / buffer.length;

    const normalized = new Float32Array(buffer.length);
    for (let i = 0; i < buffer.length; i++) {
        normalized[i] = buffer[i] - mean;
    }

    // Autocorrelation
    const correlations = new Float32Array(buffer.length);
    for (let lag = 0; lag < buffer.length; lag++) {
        let sum = 0;
        for (let i = 0; i < buffer.length - lag; i++) {
            sum += normalized[i] * normalized[i + lag];
        }
        correlations[lag] = sum;
    }

    // 첫 번째 피크 찾기
    let start = 0;
    for (let i = 1; i < correlations.length; i++) {
        if (correlations[i] > correlations[i - 1] && correlations[i - 1] <= correlations[i - 2]) {
            start = i;
            break;
        }
    }

    if (start === 0) return null;

    // 최대 피크 찾기
    let peak = start;
    let maxCorr = correlations[start];
    for (let i = start; i < correlations.length; i++) {
        if (correlations[i] > maxCorr) {
            maxCorr = correlations[i];
            peak = i;
        }
    }

    if (peak === 0) return null;

    return sampleRate / peak;
}

// ============ 노트 변경 처리 ============

function handleNoteChange(rms) {
    // Debouncing: 가장 많이 나온 노트 선택
    const counts = {};
    let maxCount = 0;
    let mostCommon = null;

    noteHistory.forEach(note => {
        const key = note === null ? 'null' : note;
        counts[key] = (counts[key] || 0) + 1;
        if (counts[key] > maxCount) {
            maxCount = counts[key];
            mostCommon = note;
        }
    });

    if (maxCount < DEBOUNCE_COUNT) return;

    // 노트 변경
    if (mostCommon === null) {
        // Note Off
        if (currentNote !== null) {
            sendNoteOff(currentNote, 0);
            console.log(`Off ${midiToNoteName(currentNote)}`);
            currentNote = null;
        }
    } else {
        // Note On/Change
        if (mostCommon !== currentNote) {
            // 이전 노트 끄기
            if (currentNote !== null) {
                sendNoteOff(currentNote, 0);
                console.log(`Off ${midiToNoteName(currentNote)}`);
            }

            // 새 노트 켜기
            const velocity = Math.min(127, Math.max(1, Math.floor(rms * velocityScale + velocityOffset)));
            sendNoteOn(mostCommon, velocity, 0);
            console.log(`On  ${midiToNoteName(mostCommon)} (vel=${velocity})`);
            currentNote = mostCommon;
        }
    }
}

// ============ 스케일 매핑 ============

function findClosestScaleNote(rawNote) {
    if (scaleNotes.length === 0) return rawNote;

    let closest = scaleNotes[0];
    let minDist = Math.abs(rawNote - closest);

    for (let i = 1; i < scaleNotes.length; i++) {
        const dist = Math.abs(rawNote - scaleNotes[i]);
        if (dist < minDist) {
            minDist = dist;
            closest = scaleNotes[i];
        }
    }

    return closest;
}

// ============ 반주 ============

function triggerAccompaniment() {
    const now = Date.now();
    if (now - lastAccompTime < 500) return; // 최소 0.5초 간격

    lastAccompTime = now;

    const rootStep = CHORD_STEPS[accompChordIdx];
    const root = BLUES_ROOT + rootStep - 12; // 한 옥타브 아래

    const chord = CHORD_INTERVALS.map(interval => root + interval);

    // 코드 재생
    chord.forEach(note => {
        if (note >= 0 && note <= 127) {
            sendNoteOn(note, 40, 1); // 채널 1, 낮은 velocity
            setTimeout(() => {
                sendNoteOff(note, 1);
            }, 400);
        }
    });

    accompChordIdx = (accompChordIdx + 1) % CHORD_STEPS.length;
    console.log(`[Accomp] Chord ${accompChordIdx}: ${chord.map(n => midiToNoteName(n)).join(', ')}`);
}
