"""
Final attempt: Use lower-level TensorFlow.js conversion
"""
import os
import sys
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# Prevent tensorflow_decision_forests from loading
class FakeModule:
    def __getattr__(self, name):
        return FakeModule()

sys.modules['tensorflow_decision_forests'] = FakeModule()

print("Loading model...")
from tensorflow import keras
model = keras.models.load_model('mimipiano/checkPoint_model.h5', compile=False)
print("[OK] Loaded!")

# Now import tensorflowjs
from tensorflowjs.converters import save_keras_model

output_dir = 'web_app/static/data/tfjs_model'
print(f"\nConverting...")

try:
    save_keras_model(model, output_dir)
    print(f"\n[SUCCESS] Saved to {output_dir}")

    files = os.listdir(output_dir)
    print(f"\nFiles:")
    for f in files:
        size = os.path.getsize(os.path.join(output_dir, f))
        print(f"  {f}: {size:,} bytes")

except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()
