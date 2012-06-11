class EnsimeController(EnsimeCommon, EnsimeClientListener, EnsimeServerListener):
  def __init__(self, handlers):
    self.handlers = handlers
    self.client = EnsimeClient(self.window)
    self.server = EnsimeServer(self.window)

  def startup(self):
    self.lifecycleLock.acquire()
    try:
      if not self.running:
        self.in_transition = True
        self.controller = self
        self.running = True
        self.server.startup()
        self.client.startup()
    except:
      self.controller = None
      self.running = False
    finally:
      self.in_transition = False
      self.lifecycleLock.release()

  def on_server_data(self, data):
    if not self.ready and re.search("Wrote port", str_data):
      self.ready = True
      self.client.async_req([sym("swank:connection-info")], self.handle_handshake)

  def handle_handshake(self, server_info):
    if server_info[1][0] == key(":ok"):
      sublime.status_message("Initializing... ")
      req = self.codec.encode_initialize_project(conf)
      self.async_req(req, lambda: sublime.status_message("Ensime ready!"))
    else:
      sublime.error_message("There was problem initializing ensime, msgno: " + str(server_info[2]) + ".")

  def shutdown(self):
    self.lifecycleLock.acquire()
    try:
      if self.running:
        self.in_transition = True
        try: self.clear_notes() except: pass
        try: self.client.shutdown() except: pass
        try: self.server.shutdown() except: pass
    finally:
      self.running = False
      self.controller = None
      self.in_transition = False
      self.lifecycleLock.release()
