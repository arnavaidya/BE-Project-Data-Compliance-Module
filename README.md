# AI Training-Data Compliance Module

A full-stack compliance checking system for AI/ML training datasets, powered by **Microsoft Presidio** for industry-standard PII/PHI detection across GDPR, HIPAA, CCPA, ISO 27001, and PCI-DSS regulations.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![React](https://img.shields.io/badge/react-18.0+-61DAFB.svg)](https://reactjs.org/)

## 🎯 Features

- **Microsoft Presidio Integration**: Industry-standard NLP-based PII/PHI detection
- **Multi-Regulation Support**: GDPR, HIPAA, CCPA, ISO 27001, PCI-DSS compliance checking
- **CSV Upload**: Direct upload and scanning of training datasets
- **Interactive Dashboard**: Real-time visualization with charts and heatmaps
- **High Performance**: Optimized for datasets with 1000+ rows
- **Academic Research Ready**: Includes evaluation scripts for calculating metrics

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Node.js 14+

### Installation

```bash
# Clone repository
git clone https://github.com/arnavaidya/BE-Project-Data-Compliance-Module.git
cd BE-Project-Data-Compliance-Module

# Backend setup
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Frontend setup
cd ../frontend
npm install

# Run application
cd ..
python start.py
```

Access: **http://localhost:3000**

## 📊 Performance Metrics

Evaluated on 1,000-record test dataset:
- **Accuracy**: 100%
- **Precision**: 100%
- **Recall**: 100%
- **F1-Score**: 1.00

## 🛠️ Technologies

- **Backend**: FastAPI, Microsoft Presidio, spaCy, Pandas
- **Frontend**: React, Recharts

## 🙏 Acknowledgments

- Microsoft Presidio for PII detection framework
- FastAPI and React communities