from flask import Flask, request, jsonify, send_file, url_for
from flask_cors import CORS
import os
import uuid
import base64
import cv2
import numpy as np
from scipy.ndimage import gaussian_filter
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array
from werkzeug.utils import secure_filename
import matplotlib
matplotlib.use('Agg')
import json

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
PROCESSED_FOLDER = "processed"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

model = load_model("models/arch_classifier_model.h5")

label_map_rev = {
    0: "Pes_Cavus",
    1: "Pes_Planus",
    2: "Normal_Arch"
}

def classify_foot_arch(image_path):
    img = cv2.imread(image_path)
    img = cv2.resize(img, (224, 224))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = img_to_array(img) / 255.0
    img = np.expand_dims(img, axis=0)

    pred = model.predict(img)
    class_idx = np.argmax(pred)
    class_label = label_map_rev[class_idx]
    confidence = float(np.max(pred))

    return class_label, confidence

def process_image(image_path, filename):
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise Exception("Invalid image format or corrupted image")

    _, mask = cv2.threshold(image, 150, 255, cv2.THRESH_BINARY_INV)
    smoothed = gaussian_filter(mask.astype(float), sigma=10)

    norm_range = np.max(smoothed) - np.min(smoothed)
    normalized = (smoothed - np.min(smoothed)) / norm_range if norm_range != 0 else smoothed
    norm_pressure = (normalized * 255).astype(np.uint8)

    pressure_heatmap = cv2.applyColorMap(norm_pressure, cv2.COLORMAP_JET)
    pressure_heatmap_filename = os.path.join(PROCESSED_FOLDER, f"pressure_heatmap_{filename}")
    cv2.imwrite(pressure_heatmap_filename, pressure_heatmap)

    _, high_pressure_mask = cv2.threshold(norm_pressure, 180, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(high_pressure_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contour_overlay = pressure_heatmap.copy()
    cv2.drawContours(contour_overlay, contours, -1, (0, 0, 0), 5)

    contour_heatmap_filename = os.path.join(PROCESSED_FOLDER, f"contour_heatmap_{filename}")
    cv2.imwrite(contour_heatmap_filename, contour_overlay)

    return pressure_heatmap_filename, contour_heatmap_filename

def get_dpi(length_px):
    if length_px > 2500:
        return 300
    elif 1500 < length_px <= 2500:
        return 200
    elif 800 < length_px <= 1500:
        return 96
    elif 400 < length_px <= 800:
        return 72
    else:
        return 49

def preprocess_binary_image(image_path):
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    blur = cv2.GaussianBlur(img, (5, 5), 0)
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    invert = cv2.bitwise_not(thresh)
    return invert

def find_foot_contour(binary_img):
    contours, _ = cv2.findContours(binary_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return max(contours, key=cv2.contourArea) if contours else None

def get_dimensions_from_contour(contour):
    rect = cv2.minAreaRect(contour)
    (_, _), (width, height), _ = rect
    return max(width, height), min(width, height), cv2.contourArea(contour)

def get_arch_indices_and_widths(contour):
    x, y, w, h = cv2.boundingRect(contour)
    mask = np.zeros((h, w), dtype=np.uint8)
    shifted_contour = contour - [x, y]
    cv2.drawContours(mask, [shifted_contour], -1, 255, -1)
    vertical_projection = np.sum(mask == 255, axis=1)

    heel_region = vertical_projection[:int(h * 0.25)]
    midfoot_region = vertical_projection[int(h * 0.25):int(h * 0.65)]
    forefoot_region = vertical_projection[int(h * 0.65):]

    max_heel = np.max(heel_region) if len(heel_region) else 0
    min_mid = np.min(midfoot_region) if len(midfoot_region) else 0
    max_forefoot = np.max(forefoot_region) if len(forefoot_region) else 0

    staheli_index = round(min_mid / max_heel, 2) if max_heel else 0
    chippaux_index = round((min_mid / max_forefoot) * 100, 1) if max_forefoot else 0
    harris_index = round(min_mid / max_heel, 1) if max_heel else 0

    return staheli_index, chippaux_index, harris_index

def extract_foot_metrics(image_path):
    bin_img = preprocess_binary_image(image_path)
    contour = find_foot_contour(bin_img)
    if contour is None:
        raise ValueError("No foot contour found")

    length_px, width_px, _ = get_dimensions_from_contour(contour)
    dpi = get_dpi(length_px)
    length_cm = (length_px / dpi) * 2.54
    width_cm = (width_px / dpi) * 2.54

    staheli, chippaux, harris = get_arch_indices_and_widths(contour)

    return {
        "foot_length_cm": round(length_cm, 2),
        "foot_width_cm": round(width_cm, 2),
        "staheli_index": staheli,
        "chippaux_index": chippaux,
        "harris_index": harris
    }

@app.route("/upload", methods=["POST"])
def upload_image():
    try:
        file = request.files.get('file') or request.files.get('image')
        base64_image = request.form.get('base64_image')

        if file and file.filename != '':
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4()}_{filename}"
            file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
            file.save(file_path)
        elif base64_image:
            unique_filename = f"{uuid.uuid4()}.png"
            file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
            with open(file_path, "wb") as f:
                f.write(base64.b64decode(base64_image))
        else:
            return jsonify({"error": "No valid image provided"}), 400

        pressure_path, contour_path = process_image(file_path, unique_filename)
        predicted_label, confidence = classify_foot_arch(file_path)
        metrics = extract_foot_metrics(file_path)

        response_data = {
            "prediction": predicted_label,
            "confidence": round(confidence, 4),
            "pressure_heatmap": f"/get_image/{os.path.basename(pressure_path)}",
            "contour_heatmap": f"/get_image/{os.path.basename(contour_path)}",
            "foot_length_cm": metrics["foot_length_cm"],
            "foot_width_cm": metrics["foot_width_cm"],
            "staheli_index": metrics["staheli_index"],
            "chippaux_index": metrics["chippaux_index"],
            "harris_index": metrics["harris_index"]
        }
        print("Upload Result:", json.dumps(response_data, indent=2))

        return jsonify(response_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/get_image/<filename>")
def get_image(filename):
    image_path = os.path.join(PROCESSED_FOLDER, filename)
    if os.path.exists(image_path):
        return send_file(image_path, mimetype='image/png')
    else:
        return jsonify({"error": "Image not found"}), 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render provides this env variable
    app.run(host="0.0.0.0", port=port, debug=True)