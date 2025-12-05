import cv2
import numpy as np
import tensorflow as tf

# ===== 얼굴 인식기 =====
face_cascade = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")

# ===== CNN 모델 로드 =====
try:
    cnn_model = tf.keras.models.load_model("checkPoint_model.h5")
    print("✅ CNN 모델 로드 완료")

    # 모델의 입력 크기를 자동으로 가져오기
    input_shape = cnn_model.input_shape
    if len(input_shape) == 4:
        _, h, w, c = input_shape
    else:
        h, w, c = 64, 64, 1
    print(f"입력 형태 자동 감지됨: {h}x{w}x{c}")

except Exception as e:
    print("❌ CNN 모델 로드 실패:", e)
    cnn_model = None
    h, w, c = 64, 64, 1

emotion_labels = ['Angry', 'Disgust', 'Fear', 'Happy', 'Neutral', 'Sad', 'Surprise']

# ===== 카메라 =====
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
if not cap.isOpened():
    print("❌ 카메라를 열 수 없습니다.")
    exit()

print("🎥 CNN 기반 감정 인식 시작 (ESC로 종료)")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    for (x, y, w_, h_) in faces:
        face_roi = gray[y:y+h_, x:x+w_]
        face_resized = cv2.resize(face_roi, (w, h))

        text_cnn = "CNN: N/A"
        if cnn_model is not None:
            roi = face_resized.astype('float32') / 255.0
            if c == 3:
                roi = cv2.cvtColor(face_resized, cv2.COLOR_GRAY2RGB)
            roi = np.expand_dims(roi, axis=0)  # (1, h, w, c)
            roi = np.expand_dims(roi, axis=-1) if c == 1 else roi
            try:
                pred = cnn_model.predict(roi, verbose=0)
                label = emotion_labels[np.argmax(pred)]
                conf = np.max(pred)
                text_cnn = f"{label} ({conf:.2f})"
            except Exception as e:
                text_cnn = "CNN ERR"

        cv2.rectangle(frame, (x, y), (x+w_, y+h_), (0, 255, 0), 2)
        cv2.putText(frame, text_cnn, (x, y+h_+25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)

    cv2.imshow("CNN Emotion Detection", frame)
    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
