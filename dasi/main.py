import os
import re
import yaml
import json
import logging
import asyncio
import aiofiles
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, BackgroundTasks, status
from pydantic import BaseModel
from huggingface_hub import AsyncInferenceClient

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - [%(levelname)s] - [CORE-KNL] - %(message)s"
)
logger = logging.getLogger("D-ASI-Kernel")

app = FastAPI(title="D-ASI Kernel", version="4.0.0-ENTERPRISE")

MANIFEST_FILENAME = "agent_manifest.yaml"
TRANSACTION_LOG_PATH = "/tmp/dasi_transaction.log"

# Compile regex structures globally to prevent processing thread blockages
MANIFEST_DATA = yaml.safe_load(open(MANIFEST_FILENAME, "r"))
SECURITY_POLICIES = MANIFEST_DATA.get("security_policies", [])
COMPILED_POLICIES = [re.compile(p["regex_pattern"]) for p in SECURITY_POLICIES if "regex_pattern" in p]

# Atomic memory registry to maximize read/write performance
SYSTEM_STATE_LOCK = asyncio.Lock()
LIVE_IN_MEMORY_STATE = {
    "engine_status": "ONLINE",
    "current_step": 0,
    "matrix_context": {},
    "telemetry_stream": []
}

# Automatically initialize AsyncInferenceClient using local env tokens
hf_token = os.environ.get("HF_TOKEN", None)
inference_client = AsyncInferenceClient(token=hf_token)

class InputDirective(BaseModel):
    directive: str

async def write_transaction_entry(log_entry: Dict[str, Any]):
    """Appends atomic state steps to a fast transactional append-only log on disk."""
    async with aiofiles.open(TRANSACTION_LOG_PATH, mode="a") as f:
        await f.write(json.dumps(log_entry) + "\n")

def execute_regex_verification(content: str) -> bool:
    """Uses pre-compiled regular expressions to defend the execution loop against placeholders."""
    for pattern in COMPILED_POLICIES:
        if pattern.search(content):
            return False
    return True

async def dispatch_inference_stream(system_prompt: str, user_prompt: str, manifest: Dict[str, Any]) -> str:
    """Routes requests to verified high-density cloud-scale open weights models with exponential backoff."""
    ops = manifest["operational_profile"]
    selected_model = ops["primary_llm"]

    for attempt in range(int(ops["circuit_breaker_threshold"])):
        try:
            response = await inference_client.chat.completions.create(
                model=selected_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=ops["temperature"],
                max_tokens=ops["max_token_budget"]
            )
            return response.choices[0].message.content
        except Exception as ex:
            logger.error(f"Inference pipeline route failure on model {selected_model}: {str(ex)}")
            selected_model = ops["fallback_llm"]
            # Exponential backoff mechanism with linear incremental delay tracking
            await asyncio.sleep((2.0 ** attempt) + 0.5)

    return "CRITICAL_SYSTEM_ERROR: Base LLM abstraction tier unresponsive."

async def process_matrix_trajectory(input_directive: str):
    """Executes the VHLL Directed Acyclic Graph directly within locked memory registers."""
    global LIVE_IN_MEMORY_STATE
    manifest = MANIFEST_DATA
    agents = {a["id"]: a for a in manifest["swarm_matrix"]["agents"]}
    sequence = manifest["topology_map"]["execution_sequence"]

    async with SYSTEM_STATE_LOCK:
        LIVE_IN_MEMORY_STATE["engine_status"] = "PROCESSING"
        LIVE_IN_MEMORY_STATE["matrix_context"]["root_directive"] = input_directive

    active_payload_stream = input_directive

    for stage in sequence:
        step_number = stage["step"]
        node_id = stage["node"]
        destination_register = stage["register_destination"]

        agent_config = agents[node_id]
        system_directive = agent_config["system_prompt"] + "\nSTRICT RULE: Output complete system configurations. Zero placeholders allowed."

        loop_retries = 0
        is_valid = False
        computed_output = ""

        while loop_retries < 3 and not is_valid:
            async with SYSTEM_STATE_LOCK:
                current_context_snapshot = json.dumps(LIVE_IN_MEMORY_STATE["matrix_context"])

            computed_output = await dispatch_inference_stream(
                system_prompt=system_directive,
                user_prompt=f"System Snapshot Matrix:\n{current_context_snapshot}\n\nPipeline Active Value:\n{active_payload_stream}",
                manifest=manifest
            )

            is_valid = execute_regex_verification(computed_output)
            if not is_valid:
                loop_retries += 1
                active_payload_stream += "\n\nCRITICAL ENFORCEMENT ERROR: Previous output contained placeholders or omissions. You must re-output the entire asset without abbreviations."
            else:
                break

        if not is_valid:
            async with SYSTEM_STATE_LOCK:
                LIVE_IN_MEMORY_STATE["engine_status"] = "HALTED_ON_SECURITY_VIOLATION"
            await write_transaction_entry({"event": "PIPELINE_ABORTED", "node": node_id, "reason": "Placeholder policy breach"})
            return

        async with SYSTEM_STATE_LOCK:
            LIVE_IN_MEMORY_STATE["matrix_context"][destination_register] = computed_output
            LIVE_IN_MEMORY_STATE["current_step"] = step_number
            LIVE_IN_MEMORY_STATE["telemetry_stream"].append(f"Node [{node_id}] validated.")

        await write_transaction_entry({
            "event": "STAGE_COMPLETED",
            "step": step_number,
            "node": node_id,
            "status": "PROD_READY"
        })

        active_payload_stream = computed_output

    async with SYSTEM_STATE_LOCK:
        LIVE_IN_MEMORY_STATE["engine_status"] = "SUCCESS_STABLE"

@app.get("/health", status_code=status.HTTP_200_OK)
async def check_kernel_vitality():
    async with SYSTEM_STATE_LOCK:
        return {
            "kernel_identity": MANIFEST_DATA["system_identity"]["name"],
            "engine_state": LIVE_IN_MEMORY_STATE["engine_status"],
            "matrix_step": LIVE_IN_MEMORY_STATE["current_step"]
        }

@app.get("/matrix/telemetry", status_code=status.HTTP_200_OK)
async def inspect_runtime_memory():
    async with SYSTEM_STATE_LOCK:
        return LIVE_IN_MEMORY_STATE

@app.post("/matrix/execute", status_code=status.HTTP_202_ACCEPTED)
async def trigger_asynchronous_execution(payload: InputDirective, background_tasks: BackgroundTasks):
    background_tasks.add_task(process_matrix_trajectory, payload.directive)
    return {
        "status": "TRANSACTION_ACCEPTED",
        "message": "Orchestration array successfully initialized within async background worker pools."
    }
