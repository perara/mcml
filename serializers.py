import abc
import pickle


class Serializer(abc.ABC):

    def __init__(self):
        pass

    def serialize(self, d):
        raise NotImplementedError("The serializer has not implemented Serializer.serialize(x).")

    def deserialize(self, d):
        raise NotImplementedError("The serializer has not implemented Serializer.deserialize(x).")


class PickleSerializer(Serializer):

    def deserialize(self, d):
        return pickle.loads(d)

    def serialize(self, d):
        return pickle.dumps(d)

