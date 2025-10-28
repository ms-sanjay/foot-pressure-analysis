import os
import numpy as np
import cv2
from sklearn.model_selection import train_test_split
from tensorflow.keras import layers, models
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.models import Model
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.utils import to_categorical
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from collections import Counter

# === LABEL MAP ===
label_map = {
    "Pes_Cavus": 0,
    "Pes_Planus": 1,
    "Normal_Arch": 2
}

# === LOAD & RESIZE IMAGES TO 224x224 RGB ===
X = []
y = []
for label, value in label_map.items():
    folder_path = os.path.join("classified_results", label)
    for filename in os.listdir(folder_path):
        if filename.endswith(".png"):
            img_path = os.path.join(folder_path, filename)
            img = cv2.imread(img_path)
            img = cv2.resize(img, (224, 224))  # MobileNetV2 input size
            X.append(img)
            y.append(value)

X = np.array(X) / 255.0  # Normalize
y = np.array(y)

# === DEBUG: PRINT CLASS DISTRIBUTION =
print("Total samples:", len(y))
print("Class distribution:", Counter(y))

# === SPLIT DATA ===
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# === ONE-HOT ENCODING ===
y_train = to_categorical(y_train, num_classes=3)
y_test = to_categorical(y_test, num_classes=3)

# === DATA AUGMENTATION ===
datagen = ImageDataGenerator(
    rotation_range=15,
    width_shift_range=0.1,
    height_shift_range=0.1,
    zoom_range=0.1,
    horizontal_flip=True
)
datagen.fit(X_train)

# === MOBILENETV2 BASE ===
base_model = MobileNetV2(weights='imagenet', include_top=False, input_shape=(224, 224, 3))
for layer in base_model.layers:
    layer.trainable = False  # Freeze all base layers initially

x = base_model.output
x = layers.GlobalAveragePooling2D()(x)
x = layers.Dense(128, activation='relu')(x)
x = layers.Dropout(0.3)(x)
predictions = layers.Dense(3, activation='softmax')(x)

model = Model(inputs=base_model.input, outputs=predictions)

model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

# === EARLY STOPPING ===
early_stop = EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)

# === TRAIN MODEL ===
history = model.fit(
    datagen.flow(X_train, y_train, batch_size=8),
    epochs=25,
    validation_data=(X_test, y_test),
    callbacks=[early_stop]
)

# === EVALUATE ===
test_loss, test_acc = model.evaluate(X_test, y_test)
print("✅ MobileNetV2 Accuracy: {:.4f}".format(test_acc))

# === PREDICT ===
y_pred = model.predict(X_test)
y_pred_labels = np.argmax(y_pred, axis=1)
y_true_labels = np.argmax(y_test, axis=1)

model.save("models/arch_classifier_model.h5")