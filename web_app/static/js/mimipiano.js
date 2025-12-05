/**
 * MimiPiano - 표정 인식으로 MIDI 변조
 * 기존 mimipiano_main.py의 JavaScript 버전
 */

// ============ 설정 ============
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
        const flat0 = parseFloat(row[1]) || null;
        const flat100 = parseFloat(row[2]) || null;
        const sharp0 = parseFloat(row[3]) || null;
        const sharp100 = parseFloat(row[4]) || null;

        expressionMap[name] = { flat0, flat100, sharp0, sharp100 };
    });

    console.log('✅ Expression map loaded:', Object.keys(expressionMap));
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
    // 서버에서 MIDI 파일 목록 가져오기 (별도 API 필요)
    // 여기서는 하드코딩된 예시
    midiFiles = {
        'C': ['song1.mid', 'song2.mid'],
        'D': ['song3.mid'],
        'E': ['song4.mid']
    };

    const keySelect = document.getElementById('keySelect');
    Object.keys(midiFiles).forEach(key => {
        const option = document.createElement('option');
        option.value = key;
        option.textContent = key;
        keySelect.appendChild(option);
    });
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
    camera = new Camera(document.createElement('video'), {
        onFrame: async () => {
            await faceDetection.send({ image: camera.g });
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

    // 확률 계산
    if (expressionMap) {
        const probs = calculateProbabilities(happyScore, specialScore);
        console.log('Expression probs:', probs);
    }
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

// ============ MIDI 재생 (간단한 버전) ============

function playMIDI() {
    if (!selectedKey || !selectedMIDI) {
        showError('MIDI 파일을 선택하세요');
        return;
    }

    showSuccess(`재생 중: ${selectedKey}/${selectedMIDI}`);
    // 실제 MIDI 파일 재생 로직은 MIDI.js 또는 다른 라이브러리 필요
    // 여기서는 간단히 알림만 표시
}

function stopMIDI() {
    allNotesOff();
    showStatus('MIDI 정지');
}
