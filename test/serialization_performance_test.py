import pickle
import time
import numpy as np
import msgpack
import json
import lima
import serpy as serpy


class Message:

    def __init__(self, payload):
        self.command = "some-command"
        self.args = ("arg1", "arg2")
        self.payload = payload

class SerpyMessage(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    command = serpy.StrField()
    args = serpy.Field()
    payload = serpy.Field()

if __name__ == "__main__":


    for i in range(1, 16):
        size = 2**i
        for type in [np.uint8, np.uint64, np.float32]:
            data = np.zeros((size, size, 3), dtype=type)

            time.sleep(.1)

            msg = Message(data)


            """
            # pickle
            """
            s = time.time()
            data = pickle.dumps(msg, protocol=pickle.HIGHEST_PROTOCOL)
            print("Pickle: ", time.time() - s)

            """
            # serpy
            """
            s = time.time()
            data = SerpyMessage(msg)
            print(data.)
            print("uJSON: ", time.time() - s)




            """
            # msgpack
            """
            #s = time.time()
            #data = msgpack.packb(msg, use_bin_type=True)
            #print("Msgpack: ", time.time() - s)


