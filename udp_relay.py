import asyncio
from datetime import datetime

class UDPRelayProtocol:
    def __init__(self, input_name, outputs, stats):
        self.outputs = [(host, int(port)) for host, port in outputs]
        self.stats = stats
        self.input_name = input_name

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        now = datetime.utcnow().isoformat()
        for host, port in self.outputs:
            self.transport.sendto(data, (host, port))
            key = f"{self.input_name} -> {host}:{port}"
            self.stats[key] = now

class UDPRelayManager:
    def __init__(self):
        self.config = {}
        self.listeners = {}
        self.stats = {}

    async def load_config(self, config):
        await self.shutdown()
        self.config = config
        loop = asyncio.get_running_loop()
        for name, cfg in config.get("inputs", {}).items():
            port = cfg["port"]
            outputs = cfg["outputs"]
            listen = await loop.create_datagram_endpoint(
                lambda: UDPRelayProtocol(name, outputs, self.stats),
                local_addr=("0.0.0.0", port)
            )
            self.listeners[name] = listen

    async def shutdown(self):
        for name, (transport, _) in self.listeners.items():
            transport.close()
        self.listeners.clear()

    def get_stats(self):
        return self.stats
