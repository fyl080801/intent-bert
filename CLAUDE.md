# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Financial Intent BERT Classification System (金融意图BERT分类系统) - A multi-task learning BERT model for classifying financial domain user intents with hierarchical three-level labels.

**Architecture:**
- **Python (PyTorch)**: BERT model training and inference using Transformers
- **Node.js (TypeScript)**: REST API server that proxies requests to Python model service
- **Deployment**: Single-container Docker setup running both services

The system uses a dual-service architecture:
1. **Python Model Service** (Flask, port 5000): Loads BERT model and handles inference
2. **Node.js API Service** (Express, port 3000): Public-facing API that calls Python service

## Development Commands

### Environment Setup

```bash
# Install Python dependencies (using venv)
pip install -r lib/requirements.txt

# Install Node.js dependencies
npm install

# Build TypeScript
npm run build
```

### Model Training

```bash
# Train BERT model (requires datasets in datasets/ directory)
npm run train:model
# Uses: lib/python/train.py
# Outputs trained model to: models/
```

### Running Services Locally

**Option 1: Development (two terminals)**
```bash
# Terminal 1: Start Python model service
npm run serve:model
# Runs: lib/python/model_server.py on port 5000

# Terminal 2: Start Node.js API
npm run dev
# Runs: src/server.ts on port 3000
```

**Option 2: Production**
```bash
# Build and start Node.js server
npm run build
npm start
# Requires Python model service already running
```

### Testing & Prediction

```bash
# Interactive prediction mode
npm run predict
# Runs: lib/python/predict.py --interactive

# Test model with example predictions
npm run test:model
```

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# Build Docker image manually
docker build -t financial-intent-bert .

# Check service health
curl http://localhost:3000/health
curl http://localhost:5000/health
```

## Code Architecture

### Python Model Layer (`lib/python/`)

**Core Files:**
- `models.py`: `BertForMultiLabelClassification` - Multi-task BERT model with three classification heads (level1, level2, level3 labels)
- `train.py`: Model training script with data loading, label encoding, and training loop
- `predict.py`: `FinancialIntentPredictor` class for single/batch/file prediction
- `model_server.py`: Flask REST API (`/predict`, `/predict_batch`, `/model_info` endpoints)

**Key Concepts:**
- Model outputs logits for three hierarchical label levels simultaneously
- Label encoders are saved as `label_encoders.json` during training
- Training config saved as `training_config.json` (includes max_length, epochs, etc.)
- Model files are saved in HuggingFace format (pytorch_model.bin, config.json)

### Node.js API Layer (`src/`)

**Core Files:**
- `server.ts`: Express server with endpoints `/api/predict`, `/api/predict-batch`, `/api/model-info`, `/api/example`
- `modelClient.ts`: `FinancialIntentClient` class that calls Python service via axios
- `client.ts`: Aliyun NLP AutoML SDK client (alternative cloud-based approach)

**API Flow:**
```
Client Request → Node.js API (port 3000) → Python Model Service (port 5000) → BERT Model
```

### Data & Model Files

- `datasets/`: CSV files for training/validation (financial_intent_dataset.csv, financial_intent_validation.csv)
- `models/`: Trained model output directory (created after training)
- `datasets/dataset_labels_info.json`: Label metadata

## Important Implementation Details

### Model Service Communication
- Node.js service waits for Python service startup via `waitForService()` health check
- Python service uses Flask with CORS enabled
- Both services support health check endpoints at `/health`

### Python Virtual Environment
- Python executable path: `./venv/bin/python` (hardcoded in package.json scripts)
- All Python scripts assume venv is activated or use this path

### Environment Variables
- `MODEL_PATH`: Path to trained model directory (default: `models`)
- `MODEL_SERVICE_URL`: URL of Python model service (default: `http://localhost:5000`)
- `PORT`: Node.js API port (default: 3000)
- Aliyun credentials (for cloud NLP): `ALIBABA_CLOUD_ACCESS_KEY_ID`, `ALIBABA_CLOUD_ACCESS_KEY_SECRET`

### TypeScript Configuration
- Target: ES2017, Module: CommonJS
- Output directory: `dist/`
- Source files: `src/**/*.ts`

## Common Tasks

### Adding New Prediction Endpoints
1. Add endpoint in `src/server.ts`
2. Add corresponding method in `src/modelClient.ts`
3. Add route handler in `lib/python/model_server.py` if needed

### Retraining the Model
1. Prepare new dataset CSV in `datasets/` directory
2. Run `npm run train:model`
3. Model will be saved to `models/` directory
4. Restart services to load new model

### Debugging Model Predictions
- Use interactive mode: `npm run predict`
- Check model info: `curl http://localhost:5000/model_info`
- Python service logs show model loading and prediction details

### Docker Troubleshooting
- Check container logs: `docker logs financial-intent-bert`
- Ensure `models/` directory exists before building (or train first)
- Python service takes ~10 seconds to load model on startup
