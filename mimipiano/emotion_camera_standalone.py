import cv2
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model

# === 모델 및 분류기 로드 ===
face_cascade = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")
cnn_model = load_model("checkPoint_model.h5")
print("✅ 모델 로드 완료")

# === 감정 라벨 (훈련 시 순서와 맞춰야 함) ===
emotion_labels = ['Angry', 'Disgust', 'Fear', 'Happy', 'Neutral', 'Sad', 'Surprise']

# === 카메라 초기화 ===
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("❌ 카메라를 열 수 없습니다.")
    exit()

print("🎥 실시간 감정 분석 시작 (ESC로 종료)")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)

    for (x, y, w, h) in faces:
        roi_gray = gray[y:y+h, x:x+w]
        roi_gray = cv2.resize(roi_gray, (64, 64))
        roi = roi_gray.astype('float32') / 255.0
        roi = np.expand_dims(roi, axis=(0, -1))  # (1,64,64,1)

        preds = cnn_model.predict(roi, verbose=0)
        label = emotion_labels[np.argmax(preds)]
        conf = np.max(preds)

        cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 255, 0), 2)
        cv2.putText(frame, f"{label} ({conf:.2f})", (x, y-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)

    cv2.imshow("Emotion Recognition", frame)
    if cv2.waitKey(1) & 0xFF == 27:  # ESC
        break

cap.release()
cv2.destroyAllWindows()
