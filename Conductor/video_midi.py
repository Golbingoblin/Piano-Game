#!/usr/bin/env python3
'''
video_midi.py
────────────────────────────────────────────────────────────────────
웹캠의 모션 강도에 따라 재생 BPM을 실시간으로 바꾸는 MIDI 플레이어
- 실행 : python video_midi.py
- 종료 : 메뉴에서 0번, 또는 카메라 창에서 q 키
────────────────────────────────────────────────────────────────────
필요 패키지 (conda env 추천)
    conda install -c conda-forge opencv
    pip install mido python-rtmidi
'''

import cv2, mido, threading, time, glob, os

# ─────────  기본값  ─────────
DEFAULT_SENSITIVITY = 10
DEFAULT_CAM_INDEX   = 0
DEFAULT_OUT_PORT    = 'MIDIOUT2 (ESI MIDIMATE eX) 2'
DEFAULT_SMOOTHING   = 0.005  # <<-- 반응 속도 기본값 추가 (값이 작을수록 부드러움)

# ───  실행 중 바뀌는 설정값들을 하나의 dict 로 보관  ───
settings = {
    'midi_file': None,
    'sensitivity': DEFAULT_SENSITIVITY,
    'cam_index':   DEFAULT_CAM_INDEX,
    'out_port':    DEFAULT_OUT_PORT,
    'smoothing':   DEFAULT_SMOOTHING, # <<-- 설정에 추가
}

motion_level = 0.0
running      = False

# ─────────  유틸  ─────────
def list_midi_files(folder='.'):
    return sorted(glob.glob(os.path.join(folder, '*.mid')))

def list_output_ports():
    return mido.get_output_names()

# ─────────  카메라 스레드 (스무딩 로직 추가) ─────────
def camera_loop():
    global motion_level, running
    cap = cv2.VideoCapture(settings['cam_index'])
    if not cap.isOpened():
        print(f'❌  카메라 {settings["cam_index"]} 을(를) 열 수 없습니다.')
        running = False
        return

    ret, prev = cap.read()
    prev_gray = cv2.cvtColor(prev, cv2.COLOR_BGR2GRAY)

    while running:
        ret, frame = cap.read()
        if not ret:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        diff = cv2.absdiff(gray, prev_gray)
        
        # ▼▼▼▼▼▼▼▼▼▼▼ 핵심 수정 부분 ▼▼▼▼▼▼▼▼▼▼▼
        # 현재 프레임의 '날것' 움직임 값을 계산
        raw_motion = diff.mean()
        
        # 기존 motion_level 값과 새로운 raw_motion 값을 부드럽게 섞음
        # smoothing 값이 작을수록 기존 값의 영향이 커져서 변화가 부드러워짐
        motion_level = (motion_level * (1 - settings['smoothing'])) + (raw_motion * settings['smoothing'])
        # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
        
        prev_gray = gray

        disp  = frame.copy()
        text  = f'Motion: {motion_level:5.1f}'
        cv2.putText(disp, text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow('Camera – press q to stop', disp)

        if cv2.waitKey(1) & 0xFF in (ord('q'), ord('Q')):
            running = False
            break

    cap.release()
    cv2.destroyAllWindows()

# ─────────  MIDI 재생 (수정된 버전) ─────────
def play_midi():
    global running
    if not settings['midi_file']:
        print('⚠️  MIDI 파일이 선택되지 않았습니다.')
        return

    mid = mido.MidiFile(settings['midi_file'])
    base_bpm = 120
    out = mido.open_output(settings['out_port'])

    for tr in mid.tracks:
        for msg in tr:
            if msg.type == 'set_tempo':
                base_bpm = mido.tempo2bpm(msg.tempo)
                break
        if base_bpm != 120:
            break

    print(f'▶️  재생 시작 – {settings["midi_file"]}  (기본 BPM = {base_bpm})')

    for msg in mid:
        if not running:
            break

        scale = min(motion_level / 30.0, 3.0)
        
        # 움직임이 없을 때(scale=0) 기본 배율이 0.5가 되도록 수정
        cur_bpm = max(1, min(base_bpm * (0.5 + settings['sensitivity'] * scale), 300))

        delay = msg.time * (base_bpm / cur_bpm)
        time.sleep(delay)

        if not msg.is_meta:
            out.send(msg)

    print('⏹  재생 종료')
    out.close()

# ─────────  세션 컨트롤  ─────────
def start_session():
    global running
    running = True
    cam_thread = threading.Thread(target=camera_loop, daemon=True)
    cam_thread.start()
    play_midi()
    running = False
    cam_thread.join()

# ─────────  터미널 메뉴 (메뉴 항목 추가) ─────────
def prompt_menu():
    while True:
        print('\n──── Video-MIDI Tempo Controller ────')
        print(f'1) MIDI 파일     : {settings["midi_file"]}')
        print(f'2) 민감도        : {settings["sensitivity"]}')
        print(f'3) 반응 속도     : {settings["smoothing"]} (작을수록 부드러움)') # <<-- 메뉴 추가
        print(f'4) 카메라 인덱스 : {settings["cam_index"]}')
        print(f'5) 출력 포트     : {settings["out_port"]}')
        print('7) ▶ 재생 시작')
        print('8) 🔄 값 초기화')
        print('0) 종료')
        choice = input('메뉴 선택 → ')

        if choice == '1':
            mids = list_midi_files()
            if not mids:
                print('⚠️  .mid 파일이 없습니다. (스크립트와 같은 폴더에 넣어 두세요)')
                continue
            for i, f in enumerate(mids):
                print(f' {i}) {f}')
            sel = input('번호 선택: ')
            if sel.isdigit() and int(sel) < len(mids):
                settings['midi_file'] = mids[int(sel)]

        elif choice == '2':
            val = input('새 민감도 (예 0.5): ')
            try:
                settings['sensitivity'] = max(0.0, float(val))
            except ValueError:
                print('잘못된 숫자입니다.')
        
        elif choice == '3': # <<-- 메뉴 로직 추가
            val = input('새 반응 속도 (0.01 ~ 1.0, 예: 0.1): ')
            try:
                settings['smoothing'] = max(0.0, min(1.0, float(val)))
            except ValueError:
                print('잘못된 숫자입니다.')

        elif choice == '4':
            val = input('카메라 인덱스 (숫자): ')
            if val.isdigit():
                settings['cam_index'] = int(val)

        elif choice == '5':
            ports = list_output_ports()
            if not ports:
                print('⚠️  사용할 수 있는 MIDI 출력 포트가 없습니다.')
                continue
            for i, p in enumerate(ports):
                print(f' {i}) {p}')
            sel = input('번호 선택: ')
            if sel.isdigit() and int(sel) < len(ports):
                settings['out_port'] = ports[int(sel)]

        elif choice == '7':
            start_session()

        elif choice == '8':
            settings.update(midi_file=None,
                            sensitivity=DEFAULT_SENSITIVITY,
                            cam_index=DEFAULT_CAM_INDEX,
                            out_port=DEFAULT_OUT_PORT,
                            smoothing=DEFAULT_SMOOTHING) # <<-- 초기화에 추가

        elif choice == '0':
            print('프로그램 종료')
            break
        else:
            print('⚠️  메뉴에 없는 번호입니다.')

# ────────  ENTRY POINT  ────────
if __name__ == '__main__':
    try:
        prompt_menu()
    except KeyboardInterrupt:
        print('\n프로그램 종료')