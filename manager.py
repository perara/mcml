import asyncio
import os
import random
import ujson

import aiohttp
from aiohttp import web

from logger import manager_log
from messages import Subscription
from tcpserver import TCPServer


class WebServer:

    def __init__(self, manager):
        self.manager = manager
        self.script_path = os.path.dirname(os.path.realpath(__file__))
        self.dist = os.path.join(self.script_path, "www", "dist", "www")
        self.ws_clients = []

    async def broadcast_loop(self):
        while True:
            await self.send_tree()
            await asyncio.sleep(5)

    async def index(self, request):
        path = request.rel_url
        full_path = self.dist + str(path)
        exists = os.path.exists(full_path) and os.path.isfile(full_path)

        if exists:
            return web.FileResponse(full_path)
        return web.FileResponse(os.path.join(self.dist, "index.html"))

    async def ws_handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        self.ws_clients.append(ws)
        setattr(ws, "channels", {"*"})

        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:

                data = ujson.loads(msg.data)
                type = data["type"]
                payload = data["payload"]

                fn = getattr(self, "ws_" + type, self.ws_notfound)
                await fn(ws, type, payload)

            elif msg.type == aiohttp.WSMsgType.ERROR:
                print('ws connection closed with exception %s' %
                      ws.exception())

        self.ws_clients.remove(ws)
        print('websocket connection closed')

        return ws

    async def ws_subscribe(self, ws, type, payload):
        channel = payload["channel"]
        ws.channels.add(channel)

        """await self.send(ws, dict(
            type=type,
            payload="Successfully subscribed to " + channel
        ))"""

    async def ws_notfound(self, ws, type, payload):

        await self.send(ws, dict(
            type="notfound",
            payload="Could not find the requested ws route %s" % type
        ))

    async def send(self, ws, data, channels=None):
        print("Sending: ", data)
        data["channels"] = ws.channels if channels is None else channels
        await ws.send_str(ujson.dumps(data))

    async def ws_tree(self, ws, type, payload):
        await self.send(ws, {
            "services": self.manager.services
        }, channels=[type])

    async def send_tree(self):
        for ws in self.ws_clients:
            if "tree" in ws.channels:
                await self.ws_tree(ws, type="tree", payload={})


class Manager(TCPServer):

    def __init__(self, host="0.0.0.0", port=21000):
        TCPServer.__init__(self)

        self.host = host
        self.port = port
        self.loop = None
        self.clients = dict()
        self.services = dict()
        self.www = WebServer(self)

    async def create_webserver(self, host, port):
        app = web.Application()
        app.router.add_get('/', self.www.index)
        app.router.add_get("/ws", self.www.ws_handler)
        app.router.add_get('/{path:.*}', self.www.index)


        #app.router.add_static('/', self.www.dist)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()

    def run(self):
        self._loop = asyncio.new_event_loop()
        self._loop.create_task(self.create_server(host=self.host, port=self.port))
        self._loop.create_task(self.create_webserver(host=self.host, port=8080))
        self._loop.create_task(self.www.broadcast_loop())
        self._loop.run_forever()

    async def on_client_message(self, client, x):
        cmd = getattr(self, x.command, self.not_implemented)
        await cmd(client, x.payload, *x.args)

    async def not_implemented(self, client, payload, *args):
        client.ready = False
        print("Client attempts to call unimplemented function!")

    async def subscribe_service(self, client, payload, service):

        try:
            remote_endpoint_key = random.choice(list(self.services[service].keys()))
            remote_endpoint = self.services[service][remote_endpoint_key]

            """Register the remote endpoint as a remote in the service_list"""
            client.service["remotes"][remote_endpoint_key] = remote_endpoint

            await client.write(Subscription(endpoint=remote_endpoint["local"]))
        except KeyError as e:
            pass # client.write()  # TOdo missing service in manager

    async def quit(self, client, command, **kwargs):
        client.ready = False

    async def register_service(self, client, payload, service):
        if service not in self.services:
            self.services[service] = {}

        # TODO. not really clean
        service_endpoint = ':'.join(str(x) for x in payload['local_endpoint'])
        service_pid = payload['pid']
        service_depth = payload['depth']

        self.services[service][service_endpoint] = dict(
            pid=service_pid,
            depth=service_depth,
            remotes={},
            local=payload['local_endpoint']
        )

        """Add reference to the service in the client object"""
        client.service = self.services[service][service_endpoint]

        manager_log.warning("Registered %s as a service at %s", service, client.name)

    async def unregister_service(self, client, payload, service):
        # TODO will crash.
        if service in self.services:
            self.services[service].pop(self.services[service].find(client))
            manager_log.warning("Unregistered %s from client %s", service, client.name)