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

"""FastAPI Web Server serving the interactive Crop Doctor Dashboard.

Features:
- Programmatic execution of the ADK Workflow using InMemoryRunner.
- Side-by-side display of the PII scrubbing & security checkpoint verification.
- Human-in-the-loop modal dialog interaction (Approve/Reject plan).
- Weather risk, seasonal advice, and organic alternatives widget APIs.
"""

import os
import uuid
import json
import logging
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.genai import types

from app.agent import app as adk_app
from app.mcp_server import (
    get_organic_alternatives,
    get_seasonal_advice,
    get_treatment_catalog,
    get_weather_risk,
    lookup_disease,
)

# ---------------------------------------------------------------------------
# Setup Logger
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastAPI App Setup
# ---------------------------------------------------------------------------
app = FastAPI(title="Crop Doctor AI Portal")

# Setup ADK Services & Runner
session_service = InMemorySessionService()
artifact_service = InMemoryArtifactService()
memory_service = InMemoryMemoryService()

runner = Runner(
    app=adk_app,
    session_service=session_service,
    artifact_service=artifact_service,
    memory_service=memory_service,
)

# Keep track of active session inputs in memory for the HITL step
active_runs = {}

# ---------------------------------------------------------------------------
# Request/Response Schemas
# ---------------------------------------------------------------------------
class DiagnosisRequest(BaseModel):
    prompt: str


class HitlRequest(BaseModel):
    session_id: str
    approved: bool


# ---------------------------------------------------------------------------
# Web Dashboard Endpoints
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serves the dashboard home page."""
    html_path = Path(__file__).parent / "templates" / "index.html"
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="Dashboard template not found.")
    return html_path.read_text(encoding="utf-8")


@app.post("/api/diagnose")
async def run_diagnosis(req: DiagnosisRequest):
    """Starts a new Crop Doctor session and runs the workflow."""
    session_id = str(uuid.uuid4())
    user_id = "farmer_user"

    # Create session
    session = await runner.session_service.create_session(
        app_name=adk_app.name,
        user_id=user_id,
        session_id=session_id,
    )

    logger.info("Created session %s", session_id)

    # Prepare inputs
    user_content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=req.prompt)]
    )

    # Stream the workflow run
    hitl_event = None
    cleaned_input = req.prompt
    security_audit = {}
    blocked = False
    blocked_message = ""

    from google.adk.events.request_input import RequestInput

    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=user_content,
        ):
            # Check for PII scrubbing & security logs in state
            state = session.state or {}
            if "cleaned_input" in state:
                cleaned_input = state["cleaned_input"]
            if "security_audit" in state:
                security_audit = state["security_audit"]
            if state.get("security_blocked"):
                blocked = True
                blocked_message = state.get("security_audit", {}).get("checks", [{}])[0].get("action", "blocked")

            # Check if workflow paused for Human review using isinstance
            if isinstance(event, RequestInput) and event.interrupt_id == "farmer_review":
                # The event itself is the RequestInput event
                hitl_event = event
                break

        # Re-fetch session to get final state details
        session = await runner.session_service.get_session(
            app_name=adk_app.name,
            user_id=user_id,
            session_id=session_id,
        )

        state = session.state or {}
        cleaned_input = state.get("cleaned_input", cleaned_input)
        security_audit = state.get("security_audit", security_audit)
        blocked = state.get("security_blocked", blocked)

        if blocked:
            return JSONResponse({
                "status": "blocked",
                "message": "Security Alert: Prompt injection or blacklisted words detected.",
                "security_audit": security_audit
            })

        if hitl_event:
            # Paused for HITL
            return JSONResponse({
                "status": "hitl_pending",
                "session_id": session_id,
                "message": hitl_event.message or "Review the diagnosis plan before proceeding.",
                "cleaned_input": cleaned_input,
                "security_audit": security_audit,
            })

        # Completed directly (though agent.py has farmer_review, so it should hit hitl_pending)
        return JSONResponse({
            "status": "success",
            "session_id": session_id,
            "cleaned_input": cleaned_input,
            "security_audit": security_audit,
            "report": {
                "disease_name": state.get("diagnosis", {}).get("disease_name"),
                "confidence": state.get("diagnosis", {}).get("confidence"),
                "urgency": state.get("diagnosis", {}).get("urgency"),
                "description": state.get("diagnosis", {}).get("description"),
                "treatment_steps": state.get("treatment", {}).get("treatment_steps", []),
                "organic_options": state.get("treatment", {}).get("organic_options", []),
                "prevention_tips": state.get("treatment", {}).get("prevention_tips", []),
            }
        })

    except Exception as e:
        logger.exception("Error during diagnose run:")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/approve")
async def approve_diagnosis(req: HitlRequest):
    """Submits the farmer's decision to resume the paused HITL workflow step."""
    user_id = "farmer_user"

    # Fetch existing session to make sure it exists
    session = await runner.session_service.get_session(
        app_name=adk_app.name,
        user_id=user_id,
        session_id=req.session_id,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Format the resume message as a FunctionResponse
    approved_text = "yes" if req.approved else "no"
    resume_msg = types.Content(
        role="user",
        parts=[
            types.Part(
                function_response=types.FunctionResponse(
                    name="farmer_review",
                    id="farmer_review",
                    response={"farmer_review": approved_text}
                )
            )
        ]
    )

    try:
        # Run workflow again to resume from the review step
        async for event in runner.run_async(
            user_id=user_id,
            session_id=req.session_id,
            new_message=resume_msg,
        ):
            pass

        # Re-fetch session to get final results
        session = await runner.session_service.get_session(
            app_name=adk_app.name,
            user_id=user_id,
            session_id=req.session_id,
        )

        state = session.state or {}

        return JSONResponse({
            "status": "success",
            "session_id": req.session_id,
            "report": {
                "disease_name": state.get("diagnosis", {}).get("disease_name"),
                "confidence": state.get("diagnosis", {}).get("confidence"),
                "urgency": state.get("diagnosis", {}).get("urgency"),
                "description": state.get("diagnosis", {}).get("description"),
                "treatment_steps": state.get("treatment", {}).get("treatment_steps", []),
                "organic_options": state.get("treatment", {}).get("organic_options", []),
                "prevention_tips": state.get("treatment", {}).get("prevention_tips", []),
            }
        })

    except Exception as e:
        logger.exception("Error during HITL resume:")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# MCP Tool Adapter Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/mcp/weather-risk")
async def get_mcp_weather_risk(region: str, season: str):
    """Bridge call directly to weather risk MCP tool."""
    try:
        result_json = get_weather_risk(region, season)
        return JSONResponse(content=json.loads(result_json))
    except Exception as e:
        logger.exception("Error in weather risk MCP call:")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/mcp/seasonal-advice")
async def get_mcp_seasonal_advice(crop: str, region: str):
    """Bridge call directly to seasonal advice MCP tool."""
    try:
        result_json = get_seasonal_advice(region, crop)
        return JSONResponse(content=json.loads(result_json))
    except Exception as e:
        logger.exception("Error in seasonal advice MCP call:")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/mcp/organic-alternatives")
async def get_mcp_organic_alternatives(chemical: str):
    """Bridge call directly to organic alternatives MCP tool."""
    try:
        result_json = get_organic_alternatives(chemical)
        return JSONResponse(content=json.loads(result_json))
    except Exception as e:
        logger.exception("Error in organic alternatives MCP call:")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Start Server Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    logger.info("Starting Crop Doctor Portal on port %d...", port)
    uvicorn.run("app.web_server:app", host="127.0.0.1", port=port, reload=False)
