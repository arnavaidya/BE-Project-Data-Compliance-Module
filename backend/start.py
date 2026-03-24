#!/usr/bin/env python3
"""
start.py - Launcher for AI Training-Data Compliance Module
===========================================================
Starts both backend (FastAPI) and frontend (React) in one command.

Usage:
    python start.py
    
    Press Ctrl+C to stop both servers
"""

import os
import sys
import subprocess
import platform
import time
import signal
from pathlib import Path

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(msg):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{msg:^60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_success(msg):
    print(f"{Colors.OKGREEN}✓ {msg}{Colors.ENDC}")

def print_error(msg):
    print(f"{Colors.FAIL}✗ {msg}{Colors.ENDC}")

def print_info(msg):
    print(f"{Colors.OKCYAN}ℹ {msg}{Colors.ENDC}")

def print_warning(msg):
    print(f"{Colors.WARNING}⚠ {msg}{Colors.ENDC}")

# Track running processes
processes = []

def cleanup():
    """Kill all child processes on exit"""
    print_info("Shutting down servers...")
    for proc in processes:
        try:
            if platform.system() == "Windows":
                subprocess.call(['taskkill', '/F', '/T', '/PID', str(proc.pid)], 
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                proc.terminate()
                proc.wait(timeout=3)
        except:
            pass
    print_success("All servers stopped")

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n")
    cleanup()
    sys.exit(0)

# Register signal handler
signal.signal(signal.SIGINT, signal_handler)

def check_python():
    """Verify Python version"""
    print_info("Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print_error(f"Python 3.8+ required, found {version.major}.{version.minor}")
        return False
    print_success(f"Python {version.major}.{version.minor}.{version.micro}")
    return True

def check_node():
    """Verify Node.js is installed"""
    print_info("Checking Node.js...")
    try:
        result = subprocess.run(['node', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version = result.stdout.strip()
            print_success(f"Node.js {version}")
            return True
    except:
        pass
    print_error("Node.js not found - required for frontend")
    print_info("Download from: https://nodejs.org/")
    return False

def check_backend_setup():
    """Check if backend is set up"""
    backend_dir = Path("backend")
    
    if not backend_dir.exists():
        print_error("backend/ directory not found")
        return False
    
    venv_dir = backend_dir / ".venv"
    app_dir = backend_dir / "app"
    
    if not app_dir.exists():
        print_error("backend/app/ directory not found")
        return False
    
    if not venv_dir.exists():
        print_warning("Virtual environment not found")
        print_info("Creating virtual environment...")
        try:
            subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], 
                         check=True, cwd=str(backend_dir))
            print_success("Virtual environment created")
        except:
            print_error("Failed to create virtual environment")
            return False
    
    # Check if dependencies are installed
    if platform.system() == "Windows":
        pip_path = venv_dir / "Scripts" / "pip.exe"
        python_path = venv_dir / "Scripts" / "python.exe"
    else:
        pip_path = venv_dir / "bin" / "pip"
        python_path = venv_dir / "bin" / "python"
    
    if not pip_path.exists():
        print_error("pip not found in virtual environment")
        return False
    
    # Try to import fastapi to check if dependencies are installed
    result = subprocess.run(
        [str(python_path), "-c", "import fastapi"],
        capture_output=True, timeout=5
    )
    
    if result.returncode != 0:
        print_warning("Backend dependencies not installed")
        print_info("Installing dependencies...")
        try:
            subprocess.run([str(pip_path), "install", "-r", "requirements.txt"],
                         check=True, cwd=str(backend_dir))
            print_success("Dependencies installed")
        except:
            print_error("Failed to install dependencies")
            return False
    
    print_success("Backend setup OK")
    return True

def check_frontend_setup():
    """Check if frontend is set up"""
    frontend_dir = Path("frontend")
    
    if not frontend_dir.exists():
        print_error("frontend/ directory not found")
        print_info("Run: npx create-react-app frontend")
        return False
    
    package_json = frontend_dir / "package.json"
    node_modules = frontend_dir / "node_modules"
    
    if not package_json.exists():
        print_error("frontend/package.json not found")
        print_info("Frontend not initialized")
        return False
    
    # Check if it's Create React App or Vite
    with open(package_json, 'r') as f:
        content = f.read()
        is_vite = '"vite"' in content or '"dev": "vite"' in content
        is_cra = '"react-scripts"' in content or '"start": "react-scripts start"' in content
    
    if not is_vite and not is_cra:
        print_error("Unknown React setup - expecting Create React App or Vite")
        return False
    
    if not node_modules.exists():
        print_warning("Node modules not installed")
        print_info("Installing npm dependencies...")
        try:
            subprocess.run(['npm', 'install'], check=True, cwd=str(frontend_dir))
            print_success("Dependencies installed")
        except:
            print_error("Failed to install npm dependencies")
            return False
    
    # Check if recharts is installed
    recharts_dir = node_modules / "recharts"
    if not recharts_dir.exists():
        print_warning("recharts not installed")
        print_info("Installing recharts...")
        try:
            subprocess.run(['npm', 'install', 'recharts'], 
                         check=True, cwd=str(frontend_dir))
            print_success("recharts installed")
        except:
            print_error("Failed to install recharts")
            return False
    
    print_success("Frontend setup OK")
    return True

def start_backend():
    """Start the FastAPI backend"""
    print_info("Starting backend server...")
    backend_dir = Path("backend")
    
    if platform.system() == "Windows":
        python_path = backend_dir / ".venv" / "Scripts" / "python.exe"
        uvicorn_path = backend_dir / ".venv" / "Scripts" / "uvicorn.exe"
    else:
        python_path = backend_dir / ".venv" / "bin" / "python"
        uvicorn_path = backend_dir / ".venv" / "bin" / "uvicorn"
    
    try:
        # Start uvicorn
        proc = subprocess.Popen(
            [str(uvicorn_path), "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"],
            cwd=str(backend_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        processes.append(proc)
        
        # Wait for backend to be ready
        print_info("Waiting for backend to start...")
        max_wait = 10
        for i in range(max_wait):
            try:
                import urllib.request
                response = urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=1)
                if response.status == 200:
                    print_success("Backend running at http://127.0.0.1:8000")
                    print_info("API docs available at http://127.0.0.1:8000/docs")
                    return True
            except:
                time.sleep(1)
        
        print_warning("Backend may still be starting...")
        return True
        
    except Exception as e:
        print_error(f"Failed to start backend: {e}")
        return False

def start_frontend():
    """Start the React frontend"""
    print_info("Starting frontend server...")
    frontend_dir = Path("frontend")
    
    # Determine which command to use (Create React App vs Vite)
    package_json = frontend_dir / "package.json"
    with open(package_json, 'r') as f:
        content = f.read()
        is_vite = '"vite"' in content
    
    try:
        # Use appropriate command based on setup
        if is_vite:
            cmd = ['npm', 'run', 'dev']
            expected_port = 5173
        else:
            cmd = ['npm', 'start']
            expected_port = 3000
        
        # On Windows, wrap in cmd /c to ensure npm is found
        if platform.system() == "Windows":
            cmd = ['cmd', '/c'] + cmd
        
        # Set environment to suppress browser auto-open for CRA
        env = os.environ.copy()
        env['BROWSER'] = 'none'
        
        proc = subprocess.Popen(
            cmd,
            cwd=str(frontend_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env
        )
        processes.append(proc)
        
        # Wait for frontend to be ready
        print_info("Waiting for frontend to start...")
        time.sleep(5)  # Give it time to compile
        
        print_success(f"Frontend running at http://localhost:{expected_port}")
        return True
        
    except Exception as e:
        print_error(f"Failed to start frontend: {e}")
        return False

def main():
    """Main entry point"""
    print_header("AI Training-Data Compliance Module Launcher")
    
    # Pre-flight checks
    if not check_python():
        sys.exit(1)
    
    if not check_node():
        sys.exit(1)
    
    if not check_backend_setup():
        print_error("Backend setup incomplete")
        sys.exit(1)
    
    if not check_frontend_setup():
        print_error("Frontend setup incomplete")
        sys.exit(1)
    
    print_header("Starting Servers")
    
    # Start backend
    if not start_backend():
        print_error("Failed to start backend")
        cleanup()
        sys.exit(1)
    
    # Start frontend
    if not start_frontend():
        print_error("Failed to start frontend")
        cleanup()
        sys.exit(1)
    
    # Success - determine frontend URL
    frontend_dir = Path("frontend")
    package_json = frontend_dir / "package.json"
    with open(package_json, 'r') as f:
        content = f.read()
        is_vite = '"vite"' in content
    
    frontend_url = "http://localhost:5173" if is_vite else "http://localhost:3000"
    
    print_header("✓ All Servers Running")
    print(f"{Colors.OKGREEN}Backend:  {Colors.BOLD}http://127.0.0.1:8000{Colors.ENDC}")
    print(f"{Colors.OKGREEN}Frontend: {Colors.BOLD}{frontend_url}{Colors.ENDC}")
    print(f"{Colors.OKGREEN}API Docs: {Colors.BOLD}http://127.0.0.1:8000/docs{Colors.ENDC}\n")
    
    print_info("Press Ctrl+C to stop all servers\n")
    
    # Keep script running and show logs
    try:
        while True:
            time.sleep(1)
            # Check if processes are still running
            for proc in processes:
                if proc.poll() is not None:
                    print_error("A server process has stopped unexpectedly")
                    cleanup()
                    sys.exit(1)
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()

if __name__ == "__main__":
    # Change to script directory
    os.chdir(Path(__file__).parent)
    main()
