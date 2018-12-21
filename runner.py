import os
import asyncio
import sys
import time
import ujson
from aiopipe import aiopipe
from multiprocessing import Process
import uuid

PIPE_TERMINATOR = b'/='


class Executor:

    def __init__(self, loop=asyncio.get_event_loop(), process_count=os.cpu_count()):
        self.rx, self.tx = aiopipe()
        self.max_process_count = process_count
        self.loop = loop
        self.pool = {}

        self.loop.create_task(self.add_process_queue())
        self.loop.create_task(self.on_process_message())
        self.loop.run_forever()

    async def add_process_queue(self):
        while True:

            n_new_processes = self.max_process_count - len(self.pool)

            for _ in range(n_new_processes):
                uid = uuid.uuid4().hex
                p = Worker(uid, self.tx)
                p.daemon = True
                p.start()
                self.pool[uid] = p

            await asyncio.sleep(.05)

    async def on_process_message(self):
        stream = await self.rx.open(self.loop)
        n = 0
        last_stat = time.time()
        while True:
            msg = await stream.readuntil(PIPE_TERMINATOR)
            n += 1

            if time.time() > last_stat + 1.0:

                start = time.time()
                n = 0

    async def on_process_quit(self):
        while True:


class Worker(Process):

    def __init__(self, uid, tx):
        super().__init__()
        self.uid = uid
        self.tx = tx
        self.loop = None

    def run(self):
        self.loop = asyncio.new_event_loop()
        self.loop.create_task(self.feedback_test())
        self.loop.run_forever()

    async def feedback_test(self):

        writer = await self.tx.open(self.loop)
        while True:
            writer.write(Worker.encode({
                "glossary": {
                    "title": "example glossary",
                    "GlossDiv": {
                        "title": "S",
                        "GlossList": {
                            "GlossEntry": {
                                "ID": "SGML",
                                "SortAs": "SGML",
                                "GlossTerm": "Standard Generalized Markup Language",
                                "Acronym": "SGML",
                                "Abbrev": "ISO 8879:1986",
                                "GlossDef": {
                                    "para": "A meta-markup language, used to create markup languages such as DocBook.",
                                    "GlossSeeAlso": ["GML", "XML"]
                                },
                                "GlossSee": "markup"
                            }
                        }
                    }
                }
            }
                , json=True))
            await writer.drain()
            #await asyncio.sleep(1)

    @staticmethod
    def encode(message, json=False):
        if json:
            return ujson.encode(message).encode('utf-8') + PIPE_TERMINATOR
        return message.encode('utf-8') + PIPE_TERMINATOR

if __name__ == "__main__":

    if sys.platform == "win32":
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
    else:
        loop = asyncio.get_event_loop()

    x = Executor(loop=loop, process_count=2)

