from ensime_common import *
from ensime_server_process import EnsimeServerListener
from ensime_client_socket import EnsimeClientListener

class EnsimeController(EnsimeCommon, EnsimeClientListener, EnsimeServerListener):
  def __init__(self):
    self.running = False
    self.ready = False
    self.client = None
    self.server = None

  def __getattr__(self, name):
    if name == "connected":
      # todo. can I write this in a concise way?
      return self.client and self.client.socket and hasattr(self.client.socket, "connected") and self.client.socket.connected
    raise AttributeError()

  def startup(self):
    self.lifecycleLock.acquire()
    try:
      if not self.running:
        self.in_transition = True
        self.controller = self
        self.running = True
        _, port_file = tempfile.mkstemp("ensime_port")
        self.port_file = port.file
        self.server = EnsimeServer(self.window, port_file)
        self.server.startup()
    except:
      self.controller = None
      self.running = False
    finally:
      self.in_transition = False
      self.lifecycleLock.release()

  def on_server_data(self, data):
    if not self.ready and re.search("Wrote port", str_data):
      self.ready = True
      with open(self.port_file) as f: port = int(f.read())
      self.client = EnsimeClient(self.window, port)
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
    self.lifecycleLock.acquire()
    try:
      if self.running:
        self.in_transition = True
        try:
          self.clear_notes()
        except:
          pass
        try:
          self.client.shutdown()
        except:
          pass
        try:
          self.server.shutdown()
        except:
          pass
    finally:
      self.running = False
      self.controller = None
      self.in_transition = False
      self.lifecycleLock.release()
