"""
VF Logistics Fraud Detection Agent - Gemini 2.5 Flash
Migrated from Snowflake Cortex to Google Cloud ADK

Track: The Taskmaster - Autonomous Workflow Automation
Hackathon: All Things Agentic 2026
"""

import os
from datetime import datetime
from typing import Any

from google import genai
from google.genai import types

# Initialize Gemini client
PROJECT_ID = os.getenv("PROJECT_ID", "project-93ded24f-21c3-4f1b-a7d")
LOCATION = os.getenv("LOCATION", "global")

client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location=LOCATION
)

# Model configuration - Gemini 3.5 Flash (hackathon requirement: Gemini 3.5 or newer)
MODEL_ID = "gemini-3.5-flash"

# Fraud detection system prompt
FRAUD_DETECTION_PROMPT = """
You are an expert fraud detection agent for VF Logistics, a major logistics company in Vietnam.

Your role is to analyze shipment data and detect potential fraud patterns including:
1. Price manipulation - unusual discounts, pricing anomalies
2. Route fraud - suspicious route changes, unnecessary detours
3. Weight/dimension fraud - misreported cargo specifications
4. Document fraud - forged or manipulated shipping documents
5. Identity fraud - fake shipper/receiver information
6. Duplicate shipments - same shipment billed multiple times
7. Time fraud - manipulated delivery timestamps

When analyzing a shipment, you should:
1. Check for statistical anomalies compared to normal patterns
2. Verify consistency across related data points
3. Flag high-risk indicators with severity levels (LOW, MEDIUM, HIGH, CRITICAL)
4. Provide clear explanations for each flagged issue
5. Suggest investigation actions

Always respond in a structured JSON format with:
- risk_score: 0-100 indicating overall fraud risk
- risk_level: LOW/MEDIUM/HIGH/CRITICAL
- flags: array of detected issues
- recommendations: suggested actions
- confidence: your confidence in the assessment (0-1)
"""

async def analyze_shipment(shipment_data: dict[str, Any]) -> dict[str, Any]:
    """
    Analyze a single shipment for fraud indicators using Gemini 2.5 Flash.
    
    Args:
        shipment_data: Dictionary containing shipment details
        
    Returns:
        Fraud analysis results with risk score and recommendations
    """
    # Format shipment data for analysis
    shipment_text = f"""
    Shipment ID: {shipment_data.get('shipment_id', 'N/A')}
    Origin: {shipment_data.get('origin', 'N/A')}
    Destination: {shipment_data.get('destination', 'N/A')}
    Weight (kg): {shipment_data.get('weight_kg', 'N/A')}
    Declared Value: {shipment_data.get('declared_value', 'N/A')} VND
    Shipping Cost: {shipment_data.get('shipping_cost', 'N/A')} VND
    Shipper: {shipment_data.get('shipper_name', 'N/A')}
    Receiver: {shipment_data.get('receiver_name', 'N/A')}
    Created: {shipment_data.get('created_at', 'N/A')}
    Status: {shipment_data.get('status', 'N/A')}
    Route: {shipment_data.get('route_details', 'N/A')}
    Historical Average Cost: {shipment_data.get('avg_route_cost', 'N/A')} VND
    Shipper Transaction Count: {shipment_data.get('shipper_tx_count', 'N/A')}
    """
    
    response = await client.aio.models.generate_content(
        model=MODEL_ID,
        contents=[
            types.Content(
                role="user",
                parts=[types.Part(text=f"Analyze this shipment for fraud:\n{shipment_text}")]
            )
        ],
        config=types.GenerateContentConfig(
            system_instruction=FRAUD_DETECTION_PROMPT,
            temperature=0.1,  # Low temperature for consistent analysis
            response_mime_type="application/json",
        )
    )
    
    return {
        "shipment_id": shipment_data.get("shipment_id"),
        "analysis": response.text,
        "model": MODEL_ID,
        "analyzed_at": datetime.utcnow().isoformat()
    }


async def batch_analyze(shipments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Analyze multiple shipments in batch.
    """
    results = []
    for shipment in shipments:
        result = await analyze_shipment(shipment)
        results.append(result)
    return results


def get_agent_info() -> dict[str, str]:
    """Return agent metadata."""
    return {
        "name": "VF Logistics Fraud Detection Agent",
        "version": "1.0.0",
        "model": MODEL_ID,
        "project": PROJECT_ID,
        "location": LOCATION,
        "capabilities": [
            "shipment_fraud_detection",
            "price_anomaly_detection",
            "route_fraud_detection",
            "document_verification",
            "batch_analysis"
        ]
    }
