"""
Convert Keras model to TensorFlow.js format
"""
import os
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

# Keras 모델 로드
from tensorflow import keras
import tensorflowjs as tfjs

print("Loading Keras model...")
model = keras.models.load_model('mimipiano/checkPoint_model.h5')

print("Model loaded successfully!")
print(f"Model summary:")
model.summary()

output_dir = 'web_app/static/data/tfjs_model'
print(f"\nConverting to TensorFlow.js format...")
print(f"Output directory: {output_dir}")

# TensorFlow.js로 변환
tfjs.converters.save_keras_model(model, output_dir)

print(f"\n✅ Conversion complete! Model saved to {output_dir}")
