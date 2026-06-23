#!/bin/bash
echo "============================================"
echo "   FURIA CLIPS - Corte. Ranqueie. Domine."
echo "============================================"
echo ""

VENV_DIR=".venv"

# Create venv if needed
if [ ! -d "$VENV_DIR" ]; then
    echo "[SETUP] Criando ambiente virtual..."
    python3 -m venv "$VENV_DIR"
fi

# Activate venv
echo "[SETUP] Ativando ambiente virtual..."
source "$VENV_DIR/bin/activate"

# Upgrade pip
pip install --upgrade pip -q

# Install dependencies
echo "[SETUP] Verificando dependencias..."
pip install -r requirements.txt -q

echo ""
echo "============================================"
echo "   Iniciando Furia Clips..."
echo "   Acesse: http://localhost:3001"
echo "============================================"
echo ""

python app.py
