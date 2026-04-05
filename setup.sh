#!/bin/bash
# =============================================================
# setup.sh — Environment Setup Script
# Cross-Modal Prompt Injection Study | CMPT 479/982 SFU 2026
# Authors: Chirajay Aggarwal, Kandisa Agarwal
#
# Usage:
#   First time:  bash setup.sh
#   Any machine: bash setup.sh
# =============================================================

set -e  # stop on any error

echo "=============================================="
echo " Cross-Modal Prompt Injection Study — Setup"
echo " CMPT 479/982 | SFU 2026"
echo " Authors: Chirajay Aggarwal, Kandisa Agarwal"
echo "=============================================="

# ── Check Python ───────────────────────────────
echo ""
echo "[1/5] Checking Python version..."
if ! command -v python3 &>/dev/null; then
    echo "  ERROR: python3 not found. Install it first:"
    echo "  sudo apt install python3 python3-pip python3-venv"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo "  ✓ Found $PYTHON_VERSION"

# ── Create virtual environment ─────────────────
echo ""
echo "[2/5] Setting up virtual environment..."
if [ -d "venv" ]; then
    echo "  ✓ venv already exists — skipping creation"
else
    python3 -m venv venv
    echo "  ✓ Created venv/"
fi

# ── Activate venv ──────────────────────────────
echo ""
echo "[3/5] Activating virtual environment..."
source venv/bin/activate
echo "  ✓ venv activated"

# ── Upgrade pip ────────────────────────────────
echo ""
echo "[4/5] Upgrading pip..."
pip install --upgrade pip --quiet
echo "  ✓ pip upgraded"

# ── Install from requirements.txt ─────────────
echo ""
echo "[5/5] Installing dependencies from requirements.txt..."
echo ""

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo ""
    echo "  ✓ All dependencies installed from requirements.txt"
else
    echo "  [WARN] requirements.txt not found — installing defaults..."
    pip install \
        pandas numpy Pillow python-docx reportlab \
        matplotlib seaborn jupyter ipykernel \
        datasets requests tqdm openpyxl \
        openai google-generativeai
    echo ""
    echo "  Saving requirements.txt for future use..."
    pip freeze > requirements.txt
    echo "  ✓ requirements.txt created"
fi

echo ""
echo "=============================================="
echo " ✓ Setup complete!"
echo "=============================================="
echo ""
echo "To activate the environment in future sessions:"
echo "  source venv/bin/activate"
echo ""
echo "To run the experiments:"
echo "  python scripts/exp1_text_payload_encoder.py"
echo "  python scripts/exp2_image_generator.py"
echo "  python scripts/exp3_doc_generator.py"
echo "  python scripts/exp4_memory_generator.py"
echo "  python scripts/run_exp1_exp2.py --exp all"
echo "  python scripts/analyze_results.py"
echo ""
echo "To launch Jupyter notebook:"
echo "  jupyter notebook analysis/analysis.ipynb"
echo ""
echo "NOTE: Don't forget to create scripts/api_keys.py with your keys!"
echo "  OPENAI_API_KEY = 'sk-...'"
echo "  GEMINI_API_KEY = 'AIza...'"
echo ""