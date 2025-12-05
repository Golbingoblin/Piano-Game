#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AirPiano GUI (Tkinter + OpenCV + MediaPipe + MIDI + Particle Effects)

요구사항 반영:
- 카메라 프리뷰: 창의 최상단 중앙 배치, 16:9 비율 유지, 카메라 해상도에 맞춤
- "AirPiano" 제목 라벨
- "분위기 전환" 버튼: progression 무작위 재선택
- "일시 중지" 버튼(토글): MIDI 상호작용/이펙트 정지; 카메라 프리뷰는 계속 표시
- 손가락 인식 트리거 시 카메라 프레임 내부에서 다채로운(랜덤 컬러) 꽃잎 파티클 이펙트
- chord.CSV, progression.CSV를 exe 옆(동일 폴더)에서 상대경로로 그대로 로드

주의:
- 파이썬 실행 시: python -u airpiano_gui.py
- exe 빌드 시: pyinstaller --onefile --noconsole airpiano_gui.py
"""

from __future__ import annotations
import os, sys, time, math, random, threading, traceback
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Set
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import mido

# GUI
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

# Vision
import mediapipe as mp

# ===================== Config =====================
DEBUG = True

# CSV paths (상대경로 그대로)
CHORD_CSV_PATH = 'chord.CSV'
PROG_CSV_PATH  = 'progression.CSV'

# Window / Camera
MIRROR = True        # 좌우 반전 (기존 행동 유지)
CAMERA_TRY_IDS = [0, 1, 2]
FRAME_W, FRAME_H = 1280, 720  # 첫 시도 프레임; 실제는 카메라 해상도에 맞춤
KEEP_ASPECT = (16, 9)         # 16:9 고정 (표시 비율)

# BPM & Clock
BPM = 120.0
BEAT_SEC = 60.0 / BPM
STEPS_PER_BEAT = 1  # 1 step = 1 beat

# MIDI
PREFERRED_OUT_PORTS = ["MIDIOUT2 (ESI MIDIMATE eX) 2", "Microsoft GS Wavetable Synth"]
LEFT_CH, RIGHT_CH = 1, 0
VEL_MIN, VEL_MAX = 40, 120

# Registers (MIDI note numbers)
LEFT_LOW, LEFT_HIGH   = 40, 96
RIGHT_LOW, RIGHT_HIGH = 40, 96

# Vision: wrist smoothing
SMOOTH_ALPHA = 0.35

# Finger press/release hysteresis (deg). 180≈straight, smaller=curled
FINGER_PRESS_DEG   = 165  # <= press
FINGER_RELEASE_DEG = 175  # >= release
USE_THUMB = True

# Windows
SIMUL_WINDOW_MS = 100
JUST_PRESSED_MS = SIMUL_WINDOW_MS

# Tag sets
POLY_TAGS = {'1','2','3','4','5','6','7','T','L'}
MONO_TAGS = POLY_TAGS
FORBID_TAGS = {'A',''}
LEGACY_TO_T = {'2','4','6'}

NOTE_NAMES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
NAME2PC = {
    'C':0,'B#':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'Fb':4,
    'F':5,'E#':5,'F#':6,'Gb':6,'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11,'Cb':11
}

# Particle (꽃잎) 설정
MAX_PARTICLES = 140
PARTICLE_LIFE = (0.8, 1.8)      # sec
PARTICLE_SPEED = (70, 170)      # px/sec 초기 속도 범위
PARTICLE_SIZE = (6, 16)         # 지름(px)
PARTICLE_FADE = 1.0             # life에 따른 투명도 감소
GRAVITY = 40.0                  # 약한 중력(아래 방향 +y)

# ===================== CSV Loaders =====================
_PREFERRED_ENCODINGS = ['utf-8-sig', 'cp949', 'euc-kr', 'cp932', 'utf-16', 'latin1']

def read_csv_headerless(path: str) -> pd.DataFrame:
    last = None
    for enc in _PREFERRED_ENCODINGS:
        try:
            df = pd.read_csv(path, encoding=enc, engine='python', header=None)
            if DEBUG:
                print(f"[CSV] Loaded {path} (encoding={enc}, shape={df.shape})", flush=True)
            return df
        except Exception as e:
            last = e
    raise last if last else RuntimeError(f"Failed to read CSV: {path}")

def norm_tag(x) -> str:
    if pd.isna(x):
        return ''
    s = str(x).strip().upper()
    if s in LEGACY_TO_T:
        return 'T'
    return s

class ChordTables:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    @staticmethod
    def load(chord_csv_path: str) -> 'ChordTables':
        raw = read_csv_headerless(chord_csv_path)
        if raw.shape[1] < 13:
            raise ValueError("chord.CSV needs 13 columns (name + 12 PCs).")
        cols = ['Chord'] + NOTE_NAMES
        df = raw.iloc[:, :13].copy()
        df.columns = cols
        for n in NOTE_NAMES:
            df[n] = df[n].map(norm_tag)
        df = df.dropna(subset=['Chord'])
        df['Chord'] = df['Chord'].astype(str).str.strip()
        df = df[~df['Chord'].isin(['', 'nan'])]
        df = df.drop_duplicates(subset=['Chord'], keep='first').set_index('Chord')
        if DEBUG:
            print(f"[CSV] chord.CSV unique chords: {len(df.index)}", flush=True)
        return ChordTables(df)

    def row(self, chord_name: str) -> Optional[pd.Series]:
        base = chord_name.split('/', 1)[0].strip()
        if base in self.df.index:
            r = self.df.loc[base]
            return r if not isinstance(r, pd.DataFrame) else r.iloc[0]
        return None

def load_progressions(path: str) -> List[dict]:
    raw = read_csv_headerless(path)
    progs = []
    for i in range(len(raw)):
        row = raw.iloc[i].tolist()
        name = str(row[0]).strip() if str(row[0]).strip() else f"Row{i}"
        seq = []
        for x in row[1:33]:  # 최대 32스텝
            if pd.isna(x):
                continue
            s = str(x).strip()
            if not s or s.lower() == 'nan':
                continue
            seq.append(s)
        if seq:
            progs.append({'name': name, 'seq': seq})
    if DEBUG:
        print(f"[CSV] progression.CSV rows loaded: {len(progs)}", flush=True)
        if progs:
            print(f"[CSV] progression[0]: name={progs[0]['name']}, first4={progs[0]['seq'][:4]}", flush=True)
    return progs

# ===================== Music helpers =====================
HAND_FINGERS = [(5,6,8),(9,10,12),(13,14,16),(17,18,20)]
if USE_THUMB:
    HAND_FINGERS = [(2,3,4)] + HAND_FINGERS
_FINGER_COUNT = len(HAND_FINGERS)

def allowed_pcs(name: str, tables: ChordTables, mono: bool, exclude: Optional[int]=None) -> List[int]:
    row = tables.row(name)
    if row is None:
        return []
    tags = MONO_TAGS if mono else POLY_TAGS
    pcs = []
    for pc, col in enumerate(NOTE_NAMES):
        tag = row[col]
        if tag in FORBID_TAGS:
            continue
        if tag in tags and (exclude is None or pc != exclude):
            pcs.append(pc)
    return pcs

def bass_pc_of(name: str, tables: ChordTables) -> Optional[int]:
    base, slash = (name.split('/', 1) + [None])[:2]
    if slash:
        return NAME2PC.get(slash)
    row = tables.row(base)
    if row is None:
        return None
    for pc, col in enumerate(NOTE_NAMES):
        if row[col] == '1':
            return pc
    return None

def x_to_center(x: float, low: int, high: int) -> int:
    x = max(0.0, min(1.0, x))
    return int(round(low + x*(high - low)))

def nearest_note(pc: int, center: int, low: int, high: int) -> Optional[int]:
    best = None
    bestd = 1e9
    for k in range(10):
        n = pc + 12*k
        if low <= n <= high:
            d = abs(n - center)
            if d < bestd:
                bestd = d
                best = n
    return best

def lowest_note(pc: int, low: int, high: int) -> Optional[int]:
    for k in range(10):
        n = pc + 12*k
        if low <= n <= high:
            return n
    return None

def vel(center: int, low: int, high: int) -> int:
    mid = (low + high) // 2
    dist = abs(center - mid) / max(1, (high - low)/2)
    v = int(VEL_MAX - (VEL_MAX - VEL_MIN) * min(1.0, dist))
    return max(VEL_MIN, min(VEL_MAX, v))

# ===================== MIDI I/O =====================
def list_out_ports() -> List[str]:
    try:
        return mido.get_output_names()
    except Exception:
        return []

def pick_output_port() -> Optional[str]:
    outs = list_out_ports()
    if DEBUG:
        print("[MIDI] Available outputs:", outs, flush=True)
    if not outs:
        return None
    for pref in PREFERRED_OUT_PORTS:
        for o in outs:
            if pref in o:
                return o
    return outs[0]

def open_out() -> mido.ports.BaseOutput:
    try:
        mido.set_backend('mido.backends.rtmidi')
    except Exception:
        pass
    name = pick_output_port()
    if not name:
        raise RuntimeError("No MIDI outputs found. (가상 포트 또는 장치를 하나 연결해 주세요)")
    print("[MIDI] Using output:", name, flush=True)
    return mido.open_output(name)

def send_on(out, ch: int, note: int, v: int):
    out.send(mido.Message('note_on', channel=ch, note=int(note), velocity=int(v)))

def send_off(out, ch: int, note: int):
    out.send(mido.Message('note_off', channel=ch, note=int(note), velocity=0))

# ===================== State =====================
@dataclass
class HandState:
    label: str
    ch: int
    low: int
    high: int
    present: bool = False
    ema: Optional[Tuple[float,float]] = None
    down: int = 0
    prev_down: int = 0
    finger_down: List[bool] = field(default_factory=lambda n=_FINGER_COUNT: [False]*n)
    pressed_now: int = 0
    active: Set[int] = field(default_factory=set)
    pcs: List[int] = field(default_factory=list)

@dataclass
class GS:
    left: HandState
    right: HandState
    prog_idx: int = 0
    step: int = 0
    last_chord: str = ''
    bass_once: bool = False
    first_press_t: Optional[float] = None
    prev_total_down: int = 0
    progs: list = field(default_factory=list)
    tables: ChordTables = None
    out: mido.ports.BaseOutput = None
    running: bool = True
    paused: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)

# ===================== Particle System =====================
@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    r: int
    g: int
    b: int
    size: int
    life: float      # seconds remaining
    max_life: float  # for fade computation

def spawn_particles(particles: List[Particle], x: float, y: float, n: int, scale: float=1.0):
    for _ in range(n):
        speed = random.uniform(*PARTICLE_SPEED) * scale
        angle = random.uniform(-math.pi/2 - 0.8, -math.pi/2 + 0.8)  # 위로 흩날리는 느낌
        vx = speed * math.cos(angle)
        vy = speed * math.sin(angle)
        life = random.uniform(*PARTICLE_LIFE)
        size = int(random.uniform(*PARTICLE_SIZE))
        # 랜덤 화려한 컬러 (HSV→BGR 대신 간단히 RGB 랜덤)
        r = random.randint(100,255)
        g = random.randint(100,255)
        b = random.randint(100,255)
        particles.append(Particle(x, y, vx, vy, r, g, b, size, life, life))

def update_particles(particles: List[Particle], dt: float, frame_w: int, frame_h: int):
    alive = []
    for p in particles:
        p.vy += GRAVITY * dt
        p.x += p.vx * dt
        p.y += p.vy * dt
        p.life -= dt
        if 0 <= p.x < frame_w and 0 <= p.y < frame_h and p.life > 0:
            alive.append(p)
    # 개수 제한
    if len(alive) > MAX_PARTICLES:
        alive = alive[-MAX_PARTICLES:]
    particles[:] = alive

def render_particles(frame: np.ndarray, particles: List[Particle]):
    # 반투명 블렌딩을 위해 별도의 레이어 생성
    overlay = frame.copy()
    for p in particles:
        alpha = max(0.0, min(1.0, p.life / p.max_life)) ** PARTICLE_FADE
        # 작은 타원(꽃잎 느낌)
        axes = (max(1, p.size), max(1, int(p.size * 0.6)))
        angle = (1.0 - p.life / p.max_life) * 180.0  # 서서히 회전
        center = (int(p.x), int(p.y))
        color = (int(p.b), int(p.g), int(p.r))  # BGR
        cv2.ellipse(overlay, center, axes, angle, 0, 360, color, -1, cv2.LINE_AA)
        # 투명도 적용
    cv2.addWeighted(overlay, 0.35, frame, 0.65, 0, frame)

# ===================== Core Apply =====================
def choose_pcs(gs: GS, h: HandState, chord: str) -> List[int]:
    n = h.pressed_now if h.pressed_now > 0 else 1
    mono = (n == 1)
    pcs = allowed_pcs(chord, gs.tables, mono)
    if not pcs:
        return []
    k = min(n, len(pcs))
    return random.sample(pcs, k)

def apply_hand(gs: GS, h: HandState, extra_bass_pc: Optional[int] = None):
    out = gs.out
    total = (gs.left.down if gs.left.present else 0) + (gs.right.down if gs.right.present else 0)
    if total == 0 or gs.paused:
        for n in list(gs.left.active):
            send_off(out, gs.left.ch, n); gs.left.active.discard(n)
        for n in list(gs.right.active):
            send_off(out, gs.right.ch, n); gs.right.active.discard(n)
        return

    x = 0.5 if h.ema is None else h.ema[0]
    center = x_to_center(x, h.low, h.high)
    v = vel(center, h.low, h.high)

    want: Set[int] = set()

    for pc in h.pcs:
        nn = nearest_note(pc, center, h.low, h.high)
        if nn is not None:
            want.add(nn)

    if extra_bass_pc is not None and h.label == 'Left':
        bn = lowest_note(extra_bass_pc, h.low, h.high)
        if bn is not None:
            want.add(bn)

    for n in list(h.active - want):
        send_off(out, h.ch, n); h.active.discard(n)
    for n in sorted(want - h.active):
        send_on(out, h.ch, n, v); h.active.add(n)

# ===================== Threads =====================
class AirPianoApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("AirPiano")

        # Grid weights (카메라 프리뷰를 항상 맨 위 row=0, 중앙 column=1)
        self.root.grid_rowconfigure(0, weight=0)  # preview row (fixed to top)
        self.root.grid_rowconfigure(1, weight=0)  # title/buttons row
        self.root.grid_rowconfigure(2, weight=1)  # spacer (fill below)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=0)
        self.root.grid_columnconfigure(2, weight=1)

        # Camera Preview Label (top center)
        self.preview_label = ttk.Label(self.root)
        self.preview_label.grid(row=0, column=1, pady=(8, 0))

        # Title + Buttons row
        row1 = ttk.Frame(self.root)
        row1.grid(row=1, column=1, pady=(8, 8))
        self.title_label = ttk.Label(row1, text="AirPiano", font=("Segoe UI", 18, "bold"))
        self.title_label.pack(side=tk.TOP, anchor="center", pady=(0, 6))

        btn_row = ttk.Frame(row1)
        btn_row.pack(side=tk.TOP, anchor="center")
        self.btn_change = ttk.Button(btn_row, text="분위기 전환", command=self.on_change_prog)
        self.btn_change.pack(side=tk.LEFT, padx=6)
        self.btn_pause = ttk.Button(btn_row, text="일시 중지", command=self.on_toggle_pause)
        self.btn_pause.pack(side=tk.LEFT, padx=6)

        # Spacer
        ttk.Frame(self.root).grid(row=2, column=1)  # just to occupy grid

        # MediaPipe Hands
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            model_complexity=1,
        )
        self.drawer = mp.solutions.drawing_utils

        # MIDI
        self.out = open_out()

        # CSV
        self.tables = ChordTables.load(CHORD_CSV_PATH)
        self.progs  = load_progressions(PROG_CSV_PATH)
        if not self.progs:
            raise RuntimeError("No progressions loaded from progression.CSV")

        idx = random.randrange(len(self.progs))
        self.gs = GS(
            left=HandState('Left', LEFT_CH, LEFT_LOW, LEFT_HIGH),
            right=HandState('Right', RIGHT_CH, RIGHT_LOW, RIGHT_HIGH),
            prog_idx=idx, progs=self.progs, tables=self.tables, out=self.out
        )

        # Particles
        self.particles: List[Particle] = []
        self.last_time = time.time()

        # Camera
        self.cap, self.cam_id = self.open_camera()
        if not self.cap:
            raise RuntimeError("카메라를 열 수 없습니다. CAMERA_TRY_IDS를 확인하세요.")

        # 정확히 카메라 해상도에 맞추기
        w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if w <= 0 or h <= 0:
            w, h = FRAME_W, FRAME_H
        # 16:9 맞추기
        target_w, target_h = self._fit_keep_aspect(w, h, KEEP_ASPECT)
        self.frame_size = (target_w, target_h)

        # Clock thread (beat advance)
        self.clock_thread = threading.Thread(target=self._clock_loop, daemon=True)
        self.clock_thread.start()

        # GUI update loop
        self._update_loop()

        # Close handler
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- UI Events ----------
    def on_change_prog(self):
        with self.gs.lock:
            self.gs.prog_idx = random.randrange(len(self.gs.progs))
            self.gs.step = 0
            self.gs.last_chord = ''
            self.gs.bass_once = False
        if DEBUG:
            print("[UI] 분위기 전환: progression 재선택", flush=True)

    def on_toggle_pause(self):
        with self.gs.lock:
            self.gs.paused = not self.gs.paused
            paused = self.gs.paused
        self.btn_pause.config(text=("일시 중지 해제" if paused else "일시 중지"))
        if DEBUG:
            print(f"[UI] 일시 중지 토글 -> {paused}", flush=True)

    # ---------- Camera ----------
    def open_camera(self):
        for cam_id in CAMERA_TRY_IDS:
            cap = cv2.VideoCapture(cam_id)
            if cap.isOpened():
                # 초기 해상도 시도
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_W)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)
                print(f"[CAM] Using camera ID: {cam_id}", flush=True)
                return cap, cam_id
            cap.release()
        return None, None

    def _fit_keep_aspect(self, w: int, h: int, aspect: Tuple[int,int]) -> Tuple[int,int]:
        aw, ah = aspect
        # w:h 를 16:9로 맞추면서 카메라 원본 해상도에 "맞추는" 방향
        # 프리뷰는 카메라 해상도에 최대한 맞추되, 비율을 16:9로 보정
        cur_ratio = w / h
        target_ratio = aw / ah
        if abs(cur_ratio - target_ratio) < 1e-3:
            return w, h
        if cur_ratio > target_ratio:
            # 너무 넓음 → 폭 줄이기
            new_w = int(h * target_ratio)
            return new_w, h
        else:
            # 너무 높음 → 높이 줄이기
            new_h = int(w / target_ratio)
            return w, new_h

    # ---------- Loops ----------
    def _clock_loop(self):
        while True:
            with self.gs.lock:
                running = self.gs.running
            if not running:
                break
            t0 = time.time()
            with self.gs.lock:
                seq = self.gs.progs[self.gs.prog_idx]['seq']
                if seq:
                    self.gs.step = (self.gs.step + STEPS_PER_BEAT) % len(seq)
            dt = time.time() - t0
            time.sleep(max(0.0, BEAT_SEC - dt))

    def _update_loop(self):
        # 시간 delta
        now = time.time()
        dt = now - self.last_time
        self.last_time = now
        dt = max(1e-3, min(0.05, dt))  # 안정화

        ok, frame = self.cap.read()
        if ok:
            if MIRROR:
                frame = cv2.flip(frame, 1)

            # 16:9로 크롭/리사이즈 (카메라 해상도 기준)
            h, w = frame.shape[:2]
            target_w, target_h = self.frame_size
            # 중심 크롭
            if (w, h) != (target_w, target_h):
                # 크롭 박스 계산
                x0 = (w - target_w) // 2
                y0 = (h - target_h) // 2
                x0 = max(0, x0); y0 = max(0, y0)
                frame = frame[y0:y0+target_h, x0:x0+target_w].copy()

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = self.hands.process(rgb)

            # MediaPipe 처리 + 상태 갱신 + MIDI + 파티클
            self._process_hands_and_music(frame, res, dt)

            # 파티클 렌더링
            render_particles(frame, self.particles)

            # Tkinter 표시용 변환
            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            imgtk = ImageTk.PhotoImage(image=img)
            self.preview_label.imgtk = imgtk
            self.preview_label.configure(image=imgtk)

        # 다음 루프 예약 (Tkinter GUI 쓰레드)
        self.root.after(10, self._update_loop)

    # ---------- Hand / Music processing ----------
    def _process_hands_and_music(self, frame: np.ndarray, res, dt: float):
        # 파티클 업데이트 먼저
        h, w = frame.shape[:2]
        update_particles(self.particles, dt, w, h)

        with self.gs.lock:
            self.gs.left.present = self.gs.right.present = False
            now2 = time.monotonic()

            # Hands
            if res.multi_hand_landmarks and res.multi_handedness:
                for lm, hd in zip(res.multi_hand_landmarks, res.multi_handedness):
                    lab = hd.classification[0].label  # 'Left' / 'Right'
                    hstate = self.gs.left if lab == 'Left' else self.gs.right
                    hstate.present = True

                    # (디버그 라인 그리기 원하면 주석 해제)
                    # self.drawer.draw_landmarks(frame, lm, self.mp_hands.HAND_CONNECTIONS)

                    pts = [(p.x, p.y) for p in lm.landmark]
                    # wrist smoothing
                    w0 = pts[0]
                    if hstate.ema is None:
                        hstate.ema = w0
                    else:
                        hstate.ema = (
                            SMOOTH_ALPHA*w0[0] + (1-SMOOTH_ALPHA)*hstate.ema[0],
                            SMOOTH_ALPHA*w0[1] + (1-SMOOTH_ALPHA)*hstate.ema[1],
                        )

                    # press detection with hysteresis & edge trigger
                    down_cnt = 0
                    press_now = 0
                    for idx_f, (mcp, pip, tip) in enumerate(HAND_FINGERS):
                        a, b, c = pts[mcp], pts[pip], pts[tip]
                        v1 = (a[0]-b[0], a[1]-b[1]); v2 = (c[0]-b[0], c[1]-b[1])
                        dot = v1[0]*v2[0] + v1[1]*v2[1]
                        n1 = math.hypot(*v1); n2 = math.hypot(*v2)
                        ang = 0.0 if (n1==0 or n2==0) else math.degrees(
                            math.acos(max(-1.0, min(1.0, dot/(n1*n2))))
                        )

                        was = hstate.finger_down[idx_f]
                        now_down = was
                        if was:
                            if ang >= FINGER_RELEASE_DEG:
                                now_down = False
                        else:
                            if ang <= FINGER_PRESS_DEG:
                                now_down = True
                                press_now += 1
                                # 손가락 tip 좌표에 파티클 스폰 (카메라 프레임 좌표로 변환)
                                tip_pt = pts[tip]
                                px = int(tip_pt[0] * w)
                                py = int(tip_pt[1] * h)
                                if not self.gs.paused:
                                    # 한 번에 너무 많이 생성되지 않도록 조절
                                    spawn_particles(self.particles, px, py, n=random.randint(6, 12), scale=1.0)

                        hstate.finger_down[idx_f] = now_down
                        if now_down:
                            down_cnt += 1

                    hstate.down = down_cnt
                    hstate.pressed_now = press_now

            # Chord & step
            seq = self.gs.progs[self.gs.prog_idx]['seq']
            chord = seq[self.gs.step % len(seq)] if seq else ''
            chord_changed = (chord != self.gs.last_chord)

            if chord_changed:
                self.gs.last_chord = chord
                self.gs.bass_once = False
                if DEBUG:
                    print(f"[BEAT] Beat={self.gs.step+1}/{len(seq)} chord='{chord}'", flush=True)

            # re-sample pcs on new press
            for hstate in (self.gs.left, self.gs.right):
                if not hstate.present:
                    hstate.prev_down = 0
                    hstate.pcs = []
                    continue
                if (hstate.prev_down == 0 and hstate.down > 0) or (hstate.pressed_now > 0):
                    hstate.pcs = choose_pcs(self.gs, hstate, chord)
                    if DEBUG and hstate.pcs:
                        print(f"[PICK] {hstate.label} down={hstate.down} pressed_now={hstate.pressed_now} pcs={hstate.pcs}", flush=True)
                hstate.prev_down = hstate.down

            # Bass trigger
            total = (self.gs.left.down if self.gs.left.present else 0) + (self.gs.right.down if self.gs.right.present else 0)

            # Silence resets
            if total == 0:
                self.gs.first_press_t = None

            if self.gs.prev_total_down == 0 and total > 0 and self.gs.first_press_t is None:
                self.gs.first_press_t = now2

            extra_bass_pc = None
            if (not self.gs.bass_once) \
               and (self.gs.left.present and self.gs.left.down >= 1) \
               and (self.gs.prev_total_down < 2 and total >= 2) \
               and (self.gs.first_press_t is not None) \
               and ((now2 - self.gs.first_press_t) <= (SIMUL_WINDOW_MS/1000.0)):
                extra_bass_pc = bass_pc_of(chord, self.gs.tables)
                self.gs.bass_once = True
                if DEBUG:
                    print(f"[BASS] Fired once for chord '{chord}' (pc={extra_bass_pc})", flush=True)

            # Apply (MIDI)
            apply_hand(self.gs, self.gs.left, extra_bass_pc)
            apply_hand(self.gs, self.gs.right, None)

            # Update total
            self.gs.prev_total_down = total

            # HUD (간단히 제목 아래에 정보 덧입혀도 됨 — 여기서는 미니멀)
            # 필요하면 frame에 putText로 chord 등 표시 가능

    # ---------- Close ----------
    def _on_close(self):
        try:
            with self.gs.lock:
                self.gs.running = False
            # 모든 노트 오프
            for n in list(self.gs.left.active):
                send_off(self.gs.out, self.gs.left.ch, n)
            for n in list(self.gs.right.active):
                send_off(self.gs.out, self.gs.right.ch, n)
            if self.cap:
                self.cap.release()
            if self.out:
                self.out.close()
        finally:
            self.root.destroy()

# ===================== main =====================
def main():
    try:
        print("[BOOT] Python", sys.version, flush=True)
        root = tk.Tk()
        # OS별 폰트/테마 차이가 있어 ttk 기본 스타일을 약간 부드럽게
        try:
            root.tk.call("source", "azure.tcl")  # 있으면 쓰고, 없으면 무시
            root.tk.call("set_theme", "light")
        except Exception:
            pass

        app = AirPianoApp(root)
        # 창 최소 크기를 카메라 프리뷰 폭에 맞춰 대략 지정 (선택)
        fw, fh = app.frame_size
        root.minsize(fw + 20, fh + 120)
        root.mainloop()
    except Exception as e:
        print("[FATAL]", repr(e), flush=True)
        traceback.print_exc()

if __name__ == '__main__':
    main()
