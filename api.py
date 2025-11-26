import os
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import joblib
import pandas as pd
from feature_extraction import extract_features, feature_columns

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "Predict", "model", "xgb_model.pkl")
SCHEMA_PATH = os.path.join(BASE_DIR, "Predict", "model", "feature_schema.json")

app = FastAPI()

# Tải mô hình
try:
    model = joblib.load(MODEL_PATH)
except Exception as e:
    raise RuntimeError(f"Không thể tải mô hình: {e}")

class URLRequest(BaseModel):
    url: str

# Tải lược đồ đặc trưng
try:
    with open(SCHEMA_PATH, "r") as f:
        expected_features = json.load(f)
    expected_feature_count = len(expected_features)
except Exception as e:
    raise RuntimeError(f"Không thể tải lược đồ đặc trưng: {e}")

@app.post("/phish-url-prediction")
async def predict(input_data: URLRequest):
    url = input_data.url

    try:
        features = extract_features(url)
        X = pd.DataFrame([features], columns=feature_columns)
        print(f"Đặc trưng đã trích xuất: {X.iloc[0].to_dict()}")

        if X.shape[1] != expected_feature_count:
            raise ValueError(
                f"Số lượng đặc trưng không đúng. Mong đợi {expected_feature_count}, nhận được {X.shape[1]}"
            )

        pred = model.predict(X)[0]
        proba = model.predict_proba(X)[0][1]

        label_id = int(pred)
        label_str = "phish" if label_id == 1 else "safe"
        message = "Phishing URL" if label_id == 1 else "Legitimate URL"

        return {
            "url": url,
            "label": label_str,
            "label_id": label_id,
            "prediction": message,
            "confidence": round(float(proba), 4),
            "features": dict(zip(feature_columns, features)),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi dự đoán: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)

