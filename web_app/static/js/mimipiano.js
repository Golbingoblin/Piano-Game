/**
 * MimiPiano - 표정 인식으로 MIDI 변조
 * 기존 mimipiano_main.py의 JavaScript 버전
 */

// ============ 설정 ============

// 키 매핑 (음악 이론)
const KEY_STR_TO_PC = {"C":0,"Cs":1,"D":2,"Ds":3,"E":4,"F":5,"Fs":6,"G":7,"Gs":8,"A":9,"As":10,"B":11};
const MAJOR_SCALE_PCS = {1:0, 2:2, 3:4, 4:5, 5:7, 6:9, 7:11};
const MODE_TARGET_DEGREE = {"Lydian":4, "Mixolydian":7, "Dorian":3, "Aeolian":6, "Phrygian":2, "Locrian":5};
const MODE_SEMITONE_DELTA = {"Lydian":+1, "Mixolydian":-1, "Dorian":-1, "Aeolian":-1, "Phrygian":-1, "Locrian":-1};

let expressionMap = null;
let happyScore = 100;
let specialScore = 0;
let faceDetected = false;
let useCameraScore = true;

// TensorFlow.js 모델
let emotionModel = null;
const EMOTION_LABELS = ['Angry', 'Disgust', 'Fear', 'Happy', 'Neutral', 'Sad', 'Surprise'];

// MediaPipe Face Detection
let faceDetection = null;
let camera = null;
let canvas = null;
let ctx = null;
let isRunning = false;

// MIDI 파일 목록
let midiFiles = {};
let selectedKey = '';
let selectedMIDI = '';

// MIDI 재생
let isPlaying = false;
let playbackNoteMap = {};
let playbackTimeouts = [];
let currentMidiData = null;

// ============ 초기화 ============

window.addEventListener('load', async () => {
    canvas = document.getElementById('canvas');
    ctx = canvas.getContext('2d');

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

    // Expression CSV 로드
    await loadExpressionMap();

    // CNN 모델 로드 시도 (선택사항)
    await loadEmotionModel();

    // MIDI 파일 목록 로드
    await loadMIDIFileList();

    // UI 이벤트
    document.getElementById('useCameraScore').addEventListener('change', (e) => {
        useCameraScore = e.target.checked;
    });

    document.getElementById('happySlider').addEventListener('input', (e) => {
        if (!useCameraScore) {
            happyScore = parseFloat(e.target.value);
            document.getElementById('happyValue').textContent = happyScore;
            updateScoresDisplay();
        }
    });

    document.getElementById('specialSlider').addEventListener('input', (e) => {
        if (!useCameraScore) {
            specialScore = parseFloat(e.target.value);
            document.getElementById('specialValue').textContent = specialScore;
            updateScoresDisplay();
        }
    });

    document.getElementById('keySelect').addEventListener('change', (e) => {
        selectedKey = e.target.value;
        updateMIDISelect();
    });

    document.getElementById('midiSelect').addEventListener('change', (e) => {
        selectedMIDI = e.target.value;
    });

    showSuccess('준비 완료!');
});

// ============ Expression Map 로드 ============

async function loadExpressionMap() {
    const result = await loadCSV('/static/data/expression.csv');
    if (!result.success) {
        showError('expression.csv 로드 실패');
        return;
    }

    expressionMap = {};
    result.data.forEach((row, idx) => {
        if (idx === 0) return; // 헤더 스킵

        const name = row[0];

        // 빈 값은 null, 숫자는 그대로 (0도 유효한 값!)
        const parseOrNull = (val) => {
            if (val === '' || val === undefined || val === null) return null;
            const num = parseFloat(val);
            return isNaN(num) ? null : num;
        };

        const flat0 = parseOrNull(row[1]);
        const flat100 = parseOrNull(row[2]);
        const sharp0 = parseOrNull(row[3]);
        const sharp100 = parseOrNull(row[4]);

        expressionMap[name] = { flat0, flat100, sharp0, sharp100 };
    });

    console.log('✅ Expression map loaded:', Object.keys(expressionMap));
    console.log('Expression map details:', expressionMap);
}

// ============ CNN 모델 로드 ============

async function loadEmotionModel() {
    try {
        emotionModel = await tf.loadLayersModel('/static/data/tfjs_model/model.json');
        console.log('✅ CNN 모델 로드 성공');
        showSuccess('표정 인식 모델 로드됨');
    } catch (error) {
        console.warn('⚠️ CNN 모델 로드 실패 (표정 인식 비활성화):', error.message);
        showStatus('표정 인식 모델 없음 - 얼굴 감지만 수행');
    }
}

// ============ MIDI 파일 목록 로드 ============

async function loadMIDIFileList() {
    try {
        const response = await fetch('/api/midi-files');
        const data = await response.json();

        if (data.error) {
            showError('MIDI 파일 목록 로드 실패: ' + data.error);
            return;
        }

        midiFiles = data;

        const keySelect = document.getElementById('keySelect');
        keySelect.innerHTML = '<option value="">선택하세요</option>';

        Object.keys(midiFiles).sort().forEach(key => {
            const option = document.createElement('option');
            option.value = key;
            option.textContent = key + ` (${midiFiles[key].length}개)`;
            keySelect.appendChild(option);
        });

        console.log('MIDI files loaded:', Object.keys(midiFiles).length, 'keys');
    } catch (error) {
        showError('MIDI 파일 목록 로드 실패: ' + error.message);
    }
}

function updateMIDISelect() {
    const midiSelect = document.getElementById('midiSelect');
    midiSelect.innerHTML = '<option value="">선택하세요</option>';

    if (selectedKey && midiFiles[selectedKey]) {
        midiFiles[selectedKey].forEach(file => {
            const option = document.createElement('option');
            option.value = file;
            option.textContent = file;
            midiSelect.appendChild(option);
        });
    }
}

// ============ 얼굴 감지 시작 ============

async function startMimiPiano() {
    if (isRunning) return;

    // MediaPipe Face Detection 초기화
    faceDetection = new FaceDetection({
        locateFile: (file) => {
            return `https://cdn.jsdelivr.net/npm/@mediapipe/face_detection/${file}`;
        }
    });

    faceDetection.setOptions({
        model: 'short',
        minDetectionConfidence: 0.5
    });

    faceDetection.onResults(onFaceResults);

    // 카메라 시작
    const videoElement = document.createElement('video');
    camera = new Camera(videoElement, {
        onFrame: async () => {
            await faceDetection.send({ image: videoElement });
        },
        width: 920,
        height: 520
    });

    camera.start();

    isRunning = true;
    document.getElementById('startBtn').disabled = true;
    document.getElementById('stopBtn').disabled = false;

    showSuccess('얼굴 감지 시작!');
}

function stopMimiPiano() {
    if (!isRunning) return;

    isRunning = false;

    if (camera) {
        camera.stop();
        camera = null;
    }

    if (faceDetection) {
        faceDetection.close();
        faceDetection = null;
    }

    document.getElementById('startBtn').disabled = false;
    document.getElementById('stopBtn').disabled = true;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    showStatus('정지됨');
}

// ============ 얼굴 결과 처리 ============

async function onFaceResults(results) {
    if (!isRunning) return;

    // 캔버스 클리어
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // 비디오 프레임 그리기
    ctx.drawImage(results.image, 0, 0, canvas.width, canvas.height);

    // 얼굴 감지
    faceDetected = results.detections && results.detections.length > 0;

    if (faceDetected) {
        const detection = results.detections[0];
        const bbox = detection.boundingBox;

        // 바운딩 박스 그리기
        ctx.strokeStyle = '#00FF00';
        ctx.lineWidth = 3;
        ctx.strokeRect(
            bbox.xCenter * canvas.width - bbox.width * canvas.width / 2,
            bbox.yCenter * canvas.height - bbox.height * canvas.height / 2,
            bbox.width * canvas.width,
            bbox.height * canvas.height
        );

        // CNN 모델이 있으면 표정 인식
        if (emotionModel && useCameraScore) {
            await predictEmotion(results.image, bbox);
        } else if (useCameraScore) {
            // 모델 없으면 기본값
            happyScore = 50;
            specialScore = 10;
        }

    } else {
        // 얼굴 없으면 기본값
        if (useCameraScore) {
            happyScore = 100;
            specialScore = 0;
        }
    }

    // 슬라이더 동기화
    if (useCameraScore) {
        document.getElementById('happySlider').value = happyScore;
        document.getElementById('happyValue').textContent = happyScore.toFixed(0);
        document.getElementById('specialSlider').value = specialScore;
        document.getElementById('specialValue').textContent = specialScore.toFixed(0);
    }

    updateScoresDisplay();
}

// ============ 표정 예측 ============

async function predictEmotion(image, bbox) {
    try {
        // 얼굴 영역 크롭
        const x = Math.floor((bbox.xCenter - bbox.width / 2) * canvas.width);
        const y = Math.floor((bbox.yCenter - bbox.height / 2) * canvas.height);
        const w = Math.floor(bbox.width * canvas.width);
        const h = Math.floor(bbox.height * canvas.height);

        // 캔버스에서 이미지 데이터 가져오기
        const faceData = ctx.getImageData(x, y, w, h);

        // TensorFlow.js 텐서로 변환
        let tensor = tf.browser.fromPixels(faceData, 1); // 그레이스케일
        tensor = tf.image.resizeBilinear(tensor, [48, 48]);
        tensor = tensor.div(255.0).expandDims(0);

        // 예측
        const prediction = await emotionModel.predict(tensor);
        const scores = await prediction.data();

        // 점수 계산
        const emotionScores = {};
        EMOTION_LABELS.forEach((label, idx) => {
            emotionScores[label] = scores[idx];
        });

        const happy = 100 * (
            0.9 * (emotionScores['Happy'] || 0) +
            0.5 * (emotionScores['Neutral'] || 0) +
            0.2 * (emotionScores['Surprise'] || 0)
        );

        const special = 100 * (emotionScores['Surprise'] || 0);

        happyScore = happy;
        specialScore = special;

        // 감정 표시
        const maxEmotion = EMOTION_LABELS[scores.indexOf(Math.max(...scores))];
        document.getElementById('emotionDisplay').textContent = `감정: ${maxEmotion}`;

        // 메모리 정리
        tensor.dispose();
        prediction.dispose();

    } catch (error) {
        console.error('표정 예측 실패:', error);
    }
}

// ============ 디스플레이 업데이트 ============

function updateScoresDisplay() {
    document.getElementById('scoresDisplay').textContent =
        `Happy: ${happyScore.toFixed(0)} / Special: ${specialScore.toFixed(0)}`;
    document.getElementById('faceDisplay').textContent =
        `얼굴 감지: ${faceDetected ? '✅' : '❌'}`;

    // 확률 계산 및 표시
    if (expressionMap) {
        const probs = calculateProbabilities(happyScore, specialScore);

        // 확률이 0보다 큰 모드만 필터링
        const activeProbs = Object.entries(probs)
            .filter(([mode, prob]) => prob > 0)
            .map(([mode, prob]) => `${mode}:${(prob * 100).toFixed(0)}%`)
            .join(', ');

        if (activeProbs) {
            console.log(`[PROBS] ${activeProbs}`);
        }
    }
}

// ============ 음악 이론 함수 ============

function pc(note) {
    return note % 12;
}

function nearestMajorDegreePitchclass(rootPC, pitchPC) {
    const rel = (pitchPC - rootPC + 12) % 12;
    for (const [deg, off] of Object.entries(MAJOR_SCALE_PCS)) {
        if (rel === off) {
            return parseInt(deg);
        }
    }
    return null;
}

function maybeAlter(note, rootPC, probs) {
    const pitchPC = pc(note);
    const deg = nearestMajorDegreePitchclass(rootPC, pitchPC);

    if (!deg) return note;

    for (const [mode, targetDeg] of Object.entries(MODE_TARGET_DEGREE)) {
        if (deg === targetDeg && Math.random() < (probs[mode] || 0)) {
            const altered = note + MODE_SEMITONE_DELTA[mode];
            console.log(`[ALTER] Note ${note} -> ${altered} (${mode}, deg=${deg}, prob=${probs[mode]})`);
            return Math.max(0, Math.min(127, altered));
        }
    }

    return note;
}

// ============ 확률 계산 ============

function calculateProbabilities(happiness, special) {
    const probs = {};

    if (!expressionMap) return probs;

    Object.keys(expressionMap).forEach(name => {
        const { flat0, flat100, sharp0, sharp100 } = expressionMap[name];

        if (name !== 'Lydian' && flat0 !== null && flat100 !== null) {
            let p;
            if (happiness >= flat0) {
                p = 0.0;
            } else if (happiness <= flat100) {
                p = 1.0;
            } else {
                p = (flat0 - happiness) / (flat0 - flat100);
            }
            probs[name] = clamp(p, 0, 1);
        }

        if (name === 'Lydian' && sharp0 !== null && sharp100 !== null) {
            let p;
            if (special <= sharp0) {
                p = 0.0;
            } else if (special >= sharp100) {
                p = 1.0;
            } else {
                p = (special - sharp0) / (sharp100 - sharp0);
            }
            probs[name] = clamp(p, 0, 1);
        }
    });

    return probs;
}

// ============ MIDI 재생 ============

async function playMIDI() {
    if (!selectedKey || !selectedMIDI) {
        showError('MIDI 파일을 선택하세요');
        return;
    }

    if (isPlaying) {
        stopMIDI();
    }

    try {
        showStatus(`로딩 중: ${selectedKey}/${selectedMIDI}`);

        // 루트 피치 클래스 계산 (키 이름에서 추출)
        const rootPC = KEY_STR_TO_PC[selectedKey] || 0;
        console.log(`[MIDI] Key: ${selectedKey}, Root PC: ${rootPC}`);

        // playbackNoteMap 초기화
        playbackNoteMap = {};

        // MIDI 파일 가져오기
        const response = await fetch(`/api/midi-file/${selectedKey}/${selectedMIDI}`);
        if (!response.ok) {
            throw new Error('MIDI 파일 로드 실패');
        }

        const arrayBuffer = await response.arrayBuffer();
        currentMidiData = await Midi.fromUrl(URL.createObjectURL(new Blob([arrayBuffer])));

        showSuccess(`재생 중: ${selectedMIDI}`);
        isPlaying = true;

        // 모든 트랙의 노트를 시간순으로 정렬
        const allNotes = [];
        currentMidiData.tracks.forEach((track, trackIdx) => {
            track.notes.forEach(note => {
                allNotes.push({
                    time: note.time,
                    duration: note.duration,
                    midi: note.midi,
                    velocity: note.velocity,
                    trackIdx
                });
            });
        });

        allNotes.sort((a, b) => a.time - b.time);

        // 스케줄링
        const startTime = Date.now();
        allNotes.forEach(note => {
            const timeout = setTimeout(() => {
                if (!isPlaying) return;

                // 현재 행복/특별 점수로 확률 계산
                const probs = calculateProbabilities(happyScore, specialScore);

                // 노트 변조
                const alteredNote = maybeAlter(note.midi, rootPC, probs);
                playbackNoteMap[note.midi] = alteredNote;

                // 노트 온
                const velocity = Math.floor(note.velocity * 127);
                sendNoteOn(alteredNote, velocity, 0);

                // 노트 오프 스케줄링
                const offTimeout = setTimeout(() => {
                    if (!isPlaying) return;
                    const noteToStop = playbackNoteMap[note.midi] || note.midi;
                    sendNoteOff(noteToStop, 0);
                    delete playbackNoteMap[note.midi];
                }, note.duration * 1000);

                playbackTimeouts.push(offTimeout);
            }, note.time * 1000);

            playbackTimeouts.push(timeout);
        });

        // 재생 종료 처리
        const totalDuration = allNotes.length > 0 ? allNotes[allNotes.length - 1].time + allNotes[allNotes.length - 1].duration : 0;
        const endTimeout = setTimeout(() => {
            stopMIDI();
            showSuccess('재생 완료');
        }, totalDuration * 1000 + 500);

        playbackTimeouts.push(endTimeout);

    } catch (error) {
        showError('MIDI 재생 실패: ' + error.message);
        console.error('MIDI playback error:', error);
        isPlaying = false;
    }
}

function stopMIDI() {
    // 모든 타이머 취소
    playbackTimeouts.forEach(timeout => clearTimeout(timeout));
    playbackTimeouts = [];

    // 모든 노트 오프
    allNotesOff();

    // 노트 매핑 초기화
    playbackNoteMap = {};

    isPlaying = false;
    showStatus('MIDI 정지');
}
