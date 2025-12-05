/**
 * AirPiano - 손 제스처로 MIDI 연주
 * 기존 airpiano_gui.py의 JavaScript 버전
 */

// ============ 설정 ============
const DEBUG = true;
const MIRROR = true;
let BPM = 120;
let BEAT_SEC = 60.0 / BPM;

// MIDI 설정
const LEFT_CH = 1, RIGHT_CH = 0;
const VEL_MIN = 40, VEL_MAX = 120;
const LEFT_LOW = 40, LEFT_HIGH = 96;
const RIGHT_LOW = 40, RIGHT_HIGH = 96;

// 손가락 인식
const SMOOTH_ALPHA = 0.35;
const FINGER_PRESS_DEG = 165;
const FINGER_RELEASE_DEG = 175;
const FINGER_COUNT = 5;

// 음악 이론
const NOTE_NAMES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];
const NAME2PC = {
    'C':0,'B#':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'Fb':4,
    'F':5,'E#':5,'F#':6,'Gb':6,'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11,'Cb':11
};

// 파티클 설정
const MAX_PARTICLES = 140;
const PARTICLE_LIFE = [0.8, 1.8];
const PARTICLE_SPEED = [70, 170];
const PARTICLE_SIZE = [6, 16];
const GRAVITY = 40.0;

// ============ 상태 ============
let isRunning = false;
let isPaused = false;

let chordTables = null;
let progressions = [];
let currentProgIdx = 0;
let currentStep = 0;
let lastChord = '';
let bassOnce = false;

// 손 상태
let leftHand = createHandState('Left', LEFT_CH, LEFT_LOW, LEFT_HIGH);
let rightHand = createHandState('Right', RIGHT_CH, RIGHT_LOW, RIGHT_HIGH);

// 파티클 시스템
let particles = [];

// MediaPipe
let hands = null;
let camera = null;
let canvas = null;
let ctx = null;

// 비트 클럭
let lastBeatTime = Date.now();

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

    // CSV 로드
    await loadChordData();
    await loadProgressionData();

    if (progressions.length === 0) {
        showError('progression.CSV를 로드할 수 없습니다.');
        return;
    }

    // 랜덤 progression 선택
    currentProgIdx = Math.floor(Math.random() * progressions.length);

    // BPM 슬라이더
    document.getElementById('bpm').addEventListener('input', (e) => {
        BPM = parseInt(e.target.value);
        BEAT_SEC = 60.0 / BPM;
        document.getElementById('bpmValue').textContent = BPM;
    });

    showSuccess('준비 완료! 시작 버튼을 눌러주세요.');
});

// ============ 손 상태 객체 ============

function createHandState(label, channel, low, high) {
    return {
        label,
        channel,
        low,
        high,
        present: false,
        ema: null,
        down: 0,
        prevDown: 0,
        fingerDown: new Array(FINGER_COUNT).fill(false),
        pressedNow: 0,
        active: new Set(),
        pcs: []
    };
}

// ============ CSV 로드 ============

async function loadChordData() {
    const result = await loadCSV('/static/data/chord.CSV');
    if (!result.success) {
        showError('chord.CSV 로드 실패');
        return;
    }

    chordTables = {};
    result.data.forEach(row => {
        const chordName = row[0];
        if (!chordName || chordName === 'nan') return;

        const tags = {};
        NOTE_NAMES.forEach((noteName, idx) => {
            const tag = (row[idx + 1] || '').trim().toUpperCase();
            tags[noteName] = tag;
        });

        chordTables[chordName] = tags;
    });

    if (DEBUG) console.log('✅ Chord tables loaded:', Object.keys(chordTables).length);
}

async function loadProgressionData() {
    const result = await loadCSV('/static/data/progression.CSV');
    if (!result.success) {
        showError('progression.CSV 로드 실패');
        return;
    }

    result.data.forEach((row, i) => {
        const name = row[0] || `Row${i}`;
        const seq = row.slice(1, 33).filter(x => x && x !== 'nan');
        if (seq.length > 0) {
            progressions.push({ name, seq });
        }
    });

    if (DEBUG) console.log('✅ Progressions loaded:', progressions.length);
}

// ============ 음악 로직 ============

function allowedPCs(chordName, mono, excludePC = null) {
    if (!chordTables[chordName]) return [];

    const tags = mono ? ['1','2','3','4','5','6','7','T','L'] : ['1','2','3','4','5','6','7','T','L'];
    const forbid = ['A', ''];

    const pcs = [];
    NOTE_NAMES.forEach((noteName, pc) => {
        const tag = chordTables[chordName][noteName];
        if (forbid.includes(tag)) return;
        if (tags.includes(tag) && (excludePC === null || pc !== excludePC)) {
            pcs.push(pc);
        }
    });

    return pcs;
}

function bassPC(chordName) {
    const parts = chordName.split('/');
    const base = parts[0];

    // Slash chord
    if (parts[1]) {
        return NAME2PC[parts[1]] || null;
    }

    // Root note
    if (!chordTables[base]) return null;

    for (let pc = 0; pc < 12; pc++) {
        const noteName = NOTE_NAMES[pc];
        if (chordTables[base][noteName] === '1') {
            return pc;
        }
    }

    return null;
}

function xToCenter(x, low, high) {
    x = Math.max(0, Math.min(1, x));
    return Math.round(low + x * (high - low));
}

function nearestNote(pc, center, low, high) {
    let best = null;
    let bestDist = 1e9;

    for (let k = 0; k < 10; k++) {
        const note = pc + 12 * k;
        if (note >= low && note <= high) {
            const dist = Math.abs(note - center);
            if (dist < bestDist) {
                bestDist = dist;
                best = note;
            }
        }
    }

    return best;
}

function lowestNote(pc, low, high) {
    for (let k = 0; k < 10; k++) {
        const note = pc + 12 * k;
        if (note >= low && note <= high) {
            return note;
        }
    }
    return null;
}

function velocity(center, low, high) {
    const mid = (low + high) / 2;
    const dist = Math.abs(center - mid) / Math.max(1, (high - low) / 2);
    const v = Math.floor(VEL_MAX - (VEL_MAX - VEL_MIN) * Math.min(1, dist));
    return Math.max(VEL_MIN, Math.min(VEL_MAX, v));
}

// ============ MediaPipe 시작 ============

async function startAirPiano() {
    if (isRunning) return;

    // MediaPipe Hands 초기화
    hands = new Hands({
        locateFile: (file) => {
            return `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`;
        }
    });

    hands.setOptions({
        maxNumHands: 2,
        modelComplexity: 1,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5
    });

    hands.onResults(onHandsResults);

    // 카메라 시작
    camera = new Camera(document.createElement('video'), {
        onFrame: async () => {
            await hands.send({ image: camera.g });
        },
        width: 1280,
        height: 720
    });

    camera.start();

    isRunning = true;
    document.getElementById('startBtn').disabled = true;
    document.getElementById('pauseBtn').disabled = false;
    document.getElementById('changeBtn').disabled = false;

    showSuccess('연주 중! 손을 카메라에 보여주세요.');

    // 비트 클럭 시작
    setInterval(advanceStep, BEAT_SEC * 1000);
}

function togglePause() {
    isPaused = !isPaused;
    document.getElementById('pauseBtn').textContent = isPaused ? '▶ 재개' : '⏸ 일시 중지';

    if (isPaused) {
        // 모든 노트 끄기
        leftHand.active.forEach(note => sendNoteOff(note, LEFT_CH));
        rightHand.active.forEach(note => sendNoteOff(note, RIGHT_CH));
        leftHand.active.clear();
        rightHand.active.clear();
        showStatus('일시 중지됨');
    } else {
        showSuccess('재개됨');
    }
}

function changeProgression() {
    currentProgIdx = Math.floor(Math.random() * progressions.length);
    currentStep = 0;
    lastChord = '';
    bassOnce = false;
    showSuccess(`분위기 전환: ${progressions[currentProgIdx].name}`);
}

// ============ 비트 진행 ============

function advanceStep() {
    if (isPaused || !isRunning) return;

    const seq = progressions[currentProgIdx].seq;
    if (seq.length === 0) return;

    currentStep = (currentStep + 1) % seq.length;
}

// ============ MediaPipe 결과 처리 ============

function onHandsResults(results) {
    if (!isRunning) return;

    // 캔버스 클리어
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // 비디오 프레임 그리기
    ctx.save();
    if (MIRROR) {
        ctx.scale(-1, 1);
        ctx.translate(-canvas.width, 0);
    }
    ctx.drawImage(results.image, 0, 0, canvas.width, canvas.height);
    ctx.restore();

    // 파티클 업데이트 및 렌더링
    updateParticles(1 / 30); // 30 FPS 가정
    renderParticles();

    // 손 리셋
    leftHand.present = false;
    rightHand.present = false;

    // 손 감지
    if (results.multiHandLandmarks && results.multiHandedness) {
        for (let i = 0; i < results.multiHandLandmarks.length; i++) {
            const landmarks = results.multiHandLandmarks[i];
            const handedness = results.multiHandedness[i].label; // 'Left' or 'Right'

            const hand = handedness === 'Left' ? leftHand : rightHand;
            hand.present = true;

            processHand(hand, landmarks);

            // 손 랜드마크 그리기 (옵션)
            // drawConnectors(ctx, landmarks, HAND_CONNECTIONS, {color: '#00FF00', lineWidth: 2});
            // drawLandmarks(ctx, landmarks, {color: '#FF0000', lineWidth: 1});
        }
    }

    // 코드 진행
    const seq = progressions[currentProgIdx].seq;
    const chord = seq[currentStep % seq.length];
    const chordChanged = chord !== lastChord;

    if (chordChanged) {
        lastChord = chord;
        bassOnce = false;
        if (DEBUG) console.log(`[BEAT] Step=${currentStep + 1}/${seq.length} Chord=${chord}`);
    }

    // PCs 재샘플링
    [leftHand, rightHand].forEach(hand => {
        if (!hand.present) {
            hand.prevDown = 0;
            hand.pcs = [];
            return;
        }

        if ((hand.prevDown === 0 && hand.down > 0) || hand.pressedNow > 0) {
            const n = hand.pressedNow > 0 ? hand.pressedNow : 1;
            const mono = n === 1;
            const pcs = allowedPCs(chord, mono);

            if (pcs.length > 0) {
                // 랜덤 샘플링
                const k = Math.min(n, pcs.length);
                hand.pcs = [];
                const shuffled = [...pcs].sort(() => Math.random() - 0.5);
                for (let j = 0; j < k; j++) {
                    hand.pcs.push(shuffled[j]);
                }

                if (DEBUG && hand.pcs.length > 0) {
                    console.log(`[PICK] ${hand.label} down=${hand.down} pcs=${hand.pcs}`);
                }
            }
        }

        hand.prevDown = hand.down;
    });

    // MIDI 적용
    if (!isPaused) {
        const extraBassPC = null; // 베이스 로직 간소화
        applyHand(leftHand, extraBassPC);
        applyHand(rightHand, null);
    }
}

// ============ 손 처리 ============

function processHand(hand, landmarks) {
    // Wrist smoothing
    const wrist = landmarks[0];
    if (!hand.ema) {
        hand.ema = [wrist.x, wrist.y];
    } else {
        hand.ema[0] = SMOOTH_ALPHA * wrist.x + (1 - SMOOTH_ALPHA) * hand.ema[0];
        hand.ema[1] = SMOOTH_ALPHA * wrist.y + (1 - SMOOTH_ALPHA) * hand.ema[1];
    }

    // 손가락 인식
    const fingerIndices = [
        [2, 3, 4],    // Thumb
        [5, 6, 8],    // Index
        [9, 10, 12],  // Middle
        [13, 14, 16], // Ring
        [17, 18, 20]  // Pinky
    ];

    let downCount = 0;
    let pressedNow = 0;

    fingerIndices.forEach((indices, idx) => {
        const [mcp, pip, tip] = indices.map(i => landmarks[i]);

        // 각도 계산
        const v1 = [mcp.x - pip.x, mcp.y - pip.y];
        const v2 = [tip.x - pip.x, tip.y - pip.y];
        const dot = v1[0] * v2[0] + v1[1] * v2[1];
        const n1 = Math.hypot(v1[0], v1[1]);
        const n2 = Math.hypot(v2[0], v2[1]);
        const angle = (n1 === 0 || n2 === 0) ? 0 : Math.acos(clamp(dot / (n1 * n2), -1, 1)) * 180 / Math.PI;

        const was = hand.fingerDown[idx];
        let nowDown = was;

        if (was) {
            if (angle >= FINGER_RELEASE_DEG) {
                nowDown = false;
            }
        } else {
            if (angle <= FINGER_PRESS_DEG) {
                nowDown = true;
                pressedNow++;

                // 파티클 생성
                const px = tip.x * canvas.width;
                const py = tip.y * canvas.height;
                spawnParticles(px, py, Math.floor(Math.random() * 7) + 6);
            }
        }

        hand.fingerDown[idx] = nowDown;
        if (nowDown) downCount++;
    });

    hand.down = downCount;
    hand.pressedNow = pressedNow;
}

// ============ MIDI 적용 ============

function applyHand(hand, extraBassPC) {
    if (!hand.present || hand.down === 0 || isPaused) {
        // 모든 노트 끄기
        hand.active.forEach(note => sendNoteOff(note, hand.channel));
        hand.active.clear();
        return;
    }

    const x = hand.ema ? hand.ema[0] : 0.5;
    const center = xToCenter(x, hand.low, hand.high);
    const vel = velocity(center, hand.low, hand.high);

    const want = new Set();

    // 선택된 PCs를 MIDI 노트로 변환
    hand.pcs.forEach(pc => {
        const note = nearestNote(pc, center, hand.low, hand.high);
        if (note !== null) {
            want.add(note);
        }
    });

    // 베이스 추가 (왼손만)
    if (extraBassPC !== null && hand.label === 'Left') {
        const bassNote = lowestNote(extraBassPC, hand.low, hand.high);
        if (bassNote !== null) {
            want.add(bassNote);
        }
    }

    // Note Off
    hand.active.forEach(note => {
        if (!want.has(note)) {
            sendNoteOff(note, hand.channel);
            hand.active.delete(note);
        }
    });

    // Note On
    want.forEach(note => {
        if (!hand.active.has(note)) {
            sendNoteOn(note, vel, hand.channel);
            hand.active.add(note);
        }
    });
}

// ============ 파티클 시스템 ============

function spawnParticles(x, y, count) {
    for (let i = 0; i < count; i++) {
        const speed = Math.random() * (PARTICLE_SPEED[1] - PARTICLE_SPEED[0]) + PARTICLE_SPEED[0];
        const angle = -Math.PI / 2 + (Math.random() - 0.5) * 1.6;
        const vx = speed * Math.cos(angle);
        const vy = speed * Math.sin(angle);
        const life = Math.random() * (PARTICLE_LIFE[1] - PARTICLE_LIFE[0]) + PARTICLE_LIFE[0];
        const size = Math.floor(Math.random() * (PARTICLE_SIZE[1] - PARTICLE_SIZE[0]) + PARTICLE_SIZE[0]);
        const r = Math.floor(Math.random() * 156) + 100;
        const g = Math.floor(Math.random() * 156) + 100;
        const b = Math.floor(Math.random() * 156) + 100;

        particles.push({ x, y, vx, vy, r, g, b, size, life, maxLife: life });
    }

    // 개수 제한
    if (particles.length > MAX_PARTICLES) {
        particles = particles.slice(-MAX_PARTICLES);
    }
}

function updateParticles(dt) {
    particles = particles.filter(p => {
        p.vy += GRAVITY * dt;
        p.x += p.vx * dt;
        p.y += p.vy * dt;
        p.life -= dt;

        return p.x >= 0 && p.x < canvas.width && p.y >= 0 && p.y < canvas.height && p.life > 0;
    });
}

function renderParticles() {
    particles.forEach(p => {
        const alpha = Math.max(0, Math.min(1, p.life / p.maxLife));
        ctx.save();
        ctx.globalAlpha = alpha * 0.7;
        ctx.fillStyle = `rgb(${p.r}, ${p.g}, ${p.b})`;
        ctx.beginPath();
        ctx.ellipse(p.x, p.y, p.size, p.size * 0.6, (1 - alpha) * Math.PI, 0, 2 * Math.PI);
        ctx.fill();
        ctx.restore();
    });
}
