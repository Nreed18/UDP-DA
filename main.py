import asyncio
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import json
import os
from datetime import datetime

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


class UDPRelayManager:
    def __init__(self):
        self.config = {
            "inputs": {
                "input_1": {"port": 5001},
                "input_2": {"port": 5002}
            },
            "outputs": []
        }
        self.last_sent = {}

    def add_output(self, host: str, port: int):
        self.config["outputs"].append({"host": host, "port": port})
        self.last_sent[f"{host}:{port}"] = "Never"

    def remove_output(self, index: int):
        if 0 <= index < len(self.config["outputs"]):
            out = self.config["outputs"].pop(index)
            self.last_sent.pop(f"{out['host']}:{out['port']}", None)

    def get_stats(self):
        return self.last_sent


relay_manager = UDPRelayManager()


@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    stats = relay_manager.get_stats()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "config": relay_manager.config,
        "outputs": relay_manager.config["outputs"],
        "stats": stats,
    })


@app.post("/admin/add_output")
async def add_output(request: Request, host: str = Form(...), port: int = Form(...)):
    relay_manager.add_output(host, port)
    return RedirectResponse("/admin/dashboard", status_code=303)


@app.post("/admin/remove_output")
async def remove_output(request: Request, index: int = Form(...)):
    relay_manager.remove_output(index)
    return RedirectResponse("/admin/dashboard", status_code=303)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8082, reload=False)
