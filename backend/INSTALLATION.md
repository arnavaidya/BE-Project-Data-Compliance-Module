# AI Training-Data Compliance Backend - Complete Package

## 📦 What's Included

This package contains the complete backend for AI Training-Data Compliance checking using **Microsoft Presidio**.

### File Structure:
```
backend/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── start.py                           # Unified launcher script
├── test_scan.py                       # CLI testing script
├── sample_dataset.json                # Sample JSON dataset (with violations)
├── sample_dataset_clean.json          # Sample clean dataset
├── sample_training_data.csv           # Sample CSV (with PII/PHI)
├── sample_training_data_clean.csv     # Sample clean CSV
└── app/
    ├── __init__.py                    # Package marker
    ├── main.py                        # FastAPI application
    ├── schemas.py                     # Pydantic models
    ├── presidio_wrapper.py            # Microsoft Presidio integration
    ├── services.py                    # Audit logger, lineage, catalog
    └── routes/
        ├── __init__.py                # Package marker
        ├── compliance.py              # Main compliance scanning endpoint
        ├── csv_upload.py              # CSV file upload & processing
        ├── audit.py                   # Audit log endpoints
        ├── lineage.py                 # Data lineage tracking
        ├── metadata.py                # Metadata catalog
        ├── rbac.py                    # RBAC policy auditing
        └── security.py                # Security auditing
```

---

## 🚀 Quick Start

### Step 1: Extract Files
```powershell
# Extract all files to your desired location
# Example: D:\Data_Compliance_Module\backend\
```

### Step 2: Create Virtual Environment
```powershell
cd D:\Data_Compliance_Module\backend

# Create venv
python -m venv .venv

# Activate it (Windows)
.venv\Scripts\Activate.ps1

# If execution policy error:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Step 3: Install Dependencies
```powershell
# Install all dependencies (~500MB, takes 2-3 minutes)
pip install -r requirements.txt

# Download spaCy NLP model (required for Presidio)
python -m spacy download en_core_web_sm
```

### Step 4: Verify Installation
```powershell
# Test Presidio
python -c "from presidio_analyzer import AnalyzerEngine; print('✓ Presidio OK!')"

# Test FastAPI
python -c "from app.main import app; print('✓ FastAPI OK!')"

# Test Presidio wrapper
python -c "from app.presidio_wrapper import run_scan; print('✓ Compliance engine OK!')"
```

### Step 5: Start Backend
```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Expected output:**
```
INFO: Microsoft Presidio loaded successfully
INFO: Uvicorn running on http://127.0.0.1:8000
```

### Step 6: Test API
Open browser to: **http://127.0.0.1:8000/docs**

You should see the Swagger API documentation.

---

## 🧪 Testing

### Test 1: Health Check
```powershell
curl http://127.0.0.1:8000/health
```

### Test 2: Scan CSV File
```powershell
python test_scan.py sample_training_data.csv
```

Expected output:
```
✓ Scan complete!
📊 Overall Status: NON_COMPLIANT
🔍 Total Findings: 12
```

### Test 3: Scan JSON Dataset
```powershell
python test_scan.py sample_dataset.json
```

---

## 📊 API Endpoints

### Main Endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/compliance/scan` | POST | Scan dataset (JSON) |
| `/csv/scan` | POST | Scan CSV file |
| `/compliance/regulations` | GET | List all regulations |
| `/compliance/rules/{regulation}` | GET | Get rules for regulation |

### Full API Documentation:
http://127.0.0.1:8000/docs

---

## 🔧 Configuration

### Environment Variables (optional):
```bash
# Set custom port
export PORT=8000

# Set log level
export LOG_LEVEL=INFO
```

### CORS Settings:
Edit `app/main.py` to restrict CORS origins for production:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Change for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 📝 Sample Data

### sample_training_data.csv
Contains PII/PHI violations:
- Email addresses
- Phone numbers
- Social Security Numbers
- Credit card numbers
- Names and addresses

**Use this to test violation detection.**

### sample_training_data_clean.csv
Contains anonymized data:
- No PII
- No PHI
- Proper data classification

**Use this to verify compliant datasets pass.**

---

## 🐛 Troubleshooting

### Issue: "Presidio not available"
```powershell
pip install presidio-analyzer presidio-anonymizer --break-system-packages
python -m spacy download en_core_web_sm
```

### Issue: "ModuleNotFoundError: No module named 'app'"
```powershell
# Make sure you're in the backend folder
cd D:\Data_Compliance_Module\backend

# Verify __init__.py files exist
dir app\__init__.py
dir app\routes\__init__.py
```

### Issue: Port 8000 already in use
```powershell
# Kill process on port 8000
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Or use different port
uvicorn app.main:app --reload --port 8001
```

---

## 📚 Dependencies

### Core:
- **FastAPI** (0.109.0+) - Web framework
- **Uvicorn** (0.27.0+) - ASGI server
- **Pydantic** (2.6.0+) - Data validation

### Microsoft Presidio:
- **presidio-analyzer** (2.2.0+) - PII/PHI detection
- **presidio-anonymizer** (2.2.0+) - Data anonymization
- **spaCy** (3.7.0+) - NLP engine

### Data Processing:
- **pandas** (2.0.0+) - DataFrame handling
- **numpy** (1.24.0+) - Numerical operations

### Testing:
- **pytest** (7.4.0+) - Test framework
- **httpx** (0.26.0+) - HTTP client for tests

---

## 🔒 Security Notes

### Production Deployment:
1. **Enable HTTPS** - Use reverse proxy (Nginx/Caddy)
2. **Add authentication** - Implement API keys or OAuth
3. **Rate limiting** - Prevent abuse
4. **Restrict CORS** - Lock down allowed origins
5. **Environment variables** - Don't hardcode secrets
6. **Monitor logs** - Track compliance scans

### Example Nginx Config:
```nginx
server {
    listen 80;
    server_name api.yourcompany.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 📖 Additional Documentation

For complete migration guide and advanced features, see:
- **Presidio Documentation:** https://microsoft.github.io/presidio/
- **FastAPI Documentation:** https://fastapi.tiangolo.com/

---

## 🆘 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Verify all dependencies are installed
3. Check the logs for error messages
4. Ensure Python 3.8+ is installed

---

## ✅ Verification Checklist

Before considering setup complete:

- [ ] Virtual environment created and activated
- [ ] All dependencies installed (pip install -r requirements.txt)
- [ ] spaCy model downloaded (python -m spacy download en_core_web_sm)
- [ ] Presidio test passes (python -c "from presidio_analyzer import AnalyzerEngine; print('OK')")
- [ ] Backend starts without errors (uvicorn app.main:app --reload)
- [ ] See "Microsoft Presidio loaded successfully" in logs
- [ ] API docs accessible at http://127.0.0.1:8000/docs
- [ ] Health check returns 200 (curl http://127.0.0.1:8000/health)
- [ ] Test scan works (python test_scan.py sample_training_data.csv)

---

## 🎉 You're Ready!

Your backend is now configured with **Microsoft Presidio** for industry-standard PII/PHI detection!

Next steps:
1. Connect the React frontend
2. Test with your real datasets
3. Customize for your needs
4. Deploy to production

**Happy compliance checking!** 🚀
