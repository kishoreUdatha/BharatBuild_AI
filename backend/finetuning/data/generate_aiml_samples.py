#!/usr/bin/env python3
"""
Generate AI/ML Gold Samples for Fine-tuning

Categories:
1. PyTorch - Neural networks, training loops
2. TensorFlow/Keras - Models, training
3. Scikit-learn - ML pipelines
4. Pandas/NumPy - Data manipulation
5. Hugging Face - Transformers
6. MLOps - MLflow, deployment
7. Computer Vision - CNN, image processing
8. NLP - Text classification
9. Data Science - EDA, visualization
"""

import json
import random
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


def create_example(prompt: str, response: str, category: str) -> dict:
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response}
        ],
        "category": category
    }


# ============================================================================
# PYTORCH SAMPLES
# ============================================================================

def generate_pytorch_samples() -> list:
    samples = []

    # 1. Basic Neural Network
    samples.append(create_example(
        "Create a PyTorch neural network for image classification with CNN layers",
        """PLAN:
1) Define CNN architecture with conv layers
2) Add batch normalization and dropout
3) Create training loop with validation
4) Add model checkpointing

FILES:
- ml/models/cnn_classifier.py
- ml/train.py
- ml/utils/metrics.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/ml/models/cnn_classifier.py
@@ -0,0 +1,55 @@
+import torch
+import torch.nn as nn
+import torch.nn.functional as F
+
+class CNNClassifier(nn.Module):
+    def __init__(self, num_classes: int = 10, dropout: float = 0.5):
+        super().__init__()
+
+        # Convolutional layers
+        self.conv1 = nn.Conv2d(3, 32, kernel_size=3, padding=1)
+        self.bn1 = nn.BatchNorm2d(32)
+        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
+        self.bn2 = nn.BatchNorm2d(64)
+        self.conv3 = nn.Conv2d(64, 128, kernel_size=3, padding=1)
+        self.bn3 = nn.BatchNorm2d(128)
+
+        self.pool = nn.MaxPool2d(2, 2)
+        self.dropout = nn.Dropout(dropout)
+
+        # Fully connected layers
+        self.fc1 = nn.Linear(128 * 4 * 4, 512)
+        self.fc2 = nn.Linear(512, num_classes)
+
+    def forward(self, x: torch.Tensor) -> torch.Tensor:
+        # Conv block 1
+        x = self.pool(F.relu(self.bn1(self.conv1(x))))
+
+        # Conv block 2
+        x = self.pool(F.relu(self.bn2(self.conv2(x))))
+
+        # Conv block 3
+        x = self.pool(F.relu(self.bn3(self.conv3(x))))
+
+        # Flatten and FC layers
+        x = x.view(x.size(0), -1)
+        x = self.dropout(F.relu(self.fc1(x)))
+        x = self.fc2(x)
+
+        return x

--- /dev/null
+++ b/ml/train.py
@@ -0,0 +1,65 @@
+import torch
+import torch.nn as nn
+import torch.optim as optim
+from torch.utils.data import DataLoader
+from tqdm import tqdm
+from models.cnn_classifier import CNNClassifier
+
+def train_epoch(model, loader, criterion, optimizer, device):
+    model.train()
+    total_loss = 0
+    correct = 0
+    total = 0
+
+    for batch_idx, (data, target) in enumerate(tqdm(loader)):
+        data, target = data.to(device), target.to(device)
+
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
+    total_loss = 0
+    correct = 0
+    total = 0
+
+    with torch.no_grad():
+        for data, target in loader:
+            data, target = data.to(device), target.to(device)
+            output = model(data)
+            total_loss += criterion(output, target).item()
+            pred = output.argmax(dim=1)
+            correct += pred.eq(target).sum().item()
+            total += target.size(0)
+
+    return total_loss / len(loader), correct / total
+
+def main():
+    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
+    model = CNNClassifier(num_classes=10).to(device)
+    criterion = nn.CrossEntropyLoss()
+    optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=0.01)
+    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=100)
+
+    # Training loop
+    for epoch in range(100):
+        train_loss, train_acc = train_epoch(model, train_loader, criterion, optimizer, device)
+        val_loss, val_acc = validate(model, val_loader, criterion, device)
+        scheduler.step()
+
+        print(f"Epoch {epoch}: Train Loss={train_loss:.4f}, Acc={train_acc:.4f}")
+
+        # Save checkpoint
+        if val_acc > best_acc:
+            torch.save(model.state_dict(), "best_model.pt")
*** End Patch

COMMANDS:
- pip install torch torchvision tqdm
- python ml/train.py

NOTES:
- Uses BatchNorm for faster convergence
- Dropout prevents overfitting
- CosineAnnealing scheduler for better LR decay
- Save best model based on validation accuracy""",
        "pytorch"
    ))

    # 2. Custom Dataset
    samples.append(create_example(
        "Create a custom PyTorch Dataset for loading images from folders with augmentation",
        """PLAN:
1) Create custom Dataset class
2) Add image augmentation transforms
3) Implement DataLoader with workers
4) Add caching for faster loading

FILES:
- ml/data/dataset.py
- ml/data/transforms.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/ml/data/dataset.py
@@ -0,0 +1,55 @@
+import torch
+from torch.utils.data import Dataset, DataLoader
+from pathlib import Path
+from PIL import Image
+from typing import Optional, Callable, Tuple
+import os
+
+class ImageFolderDataset(Dataset):
+    def __init__(
+        self,
+        root_dir: str,
+        transform: Optional[Callable] = None,
+        cache_images: bool = False
+    ):
+        self.root_dir = Path(root_dir)
+        self.transform = transform
+        self.cache_images = cache_images
+        self.cache = {}
+
+        # Get class names from folder names
+        self.classes = sorted([d.name for d in self.root_dir.iterdir() if d.is_dir()])
+        self.class_to_idx = {cls: idx for idx, cls in enumerate(self.classes)}
+
+        # Collect all image paths
+        self.samples = []
+        for class_name in self.classes:
+            class_dir = self.root_dir / class_name
+            for img_path in class_dir.glob("*.jpg"):
+                self.samples.append((img_path, self.class_to_idx[class_name]))
+            for img_path in class_dir.glob("*.png"):
+                self.samples.append((img_path, self.class_to_idx[class_name]))
+
+    def __len__(self) -> int:
+        return len(self.samples)
+
+    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
+        img_path, label = self.samples[idx]
+
+        # Check cache
+        if self.cache_images and idx in self.cache:
+            image = self.cache[idx]
+        else:
+            image = Image.open(img_path).convert("RGB")
+            if self.cache_images:
+                self.cache[idx] = image
+
+        if self.transform:
+            image = self.transform(image)
+
+        return image, label
+
+def get_dataloader(dataset: Dataset, batch_size: int = 32, shuffle: bool = True):
+    return DataLoader(
+        dataset,
+        batch_size=batch_size,
+        shuffle=shuffle,
+        num_workers=4,
+        pin_memory=True
+    )
*** End Patch

COMMANDS:
- pip install torch torchvision pillow
- python -c "from ml.data.dataset import ImageFolderDataset; print('OK')"

NOTES:
- Supports jpg and png images
- Optional image caching for small datasets
- pin_memory for faster GPU transfer
- num_workers=4 for parallel loading""",
        "pytorch"
    ))

    # 3. Transfer Learning
    samples.append(create_example(
        "Implement transfer learning with a pretrained ResNet for custom classification",
        """PLAN:
1) Load pretrained ResNet50
2) Freeze base layers
3) Replace classification head
4) Fine-tune with differential learning rates

FILES:
- ml/models/transfer_model.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/ml/models/transfer_model.py
@@ -0,0 +1,60 @@
+import torch
+import torch.nn as nn
+from torchvision import models
+from typing import List
+
+class TransferResNet(nn.Module):
+    def __init__(self, num_classes: int, freeze_base: bool = True):
+        super().__init__()
+
+        # Load pretrained ResNet50
+        self.base = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V2)
+
+        # Freeze base layers
+        if freeze_base:
+            for param in self.base.parameters():
+                param.requires_grad = False
+
+        # Replace classifier head
+        in_features = self.base.fc.in_features
+        self.base.fc = nn.Sequential(
+            nn.Dropout(0.5),
+            nn.Linear(in_features, 512),
+            nn.ReLU(),
+            nn.Dropout(0.3),
+            nn.Linear(512, num_classes)
+        )
+
+    def forward(self, x: torch.Tensor) -> torch.Tensor:
+        return self.base(x)
+
+    def unfreeze_layers(self, num_layers: int = 2):
+        """Unfreeze last N layers for fine-tuning"""
+        layers = list(self.base.children())
+        for layer in layers[-num_layers:]:
+            for param in layer.parameters():
+                param.requires_grad = True
+
+    def get_optimizer_params(self, lr_base: float = 1e-5, lr_head: float = 1e-3) -> List[dict]:
+        """Get params with differential learning rates"""
+        base_params = [p for n, p in self.base.named_parameters()
+                       if 'fc' not in n and p.requires_grad]
+        head_params = list(self.base.fc.parameters())
+
+        return [
+            {'params': base_params, 'lr': lr_base},
+            {'params': head_params, 'lr': lr_head}
+        ]
+
+# Usage
+def create_model(num_classes: int):
+    model = TransferResNet(num_classes=num_classes, freeze_base=True)
+
+    # First train only head
+    optimizer = torch.optim.AdamW(model.base.fc.parameters(), lr=1e-3)
+
+    # Then unfreeze and fine-tune
+    model.unfreeze_layers(num_layers=3)
+    optimizer = torch.optim.AdamW(model.get_optimizer_params(), weight_decay=0.01)
+
+    return model, optimizer
*** End Patch

COMMANDS:
- pip install torch torchvision
- python -c "from ml.models.transfer_model import TransferResNet; m = TransferResNet(10); print(m)"

NOTES:
- Uses ResNet50 pretrained on ImageNet
- Freeze base, train head first
- Differential LR: lower for base, higher for head
- Gradually unfreeze for fine-tuning""",
        "pytorch"
    ))

    # 4. LSTM for Time Series
    samples.append(create_example(
        "Create an LSTM model for time series forecasting in PyTorch",
        """PLAN:
1) Define LSTM architecture
2) Create sequence dataset
3) Implement training with teacher forcing
4) Add inference with autoregression

FILES:
- ml/models/lstm_forecast.py
- ml/data/time_series.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/ml/models/lstm_forecast.py
@@ -0,0 +1,70 @@
+import torch
+import torch.nn as nn
+from typing import Tuple
+
+class LSTMForecaster(nn.Module):
+    def __init__(
+        self,
+        input_size: int = 1,
+        hidden_size: int = 128,
+        num_layers: int = 2,
+        output_size: int = 1,
+        dropout: float = 0.2
+    ):
+        super().__init__()
+
+        self.hidden_size = hidden_size
+        self.num_layers = num_layers
+
+        self.lstm = nn.LSTM(
+            input_size=input_size,
+            hidden_size=hidden_size,
+            num_layers=num_layers,
+            batch_first=True,
+            dropout=dropout if num_layers > 1 else 0
+        )
+
+        self.fc = nn.Sequential(
+            nn.Linear(hidden_size, hidden_size // 2),
+            nn.ReLU(),
+            nn.Dropout(dropout),
+            nn.Linear(hidden_size // 2, output_size)
+        )
+
+    def forward(self, x: torch.Tensor, hidden: Tuple = None) -> Tuple[torch.Tensor, Tuple]:
+        # x: (batch, seq_len, input_size)
+        lstm_out, hidden = self.lstm(x, hidden)
+
+        # Use last output for prediction
+        out = self.fc(lstm_out[:, -1, :])
+        return out, hidden
+
+    def predict_sequence(self, x: torch.Tensor, steps: int) -> torch.Tensor:
+        """Autoregressive prediction for multiple steps"""
+        self.eval()
+        predictions = []
+        hidden = None
+
+        with torch.no_grad():
+            # Process input sequence
+            _, hidden = self.lstm(x, hidden)
+
+            # Get last value as starting point
+            current = x[:, -1:, :]
+
+            for _ in range(steps):
+                lstm_out, hidden = self.lstm(current, hidden)
+                pred = self.fc(lstm_out[:, -1, :])
+                predictions.append(pred)
+                current = pred.unsqueeze(1)
+
+        return torch.stack(predictions, dim=1)
+
+def create_sequences(data: torch.Tensor, seq_length: int) -> Tuple[torch.Tensor, torch.Tensor]:
+    """Create sequences for training"""
+    X, y = [], []
+    for i in range(len(data) - seq_length):
+        X.append(data[i:i+seq_length])
+        y.append(data[i+seq_length])
+    return torch.stack(X), torch.stack(y)
*** End Patch

COMMANDS:
- pip install torch numpy
- python -c "from ml.models.lstm_forecast import LSTMForecaster; m = LSTMForecaster(); print(m)"

NOTES:
- Supports multi-step forecasting
- Uses teacher forcing during training
- Autoregressive inference for future steps
- Stacked LSTM with dropout for regularization""",
        "pytorch"
    ))

    return samples


# ============================================================================
# TENSORFLOW/KERAS SAMPLES
# ============================================================================

def generate_tensorflow_samples() -> list:
    samples = []

    # 1. Keras Sequential Model
    samples.append(create_example(
        "Create a TensorFlow Keras model for multi-class text classification",
        """PLAN:
1) Build text preprocessing pipeline
2) Create embedding + LSTM model
3) Add callbacks for training
4) Implement prediction function

FILES:
- ml/models/text_classifier.py
- ml/train_keras.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/ml/models/text_classifier.py
@@ -0,0 +1,75 @@
+import tensorflow as tf
+from tensorflow import keras
+from tensorflow.keras import layers
+from typing import Tuple
+
+class TextClassifier:
+    def __init__(
+        self,
+        vocab_size: int = 10000,
+        max_length: int = 200,
+        embedding_dim: int = 128,
+        num_classes: int = 5
+    ):
+        self.vocab_size = vocab_size
+        self.max_length = max_length
+        self.embedding_dim = embedding_dim
+        self.num_classes = num_classes
+
+        self.vectorizer = layers.TextVectorization(
+            max_tokens=vocab_size,
+            output_mode='int',
+            output_sequence_length=max_length
+        )
+
+        self.model = self._build_model()
+
+    def _build_model(self) -> keras.Model:
+        inputs = keras.Input(shape=(self.max_length,), dtype='int64')
+
+        # Embedding layer
+        x = layers.Embedding(
+            self.vocab_size,
+            self.embedding_dim,
+            mask_zero=True
+        )(inputs)
+
+        # Bidirectional LSTM
+        x = layers.Bidirectional(layers.LSTM(64, return_sequences=True))(x)
+        x = layers.Bidirectional(layers.LSTM(32))(x)
+
+        # Dense layers
+        x = layers.Dense(64, activation='relu')(x)
+        x = layers.Dropout(0.5)(x)
+        outputs = layers.Dense(self.num_classes, activation='softmax')(x)
+
+        model = keras.Model(inputs, outputs)
+        model.compile(
+            optimizer=keras.optimizers.Adam(1e-3),
+            loss='sparse_categorical_crossentropy',
+            metrics=['accuracy']
+        )
+        return model
+
+    def fit_vectorizer(self, texts):
+        self.vectorizer.adapt(texts)
+
+    def train(self, train_texts, train_labels, val_data=None, epochs=10):
+        # Vectorize texts
+        train_x = self.vectorizer(train_texts)
+
+        callbacks = [
+            keras.callbacks.EarlyStopping(patience=3, restore_best_weights=True),
+            keras.callbacks.ReduceLROnPlateau(factor=0.5, patience=2),
+            keras.callbacks.ModelCheckpoint('best_model.h5', save_best_only=True)
+        ]
+
+        return self.model.fit(
+            train_x, train_labels,
+            validation_data=val_data,
+            epochs=epochs,
+            callbacks=callbacks,
+            batch_size=32
+        )
+
+    def predict(self, texts):
+        x = self.vectorizer(texts)
+        return self.model.predict(x)
*** End Patch

COMMANDS:
- pip install tensorflow
- python -c "from ml.models.text_classifier import TextClassifier; clf = TextClassifier(); print('OK')"

NOTES:
- Uses TextVectorization for preprocessing
- Bidirectional LSTM captures context
- EarlyStopping prevents overfitting
- ReduceLROnPlateau for adaptive learning rate""",
        "tensorflow"
    ))

    # 2. Custom Training Loop
    samples.append(create_example(
        "Implement custom training loop in TensorFlow with gradient tape",
        """PLAN:
1) Define model architecture
2) Create custom training step with GradientTape
3) Add metrics tracking
4) Implement validation loop

FILES:
- ml/custom_training.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/ml/custom_training.py
@@ -0,0 +1,80 @@
+import tensorflow as tf
+from tensorflow import keras
+import numpy as np
+
+class CustomTrainer:
+    def __init__(self, model: keras.Model, optimizer: keras.optimizers.Optimizer):
+        self.model = model
+        self.optimizer = optimizer
+        self.loss_fn = keras.losses.SparseCategoricalCrossentropy()
+
+        # Metrics
+        self.train_loss = keras.metrics.Mean(name='train_loss')
+        self.train_acc = keras.metrics.SparseCategoricalAccuracy(name='train_acc')
+        self.val_loss = keras.metrics.Mean(name='val_loss')
+        self.val_acc = keras.metrics.SparseCategoricalAccuracy(name='val_acc')
+
+    @tf.function
+    def train_step(self, x: tf.Tensor, y: tf.Tensor) -> dict:
+        with tf.GradientTape() as tape:
+            predictions = self.model(x, training=True)
+            loss = self.loss_fn(y, predictions)
+
+        gradients = tape.gradient(loss, self.model.trainable_variables)
+
+        # Gradient clipping
+        gradients, _ = tf.clip_by_global_norm(gradients, 1.0)
+
+        self.optimizer.apply_gradients(zip(gradients, self.model.trainable_variables))
+
+        self.train_loss.update_state(loss)
+        self.train_acc.update_state(y, predictions)
+
+        return {'loss': self.train_loss.result(), 'accuracy': self.train_acc.result()}
+
+    @tf.function
+    def val_step(self, x: tf.Tensor, y: tf.Tensor) -> dict:
+        predictions = self.model(x, training=False)
+        loss = self.loss_fn(y, predictions)
+
+        self.val_loss.update_state(loss)
+        self.val_acc.update_state(y, predictions)
+
+        return {'loss': self.val_loss.result(), 'accuracy': self.val_acc.result()}
+
+    def fit(self, train_ds, val_ds, epochs: int):
+        history = {'train_loss': [], 'train_acc': [], 'val_loss': [], 'val_acc': []}
+
+        for epoch in range(epochs):
+            # Reset metrics
+            self.train_loss.reset_states()
+            self.train_acc.reset_states()
+            self.val_loss.reset_states()
+            self.val_acc.reset_states()
+
+            # Training
+            for x_batch, y_batch in train_ds:
+                metrics = self.train_step(x_batch, y_batch)
+
+            # Validation
+            for x_batch, y_batch in val_ds:
+                val_metrics = self.val_step(x_batch, y_batch)
+
+            # Log
+            print(f"Epoch {epoch+1}/{epochs}")
+            print(f"  Train Loss: {metrics['loss']:.4f}, Acc: {metrics['accuracy']:.4f}")
+            print(f"  Val Loss: {val_metrics['loss']:.4f}, Acc: {val_metrics['accuracy']:.4f}")
+
+            # History
+            history['train_loss'].append(float(metrics['loss']))
+            history['train_acc'].append(float(metrics['accuracy']))
+            history['val_loss'].append(float(val_metrics['loss']))
+            history['val_acc'].append(float(val_metrics['accuracy']))
+
+        return history
*** End Patch

COMMANDS:
- pip install tensorflow
- python ml/custom_training.py

NOTES:
- Uses @tf.function for graph optimization
- Gradient clipping prevents exploding gradients
- Custom metrics tracking
- Clean separation of train/val steps""",
        "tensorflow"
    ))

    return samples


# ============================================================================
# SCIKIT-LEARN SAMPLES
# ============================================================================

def generate_sklearn_samples() -> list:
    samples = []

    # 1. ML Pipeline
    samples.append(create_example(
        "Create a scikit-learn pipeline with preprocessing and model selection",
        """PLAN:
1) Create preprocessing pipeline
2) Add feature engineering
3) Implement model selection with cross-validation
4) Add hyperparameter tuning

FILES:
- ml/pipeline.py
- ml/feature_engineering.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/ml/pipeline.py
@@ -0,0 +1,85 @@
+import numpy as np
+import pandas as pd
+from sklearn.pipeline import Pipeline
+from sklearn.compose import ColumnTransformer
+from sklearn.preprocessing import StandardScaler, OneHotEncoder, LabelEncoder
+from sklearn.impute import SimpleImputer
+from sklearn.feature_selection import SelectKBest, f_classif
+from sklearn.model_selection import cross_val_score, GridSearchCV
+from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
+from sklearn.linear_model import LogisticRegression
+from sklearn.svm import SVC
+from typing import List, Tuple
+
+class MLPipeline:
+    def __init__(self, numeric_features: List[str], categorical_features: List[str]):
+        self.numeric_features = numeric_features
+        self.categorical_features = categorical_features
+        self.pipeline = None
+        self.best_model = None
+
+    def _create_preprocessor(self) -> ColumnTransformer:
+        numeric_transformer = Pipeline([
+            ('imputer', SimpleImputer(strategy='median')),
+            ('scaler', StandardScaler())
+        ])
+
+        categorical_transformer = Pipeline([
+            ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
+            ('encoder', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
+        ])
+
+        return ColumnTransformer([
+            ('num', numeric_transformer, self.numeric_features),
+            ('cat', categorical_transformer, self.categorical_features)
+        ])
+
+    def create_pipeline(self, model) -> Pipeline:
+        return Pipeline([
+            ('preprocessor', self._create_preprocessor()),
+            ('feature_selection', SelectKBest(f_classif, k='all')),
+            ('classifier', model)
+        ])
+
+    def select_best_model(self, X: pd.DataFrame, y: np.ndarray) -> dict:
+        models = {
+            'random_forest': RandomForestClassifier(n_estimators=100, random_state=42),
+            'gradient_boosting': GradientBoostingClassifier(random_state=42),
+            'logistic_regression': LogisticRegression(max_iter=1000, random_state=42),
+            'svm': SVC(kernel='rbf', random_state=42)
+        }
+
+        results = {}
+        for name, model in models.items():
+            pipeline = self.create_pipeline(model)
+            scores = cross_val_score(pipeline, X, y, cv=5, scoring='accuracy')
+            results[name] = {
+                'mean_accuracy': scores.mean(),
+                'std_accuracy': scores.std()
+            }
+            print(f"{name}: {scores.mean():.4f} (+/- {scores.std():.4f})")
+
+        # Select best
+        best_name = max(results, key=lambda k: results[k]['mean_accuracy'])
+        self.best_model = models[best_name]
+        self.pipeline = self.create_pipeline(self.best_model)
+
+        return results
+
+    def tune_hyperparameters(self, X: pd.DataFrame, y: np.ndarray, param_grid: dict):
+        grid_search = GridSearchCV(
+            self.pipeline,
+            param_grid,
+            cv=5,
+            scoring='accuracy',
+            n_jobs=-1,
+            verbose=1
+        )
+        grid_search.fit(X, y)
+
+        self.pipeline = grid_search.best_estimator_
+        return grid_search.best_params_, grid_search.best_score_
+
+    def fit(self, X: pd.DataFrame, y: np.ndarray):
+        return self.pipeline.fit(X, y)
+
+    def predict(self, X: pd.DataFrame) -> np.ndarray:
+        return self.pipeline.predict(X)
*** End Patch

COMMANDS:
- pip install scikit-learn pandas numpy
- python -c "from ml.pipeline import MLPipeline; print('OK')"

NOTES:
- Handles numeric and categorical features separately
- Imputation for missing values
- Model selection with cross-validation
- GridSearchCV for hyperparameter tuning""",
        "sklearn"
    ))

    return samples


# ============================================================================
# HUGGING FACE SAMPLES
# ============================================================================

def generate_huggingface_samples() -> list:
    samples = []

    # 1. Fine-tune Transformer
    samples.append(create_example(
        "Fine-tune a Hugging Face transformer model for text classification",
        """PLAN:
1) Load pretrained model and tokenizer
2) Prepare dataset with tokenization
3) Set up Trainer with training arguments
4) Train and evaluate

FILES:
- ml/hf_classifier.py
- ml/train_hf.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/ml/hf_classifier.py
@@ -0,0 +1,90 @@
+import torch
+from transformers import (
+    AutoTokenizer,
+    AutoModelForSequenceClassification,
+    TrainingArguments,
+    Trainer,
+    DataCollatorWithPadding
+)
+from datasets import Dataset, load_metric
+import numpy as np
+from typing import Dict, List
+
+class HFTextClassifier:
+    def __init__(
+        self,
+        model_name: str = "distilbert-base-uncased",
+        num_labels: int = 2,
+        max_length: int = 512
+    ):
+        self.model_name = model_name
+        self.max_length = max_length
+
+        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
+        self.model = AutoModelForSequenceClassification.from_pretrained(
+            model_name,
+            num_labels=num_labels
+        )
+
+        self.data_collator = DataCollatorWithPadding(tokenizer=self.tokenizer)
+
+    def tokenize_function(self, examples: Dict) -> Dict:
+        return self.tokenizer(
+            examples["text"],
+            truncation=True,
+            max_length=self.max_length,
+            padding=False
+        )
+
+    def prepare_dataset(self, texts: List[str], labels: List[int]) -> Dataset:
+        dataset = Dataset.from_dict({"text": texts, "label": labels})
+        tokenized = dataset.map(self.tokenize_function, batched=True)
+        return tokenized
+
+    def compute_metrics(self, eval_pred):
+        predictions, labels = eval_pred
+        predictions = np.argmax(predictions, axis=1)
+
+        accuracy = (predictions == labels).mean()
+        return {"accuracy": accuracy}
+
+    def train(
+        self,
+        train_texts: List[str],
+        train_labels: List[int],
+        val_texts: List[str] = None,
+        val_labels: List[int] = None,
+        output_dir: str = "./hf_model",
+        epochs: int = 3
+    ):
+        train_dataset = self.prepare_dataset(train_texts, train_labels)
+        val_dataset = self.prepare_dataset(val_texts, val_labels) if val_texts else None
+
+        training_args = TrainingArguments(
+            output_dir=output_dir,
+            num_train_epochs=epochs,
+            per_device_train_batch_size=16,
+            per_device_eval_batch_size=32,
+            warmup_steps=500,
+            weight_decay=0.01,
+            logging_dir=f"{output_dir}/logs",
+            logging_steps=100,
+            evaluation_strategy="epoch" if val_dataset else "no",
+            save_strategy="epoch",
+            load_best_model_at_end=True if val_dataset else False,
+            fp16=torch.cuda.is_available(),
+        )
+
+        trainer = Trainer(
+            model=self.model,
+            args=training_args,
+            train_dataset=train_dataset,
+            eval_dataset=val_dataset,
+            tokenizer=self.tokenizer,
+            data_collator=self.data_collator,
+            compute_metrics=self.compute_metrics
+        )
+
+        trainer.train()
+        return trainer
+
+    def predict(self, texts: List[str]) -> np.ndarray:
+        inputs = self.tokenizer(texts, truncation=True, padding=True, return_tensors="pt")
+        outputs = self.model(**inputs)
+        return torch.softmax(outputs.logits, dim=1).detach().numpy()
*** End Patch

COMMANDS:
- pip install transformers datasets torch
- python -c "from ml.hf_classifier import HFTextClassifier; clf = HFTextClassifier(); print('OK')"

NOTES:
- Uses DistilBERT for efficiency
- Dynamic padding with DataCollator
- Mixed precision training with fp16
- Saves best model based on validation""",
        "huggingface"
    ))

    # 2. Text Generation
    samples.append(create_example(
        "Create a text generation pipeline with Hugging Face GPT-2",
        """PLAN:
1) Load GPT-2 model and tokenizer
2) Implement generation with sampling
3) Add beam search and top-k/top-p sampling
4) Create API endpoint

FILES:
- ml/text_generator.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/ml/text_generator.py
@@ -0,0 +1,65 @@
+import torch
+from transformers import GPT2LMHeadModel, GPT2Tokenizer
+from typing import List, Optional
+
+class TextGenerator:
+    def __init__(self, model_name: str = "gpt2"):
+        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
+        self.tokenizer = GPT2Tokenizer.from_pretrained(model_name)
+        self.model = GPT2LMHeadModel.from_pretrained(model_name).to(self.device)
+        self.model.eval()
+
+        # Set pad token
+        self.tokenizer.pad_token = self.tokenizer.eos_token
+
+    def generate(
+        self,
+        prompt: str,
+        max_length: int = 100,
+        num_return_sequences: int = 1,
+        temperature: float = 0.7,
+        top_k: int = 50,
+        top_p: float = 0.95,
+        do_sample: bool = True,
+        num_beams: Optional[int] = None
+    ) -> List[str]:
+        inputs = self.tokenizer(
+            prompt,
+            return_tensors="pt",
+            padding=True
+        ).to(self.device)
+
+        with torch.no_grad():
+            outputs = self.model.generate(
+                **inputs,
+                max_length=max_length,
+                num_return_sequences=num_return_sequences,
+                temperature=temperature,
+                top_k=top_k,
+                top_p=top_p,
+                do_sample=do_sample,
+                num_beams=num_beams if num_beams else 1,
+                pad_token_id=self.tokenizer.eos_token_id,
+                no_repeat_ngram_size=2,
+                early_stopping=True if num_beams else False
+            )
+
+        generated_texts = [
+            self.tokenizer.decode(output, skip_special_tokens=True)
+            for output in outputs
+        ]
+
+        return generated_texts
+
+    def generate_with_context(self, context: str, prompt: str, **kwargs) -> List[str]:
+        full_prompt = f"{context}\\n\\n{prompt}"
+        return self.generate(full_prompt, **kwargs)
+
+# Usage
+if __name__ == "__main__":
+    generator = TextGenerator()
+
+    results = generator.generate(
+        prompt="The future of AI is",
+        max_length=50,
+        num_return_sequences=3,
+        temperature=0.8
+    )
+
+    for i, text in enumerate(results):
+        print(f"Generation {i+1}: {text}")
*** End Patch

COMMANDS:
- pip install transformers torch
- python ml/text_generator.py

NOTES:
- Supports multiple sampling strategies
- top_k and top_p for diverse generation
- no_repeat_ngram prevents repetition
- Beam search for higher quality""",
        "huggingface"
    ))

    return samples


# ============================================================================
# DATA SCIENCE / PANDAS SAMPLES
# ============================================================================

def generate_pandas_samples() -> list:
    samples = []

    # 1. Data Preprocessing
    samples.append(create_example(
        "Create a comprehensive data preprocessing pipeline with Pandas",
        """PLAN:
1) Handle missing values
2) Detect and handle outliers
3) Feature encoding
4) Feature scaling
5) Create preprocessing report

FILES:
- ml/data/preprocessor.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/ml/data/preprocessor.py
@@ -0,0 +1,120 @@
+import pandas as pd
+import numpy as np
+from typing import List, Dict, Optional, Tuple
+from sklearn.preprocessing import StandardScaler, LabelEncoder
+from scipy import stats
+
+class DataPreprocessor:
+    def __init__(self):
+        self.scalers = {}
+        self.encoders = {}
+        self.feature_stats = {}
+
+    def analyze_missing(self, df: pd.DataFrame) -> pd.DataFrame:
+        missing = pd.DataFrame({
+            'column': df.columns,
+            'missing_count': df.isnull().sum().values,
+            'missing_pct': (df.isnull().sum() / len(df) * 100).values,
+            'dtype': df.dtypes.values
+        })
+        return missing[missing['missing_count'] > 0].sort_values('missing_pct', ascending=False)
+
+    def handle_missing(
+        self,
+        df: pd.DataFrame,
+        numeric_strategy: str = 'median',
+        categorical_strategy: str = 'mode',
+        drop_threshold: float = 0.5
+    ) -> pd.DataFrame:
+        df = df.copy()
+
+        # Drop columns with too many missing values
+        missing_pct = df.isnull().sum() / len(df)
+        cols_to_drop = missing_pct[missing_pct > drop_threshold].index
+        df = df.drop(columns=cols_to_drop)
+
+        # Fill numeric columns
+        numeric_cols = df.select_dtypes(include=[np.number]).columns
+        for col in numeric_cols:
+            if df[col].isnull().any():
+                if numeric_strategy == 'median':
+                    df[col] = df[col].fillna(df[col].median())
+                elif numeric_strategy == 'mean':
+                    df[col] = df[col].fillna(df[col].mean())
+
+        # Fill categorical columns
+        cat_cols = df.select_dtypes(include=['object', 'category']).columns
+        for col in cat_cols:
+            if df[col].isnull().any():
+                if categorical_strategy == 'mode':
+                    df[col] = df[col].fillna(df[col].mode()[0])
+                else:
+                    df[col] = df[col].fillna('MISSING')
+
+        return df
+
+    def detect_outliers(
+        self,
+        df: pd.DataFrame,
+        method: str = 'iqr',
+        threshold: float = 1.5
+    ) -> Dict[str, np.ndarray]:
+        outliers = {}
+        numeric_cols = df.select_dtypes(include=[np.number]).columns
+
+        for col in numeric_cols:
+            if method == 'iqr':
+                Q1 = df[col].quantile(0.25)
+                Q3 = df[col].quantile(0.75)
+                IQR = Q3 - Q1
+                lower = Q1 - threshold * IQR
+                upper = Q3 + threshold * IQR
+                mask = (df[col] < lower) | (df[col] > upper)
+            elif method == 'zscore':
+                z_scores = np.abs(stats.zscore(df[col].dropna()))
+                mask = z_scores > threshold
+
+            if mask.any():
+                outliers[col] = df.index[mask].values
+
+        return outliers
+
+    def handle_outliers(
+        self,
+        df: pd.DataFrame,
+        method: str = 'clip',
+        threshold: float = 1.5
+    ) -> pd.DataFrame:
+        df = df.copy()
+        numeric_cols = df.select_dtypes(include=[np.number]).columns
+
+        for col in numeric_cols:
+            Q1 = df[col].quantile(0.25)
+            Q3 = df[col].quantile(0.75)
+            IQR = Q3 - Q1
+            lower = Q1 - threshold * IQR
+            upper = Q3 + threshold * IQR
+
+            if method == 'clip':
+                df[col] = df[col].clip(lower=lower, upper=upper)
+            elif method == 'remove':
+                df = df[(df[col] >= lower) & (df[col] <= upper)]
+
+        return df
+
+    def encode_categorical(self, df: pd.DataFrame, columns: List[str] = None) -> pd.DataFrame:
+        df = df.copy()
+        if columns is None:
+            columns = df.select_dtypes(include=['object', 'category']).columns
+
+        for col in columns:
+            if df[col].nunique() <= 10:
+                # One-hot encoding for low cardinality
+                dummies = pd.get_dummies(df[col], prefix=col, drop_first=True)
+                df = pd.concat([df.drop(col, axis=1), dummies], axis=1)
+            else:
+                # Label encoding for high cardinality
+                le = LabelEncoder()
+                df[col] = le.fit_transform(df[col].astype(str))
+                self.encoders[col] = le
+
+        return df
+
+    def scale_features(self, df: pd.DataFrame, columns: List[str] = None) -> pd.DataFrame:
+        df = df.copy()
+        if columns is None:
+            columns = df.select_dtypes(include=[np.number]).columns.tolist()
+
+        scaler = StandardScaler()
+        df[columns] = scaler.fit_transform(df[columns])
+        self.scalers['standard'] = scaler
+
+        return df
*** End Patch

COMMANDS:
- pip install pandas numpy scikit-learn scipy
- python -c "from ml.data.preprocessor import DataPreprocessor; print('OK')"

NOTES:
- Handles missing values with multiple strategies
- IQR and Z-score outlier detection
- Automatic encoding based on cardinality
- Stores scalers/encoders for inference""",
        "pandas"
    ))

    return samples


# ============================================================================
# COMPUTER VISION SAMPLES
# ============================================================================

def generate_cv_samples() -> list:
    samples = []

    # 1. Object Detection
    samples.append(create_example(
        "Create object detection inference pipeline with YOLO",
        """PLAN:
1) Load YOLO model
2) Preprocess images
3) Run inference with NMS
4) Draw bounding boxes
5) Create detection API

FILES:
- ml/detection/yolo_detector.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/ml/detection/yolo_detector.py
@@ -0,0 +1,75 @@
+import torch
+import cv2
+import numpy as np
+from typing import List, Tuple, Dict
+from PIL import Image
+
+class YOLODetector:
+    def __init__(self, model_name: str = "yolov5s", confidence: float = 0.5):
+        self.model = torch.hub.load('ultralytics/yolov5', model_name, pretrained=True)
+        self.model.conf = confidence
+        self.model.eval()
+
+        if torch.cuda.is_available():
+            self.model = self.model.cuda()
+
+    def detect(self, image: np.ndarray) -> List[Dict]:
+        results = self.model(image)
+
+        detections = []
+        for *box, conf, cls in results.xyxy[0].cpu().numpy():
+            detections.append({
+                'bbox': [int(x) for x in box],
+                'confidence': float(conf),
+                'class_id': int(cls),
+                'class_name': self.model.names[int(cls)]
+            })
+
+        return detections
+
+    def detect_batch(self, images: List[np.ndarray]) -> List[List[Dict]]:
+        results = self.model(images)
+
+        all_detections = []
+        for i, result in enumerate(results.xyxy):
+            detections = []
+            for *box, conf, cls in result.cpu().numpy():
+                detections.append({
+                    'bbox': [int(x) for x in box],
+                    'confidence': float(conf),
+                    'class_id': int(cls),
+                    'class_name': self.model.names[int(cls)]
+                })
+            all_detections.append(detections)
+
+        return all_detections
+
+    def draw_detections(self, image: np.ndarray, detections: List[Dict]) -> np.ndarray:
+        image = image.copy()
+
+        for det in detections:
+            x1, y1, x2, y2 = det['bbox']
+            label = f"{det['class_name']} {det['confidence']:.2f}"
+
+            # Draw box
+            cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
+
+            # Draw label
+            (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
+            cv2.rectangle(image, (x1, y1 - 20), (x1 + w, y1), (0, 255, 0), -1)
+            cv2.putText(image, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
+
+        return image
+
+# Usage
+if __name__ == "__main__":
+    detector = YOLODetector(confidence=0.5)
+
+    # Load image
+    image = cv2.imread("test.jpg")
+    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
+
+    # Detect
+    detections = detector.detect(image_rgb)
+    print(f"Found {len(detections)} objects")
+
+    # Draw and save
+    result = detector.draw_detections(image, detections)
+    cv2.imwrite("result.jpg", result)
*** End Patch

COMMANDS:
- pip install torch torchvision opencv-python
- pip install yolov5
- python ml/detection/yolo_detector.py

NOTES:
- Uses YOLOv5 from Ultralytics
- Supports batch inference
- Draws bounding boxes with labels
- GPU acceleration when available""",
        "computer_vision"
    ))

    return samples


# ============================================================================
# NLP SAMPLES
# ============================================================================

def generate_nlp_samples() -> list:
    samples = []

    # 1. Named Entity Recognition
    samples.append(create_example(
        "Implement Named Entity Recognition with spaCy and custom training",
        """PLAN:
1) Load spaCy model
2) Create custom NER pipeline
3) Train on custom entities
4) Export trained model

FILES:
- ml/nlp/ner_model.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/ml/nlp/ner_model.py
@@ -0,0 +1,85 @@
+import spacy
+from spacy.training import Example
+from spacy.util import minibatch, compounding
+from typing import List, Tuple, Dict
+import random
+
+class CustomNER:
+    def __init__(self, base_model: str = "en_core_web_sm"):
+        try:
+            self.nlp = spacy.load(base_model)
+        except OSError:
+            spacy.cli.download(base_model)
+            self.nlp = spacy.load(base_model)
+
+        # Add NER if not present
+        if "ner" not in self.nlp.pipe_names:
+            self.ner = self.nlp.add_pipe("ner", last=True)
+        else:
+            self.ner = self.nlp.get_pipe("ner")
+
+    def add_labels(self, labels: List[str]):
+        for label in labels:
+            self.ner.add_label(label)
+
+    def train(
+        self,
+        train_data: List[Tuple[str, Dict]],
+        n_iter: int = 30,
+        drop: float = 0.35
+    ) -> List[float]:
+        # Format: [("text", {"entities": [(start, end, label), ...]}), ...]
+
+        # Get labels from training data
+        for _, annotations in train_data:
+            for ent in annotations.get("entities", []):
+                self.ner.add_label(ent[2])
+
+        # Disable other pipes during training
+        other_pipes = [pipe for pipe in self.nlp.pipe_names if pipe != "ner"]
+
+        losses_history = []
+
+        with self.nlp.disable_pipes(*other_pipes):
+            optimizer = self.nlp.begin_training()
+
+            for iteration in range(n_iter):
+                random.shuffle(train_data)
+                losses = {}
+
+                batches = minibatch(train_data, size=compounding(4.0, 32.0, 1.001))
+
+                for batch in batches:
+                    examples = []
+                    for text, annotations in batch:
+                        doc = self.nlp.make_doc(text)
+                        example = Example.from_dict(doc, annotations)
+                        examples.append(example)
+
+                    self.nlp.update(examples, drop=drop, losses=losses)
+
+                losses_history.append(losses.get("ner", 0))
+                print(f"Iteration {iteration + 1}, Loss: {losses.get('ner', 0):.4f}")
+
+        return losses_history
+
+    def predict(self, text: str) -> List[Dict]:
+        doc = self.nlp(text)
+        entities = []
+
+        for ent in doc.ents:
+            entities.append({
+                "text": ent.text,
+                "label": ent.label_,
+                "start": ent.start_char,
+                "end": ent.end_char
+            })
+
+        return entities
+
+    def save(self, path: str):
+        self.nlp.to_disk(path)
+
+    @classmethod
+    def load(cls, path: str) -> "CustomNER":
+        instance = cls.__new__(cls)
+        instance.nlp = spacy.load(path)
+        instance.ner = instance.nlp.get_pipe("ner")
+        return instance
*** End Patch

COMMANDS:
- pip install spacy
- python -m spacy download en_core_web_sm
- python -c "from ml.nlp.ner_model import CustomNER; print('OK')"

NOTES:
- Supports custom entity labels
- Uses minibatch training
- Saves/loads trained model
- Compatible with base spaCy models""",
        "nlp"
    ))

    return samples


# ============================================================================
# MLOPS SAMPLES
# ============================================================================

def generate_mlops_samples() -> list:
    samples = []

    # 1. MLflow Tracking
    samples.append(create_example(
        "Implement MLflow experiment tracking and model registry",
        """PLAN:
1) Set up MLflow tracking
2) Log parameters, metrics, artifacts
3) Register model versions
4) Create model serving endpoint

FILES:
- ml/mlops/experiment_tracker.py
- ml/mlops/model_registry.py

PATCH:
*** Begin Patch
--- /dev/null
+++ b/ml/mlops/experiment_tracker.py
@@ -0,0 +1,95 @@
+import mlflow
+import mlflow.sklearn
+import mlflow.pytorch
+from mlflow.tracking import MlflowClient
+from typing import Dict, Any, Optional
+import os
+
+class ExperimentTracker:
+    def __init__(
+        self,
+        experiment_name: str,
+        tracking_uri: str = "sqlite:///mlflow.db"
+    ):
+        mlflow.set_tracking_uri(tracking_uri)
+        mlflow.set_experiment(experiment_name)
+
+        self.client = MlflowClient()
+        self.experiment_name = experiment_name
+        self.run = None
+
+    def start_run(self, run_name: Optional[str] = None) -> str:
+        self.run = mlflow.start_run(run_name=run_name)
+        return self.run.info.run_id
+
+    def end_run(self):
+        mlflow.end_run()
+        self.run = None
+
+    def log_params(self, params: Dict[str, Any]):
+        mlflow.log_params(params)
+
+    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None):
+        mlflow.log_metrics(metrics, step=step)
+
+    def log_artifact(self, local_path: str, artifact_path: Optional[str] = None):
+        mlflow.log_artifact(local_path, artifact_path)
+
+    def log_model(self, model, artifact_path: str, framework: str = "sklearn"):
+        if framework == "sklearn":
+            mlflow.sklearn.log_model(model, artifact_path)
+        elif framework == "pytorch":
+            mlflow.pytorch.log_model(model, artifact_path)
+        elif framework == "tensorflow":
+            mlflow.tensorflow.log_model(model, artifact_path)
+
+    def register_model(self, model_uri: str, name: str) -> str:
+        result = mlflow.register_model(model_uri, name)
+        return result.version
+
+    def transition_model_stage(self, name: str, version: str, stage: str):
+        self.client.transition_model_version_stage(
+            name=name,
+            version=version,
+            stage=stage  # "Staging", "Production", "Archived"
+        )
+
+    def get_best_run(self, metric: str, mode: str = "min") -> Dict:
+        experiment = mlflow.get_experiment_by_name(self.experiment_name)
+
+        order = "ASC" if mode == "min" else "DESC"
+        runs = mlflow.search_runs(
+            experiment_ids=[experiment.experiment_id],
+            order_by=[f"metrics.{metric} {order}"],
+            max_results=1
+        )
+
+        if len(runs) > 0:
+            return runs.iloc[0].to_dict()
+        return None
+
+    def load_model(self, model_uri: str, framework: str = "sklearn"):
+        if framework == "sklearn":
+            return mlflow.sklearn.load_model(model_uri)
+        elif framework == "pytorch":
+            return mlflow.pytorch.load_model(model_uri)
+
+# Usage
+def train_with_tracking():
+    tracker = ExperimentTracker("my_experiment")
+
+    tracker.start_run(run_name="training_v1")
+
+    # Log parameters
+    tracker.log_params({
+        "learning_rate": 0.001,
+        "batch_size": 32,
+        "epochs": 100
+    })
+
+    # Training loop
+    for epoch in range(100):
+        train_loss = 0.5 - epoch * 0.004
+        tracker.log_metrics({"train_loss": train_loss}, step=epoch)
+
+    # Log model
+    tracker.log_model(model, "model", framework="sklearn")
+
+    tracker.end_run()
*** End Patch

COMMANDS:
- pip install mlflow scikit-learn
- mlflow ui --port 5000
- python ml/mlops/experiment_tracker.py

NOTES:
- SQLite backend for local tracking
- Supports sklearn, pytorch, tensorflow
- Model versioning and staging
- Query best runs by metric""",
        "mlops"
    ))

    return samples


# ============================================================================
# MAIN GENERATOR
# ============================================================================

def generate_all_aiml_samples() -> List[dict]:
    """Generate all AI/ML samples."""
    samples = []

    print("Generating PyTorch samples...")
    samples.extend(generate_pytorch_samples())

    print("Generating TensorFlow samples...")
    samples.extend(generate_tensorflow_samples())

    print("Generating Scikit-learn samples...")
    samples.extend(generate_sklearn_samples())

    print("Generating Hugging Face samples...")
    samples.extend(generate_huggingface_samples())

    print("Generating Pandas/Data Science samples...")
    samples.extend(generate_pandas_samples())

    print("Generating Computer Vision samples...")
    samples.extend(generate_cv_samples())

    print("Generating NLP samples...")
    samples.extend(generate_nlp_samples())

    print("Generating MLOps samples...")
    samples.extend(generate_mlops_samples())

    return samples


def main():
    print("=" * 60)
    print("GENERATING AI/ML GOLD SAMPLES")
    print("=" * 60)

    samples = generate_all_aiml_samples()

    # Count by category
    categories = {}
    for sample in samples:
        cat = sample.get("category", "other")
        categories[cat] = categories.get(cat, 0) + 1

    print(f"\nTotal AI/ML Samples: {len(samples)}")
    print("\nBy Category:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    # Load existing gold samples
    existing_file = OUTPUT_DIR / "gold_samples.jsonl"
    existing_samples = []
    if existing_file.exists():
        with open(existing_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    existing_samples.append(json.loads(line))

    print(f"\nExisting samples: {len(existing_samples)}")

    # Merge
    all_samples = existing_samples + samples
    print(f"Total samples: {len(all_samples)}")

    # Save
    OUTPUT_DIR.mkdir(exist_ok=True)
    with open(existing_file, 'w', encoding='utf-8') as f:
        for sample in all_samples:
            f.write(json.dumps(sample, ensure_ascii=False) + '\n')

    # Update summary
    all_categories = {}
    for sample in all_samples:
        cat = sample.get("category", "other")
        all_categories[cat] = all_categories.get(cat, 0) + 1

    summary = {
        "total_samples": len(all_samples),
        "categories": all_categories,
        "output_format": ["PLAN", "FILES", "PATCH", "COMMANDS", "NOTES"]
    }

    with open(OUTPUT_DIR / "summary.json", 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\nSaved to: {existing_file}")

    print("\n" + "=" * 60)
    print("AI/ML SAMPLES ADDED")
    print("=" * 60)


if __name__ == "__main__":
    main()
