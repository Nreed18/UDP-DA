import asyncio
import uvicorn
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json
import os
from udp_relay import UDPRelayManager

CONFIG_FILE = "config.json"

app = FastAPI()
if os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

relay_manager = UDPRelayManager()

@app.on_event("startup")
async def startup_event():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            try:
                config = json.load(f)
                await relay_manager.load_config(config)
            except Exception as e:
                print(f"Failed to load config: {e}")

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    stats = relay_manager.get_stats()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "config": relay_manager.config,
        "stats": stats
    })

@app.post("/admin/update")
async def update_config(
    input1_port: int = Form(...),
    input2_port: int = Form(...),
    input1_outputs: str = Form(...),
    input2_outputs: str = Form(...),
):
    config = {
        "inputs": {
            "input_1": {
                "port": input1_port,
                "outputs": [tuple(x.strip().split(":")) for x in input1_outputs.strip().splitlines() if x]
            },
            "input_2": {
                "port": input2_port,
                "outputs": [tuple(x.strip().split(":")) for x in input2_outputs.strip().splitlines() if x]
            }
        }
    }
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    await relay_manager.load_config(config)
    return RedirectResponse(url="/admin", status_code=302)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8081)
