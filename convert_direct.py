"""
Direct conversion using tensorflowjs Python API
"""
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

print("Loading model...")
from tensorflow import keras
model = keras.models.load_model('mimipiano/checkPoint_model.h5', compile=False)
print("[OK] Model loaded!")
print(f"Input: {model.input_shape}")
print(f"Output: {model.output_shape}")

# Direct conversion using save_keras_model
output_dir = 'web_app/static/data/tfjs_model'
print(f"\nConverting to TensorFlow.js...")

try:
    # Import only what we need
    from tensorflowjs.converters import save_keras_model
    save_keras_model(model, output_dir)
    print(f"\n[SUCCESS] Model saved to {output_dir}")

    # List files
    import os
    files = os.listdir(output_dir)
    print(f"\nGenerated files:")
    for f in files:
        size = os.path.getsize(os.path.join(output_dir, f))
        print(f"  - {f} ({size:,} bytes)")

except Exception as e:
    print(f"\n[ERROR] {e}")
    print("\nTrying alternative method...")

    # Alternative: export and use command line with proper flags
    import shutil
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # Save weights and architecture separately
    model.save_weights(os.path.join(output_dir, 'model_weights.h5'))
    with open(os.path.join(output_dir, 'model_architecture.json'), 'w') as f:
        f.write(model.to_json())

    print("[PARTIAL] Saved weights and architecture")
    print("You'll need to load these manually in JavaScript")
