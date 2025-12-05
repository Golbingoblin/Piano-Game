/**
 * 공통 유틸리티 - Web MIDI API, 카메라 접근 등
 */

// ============ MIDI 유틸리티 ============
let midiAccess = null;
let midiOutput = null;

/**
 * Web MIDI API 초기화
 * @param {string} preferredOutputId - 선호하는 출력 장치 ID (선택사항)
 */
async function initMIDI(preferredOutputId = null) {
    try {
        if (!navigator.requestMIDIAccess) {
            throw new Error('Web MIDI API를 지원하지 않는 브라우저입니다. Chrome 또는 Edge를 사용하세요.');
        }

        // sysex 권한 요청 (더 많은 MIDI 장치 접근 가능)
        midiAccess = await navigator.requestMIDIAccess({ sysex: false });
        console.log('✅ MIDI Access 획득');

        // 출력 포트 목록
        const outputs = Array.from(midiAccess.outputs.values());

        // 디버깅: 모든 MIDI 장치 상세 정보 출력
        console.log('🎹 감지된 MIDI 출력 장치 목록:');
        outputs.forEach((output, index) => {
            console.log(`  [${index}] ID: ${output.id}`);
            console.log(`      Name: ${output.name}`);
            console.log(`      Manufacturer: ${output.manufacturer || 'N/A'}`);
            console.log(`      State: ${output.state}`);
            console.log(`      Connection: ${output.connection}`);
            console.log('      ---');
        });

        if (outputs.length === 0) {
            throw new Error('MIDI 출력 장치가 연결되지 않았습니다.');
        }

        // 저장된 선호 장치 확인
        const savedOutputId = preferredOutputId || localStorage.getItem('preferredMidiOutput');

        // 저장된 ID로 장치 찾기
        if (savedOutputId) {
            const found = outputs.find(output => output.id === savedOutputId);
            if (found) {
                midiOutput = found;
                console.log('✅ 저장된 MIDI 출력 사용:', midiOutput.name, '(ID:', midiOutput.id + ')');
                return { success: true, outputs, selected: midiOutput };
            } else {
                console.warn('⚠️ 저장된 장치를 찾을 수 없음 (ID:', savedOutputId + '), 자동 선택으로 전환');
            }
        }

        // 자동 선택: 선호하는 포트 이름으로 검색
        // Microsoft GS Wavetable Synth를 우선 순위에 추가
        const preferredPorts = [
            'Microsoft GS Wavetable Synth',  // Windows 기본 장치
            'MIDIOUT2 (ESI MIDIMATE eX) 2',
            'MIDIOUT2',
            'ESI MIDIMATE',
            'loopMIDI',
            'IAC Driver'
        ];

        console.log('🔍 자동 선택 시도 중...');
        for (const pref of preferredPorts) {
            // 대소문자 구분 없이, 부분 일치 검색
            const found = outputs.find(output =>
                output.name.toLowerCase().includes(pref.toLowerCase())
            );
            if (found) {
                midiOutput = found;
                console.log(`✅ "${pref}" 패턴으로 장치 선택됨:`, found.name, '(ID:', found.id + ')');
                break;
            } else {
                console.log(`   "${pref}" 패턴 매칭 실패`);
            }
        }

        // 선호하는 포트가 없으면 첫 번째 포트 사용
        if (!midiOutput) {
            midiOutput = outputs[0];
            console.log('⚠️ 선호 장치 없음, 첫 번째 장치 사용:', midiOutput.name, '(ID:', midiOutput.id + ')');
        }

        console.log('✅ 최종 선택된 MIDI 출력:', midiOutput.name);
        console.log('   ID:', midiOutput.id);
        console.log('   Manufacturer:', midiOutput.manufacturer || 'N/A');
        console.log('   State:', midiOutput.state);

        return { success: true, outputs, selected: midiOutput };

    } catch (error) {
        console.error('❌ MIDI 초기화 실패:', error);
        return { success: false, error: error.message };
    }
}

/**
 * MIDI 출력 장치 변경
 * @param {string} outputId - 출력 장치 ID
 */
function selectMidiOutput(outputId) {
    if (!midiAccess) {
        console.error('MIDI가 초기화되지 않았습니다.');
        return false;
    }

    const outputs = Array.from(midiAccess.outputs.values());
    const output = outputs.find(o => o.id === outputId);

    if (!output) {
        console.error('해당 ID의 MIDI 출력을 찾을 수 없습니다:', outputId);
        return false;
    }

    // 기존 출력 종료
    allNotesOff();

    // 새 출력 설정
    midiOutput = output;
    localStorage.setItem('preferredMidiOutput', outputId);

    console.log('✅ MIDI 출력 변경:', midiOutput.name);
    return true;
}

/**
 * 모든 MIDI 출력 장치 목록 가져오기
 */
function getMidiOutputs() {
    if (!midiAccess) {
        return [];
    }
    return Array.from(midiAccess.outputs.values());
}

/**
 * MIDI 출력 선택 UI 업데이트
 * @param {HTMLSelectElement} selectElement - select 요소
 * @param {Array} outputs - MIDI 출력 장치 목록
 * @param {Object} selectedOutput - 현재 선택된 출력 장치
 */
function populateMidiSelect(selectElement, outputs, selectedOutput) {
    if (!selectElement) return;

    selectElement.innerHTML = '';

    if (outputs.length === 0) {
        selectElement.innerHTML = '<option value="">MIDI 장치 없음</option>';
        return;
    }

    outputs.forEach(output => {
        const option = document.createElement('option');
        option.value = output.id;
        option.textContent = output.name;

        // 현재 선택된 장치 표시
        if (selectedOutput && output.id === selectedOutput.id) {
            option.selected = true;
        }

        selectElement.appendChild(option);
    });

    // 선택 변경 이벤트
    selectElement.addEventListener('change', (e) => {
        const outputId = e.target.value;
        if (selectMidiOutput(outputId)) {
            const selectedName = e.target.options[e.target.selectedIndex].text;
            showSuccess(`MIDI 출력 변경: ${selectedName}`);
        } else {
            showError('MIDI 출력 변경 실패');
        }
    });
}

/**
 * MIDI Note On 전송
 */
function sendNoteOn(note, velocity, channel = 0) {
    if (!midiOutput) {
        console.warn('MIDI 출력이 초기화되지 않았습니다.');
        return;
    }

    const status = 0x90 + channel; // Note On
    midiOutput.send([status, note, velocity]);
}

/**
 * MIDI Note Off 전송
 */
function sendNoteOff(note, channel = 0) {
    if (!midiOutput) {
        console.warn('MIDI 출력이 초기화되지 않았습니다.');
        return;
    }

    const status = 0x80 + channel; // Note Off
    midiOutput.send([status, note, 0]);
}

/**
 * MIDI Control Change 전송
 */
function sendControlChange(controller, value, channel = 0) {
    if (!midiOutput) {
        console.warn('MIDI 출력이 초기화되지 않았습니다.');
        return;
    }

    const status = 0xB0 + channel; // Control Change
    midiOutput.send([status, controller, value]);
}

/**
 * 모든 노트 끄기 (All Notes Off)
 */
function allNotesOff() {
    if (!midiOutput) return;

    for (let channel = 0; channel < 16; channel++) {
        // All Notes Off (CC 123)
        sendControlChange(123, 0, channel);

        // 안전을 위해 모든 노트 개별 끄기
        for (let note = 0; note < 128; note++) {
            sendNoteOff(note, channel);
        }
    }
}

// ============ 카메라 유틸리티 ============

/**
 * 카메라 스트림 획득
 */
async function getCameraStream(constraints = { video: true }) {
    try {
        const stream = await navigator.mediaDevices.getUserMedia(constraints);
        console.log('✅ 카메라 접근 성공');
        return { success: true, stream };
    } catch (error) {
        console.error('❌ 카메라 접근 실패:', error);
        return { success: false, error: error.message };
    }
}

/**
 * 오디오 스트림 획득
 */
async function getAudioStream(constraints = { audio: true }) {
    try {
        const stream = await navigator.mediaDevices.getUserMedia(constraints);
        console.log('✅ 마이크 접근 성공');
        return { success: true, stream };
    } catch (error) {
        console.error('❌ 마이크 접근 실패:', error);
        return { success: false, error: error.message };
    }
}

// ============ CSV 로더 ============

/**
 * CSV 파일 로드 및 파싱
 */
async function loadCSV(url) {
    try {
        const response = await fetch(url);
        const text = await response.text();

        // 간단한 CSV 파싱 (헤더 없음)
        const lines = text.trim().split('\n');
        const data = lines.map(line => {
            // CSV 파싱 (따옴표 처리 포함)
            const values = [];
            let current = '';
            let inQuotes = false;

            for (let i = 0; i < line.length; i++) {
                const char = line[i];

                if (char === '"') {
                    inQuotes = !inQuotes;
                } else if (char === ',' && !inQuotes) {
                    values.push(current.trim());
                    current = '';
                } else {
                    current += char;
                }
            }
            values.push(current.trim());

            return values;
        });

        console.log(`✅ CSV 로드: ${url} (${data.length} rows)`);
        return { success: true, data };

    } catch (error) {
        console.error('❌ CSV 로드 실패:', error);
        return { success: false, error: error.message };
    }
}

// ============ UI 헬퍼 ============

/**
 * 상태 메시지 표시
 */
function showStatus(message, type = 'info') {
    const statusEl = document.getElementById('status');
    if (!statusEl) return;

    statusEl.textContent = message;
    statusEl.className = `status ${type}`;

    console.log(`[${type.toUpperCase()}] ${message}`);
}

/**
 * 에러 메시지 표시
 */
function showError(message) {
    showStatus('❌ ' + message, 'error');
}

/**
 * 성공 메시지 표시
 */
function showSuccess(message) {
    showStatus('✅ ' + message, 'success');
}

// ============ 수학 유틸리티 ============

/**
 * 값을 범위 내로 제한
 */
function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
}

/**
 * 선형 보간
 */
function lerp(a, b, t) {
    return a + (b - a) * t;
}

/**
 * 값 매핑 (한 범위에서 다른 범위로)
 */
function mapRange(value, inMin, inMax, outMin, outMax) {
    return outMin + (outMax - outMin) * ((value - inMin) / (inMax - inMin));
}

// ============ MIDI 음악 이론 ============

const NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];

/**
 * MIDI 노트 번호를 음이름으로 변환
 */
function midiToNoteName(note) {
    const octave = Math.floor(note / 12) - 1;
    const noteName = NOTE_NAMES[note % 12];
    return `${noteName}${octave}`;
}

/**
 * 주파수를 MIDI 노트 번호로 변환
 */
function frequencyToMidi(freq) {
    return Math.round(69 + 12 * Math.log2(freq / 440.0));
}

/**
 * MIDI 노트 번호를 주파수로 변환
 */
function midiToFrequency(note) {
    return 440 * Math.pow(2, (note - 69) / 12);
}

// ============ 페이지 언로드 시 정리 ============
window.addEventListener('beforeunload', () => {
    allNotesOff();
});

// ============ 터치 이벤트 최적화 ============
// 더블탭 줌 방지
document.addEventListener('touchstart', (e) => {
    if (e.touches.length > 1) {
        e.preventDefault();
    }
}, { passive: false });

let lastTouchEnd = 0;
document.addEventListener('touchend', (e) => {
    const now = Date.now();
    if (now - lastTouchEnd <= 300) {
        e.preventDefault();
    }
    lastTouchEnd = now;
}, false);
