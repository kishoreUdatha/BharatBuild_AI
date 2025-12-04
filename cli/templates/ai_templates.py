"""
AI/ML/Deep Learning/Generative AI Project Templates
"""

from typing import Dict, List, Any

AI_ML_TEMPLATES: Dict[str, Dict[str, Any]] = {
    # ==========================================
    # Machine Learning Templates
    # ==========================================
    "ml-classification": {
        "name": "ML Classification Project",
        "description": "Machine learning classification project with scikit-learn",
        "category": "Machine Learning",
        "files": {
            "main.py": '''"""
Machine Learning Classification Project
"""
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import joblib
import matplotlib.pyplot as plt
import seaborn as sns

def load_data(filepath: str) -> pd.DataFrame:
    """Load dataset from CSV"""
    return pd.read_csv(filepath)

def preprocess_data(df: pd.DataFrame, target_col: str):
    """Preprocess data for training"""
    X = df.drop(columns=[target_col])
    y = df[target_col]

    # Encode categorical variables
    le = LabelEncoder()
    y = le.fit_transform(y)

    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X.select_dtypes(include=[np.number]))

    return X_scaled, y, scaler, le

def train_model(X_train, y_train, model_type="random_forest"):
    """Train classification model"""
    if model_type == "random_forest":
        model = RandomForestClassifier(n_estimators=100, random_state=42)
    elif model_type == "gradient_boosting":
        model = GradientBoostingClassifier(n_estimators=100, random_state=42)

    model.fit(X_train, y_train)
    return model

def evaluate_model(model, X_test, y_test):
    """Evaluate model performance"""
    y_pred = model.predict(X_test)

    print("Classification Report:")
    print(classification_report(y_test, y_pred))

    print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")

    return y_pred

def plot_confusion_matrix(y_test, y_pred, labels=None):
    """Plot confusion matrix"""
    cm = confusion_matrix(y_test, y_pred)
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
    plt.xlabel('Predicted')
    plt.ylabel('Actual')
    plt.title('Confusion Matrix')
    plt.savefig('confusion_matrix.png')
    plt.close()

if __name__ == "__main__":
    # Example usage
    print("ML Classification Project Ready!")
    print("Add your dataset and modify the code as needed.")
''',
            "requirements.txt": '''pandas>=2.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
matplotlib>=3.7.0
seaborn>=0.12.0
joblib>=1.3.0
''',
            "README.md": '''# ML Classification Project

## Setup
```bash
pip install -r requirements.txt
```

## Usage
```bash
python main.py
```

## Features
- Data loading and preprocessing
- Multiple classifier support (Random Forest, Gradient Boosting)
- Model evaluation with metrics
- Confusion matrix visualization
'''
        }
    },

    "ml-regression": {
        "name": "ML Regression Project",
        "description": "Machine learning regression project",
        "category": "Machine Learning",
        "files": {
            "main.py": '''"""
Machine Learning Regression Project
"""
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import matplotlib.pyplot as plt
import joblib

def load_and_prepare_data(filepath: str, target_col: str):
    """Load and prepare data"""
    df = pd.read_csv(filepath)
    X = df.drop(columns=[target_col])
    y = df[target_col]
    return X, y

def train_and_evaluate(X, y, model_name="random_forest"):
    """Train and evaluate regression model"""
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    models = {
        "linear": LinearRegression(),
        "ridge": Ridge(alpha=1.0),
        "lasso": Lasso(alpha=1.0),
        "random_forest": RandomForestRegressor(n_estimators=100, random_state=42),
        "gradient_boosting": GradientBoostingRegressor(n_estimators=100, random_state=42)
    }

    model = models.get(model_name, models["random_forest"])
    model.fit(X_train_scaled, y_train)

    y_pred = model.predict(X_test_scaled)

    print(f"Model: {model_name}")
    print(f"RMSE: {np.sqrt(mean_squared_error(y_test, y_pred)):.4f}")
    print(f"MAE: {mean_absolute_error(y_test, y_pred):.4f}")
    print(f"R2 Score: {r2_score(y_test, y_pred):.4f}")

    return model, scaler

if __name__ == "__main__":
    print("ML Regression Project Ready!")
''',
            "requirements.txt": '''pandas>=2.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
matplotlib>=3.7.0
joblib>=1.3.0
'''
        }
    },

    # ==========================================
    # Deep Learning Templates
    # ==========================================
    "dl-image-classification": {
        "name": "Deep Learning Image Classification",
        "description": "CNN-based image classification with PyTorch",
        "category": "Deep Learning",
        "files": {
            "model.py": '''"""
CNN Model for Image Classification
"""
import torch
import torch.nn as nn
import torch.nn.functional as F

class CNN(nn.Module):
    def __init__(self, num_classes=10):
        super(CNN, self).__init__()
        self.conv1 = nn.Conv2d(3, 32, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(32)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm2d(64)
        self.conv3 = nn.Conv2d(64, 128, kernel_size=3, padding=1)
        self.bn3 = nn.BatchNorm2d(128)
        self.pool = nn.MaxPool2d(2, 2)
        self.dropout = nn.Dropout(0.5)
        self.fc1 = nn.Linear(128 * 4 * 4, 512)
        self.fc2 = nn.Linear(512, num_classes)

    def forward(self, x):
        x = self.pool(F.relu(self.bn1(self.conv1(x))))
        x = self.pool(F.relu(self.bn2(self.conv2(x))))
        x = self.pool(F.relu(self.bn3(self.conv3(x))))
        x = x.view(-1, 128 * 4 * 4)
        x = self.dropout(F.relu(self.fc1(x)))
        x = self.fc2(x)
        return x

class ResNetBlock(nn.Module):
    def __init__(self, in_channels, out_channels, stride=1):
        super(ResNetBlock, self).__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3, stride=stride, padding=1)
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm2d(out_channels)

        self.shortcut = nn.Sequential()
        if stride != 1 or in_channels != out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=1, stride=stride),
                nn.BatchNorm2d(out_channels)
            )

    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += self.shortcut(x)
        out = F.relu(out)
        return out
''',
            "train.py": '''"""
Training script for image classification
"""
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
from model import CNN
from tqdm import tqdm
import matplotlib.pyplot as plt

def get_data_loaders(batch_size=64):
    transform_train = transforms.Compose([
        transforms.RandomHorizontalFlip(),
        transforms.RandomCrop(32, padding=4),
        transforms.ToTensor(),
        transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
    ])

    transform_test = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
    ])

    train_dataset = datasets.CIFAR10(root='./data', train=True, download=True, transform=transform_train)
    test_dataset = datasets.CIFAR10(root='./data', train=False, download=True, transform=transform_test)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=2)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, num_workers=2)

    return train_loader, test_loader

def train(model, train_loader, criterion, optimizer, device):
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0

    for inputs, labels in tqdm(train_loader, desc="Training"):
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

    return running_loss / len(train_loader), 100. * correct / total

def evaluate(model, test_loader, criterion, device):
    model.eval()
    running_loss = 0.0
    correct = 0
    total = 0

    with torch.no_grad():
        for inputs, labels in tqdm(test_loader, desc="Evaluating"):
            inputs, labels = inputs.to(device), labels.to(device)
            outputs = model(inputs)
            loss = criterion(outputs, labels)

            running_loss += loss.item()
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += predicted.eq(labels).sum().item()

    return running_loss / len(test_loader), 100. * correct / total

def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    model = CNN(num_classes=10).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.1)

    train_loader, test_loader = get_data_loaders()

    epochs = 20
    train_losses, test_losses = [], []
    train_accs, test_accs = [], []

    for epoch in range(epochs):
        train_loss, train_acc = train(model, train_loader, criterion, optimizer, device)
        test_loss, test_acc = evaluate(model, test_loader, criterion, device)
        scheduler.step()

        train_losses.append(train_loss)
        test_losses.append(test_loss)
        train_accs.append(train_acc)
        test_accs.append(test_acc)

        print(f"Epoch {epoch+1}/{epochs}")
        print(f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.2f}%")
        print(f"Test Loss: {test_loss:.4f}, Test Acc: {test_acc:.2f}%")

    torch.save(model.state_dict(), 'model.pth')
    print("Model saved!")

if __name__ == "__main__":
    main()
''',
            "requirements.txt": '''torch>=2.0.0
torchvision>=0.15.0
tqdm>=4.65.0
matplotlib>=3.7.0
'''
        }
    },

    "dl-nlp-transformer": {
        "name": "NLP Transformer Model",
        "description": "Text classification with Transformers (BERT)",
        "category": "Deep Learning",
        "files": {
            "train.py": '''"""
Text Classification with BERT
"""
import torch
from torch.utils.data import DataLoader, Dataset
from transformers import BertTokenizer, BertForSequenceClassification, AdamW
from transformers import get_linear_schedule_with_warmup
from sklearn.model_selection import train_test_split
import pandas as pd
from tqdm import tqdm

class TextDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_length=128):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = self.labels[idx]

        encoding = self.tokenizer.encode_plus(
            text,
            add_special_tokens=True,
            max_length=self.max_length,
            return_token_type_ids=False,
            padding='max_length',
            truncation=True,
            return_attention_mask=True,
            return_tensors='pt',
        )

        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long)
        }

def train_epoch(model, data_loader, optimizer, scheduler, device):
    model.train()
    total_loss = 0
    correct = 0
    total = 0

    for batch in tqdm(data_loader, desc="Training"):
        input_ids = batch['input_ids'].to(device)
        attention_mask = batch['attention_mask'].to(device)
        labels = batch['labels'].to(device)

        optimizer.zero_grad()
        outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
        loss = outputs.loss
        logits = outputs.logits

        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        scheduler.step()

        total_loss += loss.item()
        _, predicted = torch.max(logits, 1)
        total += labels.size(0)
        correct += (predicted == labels).sum().item()

    return total_loss / len(data_loader), correct / total

def evaluate(model, data_loader, device):
    model.eval()
    total_loss = 0
    correct = 0
    total = 0

    with torch.no_grad():
        for batch in tqdm(data_loader, desc="Evaluating"):
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['labels'].to(device)

            outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
            loss = outputs.loss
            logits = outputs.logits

            total_loss += loss.item()
            _, predicted = torch.max(logits, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

    return total_loss / len(data_loader), correct / total

def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # Load tokenizer and model
    tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
    model = BertForSequenceClassification.from_pretrained('bert-base-uncased', num_labels=2)
    model.to(device)

    # Example data (replace with your dataset)
    texts = ["This is a positive review", "This is a negative review"] * 100
    labels = [1, 0] * 100

    train_texts, val_texts, train_labels, val_labels = train_test_split(
        texts, labels, test_size=0.2, random_state=42
    )

    train_dataset = TextDataset(train_texts, train_labels, tokenizer)
    val_dataset = TextDataset(val_texts, val_labels, tokenizer)

    train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=16)

    optimizer = AdamW(model.parameters(), lr=2e-5)
    total_steps = len(train_loader) * 3
    scheduler = get_linear_schedule_with_warmup(optimizer, num_warmup_steps=0, num_training_steps=total_steps)

    for epoch in range(3):
        train_loss, train_acc = train_epoch(model, train_loader, optimizer, scheduler, device)
        val_loss, val_acc = evaluate(model, val_loader, device)
        print(f"Epoch {epoch+1}: Train Loss={train_loss:.4f}, Train Acc={train_acc:.4f}, Val Loss={val_loss:.4f}, Val Acc={val_acc:.4f}")

    model.save_pretrained('./model')
    tokenizer.save_pretrained('./model')
    print("Model saved!")

if __name__ == "__main__":
    main()
''',
            "requirements.txt": '''torch>=2.0.0
transformers>=4.30.0
pandas>=2.0.0
scikit-learn>=1.3.0
tqdm>=4.65.0
'''
        }
    },

    # ==========================================
    # Generative AI Templates
    # ==========================================
    "genai-langchain-rag": {
        "name": "LangChain RAG Application",
        "description": "Retrieval-Augmented Generation with LangChain",
        "category": "Generative AI",
        "files": {
            "app.py": '''"""
RAG Application with LangChain
"""
from langchain.document_loaders import PyPDFLoader, TextLoader, DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings, HuggingFaceEmbeddings
from langchain.vectorstores import Chroma, FAISS
from langchain.chat_models import ChatOpenAI, ChatAnthropic
from langchain.chains import RetrievalQA, ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
import os

class RAGApplication:
    def __init__(self, model_provider="openai", embedding_provider="huggingface"):
        self.model_provider = model_provider
        self.embedding_provider = embedding_provider
        self.vectorstore = None
        self.chain = None
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )

        # Initialize embeddings
        if embedding_provider == "openai":
            self.embeddings = OpenAIEmbeddings()
        else:
            self.embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )

        # Initialize LLM
        if model_provider == "openai":
            self.llm = ChatOpenAI(model_name="gpt-4", temperature=0)
        elif model_provider == "anthropic":
            self.llm = ChatAnthropic(model="claude-3-sonnet-20240229", temperature=0)

    def load_documents(self, path: str, file_type: str = "pdf"):
        """Load documents from path"""
        if file_type == "pdf":
            loader = PyPDFLoader(path)
        elif file_type == "txt":
            loader = TextLoader(path)
        elif file_type == "directory":
            loader = DirectoryLoader(path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

        documents = loader.load()

        # Split documents
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        splits = text_splitter.split_documents(documents)

        return splits

    def create_vectorstore(self, documents, store_type: str = "chroma"):
        """Create vector store from documents"""
        if store_type == "chroma":
            self.vectorstore = Chroma.from_documents(
                documents,
                self.embeddings,
                persist_directory="./chroma_db"
            )
        elif store_type == "faiss":
            self.vectorstore = FAISS.from_documents(documents, self.embeddings)

        return self.vectorstore

    def create_chain(self):
        """Create retrieval chain"""
        if self.vectorstore is None:
            raise ValueError("Vectorstore not initialized. Load documents first.")

        retriever = self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 4}
        )

        prompt_template = """Use the following pieces of context to answer the question at the end.
If you don't know the answer, just say that you don't know, don't try to make up an answer.

Context: {context}

Question: {question}

Answer:"""

        PROMPT = PromptTemplate(
            template=prompt_template,
            input_variables=["context", "question"]
        )

        self.chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=retriever,
            memory=self.memory,
            combine_docs_chain_kwargs={"prompt": PROMPT}
        )

        return self.chain

    def query(self, question: str) -> str:
        """Query the RAG system"""
        if self.chain is None:
            self.create_chain()

        response = self.chain({"question": question})
        return response["answer"]

def main():
    # Example usage
    rag = RAGApplication(model_provider="openai", embedding_provider="huggingface")

    # Load documents
    # documents = rag.load_documents("./documents", file_type="directory")
    # rag.create_vectorstore(documents)

    print("RAG Application initialized!")
    print("Load your documents and start querying.")

if __name__ == "__main__":
    main()
''',
            "requirements.txt": '''langchain>=0.1.0
langchain-openai>=0.0.5
langchain-anthropic>=0.1.0
langchain-community>=0.0.20
chromadb>=0.4.0
faiss-cpu>=1.7.0
sentence-transformers>=2.2.0
pypdf>=3.0.0
openai>=1.0.0
anthropic>=0.18.0
tiktoken>=0.5.0
'''
        }
    },

    "genai-image-generation": {
        "name": "Image Generation with Diffusers",
        "description": "Stable Diffusion image generation",
        "category": "Generative AI",
        "files": {
            "generate.py": '''"""
Image Generation with Stable Diffusion
"""
import torch
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
from diffusers import StableDiffusionImg2ImgPipeline
from PIL import Image
import os

class ImageGenerator:
    def __init__(self, model_id="stabilityai/stable-diffusion-2-1"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.dtype = torch.float16 if self.device == "cuda" else torch.float32

        print(f"Loading model on {self.device}...")
        self.pipe = StableDiffusionPipeline.from_pretrained(
            model_id,
            torch_dtype=self.dtype
        )
        self.pipe.scheduler = DPMSolverMultistepScheduler.from_config(
            self.pipe.scheduler.config
        )
        self.pipe = self.pipe.to(self.device)

        # Enable memory optimization
        if self.device == "cuda":
            self.pipe.enable_attention_slicing()

    def generate(
        self,
        prompt: str,
        negative_prompt: str = None,
        num_images: int = 1,
        height: int = 512,
        width: int = 512,
        num_inference_steps: int = 30,
        guidance_scale: float = 7.5,
        seed: int = None
    ):
        """Generate images from text prompt"""
        generator = None
        if seed is not None:
            generator = torch.Generator(device=self.device).manual_seed(seed)

        images = self.pipe(
            prompt,
            negative_prompt=negative_prompt,
            num_images_per_prompt=num_images,
            height=height,
            width=width,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            generator=generator
        ).images

        return images

    def save_images(self, images, output_dir="./outputs", prefix="generated"):
        """Save generated images"""
        os.makedirs(output_dir, exist_ok=True)
        paths = []
        for i, img in enumerate(images):
            path = os.path.join(output_dir, f"{prefix}_{i}.png")
            img.save(path)
            paths.append(path)
        return paths

def main():
    generator = ImageGenerator()

    prompt = "A beautiful sunset over mountains, digital art, highly detailed"
    negative_prompt = "blurry, low quality, distorted"

    images = generator.generate(
        prompt=prompt,
        negative_prompt=negative_prompt,
        num_images=1,
        seed=42
    )

    paths = generator.save_images(images)
    print(f"Images saved to: {paths}")

if __name__ == "__main__":
    main()
''',
            "requirements.txt": '''torch>=2.0.0
diffusers>=0.25.0
transformers>=4.30.0
accelerate>=0.25.0
safetensors>=0.4.0
Pillow>=10.0.0
'''
        }
    },

    "genai-llm-finetuning": {
        "name": "LLM Fine-tuning with LoRA",
        "description": "Fine-tune LLMs using LoRA/QLoRA",
        "category": "Generative AI",
        "files": {
            "train.py": '''"""
LLM Fine-tuning with LoRA/QLoRA
"""
import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from datasets import load_dataset
import bitsandbytes as bnb

def get_model_and_tokenizer(model_name, use_4bit=True):
    """Load model with quantization"""
    bnb_config = None
    if use_4bit:
        bnb_config = bnb.BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True
        )

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True
    )

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    return model, tokenizer

def setup_lora(model):
    """Setup LoRA configuration"""
    model = prepare_model_for_kbit_training(model)

    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )

    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    return model

def prepare_dataset(tokenizer, dataset_name="timdettmers/openassistant-guanaco"):
    """Load and prepare dataset"""
    dataset = load_dataset(dataset_name, split="train")

    def tokenize(example):
        return tokenizer(
            example["text"],
            truncation=True,
            max_length=512,
            padding="max_length"
        )

    tokenized_dataset = dataset.map(tokenize, batched=True)
    return tokenized_dataset

def train(model, tokenizer, dataset):
    """Train the model"""
    training_args = TrainingArguments(
        output_dir="./results",
        num_train_epochs=3,
        per_device_train_batch_size=4,
        gradient_accumulation_steps=4,
        warmup_steps=100,
        learning_rate=2e-4,
        fp16=True,
        logging_steps=10,
        save_steps=100,
        evaluation_strategy="no"
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False)
    )

    trainer.train()

    # Save the model
    model.save_pretrained("./fine_tuned_model")
    tokenizer.save_pretrained("./fine_tuned_model")

    return trainer

def main():
    model_name = "mistralai/Mistral-7B-v0.1"

    print("Loading model and tokenizer...")
    model, tokenizer = get_model_and_tokenizer(model_name, use_4bit=True)

    print("Setting up LoRA...")
    model = setup_lora(model)

    print("Preparing dataset...")
    dataset = prepare_dataset(tokenizer)

    print("Training...")
    trainer = train(model, tokenizer, dataset)

    print("Done!")

if __name__ == "__main__":
    main()
''',
            "requirements.txt": '''torch>=2.0.0
transformers>=4.35.0
peft>=0.7.0
bitsandbytes>=0.41.0
accelerate>=0.25.0
datasets>=2.14.0
trl>=0.7.0
'''
        }
    },

    # ==========================================
    # Computer Vision Templates
    # ==========================================
    "cv-object-detection": {
        "name": "Object Detection with YOLO",
        "description": "Real-time object detection using YOLOv8",
        "category": "Computer Vision",
        "files": {
            "detect.py": '''"""
Object Detection with YOLOv8
"""
from ultralytics import YOLO
import cv2
import os

class ObjectDetector:
    def __init__(self, model_size="n"):
        """Initialize YOLOv8 model

        Args:
            model_size: 'n' (nano), 's' (small), 'm' (medium), 'l' (large), 'x' (xlarge)
        """
        self.model = YOLO(f"yolov8{model_size}.pt")

    def detect_image(self, image_path, conf_threshold=0.5, save=True):
        """Detect objects in an image"""
        results = self.model(image_path, conf=conf_threshold)

        if save:
            for r in results:
                r.save(filename=f"result_{os.path.basename(image_path)}")

        return results

    def detect_video(self, video_path, conf_threshold=0.5, save=True):
        """Detect objects in a video"""
        results = self.model(video_path, conf=conf_threshold, stream=True)

        for r in results:
            if save:
                r.save()
            yield r

    def detect_webcam(self, conf_threshold=0.5):
        """Real-time detection from webcam"""
        cap = cv2.VideoCapture(0)

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            results = self.model(frame, conf=conf_threshold)
            annotated_frame = results[0].plot()

            cv2.imshow("YOLOv8 Detection", annotated_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()

    def train_custom(self, data_yaml, epochs=100, imgsz=640):
        """Train on custom dataset"""
        results = self.model.train(
            data=data_yaml,
            epochs=epochs,
            imgsz=imgsz
        )
        return results

def main():
    detector = ObjectDetector(model_size="n")

    # Example: detect in image
    # results = detector.detect_image("image.jpg")

    # Example: webcam detection
    # detector.detect_webcam()

    print("Object Detector initialized!")
    print("Use detect_image(), detect_video(), or detect_webcam() methods")

if __name__ == "__main__":
    main()
''',
            "requirements.txt": '''ultralytics>=8.0.0
opencv-python>=4.8.0
torch>=2.0.0
'''
        }
    },

    # ==========================================
    # Reinforcement Learning Templates
    # ==========================================
    "rl-gymnasium": {
        "name": "Reinforcement Learning with Gymnasium",
        "description": "RL agent training with Stable Baselines3",
        "category": "Reinforcement Learning",
        "files": {
            "train.py": '''"""
Reinforcement Learning with Stable Baselines3
"""
import gymnasium as gym
from stable_baselines3 import PPO, DQN, A2C, SAC
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.evaluation import evaluate_policy
from stable_baselines3.common.callbacks import EvalCallback, CheckpointCallback
import os

def create_environment(env_name="CartPole-v1", n_envs=4):
    """Create vectorized environment"""
    env = make_vec_env(env_name, n_envs=n_envs)
    return env

def train_agent(env_name="CartPole-v1", algorithm="PPO", total_timesteps=100000):
    """Train RL agent"""
    env = create_environment(env_name)

    # Create log directories
    log_dir = "./logs/"
    model_dir = "./models/"
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(model_dir, exist_ok=True)

    # Select algorithm
    algorithms = {
        "PPO": PPO,
        "DQN": DQN,
        "A2C": A2C,
        "SAC": SAC
    }

    AlgoClass = algorithms.get(algorithm, PPO)

    # Create callbacks
    eval_callback = EvalCallback(
        env,
        best_model_save_path=model_dir,
        log_path=log_dir,
        eval_freq=10000,
        deterministic=True
    )

    checkpoint_callback = CheckpointCallback(
        save_freq=10000,
        save_path=model_dir,
        name_prefix=f"{algorithm.lower()}_model"
    )

    # Create and train model
    model = AlgoClass("MlpPolicy", env, verbose=1, tensorboard_log=log_dir)

    model.learn(
        total_timesteps=total_timesteps,
        callback=[eval_callback, checkpoint_callback]
    )

    # Save final model
    model.save(f"{model_dir}/{algorithm.lower()}_final")

    return model

def evaluate_agent(model_path, env_name="CartPole-v1", n_eval_episodes=10):
    """Evaluate trained agent"""
    env = gym.make(env_name)
    model = PPO.load(model_path)

    mean_reward, std_reward = evaluate_policy(
        model, env, n_eval_episodes=n_eval_episodes
    )

    print(f"Mean reward: {mean_reward:.2f} +/- {std_reward:.2f}")

    return mean_reward, std_reward

def visualize_agent(model_path, env_name="CartPole-v1", n_episodes=5):
    """Visualize trained agent"""
    env = gym.make(env_name, render_mode="human")
    model = PPO.load(model_path)

    for episode in range(n_episodes):
        obs, _ = env.reset()
        done = False
        total_reward = 0

        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, _ = env.step(action)
            done = terminated or truncated
            total_reward += reward

        print(f"Episode {episode + 1}: Total Reward = {total_reward}")

    env.close()

def main():
    # Train agent
    model = train_agent(
        env_name="CartPole-v1",
        algorithm="PPO",
        total_timesteps=50000
    )

    # Evaluate
    evaluate_agent("./models/PPO_final", n_eval_episodes=10)

    # Visualize (requires display)
    # visualize_agent("./models/PPO_final")

if __name__ == "__main__":
    main()
''',
            "requirements.txt": '''gymnasium>=0.29.0
stable-baselines3>=2.0.0
tensorboard>=2.14.0
'''
        }
    },

    # ==========================================
    # MLOps Templates
    # ==========================================
    "mlops-mlflow": {
        "name": "MLOps with MLflow",
        "description": "Experiment tracking and model management",
        "category": "MLOps",
        "files": {
            "train_with_mlflow.py": '''"""
ML Training with MLflow Tracking
"""
import mlflow
import mlflow.sklearn
import mlflow.pytorch
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score
import pandas as pd

def setup_mlflow(experiment_name="default"):
    """Setup MLflow tracking"""
    mlflow.set_tracking_uri("sqlite:///mlflow.db")
    mlflow.set_experiment(experiment_name)

def train_sklearn_model():
    """Train and log sklearn model"""
    setup_mlflow("sklearn-classification")

    # Load data
    iris = load_iris()
    X_train, X_test, y_train, y_test = train_test_split(
        iris.data, iris.target, test_size=0.2, random_state=42
    )

    # Hyperparameters to try
    params_list = [
        {"n_estimators": 50, "max_depth": 3},
        {"n_estimators": 100, "max_depth": 5},
        {"n_estimators": 200, "max_depth": 10}
    ]

    for params in params_list:
        with mlflow.start_run():
            # Log parameters
            mlflow.log_params(params)

            # Train model
            model = RandomForestClassifier(**params, random_state=42)
            model.fit(X_train, y_train)

            # Evaluate
            y_pred = model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            f1 = f1_score(y_test, y_pred, average='weighted')

            # Log metrics
            mlflow.log_metrics({
                "accuracy": accuracy,
                "f1_score": f1
            })

            # Log model
            mlflow.sklearn.log_model(model, "model")

            print(f"Params: {params}, Accuracy: {accuracy:.4f}, F1: {f1:.4f}")

def load_best_model():
    """Load best model from MLflow"""
    client = mlflow.tracking.MlflowClient()
    experiment = client.get_experiment_by_name("sklearn-classification")

    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id],
        order_by=["metrics.accuracy DESC"],
        max_results=1
    )

    if runs:
        best_run = runs[0]
        model_uri = f"runs:/{best_run.info.run_id}/model"
        model = mlflow.sklearn.load_model(model_uri)
        print(f"Loaded best model with accuracy: {best_run.data.metrics['accuracy']:.4f}")
        return model

    return None

def main():
    print("Training models with MLflow tracking...")
    train_sklearn_model()

    print("\\nLoading best model...")
    best_model = load_best_model()

    print("\\nStart MLflow UI with: mlflow ui")
    print("Then open http://localhost:5000 in your browser")

if __name__ == "__main__":
    main()
''',
            "requirements.txt": '''mlflow>=2.9.0
scikit-learn>=1.3.0
pandas>=2.0.0
'''
        }
    }
}


def get_template(template_id: str) -> Dict[str, Any]:
    """Get a specific template by ID"""
    return AI_ML_TEMPLATES.get(template_id)


def list_templates(category: str = None) -> List[Dict[str, str]]:
    """List all templates, optionally filtered by category"""
    templates = []
    for tid, template in AI_ML_TEMPLATES.items():
        if category is None or template.get("category") == category:
            templates.append({
                "id": tid,
                "name": template["name"],
                "description": template["description"],
                "category": template["category"]
            })
    return templates


def get_categories() -> List[str]:
    """Get all template categories"""
    categories = set()
    for template in AI_ML_TEMPLATES.values():
        categories.add(template["category"])
    return sorted(list(categories))
