"""
ML Templates Service - Pre-built machine learning model templates with AI customization

Supports:
- Classical ML (Scikit-learn)
- Deep Learning (PyTorch, TensorFlow)
- NLP (Transformers, BERT, LSTM)
- Computer Vision (CNN, ResNet, YOLO)
- Time Series (LSTM, Prophet)
"""

from typing import Dict, List, Any, Optional
from enum import Enum
import json
from dataclasses import dataclass


class MLFramework(str, Enum):
    PYTORCH = "pytorch"
    TENSORFLOW = "tensorflow"
    SKLEARN = "sklearn"
    HUGGINGFACE = "huggingface"


class MLCategory(str, Enum):
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    CLUSTERING = "clustering"
    NLP = "nlp"
    COMPUTER_VISION = "computer_vision"
    TIME_SERIES = "time_series"
    RECOMMENDATION = "recommendation"
    GENERATIVE = "generative"


class MLModel(str, Enum):
    # Classical ML
    LOGISTIC_REGRESSION = "logistic_regression"
    RANDOM_FOREST = "random_forest"
    XGBOOST = "xgboost"
    SVM = "svm"
    KMEANS = "kmeans"

    # Deep Learning - Vision
    CNN = "cnn"
    RESNET = "resnet"
    VGG = "vgg"
    EFFICIENTNET = "efficientnet"
    YOLO = "yolo"
    UNET = "unet"

    # Deep Learning - NLP
    LSTM = "lstm"
    GRU = "gru"
    TRANSFORMER = "transformer"
    BERT = "bert"
    GPT = "gpt"

    # Time Series
    ARIMA = "arima"
    PROPHET = "prophet"
    LSTM_TIMESERIES = "lstm_timeseries"

    # Generative
    GAN = "gan"
    VAE = "vae"

    # Recommendation
    COLLABORATIVE_FILTERING = "collaborative_filtering"
    NEURAL_CF = "neural_cf"


@dataclass
class MLTemplate:
    """ML Template metadata"""
    name: str
    model: MLModel
    category: MLCategory
    framework: MLFramework
    description: str
    files: Dict[str, str]  # filename -> content
    requirements: List[str]
    config: Dict[str, Any]


class MLTemplatesService:
    """Service for generating ML project templates"""

    def __init__(self):
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[MLModel, MLTemplate]:
        """Load all ML templates"""
        return {
            MLModel.CNN: self._create_cnn_template(),
            MLModel.RESNET: self._create_resnet_template(),
            MLModel.LSTM: self._create_lstm_template(),
            MLModel.BERT: self._create_bert_template(),
            MLModel.RANDOM_FOREST: self._create_random_forest_template(),
            MLModel.XGBOOST: self._create_xgboost_template(),
            MLModel.YOLO: self._create_yolo_template(),
            MLModel.GAN: self._create_gan_template(),
            MLModel.LSTM_TIMESERIES: self._create_timeseries_template(),
            MLModel.TRANSFORMER: self._create_transformer_template(),
        }

    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available ML models"""
        return [
            {
                "id": MLModel.CNN.value,
                "name": "CNN (Convolutional Neural Network)",
                "category": MLCategory.COMPUTER_VISION.value,
                "framework": MLFramework.PYTORCH.value,
                "description": "Image classification using convolutional layers",
                "use_cases": ["Image Classification", "Object Detection", "Feature Extraction"]
            },
            {
                "id": MLModel.RESNET.value,
                "name": "ResNet (Transfer Learning)",
                "category": MLCategory.COMPUTER_VISION.value,
                "framework": MLFramework.PYTORCH.value,
                "description": "Pre-trained ResNet for transfer learning",
                "use_cases": ["Image Classification", "Fine-tuning", "Feature Extraction"]
            },
            {
                "id": MLModel.YOLO.value,
                "name": "YOLO (Object Detection)",
                "category": MLCategory.COMPUTER_VISION.value,
                "framework": MLFramework.PYTORCH.value,
                "description": "Real-time object detection",
                "use_cases": ["Object Detection", "Real-time Detection", "Video Analysis"]
            },
            {
                "id": MLModel.LSTM.value,
                "name": "LSTM (Text Classification)",
                "category": MLCategory.NLP.value,
                "framework": MLFramework.PYTORCH.value,
                "description": "Long Short-Term Memory for text sequences",
                "use_cases": ["Sentiment Analysis", "Text Classification", "Sequence Labeling"]
            },
            {
                "id": MLModel.BERT.value,
                "name": "BERT (NLP Transformer)",
                "category": MLCategory.NLP.value,
                "framework": MLFramework.HUGGINGFACE.value,
                "description": "Pre-trained BERT for NLP tasks",
                "use_cases": ["Text Classification", "Question Answering", "Named Entity Recognition"]
            },
            {
                "id": MLModel.TRANSFORMER.value,
                "name": "Transformer (Custom)",
                "category": MLCategory.NLP.value,
                "framework": MLFramework.PYTORCH.value,
                "description": "Custom transformer architecture",
                "use_cases": ["Sequence-to-Sequence", "Translation", "Text Generation"]
            },
            {
                "id": MLModel.RANDOM_FOREST.value,
                "name": "Random Forest",
                "category": MLCategory.CLASSIFICATION.value,
                "framework": MLFramework.SKLEARN.value,
                "description": "Ensemble learning with decision trees",
                "use_cases": ["Classification", "Regression", "Feature Importance"]
            },
            {
                "id": MLModel.XGBOOST.value,
                "name": "XGBoost",
                "category": MLCategory.CLASSIFICATION.value,
                "framework": MLFramework.SKLEARN.value,
                "description": "Gradient boosting for tabular data",
                "use_cases": ["Classification", "Regression", "Ranking"]
            },
            {
                "id": MLModel.LSTM_TIMESERIES.value,
                "name": "LSTM (Time Series)",
                "category": MLCategory.TIME_SERIES.value,
                "framework": MLFramework.PYTORCH.value,
                "description": "LSTM for time series forecasting",
                "use_cases": ["Stock Prediction", "Weather Forecasting", "Demand Forecasting"]
            },
            {
                "id": MLModel.GAN.value,
                "name": "GAN (Generative)",
                "category": MLCategory.GENERATIVE.value,
                "framework": MLFramework.PYTORCH.value,
                "description": "Generative Adversarial Network",
                "use_cases": ["Image Generation", "Data Augmentation", "Style Transfer"]
            },
        ]

    def get_template(self, model: MLModel) -> Optional[MLTemplate]:
        """Get template for a specific model"""
        return self.templates.get(model)

    def generate_project(
        self,
        model: MLModel,
        project_name: str,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """Generate complete ML project from template"""
        template = self.templates.get(model)
        if not template:
            raise ValueError(f"Template not found for model: {model}")

        # Apply custom config
        files = {}
        for filename, content in template.files.items():
            # Replace placeholders
            content = content.replace("{{PROJECT_NAME}}", project_name)
            content = content.replace("{{MODEL_NAME}}", model.value)

            if config:
                for key, value in config.items():
                    content = content.replace(f"{{{{{key}}}}}", str(value))

            files[filename] = content

        return files

    def get_requirements(self, model: MLModel) -> List[str]:
        """Get requirements for a model"""
        template = self.templates.get(model)
        return template.requirements if template else []

    # ==================== Template Definitions ====================

    def _create_cnn_template(self) -> MLTemplate:
        """CNN Image Classification Template"""
        return MLTemplate(
            name="CNN Image Classifier",
            model=MLModel.CNN,
            category=MLCategory.COMPUTER_VISION,
            framework=MLFramework.PYTORCH,
            description="Convolutional Neural Network for image classification",
            requirements=[
                "torch>=2.0.0",
                "torchvision>=0.15.0",
                "numpy>=1.24.0",
                "pillow>=9.5.0",
                "matplotlib>=3.7.0",
                "tqdm>=4.65.0",
                "fastapi>=0.100.0",
                "uvicorn>=0.22.0",
                "python-multipart>=0.0.6"
            ],
            config={
                "num_classes": 10,
                "input_size": 224,
                "batch_size": 32,
                "epochs": 50,
                "learning_rate": 0.001
            },
            files={
                "models/cnn_model.py": '''"""
CNN Model Architecture
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


class CNNClassifier(nn.Module):
    """Convolutional Neural Network for Image Classification"""

    def __init__(self, num_classes: int = {{num_classes}}, input_channels: int = 3):
        super(CNNClassifier, self).__init__()

        # Convolutional layers
        self.conv1 = nn.Conv2d(input_channels, 32, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(32)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm2d(64)
        self.conv3 = nn.Conv2d(64, 128, kernel_size=3, padding=1)
        self.bn3 = nn.BatchNorm2d(128)
        self.conv4 = nn.Conv2d(128, 256, kernel_size=3, padding=1)
        self.bn4 = nn.BatchNorm2d(256)

        self.pool = nn.MaxPool2d(2, 2)
        self.dropout = nn.Dropout(0.5)

        # Fully connected layers
        self.fc1 = nn.Linear(256 * 14 * 14, 512)
        self.fc2 = nn.Linear(512, 256)
        self.fc3 = nn.Linear(256, num_classes)

    def forward(self, x):
        # Conv block 1
        x = self.pool(F.relu(self.bn1(self.conv1(x))))
        # Conv block 2
        x = self.pool(F.relu(self.bn2(self.conv2(x))))
        # Conv block 3
        x = self.pool(F.relu(self.bn3(self.conv3(x))))
        # Conv block 4
        x = self.pool(F.relu(self.bn4(self.conv4(x))))

        # Flatten
        x = x.view(x.size(0), -1)

        # Fully connected
        x = self.dropout(F.relu(self.fc1(x)))
        x = self.dropout(F.relu(self.fc2(x)))
        x = self.fc3(x)

        return x


def create_model(num_classes: int = {{num_classes}}) -> CNNClassifier:
    """Factory function to create model"""
    return CNNClassifier(num_classes=num_classes)
''',
                "data/dataset.py": '''"""
Dataset Loading and Preprocessing
"""
import os
from typing import Tuple, Optional
import torch
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms, datasets
from PIL import Image


class ImageDataset(Dataset):
    """Custom Image Dataset"""

    def __init__(
        self,
        root_dir: str,
        transform: Optional[transforms.Compose] = None,
        train: bool = True
    ):
        self.root_dir = root_dir
        self.transform = transform or self._default_transform(train)
        self.images = []
        self.labels = []
        self.class_to_idx = {}

        self._load_data()

    def _default_transform(self, train: bool) -> transforms.Compose:
        if train:
            return transforms.Compose([
                transforms.Resize(({{input_size}}, {{input_size}})),
                transforms.RandomHorizontalFlip(),
                transforms.RandomRotation(10),
                transforms.ColorJitter(brightness=0.2, contrast=0.2),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                   std=[0.229, 0.224, 0.225])
            ])
        else:
            return transforms.Compose([
                transforms.Resize(({{input_size}}, {{input_size}})),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                   std=[0.229, 0.224, 0.225])
            ])

    def _load_data(self):
        classes = sorted(os.listdir(self.root_dir))
        self.class_to_idx = {cls: idx for idx, cls in enumerate(classes)}

        for cls in classes:
            cls_dir = os.path.join(self.root_dir, cls)
            if os.path.isdir(cls_dir):
                for img_name in os.listdir(cls_dir):
                    if img_name.lower().endswith((\'.png\', \'.jpg\', \'.jpeg\')):
                        self.images.append(os.path.join(cls_dir, img_name))
                        self.labels.append(self.class_to_idx[cls])

    def __len__(self) -> int:
        return len(self.images)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        image = Image.open(self.images[idx]).convert(\'RGB\')
        label = self.labels[idx]

        if self.transform:
            image = self.transform(image)

        return image, label


def get_dataloaders(
    train_dir: str,
    val_dir: str,
    batch_size: int = {{batch_size}},
    num_workers: int = 4
) -> Tuple[DataLoader, DataLoader]:
    """Get train and validation dataloaders"""

    train_dataset = ImageDataset(train_dir, train=True)
    val_dataset = ImageDataset(val_dir, train=False)

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True
    )

    return train_loader, val_loader
''',
                "training/train.py": '''"""
Training Script for CNN Model
"""
import os
import argparse
import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import ReduceLROnPlateau
from tqdm import tqdm
import matplotlib.pyplot as plt

from models.cnn_model import create_model
from data.dataset import get_dataloaders


def train_epoch(model, loader, criterion, optimizer, device):
    """Train for one epoch"""
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0

    pbar = tqdm(loader, desc="Training")
    for inputs, labels in pbar:
        inputs, labels = inputs.to(device), labels.to(device)

        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        running_loss += loss.item()
        _, predicted = outputs.max(1)
        total += labels.size(0)
        correct += predicted.eq(labels).sum().item()

        pbar.set_postfix({
            \'loss\': f\'{running_loss/total:.4f}\',
            \'acc\': f\'{100.*correct/total:.2f}%\'
        })

    return running_loss / len(loader), 100. * correct / total


def validate(model, loader, criterion, device):
    """Validate the model"""
    model.eval()
    running_loss = 0.0
    correct = 0
    total = 0

    with torch.no_grad():
        for inputs, labels in tqdm(loader, desc="Validating"):
            inputs, labels = inputs.to(device), labels.to(device)
            outputs = model(inputs)
            loss = criterion(outputs, labels)

            running_loss += loss.item()
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += predicted.eq(labels).sum().item()

    return running_loss / len(loader), 100. * correct / total


def train(args):
    """Main training function"""
    # Device
    device = torch.device(\'cuda\' if torch.cuda.is_available() else \'cpu\')
    print(f"Using device: {device}")

    # Data
    train_loader, val_loader = get_dataloaders(
        args.train_dir,
        args.val_dir,
        batch_size=args.batch_size
    )

    # Model
    model = create_model(num_classes=args.num_classes).to(device)

    # Loss and optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = ReduceLROnPlateau(optimizer, mode=\'min\', patience=5, factor=0.5)

    # Training history
    history = {\'train_loss\': [], \'train_acc\': [], \'val_loss\': [], \'val_acc\': []}
    best_acc = 0.0

    # Training loop
    for epoch in range(args.epochs):
        print(f"\\nEpoch {epoch+1}/{args.epochs}")
        print("-" * 40)

        train_loss, train_acc = train_epoch(model, train_loader, criterion, optimizer, device)
        val_loss, val_acc = validate(model, val_loader, criterion, device)

        scheduler.step(val_loss)

        history[\'train_loss\'].append(train_loss)
        history[\'train_acc\'].append(train_acc)
        history[\'val_loss\'].append(val_loss)
        history[\'val_acc\'].append(val_acc)

        print(f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.2f}%")
        print(f"Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.2f}%")

        # Save best model
        if val_acc > best_acc:
            best_acc = val_acc
            torch.save({
                \'epoch\': epoch,
                \'model_state_dict\': model.state_dict(),
                \'optimizer_state_dict\': optimizer.state_dict(),
                \'best_acc\': best_acc,
            }, os.path.join(args.output_dir, \'best_model.pth\'))
            print(f"Saved best model with accuracy: {best_acc:.2f}%")

    # Save training history plot
    plot_history(history, args.output_dir)

    return model, history


def plot_history(history, output_dir):
    """Plot training history"""
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    axes[0].plot(history[\'train_loss\'], label=\'Train\')
    axes[0].plot(history[\'val_loss\'], label=\'Validation\')
    axes[0].set_title(\'Loss\')
    axes[0].set_xlabel(\'Epoch\')
    axes[0].legend()

    axes[1].plot(history[\'train_acc\'], label=\'Train\')
    axes[1].plot(history[\'val_acc\'], label=\'Validation\')
    axes[1].set_title(\'Accuracy\')
    axes[1].set_xlabel(\'Epoch\')
    axes[1].legend()

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, \'training_history.png\'))
    plt.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train CNN Model")
    parser.add_argument("--train_dir", type=str, required=True, help="Training data directory")
    parser.add_argument("--val_dir", type=str, required=True, help="Validation data directory")
    parser.add_argument("--output_dir", type=str, default="outputs", help="Output directory")
    parser.add_argument("--num_classes", type=int, default={{num_classes}}, help="Number of classes")
    parser.add_argument("--batch_size", type=int, default={{batch_size}}, help="Batch size")
    parser.add_argument("--epochs", type=int, default={{epochs}}, help="Number of epochs")
    parser.add_argument("--lr", type=float, default={{learning_rate}}, help="Learning rate")

    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    train(args)
''',
                "inference/predict.py": '''"""
Inference Module
"""
import torch
from torchvision import transforms
from PIL import Image
from typing import Dict, List
import json

from models.cnn_model import create_model


class Predictor:
    """Image Classification Predictor"""

    def __init__(
        self,
        model_path: str,
        class_names: List[str],
        device: str = None
    ):
        self.device = device or (\'cuda\' if torch.cuda.is_available() else \'cpu\')
        self.class_names = class_names

        # Load model
        self.model = create_model(num_classes=len(class_names))
        checkpoint = torch.load(model_path, map_location=self.device)
        self.model.load_state_dict(checkpoint[\'model_state_dict\'])
        self.model.to(self.device)
        self.model.eval()

        # Transform
        self.transform = transforms.Compose([
            transforms.Resize(({{input_size}}, {{input_size}})),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                               std=[0.229, 0.224, 0.225])
        ])

    def predict(self, image_path: str) -> Dict:
        """Predict class for an image"""
        image = Image.open(image_path).convert(\'RGB\')
        input_tensor = self.transform(image).unsqueeze(0).to(self.device)

        with torch.no_grad():
            outputs = self.model(input_tensor)
            probabilities = torch.softmax(outputs, dim=1)
            confidence, predicted = probabilities.max(1)

        return {
            \'class\': self.class_names[predicted.item()],
            \'confidence\': confidence.item(),
            \'probabilities\': {
                name: prob.item()
                for name, prob in zip(self.class_names, probabilities[0])
            }
        }

    def predict_batch(self, image_paths: List[str]) -> List[Dict]:
        """Predict classes for multiple images"""
        return [self.predict(path) for path in image_paths]
''',
                "api/app.py": '''"""
FastAPI Application for Model Serving
"""
import os
import io
from typing import List
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PIL import Image
import torch

from inference.predict import Predictor

app = FastAPI(
    title="{{PROJECT_NAME}} - Image Classification API",
    description="CNN-based image classification service",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load model
MODEL_PATH = os.getenv("MODEL_PATH", "outputs/best_model.pth")
CLASS_NAMES = os.getenv("CLASS_NAMES", "class1,class2,class3").split(",")

predictor = None

@app.on_event("startup")
async def load_model():
    global predictor
    if os.path.exists(MODEL_PATH):
        predictor = Predictor(MODEL_PATH, CLASS_NAMES)
        print(f"Model loaded from {MODEL_PATH}")
    else:
        print(f"Warning: Model not found at {MODEL_PATH}")


@app.get("/")
async def root():
    return {"message": "Image Classification API", "status": "running"}


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "model_loaded": predictor is not None,
        "device": "cuda" if torch.cuda.is_available() else "cpu"
    }


@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    """Predict class for uploaded image"""
    if predictor is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    # Validate file
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    try:
        # Read image
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")

        # Save temp file for prediction
        temp_path = f"/tmp/{file.filename}"
        image.save(temp_path)

        # Predict
        result = predictor.predict(temp_path)

        # Cleanup
        os.remove(temp_path)

        return JSONResponse(content=result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/predict/batch")
async def predict_batch(files: List[UploadFile] = File(...)):
    """Predict classes for multiple images"""
    if predictor is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    results = []
    for file in files:
        try:
            contents = await file.read()
            image = Image.open(io.BytesIO(contents)).convert("RGB")
            temp_path = f"/tmp/{file.filename}"
            image.save(temp_path)
            result = predictor.predict(temp_path)
            result["filename"] = file.filename
            results.append(result)
            os.remove(temp_path)
        except Exception as e:
            results.append({"filename": file.filename, "error": str(e)})

    return JSONResponse(content={"predictions": results})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
''',
                "requirements.txt": '''torch>=2.0.0
torchvision>=0.15.0
numpy>=1.24.0
pillow>=9.5.0
matplotlib>=3.7.0
tqdm>=4.65.0
fastapi>=0.100.0
uvicorn>=0.22.0
python-multipart>=0.0.6
''',
                "README.md": '''# {{PROJECT_NAME}}

CNN Image Classification Project

## Setup

```bash
pip install -r requirements.txt
```

## Training

```bash
python training/train.py \\
    --train_dir data/train \\
    --val_dir data/val \\
    --num_classes 10 \\
    --epochs 50 \\
    --batch_size 32
```

## Inference

```python
from inference.predict import Predictor

predictor = Predictor("outputs/best_model.pth", ["cat", "dog", "bird"])
result = predictor.predict("test_image.jpg")
print(result)
```

## API Server

```bash
MODEL_PATH=outputs/best_model.pth CLASS_NAMES=cat,dog,bird python api/app.py
```

Then access: http://localhost:8000/docs
''',
                "config.yaml": '''# Model Configuration
model:
  name: cnn_classifier
  num_classes: {{num_classes}}
  input_size: {{input_size}}

# Training Configuration
training:
  batch_size: {{batch_size}}
  epochs: {{epochs}}
  learning_rate: {{learning_rate}}
  weight_decay: 0.0001

# Data Configuration
data:
  train_dir: data/train
  val_dir: data/val
  num_workers: 4

# Output
output:
  model_dir: outputs
  log_dir: logs
'''
            }
        )

    def _create_resnet_template(self) -> MLTemplate:
        """ResNet Transfer Learning Template"""
        return MLTemplate(
            name="ResNet Transfer Learning",
            model=MLModel.RESNET,
            category=MLCategory.COMPUTER_VISION,
            framework=MLFramework.PYTORCH,
            description="Pre-trained ResNet for transfer learning",
            requirements=[
                "torch>=2.0.0",
                "torchvision>=0.15.0",
                "numpy>=1.24.0",
                "pillow>=9.5.0",
                "fastapi>=0.100.0",
                "uvicorn>=0.22.0"
            ],
            config={"num_classes": 10, "pretrained": True},
            files={
                "models/resnet_model.py": '''"""
ResNet Transfer Learning Model
"""
import torch
import torch.nn as nn
from torchvision import models


class ResNetClassifier(nn.Module):
    """ResNet with custom classification head"""

    def __init__(self, num_classes: int = 10, pretrained: bool = True):
        super(ResNetClassifier, self).__init__()

        # Load pre-trained ResNet
        self.resnet = models.resnet50(pretrained=pretrained)

        # Freeze early layers
        for param in list(self.resnet.parameters())[:-20]:
            param.requires_grad = False

        # Replace classifier
        num_features = self.resnet.fc.in_features
        self.resnet.fc = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(num_features, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, num_classes)
        )

    def forward(self, x):
        return self.resnet(x)

    def unfreeze_all(self):
        """Unfreeze all layers for fine-tuning"""
        for param in self.resnet.parameters():
            param.requires_grad = True


def create_model(num_classes: int = 10, pretrained: bool = True):
    return ResNetClassifier(num_classes, pretrained)
''',
                "requirements.txt": '''torch>=2.0.0
torchvision>=0.15.0
numpy>=1.24.0
pillow>=9.5.0
fastapi>=0.100.0
uvicorn>=0.22.0
'''
            }
        )

    def _create_lstm_template(self) -> MLTemplate:
        """LSTM NLP Template"""
        return MLTemplate(
            name="LSTM Text Classifier",
            model=MLModel.LSTM,
            category=MLCategory.NLP,
            framework=MLFramework.PYTORCH,
            description="LSTM for text classification and sentiment analysis",
            requirements=[
                "torch>=2.0.0",
                "numpy>=1.24.0",
                "scikit-learn>=1.2.0",
                "nltk>=3.8.0",
                "fastapi>=0.100.0",
                "uvicorn>=0.22.0"
            ],
            config={
                "vocab_size": 10000,
                "embedding_dim": 128,
                "hidden_dim": 256,
                "num_layers": 2,
                "num_classes": 2,
                "dropout": 0.5
            },
            files={
                "models/lstm_model.py": '''"""
LSTM Text Classification Model
"""
import torch
import torch.nn as nn


class LSTMClassifier(nn.Module):
    """LSTM for Text Classification"""

    def __init__(
        self,
        vocab_size: int = 10000,
        embedding_dim: int = 128,
        hidden_dim: int = 256,
        num_layers: int = 2,
        num_classes: int = 2,
        dropout: float = 0.5,
        bidirectional: bool = True
    ):
        super(LSTMClassifier, self).__init__()

        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=0)

        self.lstm = nn.LSTM(
            embedding_dim,
            hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=bidirectional
        )

        lstm_output_dim = hidden_dim * 2 if bidirectional else hidden_dim

        self.attention = nn.Linear(lstm_output_dim, 1)
        self.dropout = nn.Dropout(dropout)

        self.fc = nn.Sequential(
            nn.Linear(lstm_output_dim, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, num_classes)
        )

    def attention_weights(self, lstm_output):
        """Calculate attention weights"""
        attn_scores = self.attention(lstm_output).squeeze(-1)
        attn_weights = torch.softmax(attn_scores, dim=1)
        return attn_weights

    def forward(self, x):
        # x: (batch_size, seq_length)
        embedded = self.embedding(x)  # (batch, seq, embed_dim)

        lstm_out, _ = self.lstm(embedded)  # (batch, seq, hidden*2)

        # Attention pooling
        attn_weights = self.attention_weights(lstm_out)
        context = torch.bmm(attn_weights.unsqueeze(1), lstm_out).squeeze(1)

        # Classification
        output = self.fc(self.dropout(context))
        return output


def create_model(**kwargs):
    return LSTMClassifier(**kwargs)
''',
                "data/text_processor.py": '''"""
Text Preprocessing for LSTM
"""
import re
from typing import List, Dict
from collections import Counter
import torch


class TextProcessor:
    """Text preprocessing and tokenization"""

    def __init__(self, vocab_size: int = 10000, max_length: int = 256):
        self.vocab_size = vocab_size
        self.max_length = max_length
        self.word2idx = {"<PAD>": 0, "<UNK>": 1}
        self.idx2word = {0: "<PAD>", 1: "<UNK>"}

    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        text = text.lower()
        text = re.sub(r\'[^a-zA-Z\\s]\', \'\', text)
        text = re.sub(r\'\\s+\', \' \', text).strip()
        return text

    def build_vocab(self, texts: List[str]):
        """Build vocabulary from texts"""
        word_counts = Counter()
        for text in texts:
            words = self.clean_text(text).split()
            word_counts.update(words)

        # Get most common words
        most_common = word_counts.most_common(self.vocab_size - 2)

        for idx, (word, _) in enumerate(most_common, start=2):
            self.word2idx[word] = idx
            self.idx2word[idx] = word

    def encode(self, text: str) -> List[int]:
        """Encode text to indices"""
        words = self.clean_text(text).split()
        indices = [self.word2idx.get(w, 1) for w in words]  # 1 = UNK

        # Pad or truncate
        if len(indices) < self.max_length:
            indices += [0] * (self.max_length - len(indices))
        else:
            indices = indices[:self.max_length]

        return indices

    def encode_batch(self, texts: List[str]) -> torch.Tensor:
        """Encode batch of texts"""
        return torch.tensor([self.encode(t) for t in texts])

    def save(self, path: str):
        """Save processor"""
        import json
        with open(path, \'w\') as f:
            json.dump({
                \'vocab_size\': self.vocab_size,
                \'max_length\': self.max_length,
                \'word2idx\': self.word2idx
            }, f)

    @classmethod
    def load(cls, path: str):
        """Load processor"""
        import json
        with open(path, \'r\') as f:
            data = json.load(f)

        processor = cls(data[\'vocab_size\'], data[\'max_length\'])
        processor.word2idx = data[\'word2idx\']
        processor.idx2word = {int(v): k for k, v in data[\'word2idx\'].items()}
        return processor
''',
                "requirements.txt": '''torch>=2.0.0
numpy>=1.24.0
scikit-learn>=1.2.0
nltk>=3.8.0
fastapi>=0.100.0
uvicorn>=0.22.0
'''
            }
        )

    def _create_bert_template(self) -> MLTemplate:
        """BERT NLP Template"""
        return MLTemplate(
            name="BERT Text Classifier",
            model=MLModel.BERT,
            category=MLCategory.NLP,
            framework=MLFramework.HUGGINGFACE,
            description="BERT for text classification using HuggingFace Transformers",
            requirements=[
                "torch>=2.0.0",
                "transformers>=4.30.0",
                "datasets>=2.12.0",
                "accelerate>=0.20.0",
                "scikit-learn>=1.2.0",
                "fastapi>=0.100.0",
                "uvicorn>=0.22.0"
            ],
            config={"num_classes": 2, "max_length": 512, "model_name": "bert-base-uncased"},
            files={
                "models/bert_model.py": '''"""
BERT Text Classification Model
"""
import torch
import torch.nn as nn
from transformers import BertModel, BertTokenizer


class BERTClassifier(nn.Module):
    """BERT for Text Classification"""

    def __init__(
        self,
        model_name: str = "bert-base-uncased",
        num_classes: int = 2,
        dropout: float = 0.3,
        freeze_bert: bool = False
    ):
        super(BERTClassifier, self).__init__()

        self.bert = BertModel.from_pretrained(model_name)

        if freeze_bert:
            for param in self.bert.parameters():
                param.requires_grad = False

        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Sequential(
            nn.Linear(self.bert.config.hidden_size, 256),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(256, num_classes)
        )

    def forward(self, input_ids, attention_mask):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        pooled_output = outputs.pooler_output
        output = self.classifier(self.dropout(pooled_output))
        return output


class BERTPredictor:
    """BERT Inference Wrapper"""

    def __init__(self, model_path: str, model_name: str = "bert-base-uncased", num_classes: int = 2):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = BertTokenizer.from_pretrained(model_name)

        self.model = BERTClassifier(model_name, num_classes)
        self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.to(self.device)
        self.model.eval()

    def predict(self, text: str, max_length: int = 512):
        encoding = self.tokenizer(
            text,
            truncation=True,
            max_length=max_length,
            padding="max_length",
            return_tensors="pt"
        )

        input_ids = encoding["input_ids"].to(self.device)
        attention_mask = encoding["attention_mask"].to(self.device)

        with torch.no_grad():
            outputs = self.model(input_ids, attention_mask)
            probs = torch.softmax(outputs, dim=1)
            predicted = torch.argmax(probs, dim=1)

        return {
            "class": predicted.item(),
            "confidence": probs[0][predicted].item(),
            "probabilities": probs[0].tolist()
        }
''',
                "training/train_bert.py": '''"""
BERT Training Script
"""
import os
import argparse
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from transformers import BertTokenizer, get_linear_schedule_with_warmup
from tqdm import tqdm

from models.bert_model import BERTClassifier


class TextDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_length=512):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        encoding = self.tokenizer(
            self.texts[idx],
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt"
        )
        return {
            "input_ids": encoding["input_ids"].squeeze(),
            "attention_mask": encoding["attention_mask"].squeeze(),
            "label": torch.tensor(self.labels[idx])
        }


def train(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Tokenizer
    tokenizer = BertTokenizer.from_pretrained(args.model_name)

    # Load data (implement your data loading)
    # train_texts, train_labels = load_data(args.train_file)
    # val_texts, val_labels = load_data(args.val_file)

    # Model
    model = BERTClassifier(args.model_name, args.num_classes).to(device)

    # Optimizer
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr)
    criterion = nn.CrossEntropyLoss()

    print(f"Training BERT on {device}")
    # Add training loop here

    # Save model
    torch.save(model.state_dict(), os.path.join(args.output_dir, "bert_model.pth"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_name", default="bert-base-uncased")
    parser.add_argument("--num_classes", type=int, default=2)
    parser.add_argument("--max_length", type=int, default=512)
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--output_dir", default="outputs")

    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    train(args)
''',
                "requirements.txt": '''torch>=2.0.0
transformers>=4.30.0
datasets>=2.12.0
accelerate>=0.20.0
scikit-learn>=1.2.0
fastapi>=0.100.0
uvicorn>=0.22.0
'''
            }
        )

    def _create_random_forest_template(self) -> MLTemplate:
        """Random Forest Template"""
        return MLTemplate(
            name="Random Forest Classifier",
            model=MLModel.RANDOM_FOREST,
            category=MLCategory.CLASSIFICATION,
            framework=MLFramework.SKLEARN,
            description="Random Forest for tabular data classification",
            requirements=[
                "scikit-learn>=1.2.0",
                "pandas>=2.0.0",
                "numpy>=1.24.0",
                "joblib>=1.2.0",
                "fastapi>=0.100.0",
                "uvicorn>=0.22.0"
            ],
            config={"n_estimators": 100, "max_depth": 10},
            files={
                "models/random_forest.py": '''"""
Random Forest Classifier
"""
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score, GridSearchCV
from sklearn.metrics import classification_report, confusion_matrix


class RandomForestModel:
    """Random Forest with utilities"""

    def __init__(self, n_estimators=100, max_depth=10, random_state=42):
        self.model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=random_state,
            n_jobs=-1
        )

    def train(self, X, y):
        """Train the model"""
        self.model.fit(X, y)
        return self

    def predict(self, X):
        """Make predictions"""
        return self.model.predict(X)

    def predict_proba(self, X):
        """Get prediction probabilities"""
        return self.model.predict_proba(X)

    def evaluate(self, X, y):
        """Evaluate model"""
        y_pred = self.predict(X)
        return {
            "classification_report": classification_report(y, y_pred),
            "confusion_matrix": confusion_matrix(y, y_pred).tolist(),
            "accuracy": (y_pred == y).mean()
        }

    def cross_validate(self, X, y, cv=5):
        """Cross-validation"""
        scores = cross_val_score(self.model, X, y, cv=cv)
        return {"mean": scores.mean(), "std": scores.std(), "scores": scores.tolist()}

    def feature_importance(self, feature_names=None):
        """Get feature importance"""
        importance = self.model.feature_importances_
        if feature_names:
            return dict(zip(feature_names, importance))
        return importance.tolist()

    def save(self, path):
        """Save model"""
        joblib.dump(self.model, path)

    @classmethod
    def load(cls, path):
        """Load model"""
        instance = cls()
        instance.model = joblib.load(path)
        return instance
''',
                "requirements.txt": '''scikit-learn>=1.2.0
pandas>=2.0.0
numpy>=1.24.0
joblib>=1.2.0
fastapi>=0.100.0
uvicorn>=0.22.0
'''
            }
        )

    def _create_xgboost_template(self) -> MLTemplate:
        """XGBoost Template"""
        return MLTemplate(
            name="XGBoost Classifier",
            model=MLModel.XGBOOST,
            category=MLCategory.CLASSIFICATION,
            framework=MLFramework.SKLEARN,
            description="XGBoost gradient boosting for tabular data",
            requirements=[
                "xgboost>=1.7.0",
                "scikit-learn>=1.2.0",
                "pandas>=2.0.0",
                "numpy>=1.24.0",
                "fastapi>=0.100.0"
            ],
            config={"n_estimators": 100, "max_depth": 6, "learning_rate": 0.1},
            files={
                "models/xgboost_model.py": '''"""
XGBoost Classifier
"""
import xgboost as xgb
import numpy as np
from sklearn.metrics import classification_report


class XGBoostModel:
    """XGBoost Classifier with utilities"""

    def __init__(self, n_estimators=100, max_depth=6, learning_rate=0.1):
        self.model = xgb.XGBClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            use_label_encoder=False,
            eval_metric="logloss"
        )

    def train(self, X, y, eval_set=None):
        """Train with optional early stopping"""
        self.model.fit(X, y, eval_set=eval_set, verbose=True)
        return self

    def predict(self, X):
        return self.model.predict(X)

    def predict_proba(self, X):
        return self.model.predict_proba(X)

    def save(self, path):
        self.model.save_model(path)

    @classmethod
    def load(cls, path):
        instance = cls()
        instance.model.load_model(path)
        return instance
''',
                "requirements.txt": '''xgboost>=1.7.0
scikit-learn>=1.2.0
pandas>=2.0.0
numpy>=1.24.0
fastapi>=0.100.0
'''
            }
        )

    def _create_yolo_template(self) -> MLTemplate:
        """YOLO Object Detection Template"""
        return MLTemplate(
            name="YOLO Object Detection",
            model=MLModel.YOLO,
            category=MLCategory.COMPUTER_VISION,
            framework=MLFramework.PYTORCH,
            description="YOLO for real-time object detection",
            requirements=[
                "ultralytics>=8.0.0",
                "torch>=2.0.0",
                "opencv-python>=4.7.0",
                "fastapi>=0.100.0",
                "uvicorn>=0.22.0"
            ],
            config={"model_size": "yolov8n", "conf_threshold": 0.5},
            files={
                "models/yolo_detector.py": '''"""
YOLO Object Detection
"""
from ultralytics import YOLO
import cv2
import numpy as np
from typing import List, Dict


class YOLODetector:
    """YOLO Object Detector"""

    def __init__(self, model_path: str = "yolov8n.pt", conf_threshold: float = 0.5):
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold

    def detect(self, image_path: str) -> List[Dict]:
        """Detect objects in image"""
        results = self.model(image_path, conf=self.conf_threshold)

        detections = []
        for r in results:
            boxes = r.boxes
            for box in boxes:
                detections.append({
                    "class": r.names[int(box.cls)],
                    "confidence": float(box.conf),
                    "bbox": box.xyxy[0].tolist()
                })

        return detections

    def detect_video(self, video_path: str, output_path: str):
        """Detect objects in video"""
        results = self.model(video_path, save=True, project=output_path)
        return results

    def train_custom(self, data_yaml: str, epochs: int = 100):
        """Train on custom dataset"""
        results = self.model.train(data=data_yaml, epochs=epochs)
        return results
''',
                "requirements.txt": '''ultralytics>=8.0.0
torch>=2.0.0
opencv-python>=4.7.0
fastapi>=0.100.0
uvicorn>=0.22.0
'''
            }
        )

    def _create_gan_template(self) -> MLTemplate:
        """GAN Template"""
        return MLTemplate(
            name="GAN Image Generator",
            model=MLModel.GAN,
            category=MLCategory.GENERATIVE,
            framework=MLFramework.PYTORCH,
            description="Generative Adversarial Network for image generation",
            requirements=[
                "torch>=2.0.0",
                "torchvision>=0.15.0",
                "numpy>=1.24.0",
                "matplotlib>=3.7.0"
            ],
            config={"latent_dim": 100, "img_size": 64, "channels": 3},
            files={
                "models/gan_model.py": '''"""
GAN Model - Generator and Discriminator
"""
import torch
import torch.nn as nn


class Generator(nn.Module):
    """GAN Generator"""

    def __init__(self, latent_dim=100, img_size=64, channels=3):
        super(Generator, self).__init__()

        self.init_size = img_size // 4
        self.l1 = nn.Linear(latent_dim, 128 * self.init_size ** 2)

        self.conv_blocks = nn.Sequential(
            nn.BatchNorm2d(128),
            nn.Upsample(scale_factor=2),
            nn.Conv2d(128, 128, 3, stride=1, padding=1),
            nn.BatchNorm2d(128),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Upsample(scale_factor=2),
            nn.Conv2d(128, 64, 3, stride=1, padding=1),
            nn.BatchNorm2d(64),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Conv2d(64, channels, 3, stride=1, padding=1),
            nn.Tanh()
        )

    def forward(self, z):
        out = self.l1(z)
        out = out.view(out.shape[0], 128, self.init_size, self.init_size)
        img = self.conv_blocks(out)
        return img


class Discriminator(nn.Module):
    """GAN Discriminator"""

    def __init__(self, img_size=64, channels=3):
        super(Discriminator, self).__init__()

        def block(in_feat, out_feat, bn=True):
            layers = [nn.Conv2d(in_feat, out_feat, 3, 2, 1)]
            if bn:
                layers.append(nn.BatchNorm2d(out_feat))
            layers.append(nn.LeakyReLU(0.2, inplace=True))
            return layers

        self.model = nn.Sequential(
            *block(channels, 16, bn=False),
            *block(16, 32),
            *block(32, 64),
            *block(64, 128),
        )

        ds_size = img_size // 2 ** 4
        self.adv_layer = nn.Sequential(
            nn.Linear(128 * ds_size ** 2, 1),
            nn.Sigmoid()
        )

    def forward(self, img):
        out = self.model(img)
        out = out.view(out.shape[0], -1)
        validity = self.adv_layer(out)
        return validity
''',
                "requirements.txt": '''torch>=2.0.0
torchvision>=0.15.0
numpy>=1.24.0
matplotlib>=3.7.0
'''
            }
        )

    def _create_timeseries_template(self) -> MLTemplate:
        """Time Series LSTM Template"""
        return MLTemplate(
            name="LSTM Time Series Forecasting",
            model=MLModel.LSTM_TIMESERIES,
            category=MLCategory.TIME_SERIES,
            framework=MLFramework.PYTORCH,
            description="LSTM for time series forecasting",
            requirements=[
                "torch>=2.0.0",
                "numpy>=1.24.0",
                "pandas>=2.0.0",
                "scikit-learn>=1.2.0",
                "matplotlib>=3.7.0"
            ],
            config={"seq_length": 60, "hidden_dim": 128, "num_layers": 2},
            files={
                "models/lstm_timeseries.py": '''"""
LSTM Time Series Forecasting
"""
import torch
import torch.nn as nn
import numpy as np
from sklearn.preprocessing import MinMaxScaler


class LSTMForecaster(nn.Module):
    """LSTM for Time Series"""

    def __init__(self, input_dim=1, hidden_dim=128, num_layers=2, output_dim=1):
        super(LSTMForecaster, self).__init__()

        self.lstm = nn.LSTM(
            input_dim, hidden_dim, num_layers,
            batch_first=True, dropout=0.2
        )
        self.fc = nn.Linear(hidden_dim, output_dim)

    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        predictions = self.fc(lstm_out[:, -1, :])
        return predictions


class TimeSeriesPredictor:
    """Time Series Prediction Wrapper"""

    def __init__(self, seq_length=60):
        self.seq_length = seq_length
        self.scaler = MinMaxScaler()
        self.model = None

    def prepare_data(self, data):
        """Prepare sequences for LSTM"""
        scaled = self.scaler.fit_transform(data.reshape(-1, 1))

        X, y = [], []
        for i in range(self.seq_length, len(scaled)):
            X.append(scaled[i-self.seq_length:i])
            y.append(scaled[i])

        return np.array(X), np.array(y)

    def train(self, data, epochs=100, lr=0.001):
        """Train the model"""
        X, y = self.prepare_data(data)
        X = torch.FloatTensor(X)
        y = torch.FloatTensor(y)

        self.model = LSTMForecaster()
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)

        for epoch in range(epochs):
            self.model.train()
            optimizer.zero_grad()
            output = self.model(X)
            loss = criterion(output, y)
            loss.backward()
            optimizer.step()

            if (epoch + 1) % 10 == 0:
                print(f"Epoch {epoch+1}/{epochs}, Loss: {loss.item():.6f}")

    def predict(self, data, steps=30):
        """Predict future values"""
        self.model.eval()
        predictions = []

        current_seq = self.scaler.transform(data[-self.seq_length:].reshape(-1, 1))

        for _ in range(steps):
            with torch.no_grad():
                x = torch.FloatTensor(current_seq).unsqueeze(0)
                pred = self.model(x).numpy()[0]
                predictions.append(pred)
                current_seq = np.vstack([current_seq[1:], pred])

        return self.scaler.inverse_transform(np.array(predictions))
''',
                "requirements.txt": '''torch>=2.0.0
numpy>=1.24.0
pandas>=2.0.0
scikit-learn>=1.2.0
matplotlib>=3.7.0
'''
            }
        )

    def _create_transformer_template(self) -> MLTemplate:
        """Custom Transformer Template"""
        return MLTemplate(
            name="Custom Transformer",
            model=MLModel.TRANSFORMER,
            category=MLCategory.NLP,
            framework=MLFramework.PYTORCH,
            description="Custom Transformer architecture from scratch",
            requirements=[
                "torch>=2.0.0",
                "numpy>=1.24.0"
            ],
            config={"d_model": 512, "nhead": 8, "num_layers": 6},
            files={
                "models/transformer_model.py": '''"""
Custom Transformer Architecture
"""
import torch
import torch.nn as nn
import math


class PositionalEncoding(nn.Module):
    """Positional Encoding for Transformer"""

    def __init__(self, d_model, max_len=5000, dropout=0.1):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)

        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))

        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)

        self.register_buffer("pe", pe)

    def forward(self, x):
        x = x + self.pe[:, :x.size(1)]
        return self.dropout(x)


class TransformerModel(nn.Module):
    """Custom Transformer"""

    def __init__(
        self,
        vocab_size,
        d_model=512,
        nhead=8,
        num_encoder_layers=6,
        num_decoder_layers=6,
        dim_feedforward=2048,
        dropout=0.1
    ):
        super().__init__()

        self.d_model = d_model
        self.embedding = nn.Embedding(vocab_size, d_model)
        self.pos_encoder = PositionalEncoding(d_model, dropout=dropout)

        self.transformer = nn.Transformer(
            d_model=d_model,
            nhead=nhead,
            num_encoder_layers=num_encoder_layers,
            num_decoder_layers=num_decoder_layers,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True
        )

        self.fc_out = nn.Linear(d_model, vocab_size)

    def forward(self, src, tgt, src_mask=None, tgt_mask=None):
        src = self.embedding(src) * math.sqrt(self.d_model)
        src = self.pos_encoder(src)

        tgt = self.embedding(tgt) * math.sqrt(self.d_model)
        tgt = self.pos_encoder(tgt)

        output = self.transformer(src, tgt, src_mask=src_mask, tgt_mask=tgt_mask)
        output = self.fc_out(output)

        return output

    def generate_square_subsequent_mask(self, sz):
        mask = torch.triu(torch.ones(sz, sz), diagonal=1)
        mask = mask.masked_fill(mask == 1, float("-inf"))
        return mask
''',
                "requirements.txt": '''torch>=2.0.0
numpy>=1.24.0
'''
            }
        )


# Singleton instance
ml_templates_service = MLTemplatesService()
