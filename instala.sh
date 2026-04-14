#!/bin/bash
# Setup script: instala dependencias e extrai squads.zip

set -e

# Garante que unzip esta disponivel (necessario no WSL/Ubuntu)
if ! command -v unzip &> /dev/null; then
  echo "Instalando unzip..."
  sudo apt-get update -qq && sudo apt-get install -y -qq unzip
fi

# Garante que Node.js esta disponivel no WSL
if ! command -v node &> /dev/null; then
  echo "Node.js nao encontrado no WSL. Instalando..."
  curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
  sudo apt-get install -y -qq nodejs
  echo "Node.js $(node --version) instalado com sucesso"
fi

echo "Instalando dependencias npm..."
npm install js-yaml

echo ""
echo "Extraindo squads.zip..."
if [ -f "squads.zip" ]; then
  unzip -o squads.zip
  echo "squads/ extraido com sucesso"
else
  echo "squads.zip nao encontrado na raiz do projeto"
fi

echo ""
echo "Setup completo!"
