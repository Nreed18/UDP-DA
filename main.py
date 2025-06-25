import asyncio
import json
import os
import socket
from datetime import datetime
from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

CONFIG_FILE = "config.json"

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

class UDPRelayManager:
    def __init__(self):
        self.config = {
            "input_1": {"port": 5001},
            "input_2": {"port": 5002},
            "outputs": []
        }
        self.last_sent = {}
        self.listeners = []
        self.load_config()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                self.config = json.load(f)

    def save_config(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=2)

    async def start_relays(self):
        await self.stop_relays()
        self.listeners = [
            asyncio.create_task(self.listen_and_relay("input_1")),
            asyncio.create_task(self.listen_and_relay("input_2"))
        ]

    async def stop_relays(self):
        for task in self.listeners:
            task.cancel()
        self.listeners = []

    async def listen_and_relay(self, input_name):
        input_port = self.config.get(input_name, {}).get("port")
        if not input_port:
            return

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0", input_port))
        sock.setblocking(False)

        while True:
            try:
                data, _ = await asyncio.get_event_loop().sock_recvfrom(sock, 2048)
                for output in self.config.get("outputs", []):
                    if output.get("input") == input_name:
                        target = (output["ip"], output["port"])
                        await asyncio.get_event_loop().sock_sendto(sock, data, target)
                        self.last_sent[f"{output['ip']}:{output['port']}"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            except asyncio.CancelledError:
                break

relay_manager = UDPRelayManager()

@app.on_event("startup")
async def startup():
    await relay_manager.start_relays()

@app.on_event("shutdown")
async def shutdown():
    await relay_manager.stop_relays()

@app.get("/admin/dashboard")
async def admin_dashboard(request: Request):
    stats = relay_manager.last_sent
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "config": relay_manager.config,
        "stats": stats
    })

@app.post("/admin/update_config")
async def update_config(
    request: Request,
    primary_port: int = Form(...),
    secondary_port: int = Form(...),
    outputs_json: str = Form(...)
):
    try:
        outputs = json.loads(outputs_json)
    except json.JSONDecodeError:
        outputs = []

    relay_manager.config["input_1"] = {"port": primary_port}
    relay_manager.config["input_2"] = {"port": secondary_port}
    relay_manager.config["outputs"] = outputs
    relay_manager.save_config()
    await relay_manager.start_relays()
    return RedirectResponse(url="/admin/dashboard", status_code=303)
