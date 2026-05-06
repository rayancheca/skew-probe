#!/usr/bin/env bash
# Start backend and frontend dev servers
set -e

# Backend
cd backend
if [ ! -d .venv ]; then
  echo "Creating virtualenv..."
  python3.11 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt -q
else
  source .venv/bin/activate
fi

# Generate sample data if missing
if [ ! -f ../sample_data/sample.parquet ]; then
  echo "Generating sample data..."
  python ../sample_data/generate_sample.py
fi

echo "Starting backend on :8000"
uvicorn src.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

cd ../frontend
if [ ! -d node_modules ]; then
  echo "Installing frontend deps..."
  npm install -q
fi

echo "Starting frontend on :5173"
npm run dev -- --port 5173 &
FRONTEND_PID=$!

echo ""
echo "SkewProbe running:"
echo "  Frontend: http://localhost:5173"
echo "  Backend:  http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM
wait
