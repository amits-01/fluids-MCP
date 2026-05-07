@echo off
echo Starting Fluids MCP Platform...
echo.

:: Activate virtual environment
call venv\Scripts\activate

:: Start leaf servers in background
echo Starting Generation Leaf Server on port 8002...
start "Generation Leaf" cmd /k "uvicorn leaf_servers.generation.main:app --host 0.0.0.0 --port 8002"

echo Starting Validation Leaf Server on port 8003...
start "Validation Leaf" cmd /k "uvicorn leaf_servers.validation.main:app --host 0.0.0.0 --port 8003"

:: Wait for leaf servers to start before sub-orchestrator
echo Waiting for leaf servers to start...
timeout /t 3 /nobreak > nul

:: Start sub-orchestrator
echo Starting Fluids Sub-orchestrator on port 8001...
start "Fluids Sub-orchestrator" cmd /k "uvicorn sub_orchestrators.fluids.main:app --host 0.0.0.0 --port 8001"

:: Wait for sub-orchestrator before orchestrator
echo Waiting for sub-orchestrator to start...
timeout /t 3 /nobreak > nul

:: Start top-level orchestrator last
echo Starting Top-level Orchestrator on port 8000...
start "Top-level Orchestrator" cmd /k "uvicorn orchestrator.main:app --host 0.0.0.0 --port 8000"

echo.
echo All services starting...
echo.
echo Orchestrator:        http://localhost:8000
echo Chat UI:             http://localhost:8000
echo Sub-orchestrator:    http://localhost:8001
echo Generation Leaf:     http://localhost:8002
echo Validation Leaf:     http://localhost:8003
echo.
echo Open http://localhost:8000 in your browser to start chatting.
pause