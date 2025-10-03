#!/bin/bash
set -e

echo "🦜 Party Parrot - Development Environment Setup"
echo "=============================================="

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to add to PATH if not already there
add_to_path() {
    local bin_path="$1"
    if [[ ":$PATH:" != *":$bin_path:"* ]]; then
        export PATH="$bin_path:$PATH"
        echo "export PATH=\"$bin_path:\$PATH\"" >> ~/.bashrc
        if [ -f ~/.zshrc ]; then
            echo "export PATH=\"$bin_path:\$PATH\"" >> ~/.zshrc
        fi
        echo "✅ Added $bin_path to PATH"
    fi
}

# Install system dependencies (Ubuntu/Debian)
if command_exists apt-get; then
    echo "📦 Installing system dependencies..."
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
        libgl1-mesa-dev \
        libglu1-mesa-dev \
        freeglut3-dev \
        mesa-utils \
        xvfb \
        curl \
        wget
fi

# Install Poetry if not present
if ! command_exists poetry; then
    echo "📚 Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
    add_to_path "$HOME/.local/bin"
    export PATH="$HOME/.local/bin:$PATH"
else
    echo "✅ Poetry already installed"
fi

# Install Just if not present
if ! command_exists just; then
    echo "⚡ Installing Just command runner..."
    curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to "$HOME/.local/bin"
    add_to_path "$HOME/.local/bin"
    export PATH="$HOME/.local/bin:$PATH"
else
    echo "✅ Just already installed"
fi

# Verify installations
echo ""
echo "🔍 Verifying installations..."
if command_exists poetry; then
    echo "✅ Poetry: $(poetry --version)"
else
    echo "❌ Poetry installation failed"
    exit 1
fi

if command_exists just; then
    echo "✅ Just: $(just --version)"
else
    echo "❌ Just installation failed"
    exit 1
fi

# Configure Poetry
echo ""
echo "⚙️  Configuring Poetry..."
poetry config virtualenvs.create true
poetry config virtualenvs.in-project true

# Install Python dependencies
echo ""
echo "🐍 Installing Python dependencies..."
if [ -f "pyproject.toml" ]; then
    poetry install
    echo "✅ Dependencies installed successfully"
else
    echo "❌ pyproject.toml not found"
    exit 1
fi

# Create necessary directories
echo ""
echo "📁 Creating project directories..."
mkdir -p test_output
mkdir -p logs

# Set up environment variables
echo ""
echo "🌍 Setting up environment variables..."
echo 'export PYTHONPATH="${PYTHONPATH}:$(pwd)"' >> ~/.bashrc
if [ -f ~/.zshrc ]; then
    echo 'export PYTHONPATH="${PYTHONPATH}:$(pwd)"' >> ~/.zshrc
fi

# Set up virtual display for headless OpenGL (if running headless)
if [ -z "$DISPLAY" ] && command_exists Xvfb; then
    echo "🖥️  Setting up virtual display for headless operation..."
    export DISPLAY=:99
    echo 'export DISPLAY=:99' >> ~/.bashrc
    if [ -f ~/.zshrc ]; then
        echo 'export DISPLAY=:99' >> ~/.zshrc
    fi
    
    # Start Xvfb if not already running
    if ! pgrep -f "Xvfb :99" > /dev/null; then
        Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 &
        echo "✅ Virtual display started"
    fi
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "🚀 Quick start commands:"
echo "  just launch      - Run the main Party Parrot application"
echo "  just test        - Run the test suite"
echo "  just coverage    - Show test coverage report"
echo "  poetry shell     - Activate the virtual environment"
echo ""
echo "💡 If this is your first time, try running: just test"
echo "🎵 Ready to create some audio-reactive lighting magic!"