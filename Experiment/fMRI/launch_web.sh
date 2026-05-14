#!/bin/bash
# Launch the Streamlit web version of the Grammaticality Judgment Task
#
# Usage: ./launch_web.sh
# Then open http://localhost:8501 in a browser

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Use port 8501 by default; override with PORT env var
PORT="${PORT:-8501}"

echo "Launching Streamlit at http://localhost:${PORT}"
echo "Press Ctrl+C to stop."
echo ""

streamlit run Grammaticality_RWL_Web.py \
  --server.port "${PORT}" \
  --server.headless false \
  --server.fileWatcherType none \
  --browser.gatherUsageStats false
