import cv2
import numpy as np
import pickle
import os
from tensorflow.keras.models import load_model, Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout
from tensorflow.keras.utils import to_categorical
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split

IMG_SIZE = 64

class RecognitionError(Exception):
    """Custom exception for face recognition errors."""
    pass

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "model", "face_model.h5")
LABEL_ENCODER_PATH = os.path.join(BASE_DIR, "model", "label_encoder.pkl")

# Globals
model = None
le = None

def _load_model_and_encoder():
    """Load model and label encoder with strict validation."""
    global model, le

    if not os.path.isfile(MODEL_PATH):
        raise RecognitionError(f"Model not found: {MODEL_PATH}")
    if not os.path.isfile(LABEL_ENCODER_PATH):
        raise RecognitionError(f"Label encoder not found: {LABEL_ENCODER_PATH}")

    model = load_model(MODEL_PATH)
    with open(LABEL_ENCODER_PATH, "rb") as f:
        le = pickle.load(f)

    # Validate output size
    if model.output_shape[1] != len(le.classes_):
        raise RecognitionError(
            f"Mismatch: model outputs {model.output_shape[1]} classes, "
            f"but encoder has {len(le.classes_)}"
        )

_load_model_and_encoder()

def preprocess_image(image_path):
    """Preprocess image into grayscale format for model input."""
    if not os.path.isfile(image_path):
        raise RecognitionError(f"Image file does not exist: {image_path}")
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise RecognitionError(f"Cannot read image: {image_path}")
    img_gray = cv2.resize(img, (IMG_SIZE, IMG_SIZE))
    img_gray = img_gray.astype(np.float32) / 255.0
    return img_gray.reshape(1, IMG_SIZE, IMG_SIZE, 1)

def recognize_face(image_path, threshold=0.5):
    """Recognize a face from an image path."""
    if not (0.0 <= threshold <= 1.0):
        raise RecognitionError("Threshold must be between 0.0 and 1.0")

    input_data = preprocess_image(image_path)
    prediction = model.predict(input_data, verbose=0)

    confidence = float(np.max(prediction))
    label_index = int(np.argmax(prediction))

    if label_index >= len(le.classes_):
        return None, confidence

    person_id = str(le.inverse_transform([label_index])[0]).strip()
    print(f"🤖 Model prediction: {person_id} (conf: {confidence:.3f}, threshold: {threshold})")
    return (person_id, confidence) if confidence >= threshold else (None, confidence)

def recognize_face_safe(image_path, threshold=0.5):
    """Safe wrapper that never raises exceptions."""
    try:
        pid, confidence = recognize_face(image_path, threshold)
        return {
            "found": pid is not None,
            "id": pid,
            "confidence": confidence,
            "error": None
        }
    except Exception as exc:
        return {
            "found": False,
            "id": None,
            "confidence": None,
            "error": str(exc)
        }

def reload_recognizer():
    """Reload model and encoder."""
    global model, le
    try:
        _load_model_and_encoder()
        return True, "Reloaded successfully"
    except Exception as e:
        return False, str(e)

def get_model_info():
    """Return model and encoder info for debugging."""
    return {
        "model_path": MODEL_PATH,
        "encoder_path": LABEL_ENCODER_PATH,
        "model_input_shape": str(model.input_shape) if model else None,
        "model_output_shape": str(model.output_shape) if model else None,
        "num_classes": len(le.classes_) if le else 0,
        "classes": le.classes_.tolist() if le else [],
        "files_exist": {
            "model": os.path.isfile(MODEL_PATH),
            "encoder": os.path.isfile(LABEL_ENCODER_PATH)
        }
    }


def debug_recognize(image_path, threshold=0.35):
    """Optional debug helper used by /debug-recognize endpoint."""
    result = recognize_face_safe(image_path, threshold=threshold)

    # Optionally add more internal details for diagnostics
    return {
        "debug": True,
        "input_image": image_path,
        "recognition": result,
        "model_info": get_model_info()
    }

def load_training_data():
    """Load all face images and labels from datasets."""
    images = []
    labels = []
    
    base_path = os.path.join(BASE_DIR, "datasets")
    
    # Load from AT&T dataset
    att_path = os.path.join(base_path, "AT&T")
    if os.path.exists(att_path):
        for person_dir in os.listdir(att_path):
            person_path = os.path.join(att_path, person_dir)
            if os.path.isdir(person_path):
                for img_file in os.listdir(person_path):
                    if img_file.endswith('.pgm'):
                        img_path = os.path.join(person_path, img_file)
                        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                        if img is not None:
                            img = cv2.resize(img, (IMG_SIZE, IMG_SIZE))
                            images.append(img)
                            labels.append(person_dir)
                            print(f"Loaded AT&T: {person_dir}/{img_file}")
    
    # Load from Custom dataset
    custom_path = os.path.join(base_path, "Custom")
    if os.path.exists(custom_path):
        for person_dir in os.listdir(custom_path):
            person_path = os.path.join(custom_path, person_dir)
            if os.path.isdir(person_path):
                for img_file in os.listdir(person_path):
                    if img_file.lower().endswith(('.jpg', '.jpeg', '.png', '.pgm')):
                        img_path = os.path.join(person_path, img_file)
                        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                        if img is not None:
                            img = cv2.resize(img, (IMG_SIZE, IMG_SIZE))
                            images.append(img)
                            labels.append(person_dir)
                            # Add flipped version for data augmentation (especially for new registrations with 1 image)
                            flipped = cv2.flip(img, 1)
                            images.append(flipped)
                            labels.append(person_dir)
                            print(f"Loaded Custom: {person_dir}/{img_file} (+flipped)")
    
    print(f"Total loaded: {len(images)} images, {len(set(labels))} classes: {sorted(set(labels))}")
    return np.array(images), np.array(labels)

def retrain_model():
    """Retrain the model with current dataset."""
    global model, le
    
    try:
        print("🔄 Loading training data...")
        images, labels = load_training_data()
        
        if len(images) == 0:
            print("❌ No training data found")
            return False
        
        print(f"📊 Loaded {len(images)} images with {len(set(labels))} classes")
        
        # Encode labels
        le = LabelEncoder()
        encoded_labels = le.fit_transform(labels)
        num_classes = len(le.classes_)
        print(f"Classes: {le.classes_}")
        
        # Prepare data
        X = images.astype(np.float32) / 255.0
        X = X.reshape(-1, IMG_SIZE, IMG_SIZE, 1)
        y = to_categorical(encoded_labels, num_classes)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        print(f"Train: {len(X_train)}, Test: {len(X_test)}")
        
        # Build model (improved architecture)
        model = Sequential([
            Conv2D(32, (3, 3), activation='relu', input_shape=(IMG_SIZE, IMG_SIZE, 1)),
            MaxPooling2D((2, 2)),
            Conv2D(64, (3, 3), activation='relu'),
            MaxPooling2D((2, 2)),
            Conv2D(128, (3, 3), activation='relu'),
            MaxPooling2D((2, 2)),
            Flatten(),
            Dense(256, activation='relu'),
            Dropout(0.5),
            Dense(128, activation='relu'),
            Dropout(0.3),
            Dense(num_classes, activation='softmax')
        ])
        
        model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
        
        print("🚀 Training model...")
        history = model.fit(X_train, y_train, epochs=30, batch_size=32, validation_data=(X_test, y_test), verbose=1)
        print(f"Final accuracy: {history.history['accuracy'][-1]:.2f}, Val: {history.history['val_accuracy'][-1]:.2f}")
        
        # Save model and encoder
        model.save(MODEL_PATH)
        with open(LABEL_ENCODER_PATH, 'wb') as f:
            pickle.dump(le, f)
        
        # Reload the model and encoder
        _load_model_and_encoder()
        
        print("✅ Model retrained and saved")
        return True
        
    except Exception as e:
        print(f"❌ Retraining failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧠 Face Recognition System Ready!")
    print(get_model_info())

