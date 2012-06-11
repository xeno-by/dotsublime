from ensime_client_socket import EnsimeClientListener, EnsimeClientSocket

class EnsimeClient(EnsimeClientListener, EnsimeCommon):
  def __init__():
    self.init_counters()
    methods = filter(lambda m: m[0].startswith("inbound_"), inspect.getmembers(self, predicate=inspect.ismethod))
    self._inbound_handlers = dict((":" + m[0]["inbound_".length:], m[1]) for m in methods)
    self._outbound_handlers = {}

  def startup(self):
    with open(self.port_file) as f: port = int(f.read())
    self.log_server("Launching ENSIME client socket at port " + str(port))
    self.socket = EnsimeClientSocket(port, [self, self.controller])

  def shutdown(self):
    try:
      self.sync_req([sym("swank:shutdown-server")])
      self.socket.close()
      self.socket = None
    except:
      self.log_server("Error shutting down:")
      self.log_server(sys.exc_info()[1])

  ############### INBOUND MESSAGES ###############

  def on_client_async_data(self, data):
    self.log_client("SEND ASYNC RESP: " + str(data))
    self.feedback(str(data))

    try:
      msg_type = str(data[0])
      msg_id = data[-1]
      if msg_type == ":return":
        handler = self._outbound_handlers.get(msg_id)
        if handler:
          del self._outbound_handlers[msg_id]

          reply_type = str(data[1][0])
          # (:return (:ok (:project-name nil :source-roots ("D:\\Dropbox\\Scratchpad\\Scala"))) 2)
          if reply_type == ":ok":
            payload = data[1][1]
            handler(payload)
          # (:return (:abort 210 "Error occurred in Analyzer. Check the server log.") 3)
          elif reply_type == ":abort":
            detail = data[1][2]
            sublime.status_message(detail)
          # (:return (:error NNN "SSS") 4)
          elif reply_type == ":error":
            detail = data[1][2]
            sublime.error_message(detail)
          else:
            self.log_client("unexpected reply type: " + reply_type)
      else:
        # (:compiler-ready)
        message_type = str(data[0])
        handler = self._inbound_handlers.get(message_type)
        if handler:
          payload = data[1] if len(data) > 0 else None
          handler(payload)
        else:
          self.log_client("unexpected message type: " + message_type)
    except Exception as e:
      self.log_client("error when handling message: " + str(data))
      self.log_client(traceback.format_exc())

  def inbound_compiler_ready(self, payload):
    filename = self.plugin_root + "/Encouragements.txt"
    lines = [line.strip() for line in open(filename)]
    msg = self.lines[random.randint(0, len(self.lines) - 1)]
    sublime.status_message(msg + " This could be the start of a beautiful program, " + getpass.getuser().capitalize()  + ".")

  def inbound_background_message(self, payload):
    sublime.status_message(str(payload))

  def inbound_scala_notes(self, payload):
    notes = self.codec.decode_notes(payload)
    self.add_notes(notes)

  def inbound_clear_notes(self, payload):
    self.clear_notes()

  ############### OUTBOUND MESSAGES ###############

  def async_req(self, to_send, on_complete = None, msg_id = None):
    if self.ready and not self.connected:
      self.client.connect()

    msg_id = self.next_message_id()
    self._outbound_handlers[msg_id] = on_complete
    msg_str = sexp.to_string([key(":swank-rpc"), to_send, msg_id])
    msg_str = "%06x" % len(data) + data

    self.feedback(msg_str)
    self.log_client("SEND ASYNC REQ: " + msg_str)
    self.client.send(msg_str)

  def sync_req(self, to_send):
    msg_id = self.next_message_id()
    msg_str = sexp.to_string([key(":swank-rpc"), to_send, msg_id])
    msg_str = "%06x" % len(data) + data

    self.feedback(msg_str)
    self.log_client("SEND SYNC REQ: " + msg_str)
    resp = self.client.sync_send(msg_str, msg_id)
    self.log_client("SEND SYNC RESP: " + msg_resp)
    return resp

  ############### UTILITIES ###############

  def init_counters(self):
    self._counter = 0
    self._counterLock = threading.RLock()

  def next_message_id(self):
    self._counterLock.acquire()
    try:
      self._counter += 1
      return self._counter
    finally:
      self._counterLock.release()

  def feedback(self, msg):
    msg = msg.replace("\r\n", "\n").replace("\r", "\n") + "\n"
    self.view_insert(self.cv, msg)
