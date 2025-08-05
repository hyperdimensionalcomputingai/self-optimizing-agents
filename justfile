# Self-Optimizing Agents UI Management
# Usage: just <command>

# Default recipe to show available commands
default:
    @just --list

# Install UI dependencies
ui-install:
    @echo "📦 Installing UI dependencies..."
    cd src/ui && npm install

# Build the React app
ui-build:
    @echo "🔨 Building React app..."
    cd src/ui && npm run build

# Start the React development server
ui-dev:
    @echo "🚀 Starting React development server on port 8172..."
    @echo "📱 UI will be available at http://localhost:8172"
    cd src/ui && PORT=8172 npm start

# Start the backend API server
api:
    @echo "🌐 Starting backend API server on port 8001..."
    @echo "🔗 API will be available at http://localhost:8001"
    cd src && uv run api_server.py

# Build and start the full application (production mode)
start:
    @echo "🚀 Starting Self-Optimizing Agents UI..."
    @just ui-build
    @echo "✅ React app built successfully"
    @echo "🌐 Starting backend API server on port 8001..."
    @echo "📱 UI will be available at http://localhost:8001"
    @echo "🔗 API will be available at http://localhost:8001"
    @just api

# Start development mode (separate terminals for frontend and backend)
dev:
    @echo "🚀 Starting development mode..."
    @echo "📱 Frontend: http://localhost:8172"
    @echo "🔗 Backend: http://localhost:8001"
    @echo ""
    @echo "Run these commands in separate terminals:"
    @echo "  Terminal 1: just api"
    @echo "  Terminal 2: just ui-dev"

# Clean build artifacts
clean:
    @echo "🧹 Cleaning build artifacts..."
    rm -rf src/ui/build
    rm -rf src/ui/node_modules

# Install all dependencies (Python and Node.js)
install:
    @echo "📦 Installing all dependencies..."
    uv sync
    @just ui-install

# Setup databases (Kuzu graph + LanceDB vector)
setup-db:
    @echo "🗄️ Setting up databases..."
    @echo "📊 Building Kuzu graph database..."
    uv run src/build_graph.py
    @echo "🔍 Creating LanceDB vector database..."
    uv run src/generate_note_embeddings.py
    @echo "✅ Databases setup complete!"

# Install dependencies and setup databases
setup:
    @echo "🚀 Complete setup..."
    @just install
    @just setup-db

# Check if everything is set up correctly
check:
    @echo "🔍 Checking setup..."
    @echo "Python dependencies:"
    @uv pip list | grep -E "(fastapi|uvicorn|baml)" || echo "❌ Missing Python dependencies"
    @echo ""
    @echo "Node.js dependencies:"
    @cd src/ui && npm list --depth=0 | grep -E "(react|typescript)" || echo "❌ Missing Node.js dependencies"
    @echo ""
    @echo "Database:"
    @test -f "src/fhir_db.kuzu" && echo "✅ Database exists" || echo "❌ Database not found - run data setup first"
    @echo ""
    @echo "Environment:"
    @echo "OPENROUTER_API_KEY: $(if [ -n "$$OPENROUTER_API_KEY" ]; then echo "✅ Set"; else echo "❌ Not set"; fi)"

# Show help
help:
    @echo "Self-Optimizing Agents UI Management"
    @echo ""
    @echo "Available commands:"
    @echo "  just start      - Build and start the full application (production mode on port 8001)"
    @echo "  just dev        - Start development mode (frontend on 8172, backend on 8001)"
    @echo "  just api        - Start only the backend API server (port 8001)"
    @echo "  just ui-dev     - Start only the React development server (port 8172)"
    @echo "  just ui-build   - Build the React app"
    @echo "  just ui-install - Install UI dependencies"
    @echo "  just install    - Install all dependencies (Python + Node.js)"
    @echo "  just clean      - Clean build artifacts"
    @echo "  just check      - Check if everything is set up correctly"
    @echo "  just help       - Show this help message" 