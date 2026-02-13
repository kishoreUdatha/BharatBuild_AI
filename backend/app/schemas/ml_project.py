"""
ML Project Schemas - Pydantic models for ML project configuration
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum


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


# ==================== Request Schemas ====================

class MLProjectConfig(BaseModel):
    """Configuration for ML project generation"""
    # Required
    model_type: MLModel = Field(..., description="Type of ML model to use")
    project_name: str = Field(..., min_length=1, max_length=100, description="Project name")

    # Optional customizations
    num_classes: Optional[int] = Field(None, ge=2, description="Number of output classes")
    input_size: Optional[int] = Field(None, ge=16, description="Input image size (for vision models)")
    max_length: Optional[int] = Field(None, ge=16, description="Max sequence length (for NLP models)")
    hidden_dim: Optional[int] = Field(None, ge=16, description="Hidden layer dimension")
    num_layers: Optional[int] = Field(None, ge=1, description="Number of layers")
    learning_rate: Optional[float] = Field(None, gt=0, description="Learning rate")
    batch_size: Optional[int] = Field(None, ge=1, description="Batch size")
    epochs: Optional[int] = Field(None, ge=1, description="Number of training epochs")

    # AI customization prompt
    customization_prompt: Optional[str] = Field(
        None,
        max_length=2000,
        description="Additional requirements for AI to customize the template"
    )


class MLProjectCreateRequest(BaseModel):
    """Request to create a new ML project"""
    config: MLProjectConfig
    workspace_id: Optional[str] = None


class MLCustomizationRequest(BaseModel):
    """Request to customize ML template with AI"""
    model_type: MLModel
    project_name: str
    base_template: bool = True  # Whether to start from template
    prompt: str = Field(..., min_length=10, description="Customization requirements")
    config: Optional[Dict[str, Any]] = None


# ==================== Response Schemas ====================

class MLModelInfo(BaseModel):
    """Information about an ML model"""
    id: str
    name: str
    category: str
    framework: str
    description: str
    use_cases: List[str]


class MLModelsListResponse(BaseModel):
    """List of available ML models"""
    models: List[MLModelInfo]
    total: int


class MLTemplateFile(BaseModel):
    """A file in the ML template"""
    path: str
    content: str
    language: str


class MLTemplateResponse(BaseModel):
    """Response with ML template files"""
    model_type: str
    project_name: str
    files: List[MLTemplateFile]
    requirements: List[str]
    config: Dict[str, Any]


class MLProjectResponse(BaseModel):
    """Response after creating ML project"""
    project_id: str
    project_name: str
    model_type: str
    category: str
    framework: str
    files_created: int
    message: str


class MLConfigOptions(BaseModel):
    """Configuration options for a model type"""
    model_type: str
    options: Dict[str, Any]
    defaults: Dict[str, Any]
    description: str


# ==================== AI Customization Schemas ====================

class AICustomizationContext(BaseModel):
    """Context for AI customization"""
    model_type: MLModel
    base_template_files: Dict[str, str]
    user_requirements: str
    config: Optional[Dict[str, Any]] = None


class AICustomizationResult(BaseModel):
    """Result from AI customization"""
    files: Dict[str, str]
    modifications_made: List[str]
    suggestions: Optional[List[str]] = None


# ==================== Prompt-Based Generation Schemas ====================

class PromptAnalysisResult(BaseModel):
    """Result of analyzing user prompt for ML project"""
    detected_model_type: str = Field(..., description="Detected ML model type")
    detected_category: str = Field(..., description="Detected ML category")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score")
    extracted_config: Dict[str, Any] = Field(default_factory=dict, description="Extracted configuration")
    extracted_features: List[str] = Field(default_factory=list, description="Extracted features/requirements")
    suggested_models: List[str] = Field(default_factory=list, description="Alternative model suggestions")
    data_type: str = Field(default="unknown", description="Detected data type: tabular, image, text, time_series")
    problem_type: str = Field(default="unknown", description="Detected problem: classification, regression, detection")


class PromptMLGenerateRequest(BaseModel):
    """Request to generate ML project from natural language prompt"""
    prompt: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Natural language description of the ML project"
    )
    project_name: Optional[str] = Field(None, max_length=100, description="Optional project name")
    workspace_id: Optional[str] = Field(None, description="Workspace to create project in")

    # Optional overrides (if user wants to specify)
    model_type: Optional[str] = Field(None, description="Override detected model type")
    num_classes: Optional[int] = Field(None, ge=2, description="Number of classes")
    input_size: Optional[int] = Field(None, ge=32, description="Input size for images")


class PromptMLGenerateResponse(BaseModel):
    """Response after generating ML project from prompt"""
    project_id: str
    project_name: str
    model_type: str
    category: str
    framework: str
    files_created: int
    prompt_analysis: PromptAnalysisResult
    message: str


class PromptAnalyzeRequest(BaseModel):
    """Request to analyze prompt without generating project"""
    prompt: str = Field(..., min_length=10, max_length=2000)


class PromptAnalyzeResponse(BaseModel):
    """Response with prompt analysis results"""
    analysis: PromptAnalysisResult
    suggested_prompt_improvements: List[str] = Field(default_factory=list)
    ready_to_generate: bool = Field(default=False)
