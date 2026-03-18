from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.mcp.registry import MCP_TOOLS

router = APIRouter()


class MCPToolRunRequest(BaseModel):
    tool: str
    payload: dict


@router.get("/tools")
async def list_tools() -> dict:
    return {"tools": list(MCP_TOOLS.keys())}


@router.post("/run")
async def run_tool(request: MCPToolRunRequest) -> dict:
    tool = MCP_TOOLS.get(request.tool)
    if not tool:
        raise HTTPException(status_code=404, detail="Unknown MCP tool")
    return {"tool": request.tool, "result": tool(request.payload)}
