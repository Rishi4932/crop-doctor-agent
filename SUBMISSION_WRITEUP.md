# Submission Write-Up: Crop Doctor AI

## Problem Statement
Small-to-medium-scale farmers often lack immediate access to agricultural experts or pathologists when their crops show signs of disease. Delayed diagnosis can turn a minor, preventable plant infection into a widespread crop failure, resulting in severe economic loss. 

Crop Doctor AI bridges this gap by offering a secure, real-time multi-agent portal. It analyzes symptom descriptions, identifies diseases, references local weather indices, and issues custom organic/chemical recovery roadmaps.

---

## Solution Architecture

The application is powered by a multi-agent workflow graph built on the **Gemini ADK 2.0** framework:

```
[START] ──> Intake Node ──> Security Checkpoint 
                                   │
                     ┌─────────────┴─────────────┐
                     ▼ (SAFE)                    ▼ (SECURITY_EVENT)
              Diagnosis Agent              Final Output (Blocked)
                     │
                     ▼
              Treatment Agent
                     │
                     ▼
             Farmer Review (HITL)
                     │
                     ▼
                Final Output (Report) ──> [END]
```

### Core Components
* **Intake Node (`app/agent.py`)**: Gathers the crop type, farming region, season, symptoms, and farmer contact info.
* **Security Checkpoint Node (`app/agent.py`)**: An automated guardrail ensuring compliance. It scrubs PII and intercepts prompt injections or unsafe keywords.
* **Diagnosis Agent (`app/agent.py`)**: An `LlmAgent` that correlates farmer symptoms with the plant disease database via local MCP tools.
* **Treatment Agent (`app/agent.py`)**: An `LlmAgent` tasked with compiling actionable natural cures and safe chemical instructions.
* **Human-in-the-Loop (`app/agent.py` & `app/web_server.py`)**: Uses `RequestInput` to pause execution, allowing farmers to confirm or cancel the treatment plan.
* **Local MCP Server (`app/mcp_server.py`)**: Exposes live tool adapters for disease lookups, weather risk calculation, crop advice catalogs, and chemical-to-organic alternatives.

---

## Security Design

To protect farmer data and system integrity, we implement a layered defense at the **Security Checkpoint**:
1. **PII Redaction**: Regex-based automatic redaction of emails, phone numbers, Aadhaar details, and GPS coordinates.
2. **Prompt Injection Mitigation**: Scans user prompts against injection keywords (e.g., "ignore previous instructions") and redirects threats to a dedicated security exception route.
3. **Agricultural Domain Filter**: A safety scanner that filters out non-agricultural or hazardous terms, logging structured JSON audits of all decisions.

---

## MCP Server Design

The Model Context Protocol (MCP) server runs alongside the agent and exposes 5 tools:
* `lookup_disease`: Returns full descriptions, symptoms, and contagious parameters.
* `get_treatment_catalog`: Returns treatment steps and recovery timelines.
* `get_weather_risk`: Examines region & season temperature/humidity conditions to calculate threat indexes.
* `get_seasonal_advice`: Issues watering, spacing, and crop catalog checklists.
* `get_organic_alternatives`: Recommends eco-friendly replacements for chemical pesticides.

---

## Impact / Value Statement
By integrating local database lookups, live risk indices, and multi-agent reasoning, Crop Doctor AI provides high-fidelity, immediate agricultural expertise. The emphasis on organic alternatives promotes sustainable farming practices, while the robust security guardrails ensure safe deployment.
