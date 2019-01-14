import abc
import asyncio
import pickle
import uuid

import msgpack
from multiprocessing import Process
import pynng

from serializers import PickleSerializer


class ManagerPull:

    def __init__(self, manager, host="0.0.0.0", port=41000):
        self.manager = manager
        self.pull = pynng.Pull0()
        self.pull.tcp_keepalive = True
        self.pull.listen("tcp://%s:%s" % (host, port))

        loop = asyncio.get_event_loop()

        loop.create_task(self.async_response())

    async def async_response(self):
        while True:
            serialized_message = await self.pull.arecv()
            #message = self.manager.serializer.deserialize(serialized_message)


            #await self.manager.pub.pub.asend(serialized_message)


class ManagerPub:
    def __init__(self, manager, host="0.0.0.0", port=41001):
        self.manager = manager
        self.pub = pynng.Pub0(listen="tcp://%s:%s" % (host, port))





class Manager(Process):

    def __init__(self, host, port, serializer=PickleSerializer):
        Process.__init__(self)
        self.daemon = True
        self.loop = None  # Init in RUN

        self.setup_host = host
        self.setup_port = port

        self.s_response = None  # The socket which takes care of initial messaging

        self.serializer = serializer()  # The serializer used to serialize/deserialize messages


    def run(self):
        """Create new event loop for the forked process."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        self.pub = ManagerPub(manager=self)
        self.pull = ManagerPull(manager=self)

        #self.loop.run_until_complete(self.async_run())
        self.loop.run_forever()



if __name__ == "__main__":
    x = Manager(host="0.0.0.0", port=41000, serializer=PickleSerializer)
    x.start()
    x.join()
