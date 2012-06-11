import re
import tempfile
import traceback
from ensime_common import *
from ensime_server import EnsimeServer
from ensime_server_process import EnsimeServerListener
from ensime_client import EnsimeClient
from ensime_client_socket import EnsimeClientListener
from sexp.sexp import sym

class EnsimeController(EnsimeCommon, EnsimeClientListener, EnsimeServerListener):
  def __init__(self, owner):
    super(type(self).__mro__[0], self).__init__(owner)
    self.running = False
    self.ready = False
    self.client = None
    self.server = None

  def __getattr__(self, name):
    if name == "connected":
      # todo. can I write this in a concise way?
      return self.client and self.client.socket and hasattr(self.client.socket, "connected") and self.client.socket.connected
    return super(type(self).__mro__[0], self).__getattr__(name)

  def startup(self):
    self.env.lifecycleLock.acquire()
    try:
      if not self.running:
        self.env.in_transition = True
        self.env.controller = self
        self.running = True
        _, port_file = tempfile.mkstemp("ensime_port")
        self.port_file = port_file
        self.server = EnsimeServer(self.owner, port_file)
        self.server.startup()
    except:
      self.env.controller = None
      self.running = False
      raise
    finally:
      self.env.in_transition = False
      self.env.lifecycleLock.release()

  def on_server_data(self, data):
    if not self.ready and re.search("Wrote port", data):
      self.ready = True
      self.client = EnsimeClient(self.owner, self.port_file)
      self.client.startup()
      self.client.async_req([sym("swank:connection-info")], self.handle_handshake)

  def handle_handshake(self, server_info):
    if server_info[1][0] == key(":ok"):
      sublime.status_message("Initializing... ")
      req = codec.encode_initialize_project(conf)
      self.async_req(req, lambda: sublime.status_message("Ensime ready!"))
    else:
      sublime.error_message("There was problem initializing ensime, msgno: " + str(server_info[2]) + ".")

  def shutdown(self):
    self.env.lifecycleLock.acquire()
    try:
      if self.running:
        self.env.in_transition = True
        try:
          self.clear_notes()
        except:
          self.log("Error shutting down ensime UI:")
          self.log(traceback.format_exc())
        try:
          if self.client:
            self.client.shutdown()
        except:
          self.log_client("Error shutting down ensime client:")
          self.log(traceback.format_exc())
        try:
          if self.server:
            self.server.shutdown()
        except:
          self.log_server("Error shutting down ensime server:")
          self.log(traceback.format_exc())
    finally:
      self.running = False
      self.env.controller = None
      self.env.in_transition = False
      self.env.lifecycleLock.release()
