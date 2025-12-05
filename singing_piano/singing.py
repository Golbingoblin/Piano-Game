import sounddevice as sd
import numpy as np
import mido
from mido import Message
import time
import threading
from collections import deque, Counter

# ==== 기본 설정 값 ====
SAMPLE_RATE       = 44100     # 샘플링 레이트 (Hz)
BLOCK_SIZE        = 1024      # 오디오 블록 크기
MIN_FREQ          = 80.0      # 유효 음역 최소 (Hz)
MAX_FREQ          = 1000.0    # 유효 음역 최대 (Hz)
RMS_THRESHOLD     = 0.02      # 노이즈 게이트 임계값
OCTAVE_SHIFT      = 1         # 출력 옥타브 이동 (semis)
OCTAVE_DOUBLING   = 1         # 옥타브 더블링 수 (0=none)
ACC_OCTAVE_SHIFT  = -1        # 반주 옥타브 이동 (C3 범위)
VELOCITY_SCALE    = 200.0     # RMS → MIDI velocity 스케일
VELOCITY_OFFSET   = 20.0      # velocity 오프셋

# Debounce/Median filter 설정 - 두값 모두 낮을수록 음이 불안정하게 떨림(최저 1)
WINDOW_SIZE       = 3         # 히스토리 윈도우 크기 (1 = 비활성) 
DEBOUNCE_COUNT    = 2         # 동일 노트 연속 검출 횟수 (1 = 비활성)

# 스케일 및 반주 프로그레션 설정
SCALE_NAME        = 'blues'
BLUES_ROOT        = 60        # C4 기준
CHORD_STEPS       = [0]*4 + [5]*2 + [0]*2 + [7, 5, 0, 7]
CHORD_INTERVALS   = [0, 4, 7, 10]  # 7th chord intervals

PREFERRED_MIDI_OUTS = [
    "MIDIOUT2 (ESI MIDIMATE eX) 2",
    "Microsoft GS Wavetable Synth 0"
]

NOTE_NAMES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']

# 반주 사용 여부 및 트리거 이벤트
ACCOMPANIMENT_ENABLED = False
ACC_EVENT = threading.Event()


def auto_select_midi_output():
    ports = mido.get_output_names()
    for name in PREFERRED_MIDI_OUTS:
        for port in ports:
            if name in port:
                print(f"✅ Selected MIDI Output: {port}")
                return mido.open_output(port)
    raise RuntimeError("❌ No preferred MIDI output port found.")


def freq_to_midi(freq):
    return int(round(69 + 12 * np.log2(freq / 440.0)))


def midi_to_name(m):
    return NOTE_NAMES[m % 12] + str(m // 12 - 1)


def detect_pitch_autocorr(signal, sr):
    signal = signal - np.mean(signal)
    corr = np.correlate(signal, signal, mode='full')
    corr = corr[len(corr)//2:]
    d = np.diff(corr)
    if not np.any(d > 0):
        return None
    start = np.where(d > 0)[0][0]
    peak = np.argmax(corr[start:]) + start
    if peak == 0:
        return None
    return sr / peak


def generate_scale_notes():
    if SCALE_NAME == 'blues':
        steps = [0, 3, 5, 6, 7, 10]
        notes = []
        for base in range(0, 128, 12):
            for s in steps:
                n = base + (BLUES_ROOT % 12) + s
                if 0 <= n <= 127:
                    notes.append(n)
        return sorted(set(notes))
    return list(range(128))


def accompaniment_thread(midi_out):
    progression = []
    for step in CHORD_STEPS:
        root = BLUES_ROOT + step + ACC_OCTAVE_SHIFT*12
        chord = [root + i for i in CHORD_INTERVALS]
        progression.append(chord)
    idx = 0
    print("🎹 Accompaniment thread started")
    while True:
        ACC_EVENT.wait()
        ACC_EVENT.clear()
        chord = progression[idx]
        for note in chord:
            midi_out.send(Message('note_on', note=note, velocity=4))
        print(f"▶ Chord {idx+1}: {[midi_to_name(n) for n in chord]}")
        while True:
            occurred = ACC_EVENT.wait(timeout=0.5)
            if occurred:
                ACC_EVENT.clear()
                continue
            break
        for note in chord:
            midi_out.send(Message('note_off', note=note, velocity=0))
        idx = (idx + 1) % len(progression)


def configure_settings():
    global SAMPLE_RATE, BLOCK_SIZE, MIN_FREQ, MAX_FREQ
    global RMS_THRESHOLD, OCTAVE_SHIFT, OCTAVE_DOUBLING, ACC_OCTAVE_SHIFT
    global VELOCITY_SCALE, VELOCITY_OFFSET, WINDOW_SIZE, DEBOUNCE_COUNT
    global SCALE_NAME, BLUES_ROOT, ACCOMPANIMENT_ENABLED

    print("\n== Settings Menu ==")
    try:
        val = input(f"Sample rate (Hz) [{SAMPLE_RATE}]: ")
        if val: SAMPLE_RATE = int(val)
        val = input(f"Block size [{BLOCK_SIZE}]: ")
        if val: BLOCK_SIZE = int(val)
        val = input(f"Min freq (Hz) [{MIN_FREQ}]: ")
        if val: MIN_FREQ = float(val)
        val = input(f"Max freq (Hz) [{MAX_FREQ}]: ")
        if val: MAX_FREQ = float(val)
        val = input(f"RMS threshold [{RMS_THRESHOLD}]: ")
        if val: RMS_THRESHOLD = float(val)
        val = input(f"Vocal octave shift [{OCTAVE_SHIFT}]: ")
        if val: OCTAVE_SHIFT = int(val)
        val = input(f"Octave doubling (count) [{OCTAVE_DOUBLING}]: ")
        if val: OCTAVE_DOUBLING = int(val)
        val = input(f"Accompaniment octave shift [{ACC_OCTAVE_SHIFT}]: ")
        if val: ACC_OCTAVE_SHIFT = int(val)
        val = input(f"Velocity scale [{VELOCITY_SCALE}]: ")
        if val: VELOCITY_SCALE = float(val)
        val = input(f"Velocity offset [{VELOCITY_OFFSET}]: ")
        if val: VELOCITY_OFFSET = float(val)
        val = input(f"Window size [{WINDOW_SIZE}]: ")
        if val: WINDOW_SIZE = int(val)
        val = input(f"Debounce count [{DEBOUNCE_COUNT}]: ")
        if val: DEBOUNCE_COUNT = int(val)
        val = input(f"Scale name (chromatic/blues) [{SCALE_NAME}]: ")
        if val.lower() in ['chromatic','blues']:
            SCALE_NAME = val.lower()
        if SCALE_NAME == 'blues':
            val = input(f"Blues root MIDI note [{BLUES_ROOT}]: ")
            if val: BLUES_ROOT = int(val)
    except ValueError:
        print("Invalid input—keeping previous value.")
    print("Settings applied. Returning to menu...\n")


def select_audio_input():
    devices = sd.query_devices()
    inputs = [(i, d['name']) for i, d in enumerate(devices) if d['max_input_channels'] > 0]
    print("== 🎤 Available Audio Input Devices ==")
    for idx, name in inputs:
        print(f"[{idx}] {name}")
    while True:
        try:
            choice = int(input("Select microphone device index: "))
            if any(choice == i for i, _ in inputs):
                return choice
        except ValueError:
            pass
        print("Invalid index. Try again.")


def start_streaming():
    global ACCOMPANIMENT_ENABLED
    device = select_audio_input()
    midi_out = auto_select_midi_output()
    if ACCOMPANIMENT_ENABLED and SCALE_NAME == 'blues':
        threading.Thread(target=accompaniment_thread, args=(midi_out,), daemon=True).start()

    note_history = deque(maxlen=WINDOW_SIZE)
    scale_notes = generate_scale_notes()
    is_on = False
    last_note = None

    def callback(indata, frames, time_info, status):
        nonlocal is_on, last_note
        mono = np.mean(indata, axis=1)
        rms = np.sqrt(np.mean(mono**2))
        if rms < RMS_THRESHOLD:
            note_history.append(None)
        else:
            freq = detect_pitch_autocorr(mono, SAMPLE_RATE)
            if freq and MIN_FREQ < freq < MAX_FREQ:
                raw = freq_to_midi(freq) + (OCTAVE_SHIFT * 12)
                raw = max(0, min(127, raw))
                mapped = min(scale_notes, key=lambda n: abs(n - raw))
                note_history.append(mapped)
                if ACCOMPANIMENT_ENABLED and SCALE_NAME == 'blues':
                    ACC_EVENT.set()
            else:
                note_history.append(None)

        counts = Counter(note_history)
        note, count = counts.most_common(1)[0]
        if note is None:
            if is_on and count >= DEBOUNCE_COUNT:
                for k in range(OCTAVE_DOUBLING + 1):
                    off_note = last_note + k * 12
                    if 0 <= off_note <= 127:
                        midi_out.send(Message('note_off', note=off_note, velocity=0))
                print(f"Off {midi_to_name(last_note)} (doubling {OCTAVE_DOUBLING})")
                is_on = False
                last_note = None
        else:
            if count >= DEBOUNCE_COUNT and note != last_note:
                if is_on:
                    for k in range(OCTAVE_DOUBLING + 1):
                        off_note = last_note + k * 12
                        if 0 <= off_note <= 127:
                            midi_out.send(Message('note_off', note=off_note, velocity=0))
                    print(f"Off {midi_to_name(last_note)} (doubling {OCTAVE_DOUBLING})")
                velocity = int(min(127, max(1, rms * VELOCITY_SCALE + VELOCITY_OFFSET)))
                for k in range(OCTAVE_DOUBLING + 1):
                    on_note = note + k * 12
                    if 0 <= on_note <= 127:
                        midi_out.send(Message('note_on', note=on_note, velocity=velocity))
                print(f"On  {midi_to_name(note)} (doubling {OCTAVE_DOUBLING}, vel={velocity})")
                is_on = True
                last_note = note

    with sd.InputStream(device=device, channels=1, samplerate=SAMPLE_RATE,
                        blocksize=BLOCK_SIZE, callback=callback):
        print("🎵 Start singing or humming... (Ctrl+C to stop)")
        try:
            while True:
                time.sleep(0.01)
        except KeyboardInterrupt:
            print("\n👋 Stopping...")
            if is_on:
                for k in range(OCTAVE_DOUBLING + 1):
                    off_note = last_note + k * 12
                    if 0 <= off_note <= 127:
                        midi_out.send(Message('note_off', note=off_note, velocity=0))


def main():
    global ACCOMPANIMENT_ENABLED
    while True:
        print("== Main Menu ==")
        print("1) Start Streaming")
        print("2) Settings")
        choice = input("Select option: ")
        if choice.strip() == '2':
            configure_settings()
        if SCALE_NAME == 'blues':
            resp = input("Enable accompaniment? (y/n) [y]: ")
            ACCOMPANIMENT_ENABLED = (resp.strip().lower() != 'n')
        start_streaming()

if __name__ == "__main__":
    main()
