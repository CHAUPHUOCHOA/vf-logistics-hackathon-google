"""
VF Logistics Fraud Detection - Main Flask Application
Google Cloud Run deployment with Gemini 2.5 Flash

Track: The Taskmaster - Autonomous Workflow Automation
Hackathon: All Things Agentic 2026
"""

import asyncio
import os
import json
from datetime import datetime
from functools import wraps

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from agents import (
    analyze_shipment,
    batch_analyze,
    screen_shipment,
    screen_entity,
    investigate_case,
    generate_report,
    get_fraud_agent_info,
    get_compliance_agent_info,
    get_investigation_agent_info
)

app = Flask(__name__, static_folder="static", static_url_path="/static")
CORS(app)

# Helper to run async functions in Flask
def async_route(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper


@app.route("/", methods=["GET"])
def index():
    """Serve the web dashboard."""
    return send_from_directory("static", "index.html")


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "VF Logistics Fraud Detection",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "hackathon": "All Things Agentic 2026",
        "track": "The Taskmaster"
    })


@app.route("/agents", methods=["GET"])
def list_agents():
    """List all available agents and their capabilities."""
    return jsonify({
        "agents": [
            get_fraud_agent_info(),
            get_compliance_agent_info(),
            get_investigation_agent_info()
        ]
    })


# ============== FRAUD DETECTION ENDPOINTS ==============

@app.route("/api/v1/fraud/analyze", methods=["POST"])
@async_route
async def fraud_analyze():
    """Analyze a single shipment for fraud indicators."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        result = await analyze_shipment(data)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/v1/fraud/batch", methods=["POST"])
@async_route
async def fraud_batch():
    """Analyze multiple shipments in batch."""
    try:
        data = request.get_json()
        if not data or "shipments" not in data:
            return jsonify({"error": "No shipments provided"}), 400
        
        results = await batch_analyze(data["shipments"])
        return jsonify({
            "results": results,
            "count": len(results)
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============== COMPLIANCE ENDPOINTS ==============

@app.route("/api/v1/compliance/screen", methods=["POST"])
@async_route
async def compliance_screen():
    """Screen a shipment for compliance issues."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        result = await screen_shipment(data)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/v1/compliance/entity", methods=["POST"])
@async_route
async def compliance_entity():
    """Screen an entity for sanctions/compliance."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        result = await screen_entity(data)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============== INVESTIGATION ENDPOINTS ==============

@app.route("/api/v1/investigation/case", methods=["POST"])
@async_route
async def investigation_case():
    """Investigate a flagged case."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        result = await investigate_case(data)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/v1/investigation/report", methods=["POST"])
@async_route
async def investigation_report():
    """Generate consolidated investigation report."""
    try:
        data = request.get_json()
        if not data or "investigations" not in data:
            return jsonify({"error": "No investigations provided"}), 400
        
        result = await generate_report(data["investigations"])
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============== DEMO ENDPOINT ==============

@app.route("/demo", methods=["GET"])
@async_route
async def demo():
    """Demo endpoint with sample shipment analysis."""
    sample_shipment = {
        "shipment_id": "VF-2026-DEMO-001",
        "origin": "Ho Chi Minh City",
        "destination": "Hanoi",
        "weight_kg": 150,
        "declared_value": 50000000,  # 50M VND
        "shipping_cost": 2500000,    # 2.5M VND
        "shipper_name": "Demo Company Ltd",
        "receiver_name": "Sample Receiver Corp",
        "created_at": datetime.utcnow().isoformat(),
        "status": "pending",
        "route_details": "HCMC → Da Nang → Hanoi",
        "avg_route_cost": 3000000,   # 3M VND average
        "shipper_tx_count": 5
    }
    
    result = await analyze_shipment(sample_shipment)
    
    return jsonify({
        "demo": True,
        "sample_shipment": sample_shipment,
        "analysis": result
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
