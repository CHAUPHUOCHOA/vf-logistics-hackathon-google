"""
VF Logistics Compliance Screening Agent - Gemini 2.5 Flash
Verifies shipments against sanctions lists, trade regulations, and compliance rules.

Track: The Taskmaster - Autonomous Workflow Automation
"""

import os
from datetime import datetime
from typing import Any

from google import genai
from google.genai import types

PROJECT_ID = os.getenv("PROJECT_ID", "project-93ded24f-21c3-4f1b-a7d")
LOCATION = os.getenv("LOCATION", "global")

client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location=LOCATION
)

MODEL_ID = "gemini-3.5-flash"

COMPLIANCE_PROMPT = """
You are a compliance screening agent for VF Logistics, specializing in:

1. SANCTIONS SCREENING
   - Check shipper/receiver names against known sanctions lists (OFAC, UN, EU)
   - Flag high-risk countries and regions
   - Identify potential shell companies or aliases

2. TRADE COMPLIANCE
   - Verify export/import restrictions for goods categories
   - Check dual-use goods regulations
   - Validate customs documentation requirements

3. REGULATORY COMPLIANCE
   - Verify dangerous goods classifications
   - Check packaging and labeling requirements
   - Validate carrier certifications

4. AML (Anti-Money Laundering)
   - Detect suspicious transaction patterns
   - Flag unusual payment methods
   - Identify structuring attempts

When screening, output JSON with:
- compliance_status: CLEARED/REVIEW_REQUIRED/BLOCKED
- risk_factors: array of identified concerns
- sanctions_hits: any potential sanctions matches
- regulatory_issues: compliance gaps found
- required_actions: steps needed for clearance
- confidence: screening confidence (0-1)
"""


async def screen_shipment(shipment_data: dict[str, Any]) -> dict[str, Any]:
    """
    Screen a shipment for compliance issues.
    """
    screening_text = f"""
    Shipment ID: {shipment_data.get('shipment_id', 'N/A')}
    
    SHIPPER DETAILS:
    - Name: {shipment_data.get('shipper_name', 'N/A')}
    - Company: {shipment_data.get('shipper_company', 'N/A')}
    - Country: {shipment_data.get('shipper_country', 'N/A')}
    - Tax ID: {shipment_data.get('shipper_tax_id', 'N/A')}
    
    RECEIVER DETAILS:
    - Name: {shipment_data.get('receiver_name', 'N/A')}
    - Company: {shipment_data.get('receiver_company', 'N/A')}
    - Country: {shipment_data.get('receiver_country', 'N/A')}
    
    CARGO DETAILS:
    - Description: {shipment_data.get('cargo_description', 'N/A')}
    - HS Code: {shipment_data.get('hs_code', 'N/A')}
    - Value: {shipment_data.get('declared_value', 'N/A')} VND
    - Weight: {shipment_data.get('weight_kg', 'N/A')} kg
    
    ROUTE:
    - Origin: {shipment_data.get('origin', 'N/A')}
    - Destination: {shipment_data.get('destination', 'N/A')}
    - Transit Points: {shipment_data.get('transit_points', 'N/A')}
    """
    
    response = await client.aio.models.generate_content(
        model=MODEL_ID,
        contents=[
            types.Content(
                role="user",
                parts=[types.Part(text=f"Screen this shipment for compliance:\n{screening_text}")]
            )
        ],
        config=types.GenerateContentConfig(
            system_instruction=COMPLIANCE_PROMPT,
            temperature=0.1,
            response_mime_type="application/json",
        )
    )
    
    return {
        "shipment_id": shipment_data.get("shipment_id"),
        "screening_result": response.text,
        "model": MODEL_ID,
        "screened_at": datetime.utcnow().isoformat()
    }


async def screen_entity(entity_data: dict[str, Any]) -> dict[str, Any]:
    """
    Screen a specific entity (shipper/receiver) for sanctions.
    """
    entity_text = f"""
    Entity Name: {entity_data.get('name', 'N/A')}
    Company: {entity_data.get('company', 'N/A')}
    Country: {entity_data.get('country', 'N/A')}
    Tax ID: {entity_data.get('tax_id', 'N/A')}
    Known Aliases: {entity_data.get('aliases', 'N/A')}
    Previous Transactions: {entity_data.get('transaction_count', 'N/A')}
    """
    
    response = await client.aio.models.generate_content(
        model=MODEL_ID,
        contents=[
            types.Content(
                role="user",
                parts=[types.Part(text=f"Screen this entity for sanctions and compliance:\n{entity_text}")]
            )
        ],
        config=types.GenerateContentConfig(
            system_instruction=COMPLIANCE_PROMPT,
            temperature=0.1,
            response_mime_type="application/json",
        )
    )
    
    return {
        "entity_name": entity_data.get("name"),
        "screening_result": response.text,
        "screened_at": datetime.utcnow().isoformat()
    }


def get_agent_info() -> dict[str, str]:
    """Return agent metadata."""
    return {
        "name": "VF Logistics Compliance Screening Agent",
        "version": "1.0.0",
        "model": MODEL_ID,
        "capabilities": [
            "sanctions_screening",
            "trade_compliance",
            "regulatory_compliance",
            "aml_detection",
            "entity_screening"
        ]
    }
