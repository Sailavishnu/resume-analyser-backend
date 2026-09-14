# Backend Setup Guide

## 🎯 Quick Start

Your backend has **ALL AI/ML/NLP components** ready! Here's how to get started:

### 1️⃣ Activate Virtual Environment

**Every time you work on the backend, activate the venv first:**

```powershell
# In PowerShell
.\venv\Scripts\Activate.ps1
```

You'll see `(venv)` in your prompt.

---

### 2️⃣ Environment Variables

Update `.env` file with your credentials:

```env
# MongoDB (already configured)
MONGODB_URI=mongodb+srv://sailavishnu29_db_user:SMG_2006@ppp-cluster.rutlvew.mongodb.net/?appName=ppp-cluster

# Cloudinary (ADD THESE - get from cloudinary.com)
CLOUDINARY_CLOUD_NAME=your_cloud_name_here
CLOUDINARY_API_KEY=your_api_key_here
CLOUDINARY_API_SECRET=your_api_secret_here

# JWT Secret (already set)
JWT_SECRET_KEY=your-secret-key-change-this-in-production
```

**How to get Cloudinary credentials:**
1. Go to [cloudinary.com](https://cloudinary.com)
2. Sign up for free account
3. Go to Dashboard
4. Copy: Cloud Name, API Key, API Secret

---

### 3️⃣ Build FAISS Vector Index

**This creates the semantic search database from your MongoDB jobs:**

```powershell
# Activate venv first!
.\venv\Scripts\Activate.ps1

# Build index from existing jobs
python ml/scripts/build_vector_index.py
```

**Output:**
```
Found 50 active jobs
Generating embeddings... (takes 2-3 minutes)
✅ Index Build Complete!
  Successfully indexed: 50
  Index saved to: ml/artifacts/job_vectors.index
```

**Rebuild after adding new jobs:**
```powershell
python ml/scripts/build_vector_index.py --rebuild
```

---

### 4️⃣ Start the Server

```powershell
# Make sure venv is activated
.\venv\Scripts\Activate.ps1

# Start FastAPI server
python run.py
```

**Expected output:**
```
🚀 Starting Resume AI & Placement Platform v1.0.0
✅ MongoDB connection established
⚠️  ML model loading failed: ml/artifacts/resume_job_match_model.joblib not found
   → Job matching will be unavailable until model is trained

📚 Loading NLP models...
✅ spaCy model loaded successfully
✅ Sentence-BERT model loaded successfully
✅ FAISS index loaded successfully (50 jobs indexed)
✅ Cloudinary configuration found

🌍 API Documentation: http://localhost:8000/docs
📊 Health Check: http://localhost:8000/health
```

Access the API:
- **Swagger UI**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

---

### 5️⃣ Train ML Model (Optional but Recommended)

The traditional RandomForest model enhances semantic search with feature-based matching.

```powershell
# After you have some resume-job match data in MongoDB
python ml/scripts/train_model.py
```

This creates: `ml/artifacts/resume_job_match_model.joblib`

---

## 🧪 Testing the Semantic Search

### Test the models:
```powershell
python ml/download_models.py --check
```

### Test the vector index:
```powershell
python ml/scripts/build_vector_index.py --info
```

### Test API with curl:
```powershell
# Health check
curl http://localhost:8000/health

# Get API docs
curl http://localhost:8000/
```

---

## 📊 What's Included

### ✅ Fully Implemented:
1. **MongoDB Integration** - 27 collections defined
2. **Authentication** - JWT-based auth with bcrypt
3. **Resume Parsing** - PDF/DOCX support with PyMuPDF
4. **ATS Scoring** - Keyword-based compatibility scoring
5. **File Uploads** - Cloudinary integration (needs API keys)
6. **NLP Processing** - spaCy en_core_web_sm (installed ✅)
7. **Embeddings** - Sentence-BERT all-MiniLM-L6-v2 (installed ✅)
8. **Vector Search** - FAISS for semantic job matching
9. **ML Model** - RandomForest (needs training)
10. **API Endpoints** - Complete REST API with FastAPI

### 🔬 AI/ML Features:
- **Semantic Job Search** - Find jobs using AI understanding of resumes
- **Hybrid Scoring** - 60% semantic + 40% ML model
- **Skill Normalization** - Recognizes JS = JavaScript, k8s = kubernetes
- **Entity Extraction** - Extracts companies, skills, education from text
- **Text Similarity** - spaCy-based description matching

---

## 📁 Project Structure

```
backend/
├── app/
│   ├── api/           # API route handlers
│   │   ├── auth.py
│   │   ├── resumes.py
│   │   ├── ats.py
│   │   ├── jd_match.py    # Job matching + semantic search
│   │   └── jobs.py
│   ├── services/      # Business logic
│   │   ├── semantic_match_service.py  # 🆕 Semantic search
│   │   └── jd_match_service.py
│   ├── ml/            # Machine Learning
│   │   ├── embeddings.py              # 🆕 Sentence-BERT
│   │   ├── vector_store.py            # 🆕 FAISS
│   │   ├── nlp_processor.py           # 🆕 spaCy NLP
│   │   ├── feature_extractor.py       # Enhanced with semantic
│   │   └── predictor.py               # ML model
│   ├── db/            # Database
│   └── core/          # Config, dependencies
├── ml/
│   ├── scripts/
│   │   └── build_vector_index.py      # 🆕 Build FAISS index
│   ├── download_models.py             # 🆕 Download AI models
│   └── artifacts/     # Stores models and index
├── requirements.txt   # All dependencies (installed ✅)
├── .env              # Environment variables
└── run.py            # Server entry point
```

---

## 🚀 API Endpoints

### Semantic Search (NEW!)
- `POST /api/v1/jd-match/semantic/search` - Find matching jobs with AI
- `POST /api/v1/jd-match/semantic/score` - Detailed match analysis
- `POST /api/v1/jd-match/semantic/skills-search` - Search by skills

### Traditional
- `POST /api/v1/resumes/upload` - Upload resume
- `POST /api/v1/ats/score` - ATS compatibility score
- `POST /api/v1/jd-match` - Traditional ML match
- `GET /api/v1/jobs` - List all jobs

---

## 🐛 Troubleshooting

### Models not loading?
```powershell
python ml/download_models.py --check
```

### FAISS index empty?
```powershell
# Check if jobs exist in MongoDB first
python ml/scripts/build_vector_index.py --info
```

### Cloudinary errors?
Check `.env` has all three variables set correctly.

### MongoDB connection fails?
Verify the MONGODB_URI in `.env` is correct.

---

## 📝 Next Steps

1. **Add Cloudinary API keys** to `.env`
2. **Add jobs to MongoDB** (use the jobs API or seed script)
3. **Build FAISS index** with `python ml/scripts/build_vector_index.py`
4. **Test semantic search** via Swagger UI at `/docs`
5. **Train ML model** when you have enough data

---

## 💡 Tips

- Always activate venv before running any commands
- Rebuild FAISS index after adding new jobs to MongoDB
- Check `/health` endpoint to see component status
- Use Swagger UI at `/docs` for interactive API testing
- Models auto-load on server startup (no manual loading needed)

---

## 🎉 You're Ready!

All AI/NLP components are installed and configured. Just add your Cloudinary keys and start the server!

```powershell
.\venv\Scripts\Activate.ps1
python run.py
```

Visit: **http://localhost:8000/docs** 🚀
