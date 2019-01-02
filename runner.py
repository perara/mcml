import os
import asyncio
import random
import sys
import time
import ujson
from aiopipe import aiopipe
from multiprocessing import Process, Event
import uuid
from logger import mcml_log

PIPE_TERMINATOR = b'/='


class Executor:

    def __init__(self, loop=asyncio.get_event_loop(), workers=os.cpu_count()-1, receivers=1):
        self.rx, self.tx = aiopipe()
        self.worker_count = workers
        self.receiver_count = receivers
        self.receiver_iterator = 0

        self.receivers = []
        self.worker_cls = Worker

        self.loop = loop
        self.pool = {}

    def set_receiver(self, receiver_cls):
        self.receivers.clear()

        for i in range(self.receiver_count):
            r = receiver_cls(tx=self.tx)
            r.daemon = True
            r.start()
            self.receivers.append(r)
        mcml_log.debug("Added %s receivers of class %s.", len(self.receivers), type(receiver_cls(self.tx)).__name__)

    def set_worker(self, worker_cls):
        self.worker_cls = worker_cls

    def start(self):
        self.loop.create_task(self.worker_queue())
        self.loop.create_task(self.on_process_message())
        self.loop.create_task(self.on_process_quit())
        self.loop.run_forever()

    async def worker_queue(self):
        while True:

            n_new_workers = self.worker_count - len(self.pool)

            for _ in range(n_new_workers):
                uid = uuid.uuid4().hex
                mcml_log.debug("Starting worker with id %s", uid)
                p = self.worker_cls(uid, self.receivers[self.receiver_iterator % self.receiver_count].tx)
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
            dels = []
            for uid, p in self.pool.items():
                if not p.is_alive():
                    p.join()
                    dels.append(uid)

            for d in dels:
                del self.pool[d]

            await asyncio.sleep(.1)


class Worker(Process):

    def __init__(self, uid, tx):
        Process.__init__(self)
        self.exit = Event()
        self.uid = uid
        self.tx = tx
        self._loop = None
        self.sequence = []
        self.writer = None

    def run(self):
        self._loop = asyncio.new_event_loop()

        self._loop.run_until_complete(self.runner())

    async def runner(self):
        self.writer = await self.tx.open(self._loop)

        for seq in self.sequence:
            seq()
        self.terminate()

    async def send(self, data):
        self.writer.write(Worker.encode(data))
        await self.writer.drain()

    def terminate(self):
        self.exit.set()

    @staticmethod
    def encode(message, json=False):
        if json:
            return ujson.encode(message).encode('utf-8') + PIPE_TERMINATOR
        return message.encode('utf-8') + PIPE_TERMINATOR


class Receiver(Process):

    def __init__(self, tx):
        self.uid = uuid.uuid4().hex
        Process.__init__(self)
        self.rx, self.tx = aiopipe()
        self.parent_tx = tx
        self.transforms = []
        self._loop = None

    def run(self):
        mcml_log.debug("Started Receiver with id %s", self.uid)
        self._loop = asyncio.new_event_loop()
        self._loop.run_until_complete(self.on_message())

    async def on_message(self):
        stream = await self.rx.open(self._loop)
        while True:
            data = await stream.readuntil(PIPE_TERMINATOR)
            data = await self._process(data)

            self.parent_tx.write(data)
            await self.parent_tx.drain()

    async def _process(self, data):
        for transform in self.transforms:
            data = await transform(data)
        return data

if __name__ == "__main__":

    if sys.platform == "win32":
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
    else:
        loop = asyncio.get_event_loop()

    class TransformReceiver(Receiver):
        def __init__(self, tx):
            super().__init__(tx)

            self.transforms.extend([self.resize, self.rgb_2_gray])

        def resize(self, x):
            return x

        def rgb_2_gray(self, x):
            return x

    class GameWorker(Worker):

        def __init__(self, uid, tx):
            super().__init__(uid, tx)

            self.sequence.extend([self.loop, self.cleanup])

        def loop(self):
            start = time.time() + random.randint(1, 20)

            while True:

                if time.time() > start:
                    break

        def cleanup(self):
            pass

    # Multiprocessor
    x = Executor(loop=loop, workers=2, receivers=1)
    x.set_receiver(TransformReceiver)
    x.set_worker(GameWorker)

    x.start()







