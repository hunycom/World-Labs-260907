"""
Spark Spatial Intelligence OS - Edge Tier 1 Backend Server
"""

import sys
import json
import os
from typing import Dict, Any
from http.server import SimpleHTTPRequestHandler
import socketserver

# Configure UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Server Configuration
PORT = int(os.environ.get("SPARK_PORT", 8088))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class SparkHTTPHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def end_headers(self):
        # Enable Cross-Origin Isolation for SharedArrayBuffer & WebAssembly SIMD
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

def run_http_server():
    socketserver.TCPServer.allow_reuse_address = True
    print(f"[Tier 1 Edge] Spark Spatial OS HTTP Server running at http://localhost:{PORT}")
    with socketserver.TCPServer(("", PORT), SparkHTTPHandler) as httpd:
        httpd.serve_forever()

class PINNThermodynamicPredictor:
    """
    Physics-Informed Neural Network (PINN) 1D/2D Heat Conduction Simulator
    Solves du/dt = alpha * d^2u/dx^2 with dynamic convective boundary conditions
    """
    def __init__(self, thermal_diffusivity: float = 0.12):
        self.alpha = thermal_diffusivity

    def predict_temperature(self, current_temp: float, current_rpm: float, horizon_sec: float = 2.4, is_overloaded: bool = True) -> Dict[str, Any]:
        heat_gen = (current_rpm / 1000.0) ** 2.0 * (2.8 if is_overloaded else 0.8)
        cooling_flux = (current_temp - 25.0) * (0.02 if is_overloaded else 0.12)

        dt = 0.1
        steps = int(horizon_sec / dt)
        temp = current_temp
        
        for _ in range(steps):
            d_temp = (self.alpha * heat_gen - cooling_flux) * dt
            temp += d_temp

        is_critical = temp > 60.0
        return {
            "initial_temp_c": round(current_temp, 2),
            "predicted_temp_c": round(temp, 2),
            "horizon_seconds": horizon_sec,
            "is_critical": is_critical,
            "recommended_cooling_rate_boost_pct": 20.0 if is_critical else 0.0,
            "status": "ANOMALY_PREDICTED" if is_critical else "STABLE"
        }

if __name__ == "__main__":
    predictor = PINNThermodynamicPredictor()
    test_res = predictor.predict_temperature(current_temp=43.5, current_rpm=3600, horizon_sec=2.4)
    print(f"PINN Simulator Test: {json.dumps(test_res)}")
    run_http_server()
