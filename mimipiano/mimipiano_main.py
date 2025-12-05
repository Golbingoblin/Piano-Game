import tkinter as tk
from tkinter import ttk, messagebox
import threading, random, json, time
from pathlib import Path
import numpy as np
import pandas as pd
import mido
from mido import MidiFile, Message
import cv2
import tensorflow as tf
from PIL import Image, ImageTk

# ===== 경로 설정 =====
BASE_PATH = Path(__file__).parent
CSV_PATH = BASE_PATH / "expression.csv"
MUSIC_ROOT = BASE_PATH / "MusicRoot"
SETTINGS_JSON = BASE_PATH / "debug_settings.json"

# ===== 키 매핑 =====
KEY_STR_TO_PC = {"C":0,"Cs":1,"D":2,"Ds":3,"E":4,"F":5,"Fs":6,"G":7,"Gs":8,"A":9,"As":10,"B":11}
MAJOR_SCALE_PCS = {1:0,2:2,3:4,4:5,5:7,6:9,7:11}
MODE_TARGET_DEGREE = {"Lydian":4,"Mixolydian":7,"Dorian":3,"Aeolian":6,"Phrygian":2,"Locrian":5}
MODE_SEMITONE_DELTA = {"Lydian":+1,"Mixolydian":-1,"Dorian":-1,"Aeolian":-1,"Phrygian":-1,"Locrian":-1}

def pc(note): return note % 12
def nearest_major_degree_pitchclass(root_pc,pitch_pc):
    rel=(pitch_pc-root_pc)%12
    for deg,off in MAJOR_SCALE_PCS.items():
        if rel==off:return deg
    return None

# ===== 확률 계산 =====
class ExpressionMap:
    def __init__(self,path):
        df=pd.read_csv(path)
        df=df.rename(columns={c.strip():c.strip() for c in df.columns})
        self.rules=[]
        for _,r in df.iterrows():
            self.rules.append({
                "name":str(r.iloc[0]).strip(),
                "flat0":r.get("Flat 0"),"flat100":r.get("Flat 100"),
                "sharp0":r.get("Sharp 0"),"sharp100":r.get("Sharp 100"),
            })
    def probs(self,happiness,special):
        out={}
        for r in self.rules:
            n=r["name"]; flat0,flat100,sharp0,sharp100=r["flat0"],r["flat100"],r["sharp0"],r["sharp100"]
            if n!="Lydian" and flat0 is not None and flat100 is not None:
                if happiness>=flat0:p=0.0
                elif happiness<=flat100:p=1.0
                else:p=(flat0-happiness)/(flat0-flat100)
                out[n]=float(np.clip(p,0,1))
            if n=="Lydian" and sharp0 is not None and sharp100 is not None:
                if special<=sharp0:p=0.0
                elif special>=sharp100:p=1.0
                else:p=(special-sharp0)/(sharp100-sharp0)
                out[n]=float(np.clip(p,0,1))
        return out

# ===== MIDI Player =====
class DebugPlayer:
    def __init__(self,out_name,expr_map,gui):
        self.port=mido.open_output(out_name)
        self.expr_map=expr_map
        self.gui=gui
        self.running=False
        self.note_map={}
    def play_async(self,midi_path):
        if self.running:return
        self.running=True
        threading.Thread(target=self._play_thread,args=(midi_path,),daemon=True).start()
    def _play_thread(self,midi_path):
        mid=MidiFile(midi_path)
        key=midi_path.parent.name
        root_pc=KEY_STR_TO_PC.get(key,0)
        for msg in mid.play():
            if not self.running:break
            h=self.gui.h_val; s=self.gui.s_val
            probs=self.expr_map.probs(h,s)
            if msg.type=="note_on" and msg.velocity>0:
                new=self._maybe_alter(msg.note,root_pc,probs)
                self.note_map[msg.note]=new
                self.port.send(Message("note_on",note=new,velocity=msg.velocity))
            elif msg.type=="note_off":
                nn=self.note_map.pop(msg.note,msg.note)
                self.port.send(Message("note_off",note=nn,velocity=msg.velocity))
            elif msg.type=="control_change":self.port.send(msg)
        self.running=False; self._safe_close()
    def _maybe_alter(self,n,root_pc,probs):
        pitch_pc=pc(n);deg=nearest_major_degree_pitchclass(root_pc,pitch_pc)
        if not deg:return n
        for mode,tdeg in MODE_TARGET_DEGREE.items():
            if deg==tdeg and random.random()<probs.get(mode,0):return int(np.clip(n+MODE_SEMITONE_DELTA[mode],0,127))
        return n
    def stop(self):
        self.running=False
        for n in list(self.note_map.values()):
            try:self.port.send(Message("note_off",note=n,velocity=0))
            except:pass
        self._safe_close()
    def _safe_close(self):
        try:self.port.close()
        except:pass
        self.note_map.clear()

# ===== Vision Engine =====
class VisionEngine(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.running=False
        self.frame=None
        self.last_scores=(100,0)
        self.face_ok=False
        self.model=None
        self.labels=['Angry','Disgust','Fear','Happy','Neutral','Sad','Surprise']
        self.cascade=cv2.CascadeClassifier(str(BASE_PATH/"haarcascade_frontalface_default.xml"))
        try:
            self.model=tf.keras.models.load_model(str(BASE_PATH/"checkPoint_model.h5"))
            print("✅ CNN 로드 완료",self.model.input_shape)
        except Exception as e:
            print("❌ CNN 로드 실패:",e)
    def run(self):
        cap=self._open_cam()
        if cap is None:return
        while self.running:
            ok,frame=cap.read()
            if not ok:continue
            gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
            faces=self.cascade.detectMultiScale(gray,1.3,5)
            self.face_ok=len(faces)>0
            happy,special=self.last_scores
            if self.model is not None and self.face_ok:
                x,y,w,h=sorted(faces,key=lambda r:r[2]*r[3],reverse=True)[0]
                face=gray[y:y+h,x:x+w]
                face=cv2.resize(face,(48,48)).astype("float32")/255.0
                face=np.expand_dims(face,(-1,0))
                pred=self.model.predict(face,verbose=0)[0]
                li={n:i for i,n in enumerate(self.labels)}
                p=lambda n:float(pred[li[n]]) if n in li else 0.0
                happy=100*(0.9*p('Happy')+0.5*p('Neutral')+0.2*p('Surprise'))
                special=100*p('Surprise')
                self.last_scores=(happy,special)
                cv2.rectangle(frame,(x,y),(x+w,y+h),(0,255,0),2)
                cv2.putText(frame,f"Happy:{happy:.1f}  Special:{special:.1f}",(x,y-10),
                            cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,255,0),2)
            self.frame=frame
            time.sleep(0.03)
        cap.release()
    def _open_cam(self):
        for idx in [1,0,2]:
            cap=cv2.VideoCapture(idx,cv2.CAP_DSHOW)
            if cap.isOpened():print(f"카메라 선택됨 {idx}");return cap
        print("❌ 카메라 실패");return None
    def start_cam(self):
        if self.running:return
        self.running=True
        self.start()
    def stop_cam(self):
        self.running=False

# ===== GUI =====
class MimiGUI:
    def __init__(self):
        self.root=tk.Tk()
        self.root.title("MIMI Piano – CNN GUI Mode v7")
        self.root.geometry("960x900")
        self.expr_map=ExpressionMap(CSV_PATH)
        self.vision=VisionEngine()
        self.h_val=100;self.s_val=0
        self.player=None

        # === 카메라 영상 ===
        self.video_label=tk.Label(self.root,bg="black")
        self.video_label.pack(pady=5)

        # === 상태 표시줄 ===
        self.status=tk.Label(self.root,text="준비됨")
        self.status.pack()

        # === MIDI 선택 메뉴 ===
        menu_frame=tk.Frame(self.root)
        menu_frame.pack(pady=6)
        tk.Label(menu_frame,text="MIDI 출력 장치").grid(row=0,column=0,padx=4)
        devs=mido.get_output_names()
        self.device_var=tk.StringVar(value=devs[0] if devs else "Microsoft GS Wavetable Synth 0")
        self.device_menu=ttk.Combobox(menu_frame,values=devs,textvariable=self.device_var,state="readonly",width=45)
        self.device_menu.grid(row=0,column=1,padx=4)

        tk.Label(menu_frame,text="Key 폴더").grid(row=1,column=0,sticky="w",padx=4)
        keys=[p.name for p in MUSIC_ROOT.iterdir() if p.is_dir()]
        self.key_var=tk.StringVar();self.file_var=tk.StringVar()
        self.key_menu=ttk.Combobox(menu_frame,values=keys,textvariable=self.key_var,state="readonly",width=15)
        self.key_menu.grid(row=1,column=1,sticky="w")
        self.key_menu.bind("<<ComboboxSelected>>",self._update_file_menu)

        tk.Label(menu_frame,text="MIDI 파일").grid(row=2,column=0,sticky="w",padx=4)
        self.file_menu=ttk.Combobox(menu_frame,values=[],textvariable=self.file_var,state="readonly",width=45)
        self.file_menu.grid(row=2,column=1,sticky="w")

        ttk.Button(menu_frame,text="재생",command=self.play).grid(row=3,column=0,padx=4,pady=3)
        ttk.Button(menu_frame,text="정지",command=self.stop).grid(row=3,column=1,padx=4,pady=3,sticky="w")

        # === 점수/카메라 제어 ===
        self.h_slider=tk.Scale(self.root,from_=0,to=100,orient="horizontal",length=600,label="행복점수")
        self.h_slider.set(100);self.h_slider.pack()
        self.s_slider=tk.Scale(self.root,from_=0,to=100,orient="horizontal",length=600,label="특별점수")
        self.s_slider.set(0);self.s_slider.pack()

        cam_frame=tk.Frame(self.root)
        cam_frame.pack()
        self.use_cam_var=tk.BooleanVar(value=True)
        ttk.Checkbutton(cam_frame,text="🙂 카메라 점수 사용",variable=self.use_cam_var).pack(side="left",padx=5)

        # === 디버그 토글 ===
        self.root.bind("<Control-d>",self._toggle_debug)
        self.debug_visible=True

        # === 카메라 시작 ===
        self.vision.start_cam()
        self._update_gui()
        self.root.protocol("WM_DELETE_WINDOW",self._on_close)
        self.root.mainloop()

    def _update_file_menu(self,event=None):
        k=self.key_var.get()
        folder=MUSIC_ROOT/k
        files=[f.name for f in folder.glob("*.mid")]
        self.file_menu.config(values=files)
        if files:self.file_var.set(files[0])

    def _toggle_debug(self,event=None):
        self.debug_visible=not self.debug_visible
        if self.debug_visible:
            self.h_slider.pack(); self.s_slider.pack()
        else:
            self.h_slider.pack_forget(); self.s_slider.pack_forget()

    def _update_gui(self):
        if self.vision.frame is not None:
            frame=cv2.cvtColor(self.vision.frame,cv2.COLOR_BGR2RGB)
            img=cv2.resize(frame,(920,520))
            imgtk=ImageTk.PhotoImage(Image.fromarray(img))
            self.video_label.configure(image=imgtk)
            self.video_label.imgtk=imgtk

        (h,s)=self.vision.last_scores
        face=self.vision.face_ok
        if self.use_cam_var.get():
            self.h_slider.set(int(h));self.s_slider.set(int(s))
        else:
            h=self.h_slider.get();s=self.s_slider.get()
        self.h_val=h;self.s_val=s
        self.status.config(text=f"행복:{h:.1f} 특별:{s:.1f} 얼굴:{'O' if face else 'X'}")
        self.root.after(50,self._update_gui)

    def play(self):
        k=self.key_var.get();f=self.file_var.get()
        if not k or not f:return
        path=MUSIC_ROOT/k/f
        dev=self.device_var.get()
        self.player=DebugPlayer(dev,self.expr_map,self)
        self.player.play_async(path)

    def stop(self):
        if self.player:self.player.stop()

    def _on_close(self):
        self.vision.stop_cam()
        if self.player:self.player.stop()
        self.root.destroy()

if __name__=="__main__":
    MimiGUI()
