"""
Convert Keras model to TensorFlow.js format - Version 2
Suppress tensorflow-decision-forests warnings
"""
import os
import warnings
warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

# 먼저 Keras 모델만 로드
from tensorflow import keras
print("Loading Keras model...")
model = keras.models.load_model('mimipiano/checkPoint_model.h5')
print("[OK] Model loaded successfully!")
print(f"\nModel summary:")
model.summary()

# TensorFlow.js 변환을 위해 SavedModel 형식으로 먼저 저장
temp_saved_model_path = 'temp_saved_model'
print(f"\n[SAVING] SavedModel format -> {temp_saved_model_path}")
model.save(temp_saved_model_path, save_format='tf')
print("[OK] SavedModel saved!")

# 이제 tensorflowjs로 변환 (import를 여기서 해서 모델 로드 후에만 발생하도록)
print("\n[IMPORT] Importing tensorflowjs...")
try:
    import tensorflowjs as tfjs

    output_dir = 'web_app/static/data/tfjs_model'
    print(f"[CONVERT] Converting to TensorFlow.js format...")
    tfjs.converters.save_keras_model(model, output_dir)
    print(f"\n[SUCCESS] Conversion complete! Model saved to {output_dir}")

except Exception as e:
    print(f"\n[ERROR] TensorFlow.js conversion failed: {e}")
    print("\n[FALLBACK] Trying SavedModel conversion...")
    import subprocess
    result = subprocess.run([
        'tensorflowjs_converter',
        '--input_format=tf_saved_model',
        temp_saved_model_path,
        'web_app/static/data/tfjs_model'
    ], capture_output=True, text=True)

    if result.returncode == 0:
        print("[SUCCESS] Conversion complete!")
    else:
        print(f"[ERROR] Conversion failed:\n{result.stderr}")

# 임시 파일 정리
import shutil
if os.path.exists(temp_saved_model_path):
    shutil.rmtree(temp_saved_model_path)
    print(f"\n[CLEANUP] Temporary files removed: {temp_saved_model_path}")
