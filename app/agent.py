# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Crop Doctor Agent — Multi-agent plant health diagnosis system.

Workflow: intake → security_checkpoint → diagnosis → treatment → human_review → final_output
"""

import json
import re
import logging
from datetime import datetime, timezone

from google.adk.agents import LlmAgent
from google.adk.agents.context import Context
from google.adk.apps import App
from google.adk.events.event import Event
from google.adk.events.request_input import RequestInput
from google.adk.tools import MCPToolset
from mcp import StdioServerParameters
from google.adk.workflow import Workflow
from google.genai import types
from pydantic import BaseModel

from .config import config

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------

class SymptomReport(BaseModel):
    plant_name: str
    symptoms: list[str]
    growth_stage: str
    location_region: str
    severity: str  # mild, moderate, severe


class DiagnosisResult(BaseModel):
    disease_name: str
    confidence: str  # high, medium, low
    description: str
    affected_parts: list[str]
    is_contagious: bool
    urgency: str  # low, medium, high, critical


class TreatmentPlan(BaseModel):
    treatment_steps: list[str]
    organic_options: list[str]
    chemical_options: list[str]
    prevention_tips: list[str]
    estimated_recovery_days: int
    follow_up_actions: list[str]


# ---------------------------------------------------------------------------
# MCP Toolset (connected to mcp_server.py)
# ---------------------------------------------------------------------------

mcp_tools = MCPToolset(
    connection_params=StdioServerParameters(
        command="uv",
        args=["run", "python", "-m", "app.mcp_server"],
    ),
)

# ---------------------------------------------------------------------------
# Sub-Agents (LlmAgent)
# ---------------------------------------------------------------------------

diagnosis_agent = LlmAgent(
    name="diagnosis_agent",
    model=config.model,
    instruction="""You are an expert plant pathologist AI. Your job is to diagnose plant diseases.

Given the farmer's description of their plant's symptoms, you MUST:
1. Identify the most likely disease or condition
2. Assess confidence level (high/medium/low)
3. Describe the disease and its progression
4. List affected plant parts
5. Determine if the disease is contagious to nearby plants
6. Rate urgency (low/medium/high/critical)

Use the MCP tools available to you:
- lookup_disease: Search the plant disease database for matching conditions
- get_weather_risk: Check if current weather conditions favor disease spread

Be specific and evidence-based. If symptoms are ambiguous, state the top 2 possibilities.
Always respond with structured diagnosis data.""",
    output_schema=DiagnosisResult,
    output_key="diagnosis",
    tools=[mcp_tools],
)

treatment_agent = LlmAgent(
    name="treatment_agent",
    model=config.model,
    instruction="""You are an agricultural treatment specialist AI. Your job is to recommend treatments for plant diseases.

Given a diagnosis, you MUST provide:
1. Step-by-step treatment instructions (practical for small/medium farmers)
2. Organic/natural treatment options (neem oil, baking soda, crop rotation, etc.)
3. Chemical treatment options (fungicides, pesticides — with safety warnings)
4. Prevention tips to avoid recurrence
5. Estimated recovery timeline in days
6. Follow-up actions the farmer should take

Use the MCP tools available to you:
- get_treatment_catalog: Look up recommended treatments for the diagnosed disease
- get_seasonal_advice: Get season-specific farming advice for the region

Prioritize organic options. Always warn about chemical safety.
Keep language simple — farmers may not have technical backgrounds.""",
    output_schema=TreatmentPlan,
    output_key="treatment",
    tools=[mcp_tools],
)


# ---------------------------------------------------------------------------
# Function Nodes
# ---------------------------------------------------------------------------

def intake(ctx: Context, node_input: types.Content) -> str:
    """Parse user input and store in state."""
    user_text = ""
    if node_input and node_input.parts:
        user_text = node_input.parts[0].text or ""

    ctx.state["user_input"] = user_text
    ctx.state["timestamp"] = datetime.now(timezone.utc).isoformat()
    return user_text


def security_checkpoint(ctx: Context, node_input: str):
    """Security gate: PII scrubbing, prompt injection detection, audit logging."""
    audit_log = {
        "timestamp": ctx.state.get("timestamp", datetime.now(timezone.utc).isoformat()),
        "node": "security_checkpoint",
        "checks": [],
    }

    cleaned_text = node_input
    pii_found = False
    injection_found = False

    # --- PII Scrubbing ---
    if config.pii_redaction_enabled:
        pii_patterns = {
            "phone": r"\b(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "aadhaar": r"\b\d{4}\s?\d{4}\s?\d{4}\b",
            "gps_coordinates": r"\b-?\d{1,3}\.\d{4,},\s*-?\d{1,3}\.\d{4,}\b",
            "bank_account": r"\b\d{9,18}\b(?=.*(?:account|bank|ifsc))",
        }

        for pii_type, pattern in pii_patterns.items():
            matches = re.findall(pattern, cleaned_text, re.IGNORECASE)
            if matches:
                pii_found = True
                cleaned_text = re.sub(pattern, f"[{pii_type.upper()}_REDACTED]", cleaned_text, flags=re.IGNORECASE)
                audit_log["checks"].append({
                    "type": "pii_scrub",
                    "pii_type": pii_type,
                    "count": len(matches),
                    "severity": "WARNING",
                    "action": "redacted",
                })

    # --- Prompt Injection Detection ---
    if config.injection_detection_enabled:
        injection_keywords = [
            "ignore previous instructions",
            "ignore all instructions",
            "system prompt",
            "you are now",
            "forget everything",
            "disregard",
            "override",
            "act as admin",
            "reveal your prompt",
            "bypass security",
        ]

        input_lower = cleaned_text.lower()
        for keyword in injection_keywords:
            if keyword in input_lower:
                injection_found = True
                audit_log["checks"].append({
                    "type": "injection_detect",
                    "keyword": keyword,
                    "severity": "CRITICAL",
                    "action": "blocked",
                })

    # --- Domain-Specific: Agricultural Content Filter ---
    non_agricultural_keywords = [
        "hack", "exploit", "weapon", "bomb", "illegal",
        "narcotic", "drug synthesis", "poison human",
    ]

    for keyword in non_agricultural_keywords:
        if keyword in cleaned_text.lower():
            injection_found = True
            audit_log["checks"].append({
                "type": "content_filter",
                "keyword": keyword,
                "severity": "CRITICAL",
                "action": "blocked",
            })

    # --- Audit Log ---
    if not audit_log["checks"]:
        audit_log["checks"].append({
            "type": "all_clear",
            "severity": "INFO",
            "action": "passed",
        })

    logger.info("SECURITY_AUDIT: %s", json.dumps(audit_log))

    if injection_found:
        return Event(
            output="I'm sorry, but I can only help with plant health and agricultural questions. "
                   "Your request has been flagged by our security system. "
                   "Please describe your plant's symptoms and I'll be happy to help!",
            route="SECURITY_EVENT",
            state={"security_audit": audit_log, "security_blocked": True},
        )

    return Event(
        output=cleaned_text,
        route="SAFE",
        state={
            "security_audit": audit_log,
            "security_blocked": False,
            "pii_detected": pii_found,
            "cleaned_input": cleaned_text,
        },
    )


async def human_review(ctx: Context, node_input: dict):
    """Human-in-the-loop: let the farmer review the diagnosis before treatment is applied.

    NOTE: Uses RequestInput for HITL pause, then resumes via resume_inputs.
    This is an async function (not a generator) — avoids contextvars issues.
    """
    diagnosis = ctx.state.get("diagnosis", {})
    treatment = ctx.state.get("treatment", {})

    disease_name = diagnosis.get("disease_name", "Unknown")
    confidence = diagnosis.get("confidence", "unknown")
    urgency = diagnosis.get("urgency", "unknown")
    steps = treatment.get("treatment_steps", [])

    summary = (
        f"🌿 Diagnosis: {disease_name}\n"
        f"   Confidence: {confidence} | Urgency: {urgency}\n\n"
        f"💊 Recommended Treatment:\n"
    )
    for i, step in enumerate(steps, 1):
        summary += f"   {i}. {step}\n"

    summary += (
        "\nDo you want to proceed with this treatment plan?\n"
        "Reply yes to confirm, or no to cancel."
    )

    if not ctx.resume_inputs:
        # Pause the workflow and wait for farmer response
        return RequestInput(
            interrupt_id="farmer_review",
            message=summary,
        )

    farmer_response = ctx.resume_inputs.get("farmer_review", "yes")
    farmer_text = farmer_response if isinstance(farmer_response, str) else "yes"
    approved = "yes" in farmer_text.lower()
    ctx.state["farmer_approved"] = approved
    return Event(
        output={"approved": approved, "farmer_feedback": farmer_text},
        state={"farmer_approved": approved},
    )


def final_output(ctx: Context, node_input):
    """Format the final response and store in state for the web server to read.

    NOTE: Plain sync function — no yield/generator to avoid contextvars issues.
    The web_server reads diagnosis/treatment directly from ctx.state.
    """
    blocked = ctx.state.get("security_blocked", False)

    if blocked:
        msg = str(node_input) if node_input else "Request blocked by security."
        ctx.state["final_response"] = msg
        return Event(
            output=msg,
            state={"final_response": msg},
        )

    diagnosis = ctx.state.get("diagnosis", {})
    treatment = ctx.state.get("treatment", {})
    farmer_approved = ctx.state.get("farmer_approved", True)

    disease = diagnosis.get("disease_name", "Unknown condition")
    confidence = diagnosis.get("confidence", "N/A")
    description = diagnosis.get("description", "")
    urgency = diagnosis.get("urgency", "N/A")
    contagious = diagnosis.get("is_contagious", False)
    steps = treatment.get("treatment_steps", [])
    organic = treatment.get("organic_options", [])
    prevention = treatment.get("prevention_tips", [])
    recovery = treatment.get("estimated_recovery_days", 0)

    lines = []
    lines.append(f"Crop Doctor Report")
    lines.append(f"Diagnosis: {disease}")
    lines.append(f"Confidence: {confidence} | Urgency: {urgency}")
    lines.append(f"Contagious: {'Yes - isolate affected plants!' if contagious else 'No'}")
    lines.append(f"Description: {description}")
    lines.append(f"Treatment Plan ({'Farmer Approved' if farmer_approved else 'Pending Review'}):")
    for i, step in enumerate(steps, 1):
        lines.append(f"  {i}. {step}")
    if organic:
        lines.append("Organic Options:")
        for opt in organic:
            lines.append(f"  - {opt}")
    if prevention:
        lines.append("Prevention Tips:")
        for tip in prevention:
            lines.append(f"  - {tip}")
    if recovery:
        lines.append(f"Estimated Recovery: {recovery} days")
    lines.append("Stay safe and happy farming!")

    response = "\n".join(lines)
    ctx.state["final_response"] = response

    return Event(
        output=response,
        state={"final_response": response},
    )


# ---------------------------------------------------------------------------
# Workflow Graph
# ---------------------------------------------------------------------------

root_agent = Workflow(
    name="crop_doctor",
    description="AI-powered plant health diagnosis and treatment recommendation system for farmers.",
    edges=[
        # Entry: parse user input
        ("START", intake, security_checkpoint),
        # Security gate conditional routing
        (security_checkpoint, {"SAFE": diagnosis_agent, "SECURITY_EVENT": final_output}),
        # Safe path: diagnose → treat → review → output
        (diagnosis_agent, treatment_agent, human_review, final_output),
    ],
)

app = App(
    root_agent=root_agent,
    name="crop_doctor_agent",
)
