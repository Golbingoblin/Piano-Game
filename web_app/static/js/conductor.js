/**
 * Conductor - 모션으로 MIDI 템포 조절
 * 기존 video_midi.py의 JavaScript 버전
 */

// 설정
let sensitivity = 10;
let smoothing = 0.005;
let motionLevel = 0.0;

// 카메라
let videoStream = null;
let canvas = null;
let ctx = null;
let animationId = null;

// MIDI 재생
let selectedMidiFile = null;  // 선택된 파일 객체 저장
let parsedMidiData = null;     // 파싱된 MIDI 데이터
let isPlaying = false;
let baseBPM = 120;
let midiPlaybackInterval = null;

// 프레임 차이 계산용
let prevFrame = null;

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

    showSuccess('준비 완료! 시작 버튼을 눌러주세요.');

    // 슬라이더 이벤트
    document.getElementById('sensitivity').addEventListener('input', (e) => {
        sensitivity = parseFloat(e.target.value);
        document.getElementById('sensitivityValue').textContent = sensitivity.toFixed(1);
    });

    document.getElementById('smoothing').addEventListener('input', (e) => {
        smoothing = parseFloat(e.target.value);
        document.getElementById('smoothingValue').textContent = smoothing.toFixed(3);
    });

    // MIDI 파일 업로드
    const midiFileInput = document.getElementById('midiFile');
    const midiFileLabel = document.getElementById('midiFileLabel');

    midiFileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];

        // 파일이 선택되지 않음 (취소 버튼) → 기존 파일 유지
        if (!file) {
            console.log('파일 선택 취소됨. 기존 파일 유지:', selectedMidiFile?.name || '없음');

            // input의 files를 기존 파일로 복원 (불가능하므로 레이블만 유지)
            if (selectedMidiFile) {
                updateMidiFileLabel(selectedMidiFile.name);
            }
            return;
        }

        // 새 파일 선택됨
        selectedMidiFile = file;
        updateMidiFileLabel(file.name);

        // MIDI 파일 읽기
        const reader = new FileReader();
        reader.onload = async (event) => {
            try {
                // Tone.js Midi로 파싱
                if (typeof Midi === 'undefined') {
                    throw new Error('MIDI 라이브러리가 로드되지 않았습니다.');
                }

                const midi = await Midi.fromUrl(URL.createObjectURL(file));
                parsedMidiData = midi;

                // MIDI 파일 정보 추출
                baseBPM = midi.header.tempos[0]?.bpm || 120;

                showSuccess(`✅ MIDI 파일 로드됨: ${file.name}`);
                console.log(`MIDI 정보:`);
                console.log(`  - BPM: ${baseBPM}`);
                console.log(`  - Tracks: ${midi.tracks.length}`);
                console.log(`  - Duration: ${midi.duration.toFixed(2)}s`);

                // 트랙 정보 출력
                midi.tracks.forEach((track, idx) => {
                    console.log(`  - Track ${idx}: ${track.name || 'Unnamed'} (${track.notes.length} notes)`);
                });

            } catch (error) {
                showError('MIDI 파일 파싱 실패: ' + error.message);
                selectedMidiFile = null;
                parsedMidiData = null;
                updateMidiFileLabel('파일 없음');
                console.error('MIDI 파싱 에러:', error);
            }
        };
        reader.onerror = () => {
            showError('파일 읽기 실패');
            selectedMidiFile = null;
            parsedMidiData = null;
            updateMidiFileLabel('파일 없음');
        };
        reader.readAsArrayBuffer(file);
    });

    // 파일 선택 레이블 업데이트 함수
    function updateMidiFileLabel(filename) {
        if (midiFileLabel) {
            midiFileLabel.textContent = filename;
            midiFileLabel.style.color = '#4CAF50';
        }
    }
});

// ============ 세션 제어 ============

async function startSession() {
    if (isPlaying) return;

    // 카메라 시작
    const cameraResult = await getCameraStream({
        video: {
            width: { ideal: 1280 },
            height: { ideal: 720 }
        }
    });

    if (!cameraResult.success) {
        showError(cameraResult.error);
        return;
    }

    videoStream = cameraResult.stream;

    // 비디오 스트림을 캔버스에 표시
    const video = document.createElement('video');
    video.srcObject = videoStream;
    video.play();

    video.addEventListener('loadeddata', () => {
        isPlaying = true;
        document.getElementById('startBtn').disabled = true;
        document.getElementById('stopBtn').disabled = false;

        // MIDI 재생 타이머 초기화
        lastMidiUpdateTime = Date.now();

        if (parsedMidiData) {
            showSuccess(`재생 중: ${selectedMidiFile.name} (움직임으로 템포 조절)`);
        } else {
            showSuccess('재생 중... 움직여보세요!');
        }

        // 애니메이션 루프 시작
        animationId = requestAnimationFrame(function loop() {
            processFrame(video);
            if (isPlaying) {
                animationId = requestAnimationFrame(loop);
            }
        });
    });
}

function stopSession() {
    if (!isPlaying) return;

    isPlaying = false;

    // 카메라 정지
    if (videoStream) {
        videoStream.getTracks().forEach(track => track.stop());
        videoStream = null;
    }

    // 애니메이션 정지
    if (animationId) {
        cancelAnimationFrame(animationId);
        animationId = null;
    }

    // MIDI 재생 상태 초기화
    midiPlaybackStartTime = null;
    midiPlaybackPosition = 0;
    lastMidiUpdateTime = 0;

    // 활성 노트 끄기
    if (activeNotes && activeNotes.size > 0) {
        activeNotes.forEach(noteId => {
            const parts = noteId.split('-');
            const midi = parseInt(parts[1]);
            const trackIdx = parseInt(parts[0]);
            sendNoteOff(midi, trackIdx % 16);
        });
        activeNotes.clear();
    }

    // 모든 MIDI 노트 끄기
    allNotesOff();

    document.getElementById('startBtn').disabled = false;
    document.getElementById('stopBtn').disabled = true;
    showStatus('정지됨');

    // 캔버스 클리어
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    prevFrame = null;
}

// ============ 프레임 처리 ============

function processFrame(video) {
    // 비디오를 캔버스에 그리기
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // 현재 프레임 데이터 가져오기
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const currentFrame = imageData.data;

    // 이전 프레임이 있으면 차이 계산
    if (prevFrame) {
        const rawMotion = calculateFrameDifference(currentFrame, prevFrame);

        // 스무딩 적용 (EMA - Exponential Moving Average)
        motionLevel = motionLevel * (1 - smoothing) + rawMotion * smoothing;

        // 캔버스에 모션 레벨 표시
        ctx.fillStyle = 'rgba(0, 255, 0, 0.8)';
        ctx.font = 'bold 30px Arial';
        ctx.fillText(`Motion: ${motionLevel.toFixed(1)}`, 20, 50);

        // BPM 계산 및 표시
        const scale = Math.min(motionLevel / 30.0, 3.0);
        const currentBPM = Math.max(1, Math.min(baseBPM * (0.5 + sensitivity * scale), 300));

        ctx.fillStyle = 'rgba(255, 255, 0, 0.8)';
        ctx.fillText(`BPM: ${currentBPM.toFixed(0)}`, 20, 90);

        // MIDI 파일 상태 표시
        if (parsedMidiData) {
            ctx.fillStyle = 'rgba(100, 255, 100, 0.8)';
            ctx.font = 'bold 20px Arial';
            ctx.fillText(`📄 MIDI: ${selectedMidiFile.name}`, 20, 130);
        }

        // MIDI 출력
        if (parsedMidiData) {
            // MIDI 파일이 있으면 모션으로 재생 제어
            playMidiWithMotion(currentBPM);
        } else {
            // MIDI 파일이 없으면 실시간 비트 생성
            generateSimpleBeat(currentBPM);
        }
    }

    // 현재 프레임을 이전 프레임으로 저장
    prevFrame = new Uint8ClampedArray(currentFrame);
}

/**
 * 프레임 차이 계산 (평균 픽셀 차이)
 */
function calculateFrameDifference(current, previous) {
    let totalDiff = 0;
    const pixelCount = current.length / 4; // RGBA

    for (let i = 0; i < current.length; i += 4) {
        // 그레이스케일 변환 후 차이 계산
        const currGray = (current[i] + current[i + 1] + current[i + 2]) / 3;
        const prevGray = (previous[i] + previous[i + 1] + previous[i + 2]) / 3;
        totalDiff += Math.abs(currGray - prevGray);
    }

    return totalDiff / pixelCount;
}

// ============ 간단한 비트 생성 (MIDI 파일 없을 때) ============

let lastBeatTime = 0;
let beatNote = 60; // C4

function generateSimpleBeat(bpm) {
    const beatInterval = (60 / bpm) * 1000; // ms
    const now = Date.now();

    if (now - lastBeatTime > beatInterval) {
        // 비트 재생
        sendNoteOn(beatNote, 80, 9); // 채널 9 (드럼)
        setTimeout(() => {
            sendNoteOff(beatNote, 9);
        }, 100);

        lastBeatTime = now;

        // 다음 노트 변경 (간단한 패턴)
        beatNote = beatNote === 60 ? 64 : 60;
    }
}

// ============ MIDI 파일 재생 (모션 제어) ============

let midiPlaybackStartTime = null;
let midiPlaybackPosition = 0; // 현재 재생 위치 (초)
let activeNotes = new Set();   // 현재 재생 중인 노트
let lastMidiUpdateTime = 0;

function playMidiWithMotion(currentBPM) {
    if (!parsedMidiData || !parsedMidiData.tracks || parsedMidiData.tracks.length === 0) {
        return;
    }

    const now = Date.now();

    // 첫 재생 시작
    if (midiPlaybackStartTime === null) {
        midiPlaybackStartTime = now;
        midiPlaybackPosition = 0;
        console.log('🎵 MIDI 재생 시작');
    }

    // 모션 기반 BPM에 따른 재생 속도 조절
    const speedFactor = currentBPM / baseBPM;
    const deltaTime = (now - lastMidiUpdateTime) / 1000 * speedFactor;

    lastMidiUpdateTime = now;
    midiPlaybackPosition += deltaTime;

    // 재생 위치에 해당하는 모든 트랙의 노트 찾기
    parsedMidiData.tracks.forEach((track, trackIdx) => {
        track.notes.forEach(note => {
            const noteStart = note.time;
            const noteEnd = note.time + note.duration;

            // 현재 재생 위치에 있는 노트 찾기
            if (midiPlaybackPosition >= noteStart && midiPlaybackPosition < noteEnd) {
                const noteId = `${trackIdx}-${note.midi}-${noteStart}`;

                if (!activeNotes.has(noteId)) {
                    // Note On
                    const velocity = Math.round(note.velocity * 127);
                    sendNoteOn(note.midi, velocity, trackIdx % 16);
                    activeNotes.add(noteId);
                }
            } else if (midiPlaybackPosition >= noteEnd) {
                const noteId = `${trackIdx}-${note.midi}-${noteStart}`;

                if (activeNotes.has(noteId)) {
                    // Note Off
                    sendNoteOff(note.midi, trackIdx % 16);
                    activeNotes.delete(noteId);
                }
            }
        });
    });

    // MIDI 파일 끝에 도달하면 처음부터 다시 재생
    if (midiPlaybackPosition >= parsedMidiData.duration) {
        console.log('🔄 MIDI 루프 재생');

        // 모든 활성 노트 끄기
        activeNotes.forEach(noteId => {
            const parts = noteId.split('-');
            const midi = parseInt(parts[1]);
            const trackIdx = parseInt(parts[0]);
            sendNoteOff(midi, trackIdx % 16);
        });
        activeNotes.clear();

        // 재생 위치 초기화
        midiPlaybackPosition = 0;
        midiPlaybackStartTime = now;
    }
}
