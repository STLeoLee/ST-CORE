"""
FastAPI Web Server for Chatbot with SkillKit Integration
"""

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import sys
import os
import logging
import uuid
import json
import pickle
import asyncio
import concurrent.futures
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict, Counter
import requests
import httpx

from isetia_mcp import list_my_documents, get_auth_token, BASE_URL, _resolve_stages, mcp
from novade_API import get_safety_actions

# ==================== Logging Setup ====================
logger = logging.getLogger("powerbi-chatbot")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s'))
    logger.addHandler(ch)

# ==================== Path Setup ====================
current_dir = Path(__file__).parent
sys.path.append(str(current_dir / "skills"))

# ==================== Import Chatbot ====================
try:
    from chat import Chatbot, ChatStatus
except ImportError as e:
    logger.error(f"❌ Failed to import Chatbot: {e}")
    sys.exit(1)

# ==================== Config ====================
POWERBI_CONFIG = {
    'clientId': 'e62b1ea5-033a-497d-9220-3f8f155f00a5',
    'clientSecret': 'a2c8Q~q_t1uIdveQBzV5aOH3RRsS~UR3OTJ3dbvd',
    'tenantId': '65f7aa87-2828-4e09-86d0-65e26540ce78',
    'workspaceId': '59b43e23-561e-49a0-a214-961aaffa7a5c',
    'reportId': '2dbc78a5-e402-4ebb-b744-4eee3d0bcb58'
}

DIFY_API_BASE = "http://10.1.2.230/v1"
DIFY_API_KEY = "app-NLU7VWvf8xj7pywyxdktBy6C"

EXCLUDED_PROJECT_IDS = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,20,21,22,23,24]
EXCLUDED_BOARD_IDS = [36, 37, 134, 143, 144, 145, 180, 182]

# ==================== Power BI Helpers ====================
def get_powerbi_access_token():
    token_url = f"https://login.microsoftonline.com/{POWERBI_CONFIG['tenantId']}/oauth2/v2.0/token"
    token_data = {
        'client_id': POWERBI_CONFIG['clientId'],
        'client_secret': POWERBI_CONFIG['clientSecret'],
        'scope': 'https://analysis.windows.net/powerbi/api/.default',
        'grant_type': 'client_credentials'
    }
    response = requests.post(token_url, data=token_data)
    response.raise_for_status()
    return response.json()['access_token']

def get_report_embed_config(report_id):
    try:
        access_token = get_powerbi_access_token()
        headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
        report_url_api = f"https://api.powerbi.com/v1.0/myorg/groups/{POWERBI_CONFIG['workspaceId']}/reports/{report_id}"
        report_response = requests.get(report_url_api, headers=headers)
        report_response.raise_for_status()
        report_data = report_response.json()
        
        embed_token_api = f"https://api.powerbi.com/v1.0/myorg/groups/{POWERBI_CONFIG['workspaceId']}/reports/{report_id}/GenerateToken"
        embed_body = {
            "accessLevel": "View", "allowSaveAs": False,
            "datasets": [{"id": report_data['datasetId']}],
            "targetWorkspaces": [{"id": POWERBI_CONFIG['workspaceId']}]
        }
        embed_response = requests.post(embed_token_api, headers=headers, json=embed_body)
        embed_response.raise_for_status()
        embed_result = embed_response.json()
        return {
            'reportId': report_id, 'embedToken': embed_result['token'],
            'embedUrl': report_data['embedUrl'], 'datasetId': report_data['datasetId'],
            'tokenExpiry': embed_result.get('expiration', 'N/A'), 'workspaceId': POWERBI_CONFIG['workspaceId']
        }
    except Exception as e:
        logger.error(f"❌ Power BI embed config error: {str(e)}")
        raise

executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

# ==================== Session Manager ====================
class SessionFileStorage:
    def __init__(self, storage_dir: str = "sessions"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.session_timeout = 3600
    
    def get_session_file_path(self, session_id: str) -> Path:
        return self.storage_dir / f"{session_id}.pkl"
    
    def save_session(self, session_id: str, session_data: Dict[str, Any]):
        file_path = self.get_session_file_path(session_id)
        try:
            with open(file_path, 'wb') as f:
                pickle.dump(session_data, f)
            return True
        except: return False
    
    def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        file_path = self.get_session_file_path(session_id)
        if not file_path.exists(): return None
        try:
            with open(file_path, 'rb') as f:
                return pickle.load(f)
        except: return None
    
    def delete_session_file(self, session_id: str) -> bool:
        file_path = self.get_session_file_path(session_id)
        if file_path.exists():
            try:
                file_path.unlink()
                return True
            except: return False
        return False

class SessionManager:
    def __init__(self):
        self.storage = SessionFileStorage()
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.max_sessions = 1000
        logger.info("✅ Session Manager initialized")
    
    def get_or_create_session(self, session_id: Optional[str] = None) -> str:
        if session_id and session_id in self.active_sessions:
            self.active_sessions[session_id]['last_activity'] = datetime.now()
            return session_id
            
        if session_id:
            session_data = self.storage.load_session(session_id)
            if session_data:
                chatbot = Chatbot("Power BI Chatbot", use_llm=True)
                self.active_sessions[session_id] = {
                    'chatbot': chatbot,
                    'created_at': datetime.now(),
                    'last_activity': datetime.now()
                }
                return session_id
        
        new_session_id = str(uuid.uuid4())
        self.active_sessions[new_session_id] = {
            'chatbot': Chatbot("Power BI Chatbot", use_llm=True),
            'created_at': datetime.now(),
            'last_activity': datetime.now()
        }
        return new_session_id
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        if session_id in self.active_sessions:
            return {"created_at": self.active_sessions[session_id]['created_at'].isoformat(), "status": "active"}
        return None
    
    def delete_session(self, session_id: str) -> bool:
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        return self.storage.delete_session_file(session_id)

session_manager = SessionManager()

# ==================== Card Helpers ====================
async def fetch_dashboard_cards_data(project_id: int = 0, board_id: int = 0, client: httpx.AsyncClient = None, token: str = None):
    own_client = False
    if not client or not token:
        client = httpx.AsyncClient(timeout=180.0)
        own_client = True
        token = await get_auth_token(client)

    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    cards = []
    stage_map = {}
    
    try:
        if board_id and board_id != 0:
            if board_id in EXCLUDED_BOARD_IDS: return await _aggregate_cards(client, token, [], project_id, {})
            c_resp = await client.get(f"{BASE_URL}/api/boards/{board_id}/todos", headers=headers)
            if c_resp.status_code == 200: cards.extend(c_resp.json())
        else:
            if project_id and project_id != 0:
                project_ids = [project_id]
            else:
                proj_resp = await client.get(f"{BASE_URL}/api/projects", headers=headers)
                proj_resp.raise_for_status()
                project_ids = [p.get("Id") for p in proj_resp.json() if p.get("Id") not in EXCLUDED_PROJECT_IDS]
            
            for pid in project_ids:
                b_resp = await client.get(f"{BASE_URL}/api/projects/{pid}/boards", headers=headers)
                if b_resp.status_code != 200: continue
                for b in b_resp.json():
                    bid = b.get("Id")
                    if bid in EXCLUDED_BOARD_IDS: continue
                    c_resp = await client.get(f"{BASE_URL}/api/boards/{bid}/todos", headers=headers)
                    if c_resp.status_code == 200: cards.extend(c_resp.json())
        
        if cards: stage_map = await _resolve_stages(client, token, cards)
    except Exception as e:
        logger.error(f"❌ [CARDS] Error: {e}")
    finally:
        if own_client: await client.aclose()

    return await _aggregate_cards(client, token, cards, project_id, stage_map=stage_map)

async def _aggregate_cards(client: httpx.AsyncClient, token: str, cards: List[Dict[str, Any]], project_id: int, stage_map: dict = None) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    stage_map = stage_map or {}
    stage_counter, timeline_counter, stage_meta, table_rows = Counter(), Counter(), {}, []
    total, overdue_count, pending_count = len(cards), 0, 0

    async def fetch_card_docs(c):
        cid = c.get("Id")
        if not cid: return cid, []
        try:
            url = f"{BASE_URL}/api/todos/{cid}/documents"
            resp = await client.get(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}, timeout=30.0)
            if resp.status_code == 200: return cid, resp.json()
        except: pass
        return cid, []

    doc_results = await asyncio.gather(*(fetch_card_docs(c) for c in cards))
    docs_map = {cid: docs for cid, docs in doc_results}

    for c in cards:
        cid = c.get("Id")
        card_docs = docs_map.get(cid) or []
        
        stage_id = c.get("Stage_Id")
        stage = stage_map.get(stage_id) or {"Id": stage_id, "Name": "Unknown", "Color": "#8899bb"}
        stage_name, stage_color = stage.get("Name"), stage.get("Color")
        
        stage_meta[stage_name] = {"id": stage.get("Id"), "name": stage_name, "color": stage_color}
        stage_counter[stage_name] += 1

        finish_dt = None
        if c.get("PlannedFinishDate"):
            try:
                finish_dt = datetime.fromisoformat(c["PlannedFinishDate"].replace("Z", "+00:00"))
                if finish_dt.tzinfo is None: finish_dt = finish_dt.replace(tzinfo=timezone.utc)
            except: pass

        completed_percent = float(c.get("CompletedPercent") or 0)
        is_completed = c.get("IsFinished") is True or completed_percent >= 100.0
        is_overdue = not is_completed and finish_dt is not None and finish_dt < now
        is_pending = not is_overdue and not is_completed
        
        if is_overdue: overdue_count += 1
        elif is_pending: pending_count += 1

        if finish_dt:
            month_key = finish_dt.strftime("%Y-%m")
            timeline_counter[(month_key, stage_name)] += 1

        first_doc_id = None
        if isinstance(card_docs, list) and len(card_docs) > 0:
            first_doc_id = card_docs[0].get("Id") or card_docs[0].get("DocumentId")

        table_rows.append({
            "id": cid, "userDefinedId": c.get("UserDefinedId"), "name": c.get("Name"),
            "stageId": stage_id, "stageName": stage_name, "stageColor": stage_color,
            "plannedStartDate": c.get("PlannedStartDate"), "plannedFinishDate": c.get("PlannedFinishDate"),
            "completedPercent": completed_percent, "isOverdue": is_overdue, "isPending": is_pending,
            "dateStatus": "Overdue" if is_overdue else ("Completed" if is_completed else "Pending"),
            "documentId": first_doc_id, "documents": card_docs
        })

    stage_pie = [{"name": n, "value": c, "color": stage_meta[n]["color"], "stageId": stage_meta[n]["id"]} for n, c in sorted(stage_counter.items(), key=lambda kv: -kv[1])]
    stage_names = [item["name"] for item in stage_pie]
    months = sorted({m for (m, _) in timeline_counter.keys()})
    timeline_bars = [{"month": m, **{s: timeline_counter.get((m, s), 0) for s in stage_names}} for m in months]

    return {
        "totalCards": total, "overdueCards": overdue_count, "pendingActionCards": pending_count,
        "stagePie": stage_pie, "timelineBars": timeline_bars, "stageNames": stage_names,
        "stageColors": {n: stage_meta[n]["color"] for n in stage_names},
        "stageIds": {n: stage_meta[n]["id"] for n in stage_names},
        "cards": table_rows,
    }

# ==================== MCP Setup ====================
mcp_app = mcp.http_app(path="/")

# ==================== FastAPI App ====================
app = FastAPI(
    title="ST-CORE API", version="2.0.0",
    redirect_slashes=False, lifespan=mcp_app.lifespan
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ==================== WEBSOCKET ENDPOINTS ====================

@app.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    await websocket.accept()
    logger.info(f"🔌 Chat WS connected: {session_id[:8]}")
    
    try:
        await websocket.send_json({'type': 'status', 'data': {'status': 'idle', 'message': 'Ready'}})
        
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
                
                # --- SMART DOCS DIFY CHAT ---
                if data.get('type') == 'smart_docs_query':
                    question = data.get('question', '')
                    conv_id = data.get('conversation_id', '')
                    
                    try:
                        dify_url = f"{DIFY_API_BASE}/chat-messages"
                        headers = {"Authorization": f"Bearer {DIFY_API_KEY}", "Content-Type": "application/json"}
                        payload = {
                            "inputs": {}, 
                            "query": question, 
                            "response_mode": "streaming",
                            "conversation_id": conv_id, 
                            "user": session_id
                        }
                        
                        final_answer = ""
                        new_conv_id = conv_id
                        
                        async with httpx.AsyncClient(timeout=300.0) as client:
                            async with client.stream("POST", dify_url, json=payload, headers=headers) as response:
                                response.raise_for_status()
                                
                                async for line in response.aiter_lines():
                                    if not line.strip(): continue
                                    
                                    if line.startswith("data: "):
                                        try:
                                            chunk_data = json.loads(line[6:])
                                            event_type = chunk_data.get("event")
                                            
                                            if event_type == "node_started":
                                                title = chunk_data.get("data", {}).get("title", "Processing node")
                                                await websocket.send_json({
                                                    'type': 'status',
                                                    'data': {
                                                        'status': 'thinking',
                                                        'stage': 0,
                                                        'total_stages': 1,
                                                        'stage_name': title,
                                                        'message': f'⚙️ Running: {title}...'
                                                    }
                                                })
                                            
                                            elif event_type == "node_finished":
                                                title = chunk_data.get("data", {}).get("title", "Node")
                                                await websocket.send_json({
                                                    'type': 'status',
                                                    'data': {
                                                        'status': 'thinking',
                                                        'stage': 0,
                                                        'total_stages': 1,
                                                        'stage_name': title,
                                                        'message': f'✅ Finished: {title}'
                                                    }
                                                })

                                            elif event_type == "message":
                                                final_answer += chunk_data.get("answer", "")
                                            
                                            elif event_type == "message_end":
                                                new_conv_id = chunk_data.get("conversation_id", conv_id)
                                                
                                        except json.JSONDecodeError:
                                            pass
                        
                        await websocket.send_json({
                            'type': 'result', 
                            'data': {
                                'answer': final_answer or "No response from Dify.", 
                                'conversation_id': new_conv_id
                            }
                        })
                    except Exception as e:
                        logger.error(f"❌ Smart Docs Error: {e}")
                        await websocket.send_json({'type': 'error', 'data': {'error': str(e)}})
                    continue

                # --- POWER BI CHAT PLACEHOLDER ---
                question = data.get('question', '')
                if question and data.get('type') != 'smart_docs_query':
                    await websocket.send_json({'type': 'status', 'data': {'status': 'thinking', 'message': '🧠 Thinking...'}})
                    await websocket.send_json({'type': 'result', 'data': {'answer': 'Power BI logic placeholder', 'response': 'Power BI placeholder'}})

            except asyncio.TimeoutError:
                try: await websocket.send_json({'type': 'ping'})
                except: break
            except WebSocketDisconnect: break
    except Exception as e:
        logger.error(f"Chat WS Error: {e}")

@app.websocket("/ws/data/{session_id}")
async def websocket_data(websocket: WebSocket, session_id: str):
    await websocket.accept()
    logger.info(f"🔌 Data WS connected: {session_id[:8]}")
    
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=60.0)
                
                if data.get('type') == 'get_projects':
                    try:
                        async with httpx.AsyncClient(timeout=30.0) as client:
                            token = await get_auth_token(client)
                            res = await client.get(f"{BASE_URL}/api/projects", headers={"Authorization": f"Bearer {token}"})
                            projects = [p for p in res.json() if p.get("Id") not in EXCLUDED_PROJECT_IDS]
                            await websocket.send_json({'type': 'projects_list', 'data': projects})
                    except Exception as e:
                        await websocket.send_json({'type': 'error', 'data': {'error': str(e)}})
                    continue

                if data.get('type') == 'get_cards_data':
                    try:
                        async with httpx.AsyncClient(timeout=180.0) as client:
                            token = await get_auth_token(client)
                            cards_data = await fetch_dashboard_cards_data(
                                project_id=data.get('project_id', 0),
                                board_id=data.get('board_id', 0),
                                client=client,
                                token=token
                            )
                            await websocket.send_json({'type': 'cards_update', 'data': cards_data})
                    except Exception as e:
                        await websocket.send_json({'type': 'error', 'data': {'error': str(e)}})
                    continue
                
                # --- NEW: HANDLE NOVADE DATA REQUEST ---
                if data.get('type') == 'get_novade_data':
                    project_id = data.get('project_id', 'IZ2L4')
                    since = data.get('since', 1520234658834)
                    
                    logger.info(f"🦺 [Data WS] Fetching Novade data for project: {project_id}")
                    try:
                        raw_actions = await get_safety_actions(project_id, since)
                        
                        # 1. Group by "Type" for Category Chart
                        categories = {}
                        for action in raw_actions:
                            cat_type = action.get("type", "Uncategorized") 
                            categories[cat_type] = categories.get(cat_type, 0) + 1

                        chart_data = [{"name": k, "count": v} for k, v in categories.items()]

                        # 2. Group by "Status" for the Pie Chart
                        # Mapping based on your image
                        status_mapping = {
                            "1": "Draft",     # 1 - New
                            "2": "WIP",       # 2 - WIP
                            "5": "Rectified", # 5 - Rectified
                            "7": "Closed",    # 7 - Closed
                            "8": "Rejected"   # 8 - Rejected
                        }
                        
                        # Initialize counters
                        status_counts = {"Draft": 0, "WIP": 0, "Rectified": 0, "Closed": 0, "Rejected": 0}
                        
                        for action in raw_actions:
                            raw_status = str(action.get("status", "")).strip()
                            label = status_mapping.get(raw_status)
                            if label:
                                status_counts[label] += 1
                                
                        # Format for frontend
                        status_pie_data = [
                            {"name": k, "count": v} 
                            for k, v in status_counts.items() if v > 0
                        ]

                        await websocket.send_json({
                            'type': 'novade_data',
                            'data': {
                                'success': True,
                                'chartData': chart_data,           # For "Issues By Category"
                                'statusPieData': status_pie_data,  # For "Total Issues" Modal
                                'totalIssues': len(raw_actions)
                            }
                        })
                    except Exception as e:
                        logger.error(f"❌ Novade API Error: {e}")
                        await websocket.send_json({
                            'type': 'novade_data',
                            'data': {'success': False, 'error': str(e)}
                        })
                    continue

            except asyncio.TimeoutError:
                try: await websocket.send_json({'type': 'ping'})
                except: break
            except WebSocketDisconnect:
                logger.info(f"🔌 Data WS disconnected: {session_id[:8]}")
                break
    except Exception as e:
        logger.error(f"Data WS Error: {e}")

# ==================== REST ENDPOINTS ====================
@app.post("/session/create")
async def create_session():
    session_id = session_manager.get_or_create_session()
    return {"success": True, "session_id": session_id, "session_info": session_manager.get_session_info(session_id)}

@app.get("/session/{session_id}")
async def get_session_info(session_id: str):
    info = session_manager.get_session_info(session_id)
    if info: return {"success": True, "session_id": session_id, "session_info": info}
    raise HTTPException(status_code=404, detail="Session not found")

@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    if session_manager.delete_session(session_id):
        return {"success": True, "message": "Session deleted"}
    raise HTTPException(status_code=404, detail="Session not found")

@app.get("/api/projects")
async def get_projects():
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            token = await get_auth_token(client)
            response = await client.get(f"{BASE_URL}/api/projects", headers={"Authorization": f"Bearer {token}"})
            response.raise_for_status()
            return [p for p in response.json() if p.get("Id") not in EXCLUDED_PROJECT_IDS]
        except: return []

@app.get("/api/dashboard/cards")
async def get_cards_dashboard(project_id: int = 0, board_id: int = 0):
    return await fetch_dashboard_cards_data(project_id, board_id)

# ==================== MCP MOUNT ====================
@app.api_route("/mcp", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
@app.api_route("/mcp/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def mcp_endpoint(request: Request, path: str = ""):
    scope = request.scope
    scope["path"] = "/" + path
    scope["root_path"] = "/mcp"
    return await mcp_app(scope, request.receive, request._send)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)