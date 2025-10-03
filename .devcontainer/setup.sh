#!/bin/bash
set -e

echo "🦜 Setting up Party Parrot development environment..."

# Update system packages
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    cmake \
    pkg-config \
    libasound2-dev \
    portaudio19-dev \
    libportaudio2 \
    libportaudiocpp0 \
    ffmpeg \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    libgtk-3-dev \
    libpng-dev \
    libjpeg-dev \
    libopenexr-dev \
    libtiff-dev \
    libwebp-dev \
    libgl1-mesa-dev \
    libglu1-mesa-dev \
    freeglut3-dev \
    mesa-utils \
    xvfb \
    curl \
    wget

# Install Poetry
echo "📦 Installing Poetry..."
curl -sSL https://install.python-poetry.org | python3 -
export PATH="/home/vscode/.local/bin:$PATH"
echo 'export PATH="/home/vscode/.local/bin:$PATH"' >> ~/.bashrc
echo 'export PATH="/home/vscode/.local/bin:$PATH"' >> ~/.zshrc

# Install Just
echo "⚡ Installing Just command runner..."
curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to /home/vscode/.local/bin

# Configure Poetry
poetry config virtualenvs.create true
poetry config virtualenvs.in-project true

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
poetry install

# Set up pre-commit hooks (if available)
if [ -f ".pre-commit-config.yaml" ]; then
    echo "🪝 Setting up pre-commit hooks..."
    poetry run pre-commit install
fi

# Create test output directory
mkdir -p test_output

# Set up environment variables for headless operation
echo "🖥️  Setting up headless environment..."
echo 'export DISPLAY=:99' >> ~/.bashrc
echo 'export DISPLAY=:99' >> ~/.zshrc
echo 'export PYTHONPATH="${PYTHONPATH}:/workspace"' >> ~/.bashrc
echo 'export PYTHONPATH="${PYTHONPATH}:/workspace"' >> ~/.zshrc

# Start virtual display for headless OpenGL
sudo Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 &

echo "✅ Party Parrot development environment setup complete!"
echo ""
echo "🚀 Quick start commands:"
echo "  just launch      - Run the main application"
echo "  just test        - Run tests"
echo "  just coverage    - Show test coverage"
echo "  poetry shell     - Activate virtual environment"
echo ""
echo "🎵 Ready to make some music-responsive lighting magic!"