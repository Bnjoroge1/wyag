
from gitobject import GitObject
from gitlog import kvlm_parse, kvlm_serialize


class GitCommit(GitObject):
     fmt = b'commit'
     def init(self):
          super().init()
          self.kvlm = dict()

     def serialize(self):
          #convert python dict to git commit format
          return kvlm_serialize(self.kvlm)

     def deserialize(self, data):
          self.kvlm = kvlm_parse(data)
