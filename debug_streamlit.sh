#!/bin/bash

echo "🔍 Debugging Streamlit Service (Port 8501)"
echo "=========================================="
echo ""

# Check if Streamlit is running
echo "1️⃣ Checking if Streamlit process is running..."
if ps aux | grep -v grep | grep streamlit > /dev/null; then
    echo "   ✅ Streamlit process found:"
    ps aux | grep -v grep | grep streamlit
else
    echo "   ❌ Streamlit process NOT running"
fi
echo ""

# Check if port 8501 is listening
echo "2️⃣ Checking if port 8501 is listening..."
if lsof -i :8501 > /dev/null 2>&1; then
    echo "   ✅ Port 8501 is in use:"
    lsof -i :8501
else
    echo "   ❌ Port 8501 is NOT listening"
fi
echo ""

# Check Streamlit log
echo "3️⃣ Checking Streamlit log..."
if [ -f /workspace/logs/streamlit.log ]; then
    echo "   📄 Last 30 lines of /workspace/logs/streamlit.log:"
    echo "   ================================================"
    tail -30 /workspace/logs/streamlit.log
else
    echo "   ❌ Log file not found: /workspace/logs/streamlit.log"
fi
echo ""

# Test Streamlit manually
echo "4️⃣ Testing Streamlit manually..."
echo "   Running: streamlit run ui/streamlit/src/app_simple.py --server.port 8501 --server.headless true"
echo ""

cd /workspace/rlvr-automation
PYTHONPATH=/workspace/rlvr-automation/ui/streamlit:/workspace/rlvr-automation \
    streamlit run ui/streamlit/src/app_simple.py \
    --server.port 8501 \
    --server.headless true \
    --server.address 0.0.0.0 &

STREAMLIT_PID=$!
echo "   Started Streamlit with PID: $STREAMLIT_PID"
echo "   Waiting 5 seconds..."
sleep 5

# Check if it's running
if ps -p $STREAMLIT_PID > /dev/null; then
    echo "   ✅ Streamlit is running!"
    echo ""
    echo "   Testing HTTP connection..."
    if curl -sf http://localhost:8501 > /dev/null 2>&1; then
        echo "   ✅ Streamlit is responding on port 8501!"
    else
        echo "   ❌ Streamlit is NOT responding on port 8501"
    fi
else
    echo "   ❌ Streamlit failed to start"
fi

echo ""
echo "5️⃣ Checking dependencies..."
python3 -c "import streamlit; print(f'   ✅ Streamlit version: {streamlit.__version__}')" 2>&1
python3 -c "import requests; print(f'   ✅ Requests version: {requests.__version__}')" 2>&1
python3 -c "import pandas; print(f'   ✅ Pandas version: {pandas.__version__}')" 2>&1

echo ""
echo "=========================================="
echo "🔍 Diagnosis Complete"
echo ""
echo "To view live logs:"
echo "  tail -f /workspace/logs/streamlit.log"
echo ""
echo "To restart Streamlit:"
echo "  pkill -f streamlit"
echo "  cd /workspace/rlvr-automation/ui/streamlit"
echo "  PYTHONPATH=/workspace/rlvr-automation/ui/streamlit:/workspace/rlvr-automation \\"
echo "    nohup streamlit run src/app_simple.py --server.port 8501 --server.headless true --server.address 0.0.0.0 > /workspace/logs/streamlit.log 2>&1 &"
echo ""

