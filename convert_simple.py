"""
Simple Keras to TensorFlow.js converter - bypassing tensorflowjs package
"""
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

print("Loading model...")
from tensorflow import keras
model = keras.models.load_model('mimipiano/checkPoint_model.h5')
print("[OK] Model loaded!")
print(f"Input shape: {model.input_shape}")
print(f"Output shape: {model.output_shape}")

# Export to SavedModel
output_dir = 'temp_savedmodel'
print(f"\nExporting to SavedModel format...")
model.export(output_dir)
print("[OK] Exported!")

# Use command-line converter
import subprocess
result = subprocess.run([
    'tensorflowjs_converter',
    '--input_format=tf_saved_model',
    '--output_format=tfjs_graph_model',
    output_dir,
    'web_app/static/data/tfjs_model'
], capture_output=True, text=True)

if result.returncode == 0:
    print("\n[SUCCESS] Conversion complete!")
    print(f"Model saved to: web_app/static/data/tfjs_model")
else:
    print(f"\n[ERROR] Conversion failed")
    print(result.stderr)

# Cleanup
import shutil
if os.path.exists(output_dir):
    shutil.rmtree(output_dir)
    print(f"\n[CLEANUP] Temporary files removed")
