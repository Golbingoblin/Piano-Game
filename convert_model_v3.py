"""
Convert Keras model to TensorFlow.js - Version 3
Using command-line converter to avoid NumPy compatibility issues
"""
import os
import subprocess
import shutil

# Suppress warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

print("=" * 60)
print("Step 1: Loading Keras model...")
print("=" * 60)

from tensorflow import keras
model = keras.models.load_model('mimipiano/checkPoint_model.h5')
print("[OK] Model loaded successfully!")
print("\nModel Input Shape:", model.input_shape)
print("Model Output Shape:", model.output_shape)

# Save as SavedModel format
temp_dir = 'temp_savedmodel'
print("\n" + "=" * 60)
print(f"Step 2: Saving as SavedModel -> {temp_dir}")
print("=" * 60)

if os.path.exists(temp_dir):
    shutil.rmtree(temp_dir)
model.export(temp_dir)
print("[OK] SavedModel saved!")

# Convert using CLI tool
output_dir = 'web_app/static/data/tfjs_model'
print("\n" + "=" * 60)
print(f"Step 3: Converting to TensorFlow.js -> {output_dir}")
print("=" * 60)

if os.path.exists(output_dir):
    shutil.rmtree(output_dir)

# Use tensorflowjs_converter
cmd = [
    'tensorflowjs_converter',
    '--input_format=tf_saved_model',
    '--output_format=tfjs_graph_model',
    '--signature_name=serving_default',
    '--saved_model_tags=serve',
    temp_dir,
    output_dir
]

print(f"Command: {' '.join(cmd)}")
result = subprocess.run(cmd, capture_output=True, text=True)

if result.returncode == 0:
    print("\n[SUCCESS] Conversion successful!")
    print(f"\nModel files created in: {output_dir}")

    # List created files
    if os.path.exists(output_dir):
        files = os.listdir(output_dir)
        print("\nGenerated files:")
        for f in files:
            size = os.path.getsize(os.path.join(output_dir, f))
            print(f"  - {f} ({size:,} bytes)")
else:
    print("\n[ERROR] Conversion failed!")
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)

# Cleanup
if os.path.exists(temp_dir):
    shutil.rmtree(temp_dir)
    print(f"\n[CLEANUP] Temporary directory removed: {temp_dir}")

print("\n" + "=" * 60)
print("DONE!")
print("=" * 60)
