import asyncio
import os
import random
import ujson

import aiohttp
from aiohttp import web

from logger import manager_log
from messages import SubscriptionOK, PollRequestMessage, SubscriptionFail
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
        #print("Sending: ", data)
        data["channels"] = ws.channels if channels is None else channels
        await ws.send_str(ujson.dumps(data))

    async def ws_tree(self, ws, type, payload):
        data = [x.toDict() for x in self.manager._remote_endpoints]

        await self.send(ws, {
            "services": data
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
        self._loop.create_task(self.poll_endpoint_stats())
        self._loop.create_task(self.create_webserver(host=self.host, port=8080))
        self._loop.create_task(self.www.broadcast_loop())
        self._loop.run_forever()

    async def on_client_message(self, client, x):
        cmd = getattr(self, x.command, self.not_implemented)
        await cmd(client, x.command, x.payload)

    async def not_implemented(self, client, command, payload):
        client.ready = False
        print("Client attempts to call unimplemented function!")

    async def quit(self, client, command, payload):
        client.ready = False

    async def subscribe_service(self, client, command, payload):
        service = payload["service"]
        service_id = payload["id"]

        try:
            selection = [x for x in self._remote_endpoints if x.type == service]

            if not selection:
                subscription_fail = SubscriptionFail(
                    id=service_id,
                    service=service
                )

                await client.write(subscription_fail)
                return False

            remote_endpoint = random.choice(selection)

            """Register the remote endpoint as a remote in the service_list"""
            client.metadata["remotes"].append(remote_endpoint)

            subscription_ok = SubscriptionOK(
                id=service_id,
                service=remote_endpoint.type,
                host=remote_endpoint.metadata["host"],
                port=remote_endpoint.metadata["port"]
            )

            await client.write(subscription_ok)

        except KeyError as e:

            raise NotImplementedError("NOT IMPLEMENTED HANDLER FOR WHEN NO SUBSCRIPTION IS AVAILABLE!")

    async def register_service(self, client, command, payload):
        service = payload["service"]
        service_endpoint = payload['local_endpoint']
        service_pid = payload['pid']
        service_depth = payload['depth']

        client.metadata.update(dict(
            pid=service_pid,
            depth=service_depth,
            remotes=[],
            host=payload['local_endpoint'][0],  # Local in this case is the manager's remote
            port=payload['local_endpoint'][1],
            service=service,
            id=client.id,
            throughput=0
        ))
        client.type = service

        manager_log.warning("[%s]: %s (%s:%s) was registered.",
                            self._service_name, client.type, client.host, client.port)

    async def unregister_service(self, client, payload, service):
        # TODO will crash.
        raise NotImplementedError("IMPLEMENT!")
        if service in self.services:
            self.services[service].pop(self.services[service].find(client))
            manager_log.warning("Unregistered %s from client %s", service, client.name)

    async def poll_response(self, client, command, payload):
        client.diagnosis.update(payload)

    async def poll_endpoint_stats(self):
        """
        Polls all remote endpoints for statistics. This keeps track of all endpoint statuses to easily debug.
        :return:
        """

        poll_request = PollRequestMessage()
        while True:
            for service in self._remote_endpoints:
                await service.write(poll_request)

            await asyncio.sleep(1.0)


