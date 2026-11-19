import httpx
import json
import logging
import os
import re
import asyncio
from datetime import datetime, timezone
from collections import Counter
from fastmcp import FastMCP
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

# ==========================================
# CONFIGURE LOGGING
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("isetia_mcp")

mcp = FastMCP("ISTClientCore MCP")

BASE_URL = "https://spatial-technology.isetia.eu"

# ==========================================
# HARDCODED CREDENTIALS FOR TESTING
# ==========================================
HARDCODED_USERNAME = "Leo"
HARDCODED_PASSWORD = "Leolee88*"
# ==========================================

# ==========================================
# DIFY UPLOAD CONFIGURATION
# ==========================================
DIFY_BASE_URL = "http://10.1.2.230/v1"
DIFY_API_KEY = "app-NLU7VWvf8xj7pywyxdktBy6C"

DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ==========================================
# IN-MEMORY CACHES
# ==========================================
_STAGE_CACHE: dict = {}
_CARD_DOCS_CACHE: dict = {}  # <--- NEW: Cache for card documents

async def get_auth_token(client: httpx.AsyncClient) -> str:
    """Helper function to handle login and return the token."""
    login_url = f"{BASE_URL}/api/Authentication/Login"
    login_payload = {"userName": HARDCODED_USERNAME, "password": HARDCODED_PASSWORD}

    logger.info(f"[AUTH] Attempting login for user: {HARDCODED_USERNAME}")
    response = await client.post(login_url, json=login_payload)
    response.raise_for_status()

    try:
        json_data = response.json()
        if isinstance(json_data, dict) and "AccessToken" in json_data:
            return json_data["AccessToken"]
    except json.JSONDecodeError:
        pass

    return response.text.strip('"')

# ==========================================
# STAGE LOOKUP (CACHED)
# ==========================================

async def _get_stage(client: httpx.AsyncClient, token: str, stage_id: int) -> dict:
    if not stage_id:
        return {"Id": None, "Name": "Unknown", "Color": "#8899bb"}

    if stage_id in _STAGE_CACHE:
        return _STAGE_CACHE[stage_id]

    url = f"{BASE_URL}/api/stages/{stage_id}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    try:
        resp = await client.get(url, headers=headers, timeout=30.0)
        if resp.status_code == 200:
            data = resp.json()
            stage = {
                "Id": data.get("Id", stage_id),
                "Name": data.get("Name") or f"Stage {stage_id}",
                "Color": data.get("Color") or "#8899bb",
                "Order": data.get("Order"),
                "DefaultProgress": data.get("DefaultProgress"),
            }
            _STAGE_CACHE[stage_id] = stage
            logger.info(f"[STAGES] Cached stage {stage_id} -> {stage['Name']} ({stage['Color']})")
            return stage
        logger.warning(f"[STAGES] Failed to fetch stage {stage_id}: HTTP {resp.status_code}")
    except Exception as e:
        logger.warning(f"[STAGES] Error fetching stage {stage_id}: {e}")

    fallback = {"Id": stage_id, "Name": f"Stage {stage_id}", "Color": "#8899bb"}
    _STAGE_CACHE[stage_id] = fallback
    return fallback


async def _resolve_stages(client: httpx.AsyncClient, token: str, cards: list) -> dict:
    stage_ids = {c.get("Stage_Id") for c in cards if c.get("Stage_Id") is not None}
    if not stage_ids:
        return {}

    missing = [sid for sid in stage_ids if sid not in _STAGE_CACHE]
    if missing:
        logger.info(f"[STAGES] Cache miss for {len(missing)} stage(s): {sorted(missing)}")
        await asyncio.gather(*[_get_stage(client, token, sid) for sid in missing])
    else:
        logger.info(f"[STAGES] All {len(stage_ids)} stage(s) served from cache")

    return {sid: _STAGE_CACHE[sid] for sid in stage_ids}


def _stage_cache_snapshot() -> list:
    return sorted(_STAGE_CACHE.values(), key=lambda s: (s.get("Order") or 999, s.get("Id") or 0))

# ==========================================
# MCP TOOLS
# ==========================================

@mcp.tool()
async def list_my_documents(project_id: int, search_query: Optional[str] = None) -> str:
    """
    Lists documents for a specific project.
    Optionally filters by document Name using a keyword search (`search_query`).
    Returns documents that contain ANY of the keywords (case-insensitive).
    """
    logger.info(f"--- Tool 'list_my_documents' invoked for Project ID: {project_id} | Search: {search_query} ---")
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            token = await get_auth_token(client)
            docs_url = f"{BASE_URL}/api/projects/{project_id}/documents"
            headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
            logger.info(f"[DOCS] Fetching documents from {docs_url}")
            response = await client.get(docs_url, headers=headers)
            response.raise_for_status()
            
            documents = response.json()
            
            if search_query and isinstance(documents, list):
                keywords = [kw.strip().lower() for kw in search_query.split() if kw.strip()]
                
                if keywords:
                    filtered_docs = []
                    for doc in documents:
                        doc_name = str(doc.get("Name", "")).lower()
                        if any(kw in doc_name for kw in keywords):
                            filtered_docs.append(doc)
                    
                    documents = filtered_docs
                    logger.info(f"[DOCS] Filtered down to {len(documents)} document(s) matching ANY keyword: {keywords}")
                
            return json.dumps(documents, indent=2)
        except Exception as e:
            logger.error(f"[DOCS] Error: {str(e)}")
            return f"Error fetching documents: {str(e)}"

@mcp.tool()
async def get_token() -> str:
    """Authenticates with the IST API and returns the Bearer Access Token."""
    logger.info("--- Tool 'get_token' invoked ---")
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            token = await get_auth_token(client)
            logger.info("[AUTH] Successfully retrieved token for Dify.")
            return token
        except Exception as e:
            logger.error(f"[AUTH] Failed to get token: {str(e)}")
            return f"ERROR: {str(e)}"

@mcp.tool()
async def download_document(document_id: int) -> str:
    """Downloads a document, uploads it to Dify, returns the Dify File ID."""
    logger.info(f"--- Tool 'download_document' invoked for Document ID: {document_id} ---")
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            token = await get_auth_token(client)
            download_url = f"{BASE_URL}/api/documents/download/{document_id}"
            headers = {"Authorization": f"Bearer {token}"}
            logger.info(f"[DOWNLOAD] Requesting file from {download_url}")

            async with client.stream("GET", download_url, headers=headers) as response:
                response.raise_for_status()
                content_disposition = response.headers.get("content-disposition", "")
                filename = f"document_{document_id}.pdf"
                if "filename=" in content_disposition:
                    parts = content_disposition.split(";")
                    for part in parts:
                        if "filename=" in part and "filename*=" not in part:
                            raw_name = part.split("filename=")[-1].strip()
                            clean_name = re.sub(r'[\\/*?:"<>|]', "", raw_name).strip('"\'')
                            if clean_name:
                                filename = clean_name
                                break
                file_path = os.path.join(DOWNLOAD_DIR, filename)
                logger.info(f"[DOWNLOAD] Saving file to {file_path}")
                with open(file_path, "wb") as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)
                file_size = os.path.getsize(file_path)
                logger.info(f"[DOWNLOAD] Success! File saved ({file_size} bytes).")

            logger.info(f"[DIFY] Uploading {filename} to Dify...")
            dify_upload_url = f"{DIFY_BASE_URL}/files/upload"
            dify_headers = {"Authorization": f"Bearer {DIFY_API_KEY}"}
            with open(file_path, "rb") as f:
                files = {
                    "file": (filename, f, "application/pdf"),
                    "user": (None, "mcp-server-user")
                }
                dify_response = await client.post(dify_upload_url, headers=dify_headers, files=files)
            dify_response.raise_for_status()
            dify_file_id = dify_response.json().get("id")
            logger.info(f"[DIFY] Successfully uploaded! Dify File ID: {dify_file_id}")
            return f"Success! File uploaded to Dify. DIFY_FILE_ID:{dify_file_id}"
        except httpx.HTTPStatusError as e:
            logger.error(f"[ERROR] HTTP Error: {e.response.status_code} - {e.response.text}")
            return f"Failed due to API error: {e.response.status_code}"
        except Exception as e:
            logger.error(f"[ERROR] {str(e)}")
            return f"Error: {str(e)}"

# ==========================================
# BOARDS & CARDS MCP TOOLS
# ==========================================

@mcp.tool()
async def list_project_boards(project_id: int) -> str:
    """Lists all boards belonging to a specific project."""
    logger.info(f"--- Tool 'list_project_boards' invoked for Project ID: {project_id} ---")
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            token = await get_auth_token(client)
            boards_url = f"{BASE_URL}/api/projects/{project_id}/boards"
            headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
            logger.info(f"[BOARDS] Fetching boards from {boards_url}")
            response = await client.get(boards_url, headers=headers)
            response.raise_for_status()
            return json.dumps(response.json(), indent=2)
        except httpx.HTTPStatusError as e:
            logger.error(f"[BOARDS] HTTP Error: {e.response.status_code} - {e.response.text}")
            return f"Failed to fetch boards: {e.response.status_code}"
        except Exception as e:
            logger.error(f"[BOARDS] Error: {str(e)}")
            return f"Error fetching boards: {str(e)}"

@mcp.tool()
async def list_board_cards(board_id: int) -> str:
    """Lists all cards (todos) on a specific board."""
    logger.info(f"--- Tool 'list_board_cards' invoked for Board ID: {board_id} ---")
    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            token = await get_auth_token(client)
            cards_url = f"{BASE_URL}/api/boards/{board_id}/todos"
            headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
            logger.info(f"[CARDS] Fetching cards from {cards_url}")
            response = await client.get(cards_url, headers=headers)
            response.raise_for_status()
            return json.dumps(response.json(), indent=2)
        except httpx.HTTPStatusError as e:
            logger.error(f"[CARDS] HTTP Error: {e.response.status_code} - {e.response.text}")
            return f"Failed to fetch cards: {e.response.status_code}"
        except Exception as e:
            logger.error(f"[CARDS] Error: {str(e)}")
            return f"Error fetching cards: {str(e)}"

# ==========================================
# NEW TOOL: GET CARD DOCUMENTS
# ==========================================

@mcp.tool()
async def get_card_documents(user_defined_id: str, board_id: int) -> str:
    """
    Finds a card by its UserDefinedId on a specific board, retrieves its system Id, 
    and then fetches the related documents from the IST API.
    """
    logger.info(f"--- Tool 'get_card_documents' invoked for UserDefinedId: {user_defined_id} on Board: {board_id} ---")
    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            token = await get_auth_token(client)
            headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
            
            cards_url = f"{BASE_URL}/api/boards/{board_id}/todos"
            logger.info(f"[CARD DOCS] Searching for card '{user_defined_id}' on board {board_id}")
            
            cards_resp = await client.get(cards_url, headers=headers)
            cards_resp.raise_for_status()
            cards = cards_resp.json()
            
            system_id = None
            if isinstance(cards, list):
                for card in cards:
                    if str(card.get("UserDefinedId", "")).strip().lower() == user_defined_id.strip().lower():
                        system_id = card.get("Id")
                        break
            
            if not system_id:
                logger.warning(f"[CARD DOCS] Card '{user_defined_id}' not found on board {board_id}.")
                return f"Error: Card with UserDefinedId '{user_defined_id}' not found on board {board_id}."
                
            logger.info(f"[CARD DOCS] Found system ID {system_id} for card '{user_defined_id}'.")
            
            docs_url = f"{BASE_URL}/api/todos/{system_id}/documents"
            logger.info(f"[CARD DOCS] Fetching related documents from {docs_url}")
            
            docs_resp = await client.get(docs_url, headers=headers)
            docs_resp.raise_for_status()
            
            return json.dumps(docs_resp.json(), indent=2)
            
        except httpx.HTTPStatusError as e:
            logger.error(f"[CARD DOCS] HTTP Error: {e.response.status_code} - {e.response.text}")
            return f"Failed to fetch card documents: HTTP {e.response.status_code}"
        except Exception as e:
            logger.error(f"[CARD DOCS] Error: {str(e)}")
            return f"Error fetching card documents: {str(e)}"

# ==========================================
# CARD ANALYTICS HELPERS
# ==========================================

def _parse_dt(value):
    if not value:
        return None
    try:
        s = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None

def _num(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def _is_completed(card):
    if card.get("IsFinished") is True:
        return True
    return _num(card.get("CompletedPercent")) >= 100.0

def _is_overdue(card, now):
    if _is_completed(card):
        return False
    finish = _parse_dt(card.get("PlannedFinishDate"))
    return finish is not None and finish < now

def _is_pending_action(card):
    if _is_completed(card):
        return False
    if card.get("IsStarted") is True:
        return False
    return card.get("ActualStartDate") is None

def _card_status(card, now):
    if _is_completed(card):
        return "Completed"
    if _is_overdue(card, now):
        return "Overdue"
    if card.get("IsStarted") is True or card.get("ActualStartDate") is not None:
        return "In Progress"
    return "Not Started"

async def _aggregate_cards(client: httpx.AsyncClient, token: str, cards: list, stage_map: dict = None):
    now = datetime.now(timezone.utc)
    stage_map = stage_map or {}
    stage_counter = Counter()
    timeline_counter = Counter()
    stage_meta = {}
    table_rows = []

    total = len(cards)
    overdue = 0
    pending = 0

    # Fetch documents for all cards in parallel
    async def fetch_docs(c):
        cid = c.get("Id")
        if not cid: return cid, None
        if cid in _CARD_DOCS_CACHE:
            return cid, _CARD_DOCS_CACHE[cid]
        
        try:
            # Look for documents attached to this card
            resp = await client.get(f"{BASE_URL}/api/todos/{cid}/documents", headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
            if resp.status_code == 200:
                docs = resp.json()
                _CARD_DOCS_CACHE[cid] = docs
                return cid, docs
        except Exception as e:
            logger.warning(f"Failed to fetch docs for card {cid}: {e}")
        
        return cid, None

    # Gather all document fetches concurrently
    doc_results = await asyncio.gather(*(fetch_docs(c) for c in cards))
    docs_map = {cid: docs for cid, docs in doc_results}

    for c in cards:
        cid = c.get("Id")
        card_docs = docs_map.get(cid) or []
        
        stage_id = c.get("Stage_Id")
        stage = stage_map.get(stage_id) or {"Id": stage_id, "Name": f"Stage {stage_id}" if stage_id else "Unknown", "Color": "#8899bb"}
        stage_name = stage.get("Name") or "Unknown"
        stage_color = stage.get("Color") or "#8899bb"

        stage_meta[stage_name] = {"id": stage.get("Id"), "name": stage_name, "color": stage_color}
        stage_counter[stage_name] += 1

        if _is_overdue(c, now): overdue += 1
        if _is_pending_action(c): pending += 1

        finish_dt = _parse_dt(c.get("PlannedFinishDate"))
        if finish_dt:
            month_key = finish_dt.strftime("%Y-%m")
            timeline_counter[(month_key, stage_name)] += 1

        # Extract the first document ID if available
        first_doc_id = card_docs[0].get("Id") if isinstance(card_docs, list) and len(card_docs) > 0 else None

        table_rows.append({
            "id": cid,
            "userDefinedId": c.get("UserDefinedId"),
            "name": c.get("Name"),
            "description": c.get("Description") or "",
            "stageId": stage_id,
            "stageName": stage_name,
            "stageColor": stage_color,
            "boardId": c.get("_boardId"),
            "wbsId": c.get("WbS_Id"),
            "plannedStartDate": c.get("PlannedStartDate"),
            "plannedFinishDate": c.get("PlannedFinishDate"),
            "actualStartDate": c.get("ActualStartDate"),
            "actualFinishDate": c.get("ActualFinishDate"),
            "completedPercent": c.get("CompletedPercent"),
            "isStarted": c.get("IsStarted"),
            "isFinished": c.get("IsFinished"),
            "dateStatus": _card_status(c, now),
            "color": c.get("Color") or "#8899bb",
            "documentId": first_doc_id, # <--- NEW: Pass Document ID to frontend
            "documents": card_docs      # <--- NEW: Pass all docs just in case
        })

    stage_pie = [
        {"name": name, "value": count, "color": stage_meta[name]["color"], "stageId": stage_meta[name]["id"]}
        for name, count in sorted(stage_counter.items(), key=lambda kv: -kv[1])
    ]

    stage_names = [item["name"] for item in stage_pie]
    months = sorted({m for (m, _) in timeline_counter.keys()})
    timeline_bars = []
    for m in months:
        row = {"month": m}
        for sname in stage_names:
            row[sname] = timeline_counter.get((m, sname), 0)
        timeline_bars.append(row)

    return {
        "totalCards": total,
        "overdueCards": overdue,
        "pendingActionCards": pending,
        "stagePie": stage_pie,
        "timelineBars": timeline_bars,
        "stageNames": stage_names,
        "stageColors": {name: stage_meta[name]["color"] for name in stage_names},
        "stageIds": {name: stage_meta[name]["id"] for name in stage_names},
        "cards": table_rows,
    }

# ==========================================
# FASTAPI WRAPPER
# ==========================================

app = FastAPI(title="IST Smart Docs API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/dashboard/stats")
async def get_dashboard_stats(project_id: int = 0):
    logger.info(f"\n{'='*50}")
    logger.info(f"📊 [DASHBOARD] New Request for Project ID: {project_id}")
    all_documents = []

    if project_id == 0:
        logger.info("🌍 [DASHBOARD] Fetching data for ALL projects...")
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                token = await get_auth_token(client)
                headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
                proj_response = await client.get(f"{BASE_URL}/api/projects", headers=headers)
                proj_response.raise_for_status()
                projects = proj_response.json()
                for proj in projects:
                    p_id = proj.get("Id")
                    logger.info(f"  -> Fetching documents for Project {p_id} ({proj.get('Name')})...")
                    docs_response = await client.get(f"{BASE_URL}/api/projects/{p_id}/documents", headers=headers)
                    if docs_response.status_code == 200:
                        docs = docs_response.json()
                        if isinstance(docs, list):
                            all_documents.extend(docs)
            except Exception as e:
                logger.error(f"❌ Error fetching all projects: {e}")
    else:
        logger.info(f"📁 [DASHBOARD] Fetching data for single project: {project_id}")
        docs_json_str = await list_my_documents(project_id)
        try:
            documents = json.loads(docs_json_str)
            if isinstance(documents, list):
                all_documents = documents
        except Exception as e:
            logger.error(f"❌ [DEBUG] JSON Parse Error: {e}")

    total_docs = len(all_documents)
    outstanding = sum(1 for d in all_documents if d.get("CheckedOutOn") is not None)
    pending = 5

    logger.info(f"🧮 [CALCULATION] Total: {total_docs} | Outstanding: {outstanding} | Pending: {pending}")
    logger.info(f"{'='*50}\n")

    return {
        "total_documents": total_docs,
        "outstanding_documents": outstanding,
        "pending_actions": pending,
        "documents": all_documents
    }

@app.get("/api/dashboard/cards")
async def get_dashboard_cards(project_id: int = 0, board_id: int = 0):
    logger.info(f"\n{'='*50}")
    logger.info(f"🃏 [CARDS] Request project_id={project_id} board_id={board_id}")

    cards = []
    boards_used = []

    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            token = await get_auth_token(client)
            headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

            board_ids = []
            if board_id and board_id != 0:
                board_ids = [board_id]
            else:
                if project_id and project_id != 0:
                    project_ids = [project_id]
                else:
                    proj_resp = await client.get(f"{BASE_URL}/api/projects", headers=headers)
                    proj_resp.raise_for_status()
                    project_ids = [p.get("Id") for p in proj_resp.json() if p.get("Id") is not None]

                for pid in project_ids:
                    b_resp = await client.get(f"{BASE_URL}/api/projects/{pid}/boards", headers=headers)
                    if b_resp.status_code != 200:
                        logger.warning(f"[CARDS] Boards fetch failed for project {pid}: {b_resp.status_code}")
                        continue
                    for b in b_resp.json():
                        bid = b.get("Id")
                        if bid is not None:
                            board_ids.append(bid)
                            boards_used.append({
                                "id": bid,
                                "name": b.get("Name"),
                                "projectId": b.get("Project_Id"),
                                "projectName": b.get("ProjectName"),
                            })

            logger.info(f"[CARDS] Fetching cards for {len(board_ids)} board(s): {board_ids}")
            for bid in board_ids:
                c_resp = await client.get(f"{BASE_URL}/api/boards/{bid}/todos", headers=headers)
                if c_resp.status_code != 200:
                    logger.warning(f"[CARDS] Cards fetch failed for board {bid}: {c_resp.status_code}")
                    continue
                data = c_resp.json()
                if isinstance(data, list):
                    for card in data:
                        card.setdefault("_boardId", bid)
                    cards.extend(data)

            stage_map = await _resolve_stages(client, token, cards)

        except Exception as e:
            logger.error(f"❌ [CARDS] Error: {e}")
            raise HTTPException(status_code=502, detail=f"Failed to build card dashboard: {e}")

    # Updated to pass client, token, and fetch documents
    agg = await _aggregate_cards(client, token, cards, stage_map=stage_map)
    agg["boards"] = boards_used
    logger.info(
        f"🧮 [CARDS] Total={agg['totalCards']} | Overdue={agg['overdueCards']} | "
        f"Pending={agg['pendingActionCards']} | Stages={agg['stageNames']} | Boards={len(boards_used)}"
    )
    logger.info(f"{'='*50}\n")
    return agg

@app.get("/api/stages")
async def get_stages_cache():
    return _stage_cache_snapshot()

@app.delete("/api/stages/cache")
async def clear_stages_cache():
    count = len(_STAGE_CACHE)
    _STAGE_CACHE.clear()
    logger.info(f"[STAGES] Cache cleared ({count} entries removed)")
    return {"cleared": count}

class DownloadRequest(BaseModel):
    document_id: int

@app.post("/api/documents/download")
async def api_download_document(req: DownloadRequest):
    result = await download_document(req.document_id)
    return {"status": "success", "message": result}

@app.get("/api/projects")
async def get_projects():
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            token = await get_auth_token(client)
            headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
            response = await client.get(f"{BASE_URL}/api/projects", headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"[PROJECTS] Error: {str(e)}")
            return []

@app.get("/api/boards")
async def get_boards(project_id: int = Query(..., description="Project ID to fetch boards for")):
    logger.info(f"[API] GET /api/boards?project_id={project_id}")
    result = await list_project_boards(project_id)
    try:
        data = json.loads(result)
        if isinstance(data, list):
            return data
        raise HTTPException(status_code=502, detail=str(data))
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="Unexpected non-JSON response from boards API")

@app.get("/api/boards/{board_id}/cards")
async def get_board_cards(board_id: int):
    logger.info(f"[API] GET /api/boards/{board_id}/cards")
    result = await list_board_cards(board_id)
    try:
        data = json.loads(result)
        if isinstance(data, list):
            return data
        raise HTTPException(status_code=502, detail=str(data))
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="Unexpected non-JSON response from cards API")

app.mount("/mcp", mcp.http_app())