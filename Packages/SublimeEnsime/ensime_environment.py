import threading 
import sublime

class EnsimeEnvironment:

  def __init__(self):
    self.settings = sublime.load_settings("Ensime.sublime-settings")
    self._clientLock = threading.RLock()
    self._client = None

  def set_client(self, client):
    self._clientLock.acquire()
    try:
      self._client = client
      return self._client
    finally:
      self._clientLock.release()

  def client(self):
    return self._client


ensime_env = EnsimeEnvironment()

