#!/usr/bin/env python3
"""
Generate AI/ML Gold Samples - Simplified Version
"""

import json
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "gold_samples"

SYSTEM_PROMPT = """You are an expert AI/ML engineer. Respond with this exact structure:

PLAN:
1) First step
2) Second step
...

FILES:
- path/to/file.py
...

PATCH:
*** Begin Patch
--- a/path/to/file.py
+++ b/path/to/file.py
@@ -line,count +line,count @@
 context
-removed
+added
*** End Patch

COMMANDS:
- command to run
...

NOTES:
- Important notes
...

Use unified diff format. Be precise."""


def create_example(prompt, response, category):
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response}
        ],
        "category": category
    }


# AI/ML Samples
AIML_SAMPLES = [
    # PyTorch CNN
    {
        "prompt": "Create a PyTorch CNN for image classification",
        "response": '''PLAN:
1) Define CNN architecture with conv layers
2) Add batch normalization and dropout
3) Create training loop
4) Add model checkpointing

FILES:
- ml/models/cnn.py
- ml/train.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/ml/models/cnn.py
@@ -0,0 +1,40 @@
+import torch
+import torch.nn as nn
+import torch.nn.functional as F
+
+class CNN(nn.Module):
+    def __init__(self, num_classes=10):
+        super().__init__()
+        self.conv1 = nn.Conv2d(3, 32, 3, padding=1)
+        self.bn1 = nn.BatchNorm2d(32)
+        self.conv2 = nn.Conv2d(32, 64, 3, padding=1)
+        self.bn2 = nn.BatchNorm2d(64)
+        self.conv3 = nn.Conv2d(64, 128, 3, padding=1)
+        self.bn3 = nn.BatchNorm2d(128)
+        self.pool = nn.MaxPool2d(2, 2)
+        self.dropout = nn.Dropout(0.5)
+        self.fc1 = nn.Linear(128 * 4 * 4, 512)
+        self.fc2 = nn.Linear(512, num_classes)
+
+    def forward(self, x):
+        x = self.pool(F.relu(self.bn1(self.conv1(x))))
+        x = self.pool(F.relu(self.bn2(self.conv2(x))))
+        x = self.pool(F.relu(self.bn3(self.conv3(x))))
+        x = x.view(x.size(0), -1)
+        x = self.dropout(F.relu(self.fc1(x)))
+        return self.fc2(x)
*** End Patch

COMMANDS:
- pip install torch torchvision
- python ml/train.py

NOTES:
- Uses BatchNorm for faster convergence
- Dropout prevents overfitting''',
        "category": "pytorch"
    },

    # PyTorch Training Loop
    {
        "prompt": "Implement PyTorch training loop with validation",
        "response": '''PLAN:
1) Create train_epoch function
2) Create validate function
3) Add learning rate scheduler
4) Save best model

FILES:
- ml/trainer.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/ml/trainer.py
@@ -0,0 +1,50 @@
+import torch
+import torch.nn as nn
+from tqdm import tqdm
+
+def train_epoch(model, loader, criterion, optimizer, device):
+    model.train()
+    total_loss, correct, total = 0, 0, 0
+
+    for data, target in tqdm(loader):
+        data, target = data.to(device), target.to(device)
+        optimizer.zero_grad()
+        output = model(data)
+        loss = criterion(output, target)
+        loss.backward()
+        optimizer.step()
+
+        total_loss += loss.item()
+        pred = output.argmax(dim=1)
+        correct += pred.eq(target).sum().item()
+        total += target.size(0)
+
+    return total_loss / len(loader), correct / total
+
+def validate(model, loader, criterion, device):
+    model.eval()
+    total_loss, correct, total = 0, 0, 0
+
+    with torch.no_grad():
+        for data, target in loader:
+            data, target = data.to(device), target.to(device)
+            output = model(data)
+            total_loss += criterion(output, target).item()
+            correct += output.argmax(1).eq(target).sum().item()
+            total += target.size(0)
+
+    return total_loss / len(loader), correct / total
*** End Patch

COMMANDS:
- pip install torch tqdm
- python ml/trainer.py

NOTES:
- Uses tqdm for progress bar
- Returns loss and accuracy''',
        "category": "pytorch"
    },

    # Transfer Learning
    {
        "prompt": "Implement transfer learning with pretrained ResNet",
        "response": '''PLAN:
1) Load pretrained ResNet50
2) Freeze base layers
3) Replace classification head
4) Fine-tune

FILES:
- ml/transfer.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/ml/transfer.py
@@ -0,0 +1,35 @@
+import torch
+import torch.nn as nn
+from torchvision import models
+
+class TransferModel(nn.Module):
+    def __init__(self, num_classes, freeze_base=True):
+        super().__init__()
+        self.base = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
+
+        if freeze_base:
+            for param in self.base.parameters():
+                param.requires_grad = False
+
+        in_features = self.base.fc.in_features
+        self.base.fc = nn.Sequential(
+            nn.Dropout(0.5),
+            nn.Linear(in_features, 512),
+            nn.ReLU(),
+            nn.Linear(512, num_classes)
+        )
+
+    def forward(self, x):
+        return self.base(x)
+
+    def unfreeze(self, layers=2):
+        children = list(self.base.children())
+        for child in children[-layers:]:
+            for param in child.parameters():
+                param.requires_grad = True
*** End Patch

COMMANDS:
- pip install torch torchvision
- python ml/transfer.py

NOTES:
- Uses ResNet50 pretrained on ImageNet
- Freeze base, train head first''',
        "category": "pytorch"
    },

    # TensorFlow Keras
    {
        "prompt": "Create TensorFlow Keras model for text classification",
        "response": '''PLAN:
1) Build text preprocessing
2) Create LSTM model
3) Add callbacks
4) Train model

FILES:
- ml/text_model.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/ml/text_model.py
@@ -0,0 +1,45 @@
+import tensorflow as tf
+from tensorflow import keras
+from tensorflow.keras import layers
+
+def create_text_classifier(vocab_size=10000, max_len=200, num_classes=5):
+    inputs = keras.Input(shape=(max_len,))
+
+    x = layers.Embedding(vocab_size, 128)(inputs)
+    x = layers.Bidirectional(layers.LSTM(64, return_sequences=True))(x)
+    x = layers.Bidirectional(layers.LSTM(32))(x)
+    x = layers.Dense(64, activation='relu')(x)
+    x = layers.Dropout(0.5)(x)
+    outputs = layers.Dense(num_classes, activation='softmax')(x)
+
+    model = keras.Model(inputs, outputs)
+    model.compile(
+        optimizer='adam',
+        loss='sparse_categorical_crossentropy',
+        metrics=['accuracy']
+    )
+    return model
+
+def train_model(model, train_x, train_y, val_data, epochs=10):
+    callbacks = [
+        keras.callbacks.EarlyStopping(patience=3, restore_best_weights=True),
+        keras.callbacks.ReduceLROnPlateau(factor=0.5, patience=2),
+        keras.callbacks.ModelCheckpoint('best.h5', save_best_only=True)
+    ]
+
+    return model.fit(
+        train_x, train_y,
+        validation_data=val_data,
+        epochs=epochs,
+        callbacks=callbacks,
+        batch_size=32
+    )
*** End Patch

COMMANDS:
- pip install tensorflow
- python ml/text_model.py

NOTES:
- Bidirectional LSTM for context
- EarlyStopping prevents overfitting''',
        "category": "tensorflow"
    },

    # Scikit-learn Pipeline
    {
        "prompt": "Create scikit-learn ML pipeline with preprocessing",
        "response": '''PLAN:
1) Create preprocessing pipeline
2) Add model selection
3) Cross-validation
4) Hyperparameter tuning

FILES:
- ml/pipeline.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/ml/pipeline.py
@@ -0,0 +1,50 @@
+from sklearn.pipeline import Pipeline
+from sklearn.compose import ColumnTransformer
+from sklearn.preprocessing import StandardScaler, OneHotEncoder
+from sklearn.impute import SimpleImputer
+from sklearn.ensemble import RandomForestClassifier
+from sklearn.model_selection import cross_val_score, GridSearchCV
+
+def create_pipeline(numeric_features, categorical_features):
+    numeric_transformer = Pipeline([
+        ('imputer', SimpleImputer(strategy='median')),
+        ('scaler', StandardScaler())
+    ])
+
+    categorical_transformer = Pipeline([
+        ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
+        ('encoder', OneHotEncoder(handle_unknown='ignore'))
+    ])
+
+    preprocessor = ColumnTransformer([
+        ('num', numeric_transformer, numeric_features),
+        ('cat', categorical_transformer, categorical_features)
+    ])
+
+    return Pipeline([
+        ('preprocessor', preprocessor),
+        ('classifier', RandomForestClassifier(n_estimators=100))
+    ])
+
+def tune_pipeline(pipeline, X, y, param_grid):
+    grid = GridSearchCV(pipeline, param_grid, cv=5, scoring='accuracy', n_jobs=-1)
+    grid.fit(X, y)
+    return grid.best_params_, grid.best_score_
*** End Patch

COMMANDS:
- pip install scikit-learn pandas
- python ml/pipeline.py

NOTES:
- Handles numeric and categorical separately
- GridSearchCV for tuning''',
        "category": "sklearn"
    },

    # Hugging Face
    {
        "prompt": "Fine-tune Hugging Face transformer for classification",
        "response": '''PLAN:
1) Load pretrained model
2) Prepare dataset
3) Configure Trainer
4) Train and evaluate

FILES:
- ml/hf_train.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/ml/hf_train.py
@@ -0,0 +1,55 @@
+from transformers import (
+    AutoTokenizer,
+    AutoModelForSequenceClassification,
+    TrainingArguments,
+    Trainer
+)
+from datasets import Dataset
+import numpy as np
+
+class HFClassifier:
+    def __init__(self, model_name="distilbert-base-uncased", num_labels=2):
+        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
+        self.model = AutoModelForSequenceClassification.from_pretrained(
+            model_name, num_labels=num_labels
+        )
+
+    def tokenize(self, examples):
+        return self.tokenizer(examples["text"], truncation=True, max_length=512)
+
+    def prepare_data(self, texts, labels):
+        dataset = Dataset.from_dict({"text": texts, "label": labels})
+        return dataset.map(self.tokenize, batched=True)
+
+    def train(self, train_texts, train_labels, val_texts=None, val_labels=None):
+        train_ds = self.prepare_data(train_texts, train_labels)
+        val_ds = self.prepare_data(val_texts, val_labels) if val_texts else None
+
+        args = TrainingArguments(
+            output_dir="./model",
+            num_train_epochs=3,
+            per_device_train_batch_size=16,
+            evaluation_strategy="epoch" if val_ds else "no",
+            save_strategy="epoch",
+            load_best_model_at_end=True if val_ds else False,
+        )
+
+        trainer = Trainer(
+            model=self.model,
+            args=args,
+            train_dataset=train_ds,
+            eval_dataset=val_ds,
+            tokenizer=self.tokenizer,
+        )
+
+        trainer.train()
+        return trainer
*** End Patch

COMMANDS:
- pip install transformers datasets torch
- python ml/hf_train.py

NOTES:
- Uses DistilBERT for efficiency
- Saves best model''',
        "category": "huggingface"
    },

    # Data Preprocessing
    {
        "prompt": "Create data preprocessing pipeline with Pandas",
        "response": '''PLAN:
1) Handle missing values
2) Detect outliers
3) Encode features
4) Scale numeric

FILES:
- ml/preprocess.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/ml/preprocess.py
@@ -0,0 +1,55 @@
+import pandas as pd
+import numpy as np
+from sklearn.preprocessing import StandardScaler, LabelEncoder
+
+class DataPreprocessor:
+    def __init__(self):
+        self.scalers = {}
+        self.encoders = {}
+
+    def handle_missing(self, df, numeric_strategy='median', cat_strategy='mode'):
+        df = df.copy()
+
+        for col in df.select_dtypes(include=[np.number]).columns:
+            if df[col].isnull().any():
+                val = df[col].median() if numeric_strategy == 'median' else df[col].mean()
+                df[col] = df[col].fillna(val)
+
+        for col in df.select_dtypes(include=['object']).columns:
+            if df[col].isnull().any():
+                df[col] = df[col].fillna(df[col].mode()[0])
+
+        return df
+
+    def remove_outliers(self, df, threshold=1.5):
+        df = df.copy()
+        for col in df.select_dtypes(include=[np.number]).columns:
+            Q1, Q3 = df[col].quantile([0.25, 0.75])
+            IQR = Q3 - Q1
+            df[col] = df[col].clip(Q1 - threshold*IQR, Q3 + threshold*IQR)
+        return df
+
+    def encode(self, df, columns=None):
+        df = df.copy()
+        if columns is None:
+            columns = df.select_dtypes(include=['object']).columns
+
+        for col in columns:
+            if df[col].nunique() <= 10:
+                dummies = pd.get_dummies(df[col], prefix=col)
+                df = pd.concat([df.drop(col, axis=1), dummies], axis=1)
+            else:
+                le = LabelEncoder()
+                df[col] = le.fit_transform(df[col].astype(str))
+                self.encoders[col] = le
+        return df
+
+    def scale(self, df, columns=None):
+        df = df.copy()
+        if columns is None:
+            columns = df.select_dtypes(include=[np.number]).columns
+        scaler = StandardScaler()
+        df[columns] = scaler.fit_transform(df[columns])
+        self.scalers['standard'] = scaler
+        return df
*** End Patch

COMMANDS:
- pip install pandas numpy scikit-learn
- python ml/preprocess.py

NOTES:
- IQR method for outliers
- Auto-encoding based on cardinality''',
        "category": "pandas"
    },

    # YOLO Detection
    {
        "prompt": "Create object detection with YOLO",
        "response": '''PLAN:
1) Load YOLO model
2) Run inference
3) Draw bounding boxes
4) Return detections

FILES:
- ml/detector.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/ml/detector.py
@@ -0,0 +1,40 @@
+import torch
+import cv2
+import numpy as np
+
+class YOLODetector:
+    def __init__(self, confidence=0.5):
+        self.model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
+        self.model.conf = confidence
+
+    def detect(self, image):
+        results = self.model(image)
+        detections = []
+
+        for *box, conf, cls in results.xyxy[0].cpu().numpy():
+            detections.append({
+                'bbox': [int(x) for x in box],
+                'confidence': float(conf),
+                'class': self.model.names[int(cls)]
+            })
+        return detections
+
+    def draw(self, image, detections):
+        img = image.copy()
+        for det in detections:
+            x1, y1, x2, y2 = det['bbox']
+            label = f"{det['class']} {det['confidence']:.2f}"
+            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
+            cv2.putText(img, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)
+        return img
*** End Patch

COMMANDS:
- pip install torch opencv-python
- python ml/detector.py

NOTES:
- Uses YOLOv5 from Ultralytics
- Returns bbox, confidence, class''',
        "category": "computer_vision"
    },

    # NER with spaCy
    {
        "prompt": "Implement Named Entity Recognition with spaCy",
        "response": '''PLAN:
1) Load spaCy model
2) Custom NER training
3) Predict entities
4) Save model

FILES:
- ml/ner.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/ml/ner.py
@@ -0,0 +1,45 @@
+import spacy
+from spacy.training import Example
+import random
+
+class CustomNER:
+    def __init__(self, model="en_core_web_sm"):
+        self.nlp = spacy.load(model)
+        if "ner" not in self.nlp.pipe_names:
+            self.ner = self.nlp.add_pipe("ner")
+        else:
+            self.ner = self.nlp.get_pipe("ner")
+
+    def train(self, train_data, n_iter=30):
+        for _, annotations in train_data:
+            for ent in annotations.get("entities", []):
+                self.ner.add_label(ent[2])
+
+        other_pipes = [p for p in self.nlp.pipe_names if p != "ner"]
+        with self.nlp.disable_pipes(*other_pipes):
+            optimizer = self.nlp.begin_training()
+            for i in range(n_iter):
+                random.shuffle(train_data)
+                losses = {}
+                for text, annotations in train_data:
+                    doc = self.nlp.make_doc(text)
+                    example = Example.from_dict(doc, annotations)
+                    self.nlp.update([example], losses=losses)
+                print(f"Iter {i}: {losses}")
+
+    def predict(self, text):
+        doc = self.nlp(text)
+        return [{"text": e.text, "label": e.label_} for e in doc.ents]
+
+    def save(self, path):
+        self.nlp.to_disk(path)
*** End Patch

COMMANDS:
- pip install spacy
- python -m spacy download en_core_web_sm
- python ml/ner.py

NOTES:
- Custom entity training
- Saves trained model''',
        "category": "nlp"
    },

    # MLflow
    {
        "prompt": "Implement MLflow experiment tracking",
        "response": '''PLAN:
1) Set up tracking
2) Log params and metrics
3) Log model
4) Register model

FILES:
- ml/tracking.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/ml/tracking.py
@@ -0,0 +1,45 @@
+import mlflow
+import mlflow.sklearn
+from mlflow.tracking import MlflowClient
+
+class ExperimentTracker:
+    def __init__(self, experiment_name, tracking_uri="sqlite:///mlflow.db"):
+        mlflow.set_tracking_uri(tracking_uri)
+        mlflow.set_experiment(experiment_name)
+        self.client = MlflowClient()
+
+    def start_run(self, name=None):
+        return mlflow.start_run(run_name=name)
+
+    def log_params(self, params):
+        mlflow.log_params(params)
+
+    def log_metrics(self, metrics, step=None):
+        mlflow.log_metrics(metrics, step=step)
+
+    def log_model(self, model, name="model"):
+        mlflow.sklearn.log_model(model, name)
+
+    def register_model(self, run_id, name):
+        model_uri = f"runs:/{run_id}/model"
+        return mlflow.register_model(model_uri, name)
+
+    def end_run(self):
+        mlflow.end_run()
+
+# Usage
+def train_with_tracking():
+    tracker = ExperimentTracker("my_exp")
+    with tracker.start_run("v1"):
+        tracker.log_params({"lr": 0.01, "epochs": 100})
+        for i in range(100):
+            tracker.log_metrics({"loss": 1.0 - i*0.01}, step=i)
+        tracker.log_model(model)
*** End Patch

COMMANDS:
- pip install mlflow scikit-learn
- mlflow ui --port 5000
- python ml/tracking.py

NOTES:
- SQLite for local tracking
- Model versioning''',
        "category": "mlops"
    },

    # LSTM Time Series
    {
        "prompt": "Create LSTM for time series forecasting",
        "response": '''PLAN:
1) Define LSTM model
2) Create sequences
3) Train with teacher forcing
4) Multi-step prediction

FILES:
- ml/lstm.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/ml/lstm.py
@@ -0,0 +1,50 @@
+import torch
+import torch.nn as nn
+
+class LSTMForecaster(nn.Module):
+    def __init__(self, input_size=1, hidden_size=64, num_layers=2, output_size=1):
+        super().__init__()
+        self.hidden_size = hidden_size
+        self.num_layers = num_layers
+
+        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=0.2)
+        self.fc = nn.Linear(hidden_size, output_size)
+
+    def forward(self, x, hidden=None):
+        out, hidden = self.lstm(x, hidden)
+        out = self.fc(out[:, -1, :])
+        return out, hidden
+
+    def predict_steps(self, x, steps):
+        self.eval()
+        preds = []
+        hidden = None
+
+        with torch.no_grad():
+            _, hidden = self.lstm(x, hidden)
+            current = x[:, -1:, :]
+
+            for _ in range(steps):
+                out, hidden = self.lstm(current, hidden)
+                pred = self.fc(out[:, -1, :])
+                preds.append(pred)
+                current = pred.unsqueeze(1)
+
+        return torch.stack(preds, dim=1)
+
+def create_sequences(data, seq_len):
+    X, y = [], []
+    for i in range(len(data) - seq_len):
+        X.append(data[i:i+seq_len])
+        y.append(data[i+seq_len])
+    return torch.stack(X), torch.stack(y)
*** End Patch

COMMANDS:
- pip install torch numpy
- python ml/lstm.py

NOTES:
- Multi-step autoregressive prediction
- Stacked LSTM with dropout''',
        "category": "pytorch"
    },

    # Custom TF Training
    {
        "prompt": "Implement custom training loop in TensorFlow",
        "response": '''PLAN:
1) Custom train step
2) Gradient tape
3) Metrics tracking
4) Validation loop

FILES:
- ml/custom_train.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/ml/custom_train.py
@@ -0,0 +1,50 @@
+import tensorflow as tf
+
+class CustomTrainer:
+    def __init__(self, model, optimizer):
+        self.model = model
+        self.optimizer = optimizer
+        self.loss_fn = tf.keras.losses.SparseCategoricalCrossentropy()
+        self.train_loss = tf.keras.metrics.Mean()
+        self.train_acc = tf.keras.metrics.SparseCategoricalAccuracy()
+
+    @tf.function
+    def train_step(self, x, y):
+        with tf.GradientTape() as tape:
+            preds = self.model(x, training=True)
+            loss = self.loss_fn(y, preds)
+
+        grads = tape.gradient(loss, self.model.trainable_variables)
+        grads, _ = tf.clip_by_global_norm(grads, 1.0)
+        self.optimizer.apply_gradients(zip(grads, self.model.trainable_variables))
+
+        self.train_loss.update_state(loss)
+        self.train_acc.update_state(y, preds)
+
+    def fit(self, train_ds, epochs):
+        for epoch in range(epochs):
+            self.train_loss.reset_states()
+            self.train_acc.reset_states()
+
+            for x, y in train_ds:
+                self.train_step(x, y)
+
+            print(f"Epoch {epoch+1}: Loss={self.train_loss.result():.4f}, Acc={self.train_acc.result():.4f}")
*** End Patch

COMMANDS:
- pip install tensorflow
- python ml/custom_train.py

NOTES:
- @tf.function for optimization
- Gradient clipping''',
        "category": "tensorflow"
    },
]


def main():
    print("=" * 60)
    print("GENERATING AI/ML GOLD SAMPLES")
    print("=" * 60)

    samples = [create_example(s["prompt"], s["response"], s["category"]) for s in AIML_SAMPLES]

    # Count by category
    categories = {}
    for sample in samples:
        cat = sample.get("category", "other")
        categories[cat] = categories.get(cat, 0) + 1

    print(f"\nNew AI/ML Samples: {len(samples)}")
    print("\nBy Category:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    # Load existing
    existing_file = OUTPUT_DIR / "gold_samples.jsonl"
    existing = []
    if existing_file.exists():
        with open(existing_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    existing.append(json.loads(line))

    print(f"\nExisting samples: {len(existing)}")

    # Merge
    all_samples = existing + samples
    print(f"Total: {len(all_samples)}")

    # Save
    OUTPUT_DIR.mkdir(exist_ok=True)
    with open(existing_file, 'w', encoding='utf-8') as f:
        for sample in all_samples:
            f.write(json.dumps(sample, ensure_ascii=False) + '\n')

    # Update summary
    all_cats = {}
    for s in all_samples:
        c = s.get("category", "other")
        all_cats[c] = all_cats.get(c, 0) + 1

    with open(OUTPUT_DIR / "summary.json", 'w') as f:
        json.dump({"total_samples": len(all_samples), "categories": all_cats}, f, indent=2)

    print(f"\nSaved to: {existing_file}")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
