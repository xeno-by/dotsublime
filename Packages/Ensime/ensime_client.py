import os, sys, stat, time, datetime, re
import functools, socket, threading
import sublime_plugin, sublime
import sexp
from string import strip
from sexp import key,sym
import ensime_notes
import traceback
import Queue

class EnsimeMessageHandler:

  def on_data(self, data):
    pass

  def on_disconnect(self, reason):
    pass

class EnsimeServerClient:

  def __init__(self, project_root, handler):
    self.project_root = project_root
    self.connected = False
    self.handler = handler
    self._lock = threading.RLock()
    self._connect_lock = threading.RLock()
    self._receiver = None

  def port(self):
    return int(open(self.project_root + "/.ensime_port").read()) 

  def receive_loop(self):
    while self.connected:
      try:
        res = self.client.recv(4096)
        print "RECV: " + unicode(res, "utf-8")
        if res:
          len_str = res[:6]
          msglen = int(len_str, 16) + 6
          msg = res[6:msglen]
          nxt = strip(res[msglen:])
          while len(nxt) > 0 or len(msg) > 0:
            form = sexp.read(msg)
            sublime.set_timeout(functools.partial(self.handler.on_data, form), 0)
            if len(nxt) > 0:
              msglen = int(nxt[:6], 16) + 6
              msg = nxt[6:msglen]
              nxt = strip(nxt[msglen:])
            else: 
              msg = ""
              msglen = ""
        else:
          self.set_connected(False)
      except Exception as e:
        print "*****    ERROR     *****"
        print e
        self.handler.on_disconnect("server")
        self.set_connected(False)

  def set_connected(self, val):
    self._lock.acquire()
    try:
      self.connected = val
    finally:
      self._lock.release()

  def start_receiving(self):
    t = threading.Thread(name = "ensime-client-" + str(self.port()), target = self.receive_loop)
    t.setDaemon(True)
    t.start()
    self._receiver = t

  def connect(self):
    self._connect_lock.acquire()
    try:
      s = socket.socket()
      s.connect(("127.0.0.1", self.port()))
      self.client = s
      self.set_connected(True)
      self.start_receiving()
      return s
    except socket.error as e:
      # set sublime error status
      self.set_connected(False)
      sublime.error_message("Can't connect to ensime server:  " + e.args[1])
    finally:
      self._connect_lock.release()

  def send(self, request):
    try:
      if not self.connected:
        self.connect()
      self.client.send(request)
    except:
      self.handler.disconnect("server")
      self.set_connected(False)

  def sync_send(self, request, msg_id): 
    self._connect_lock.acquire()
    try:
      s = socket.socket()
      s.connect(("127.0.0.1", self.port()))
      try:
        s.send(request)
        result = ""
        keep_going = True
        nxt = ""
        while keep_going: 
          res = nxt + s.recv(4096)
          msglen = int(res[:6], 16) + 6
          msg = res[6:msglen]
          if (len(msg) + 6) == msglen:
            nxt = strip(res[msglen:])
            while len(nxt) > 0 or len(msg) > 0:
              if len(nxt) > 0:
                sublime.set_timeout(functools.partial(self.handler.on_data, sexp.read(msg)), 0)
                msglen = int(nxt[:6], 16) + 6
                msg = nxt[6:msglen]
                nxt = strip(nxt[msglen:])
              else: 
                nxt = ""
                break
            result = sexp.read(msg)
            keep_going = result == None or msg_id != result[-1]
            if keep_going:
              sublime.set_timeout(functools.partial(self.handler.on_data, result), 0)
          else:
            nxt = res 
            
        return result
      except Exception as error:
        print error
      finally:
        if s: 
          s.close() 
    except Exception as error:
      print error
    finally:
      self._connect_lock.release()

  def close(self):
    self._connect_lock.acquire()
    try:
      if self.client:
        self.client.close()
      self.connect = False
    finally:
      self._connect_lock.release()    

class EnsimeClient(EnsimeMessageHandler):

  def __init__(self, settings, window, project_root):
    def ignore(d): 
      None      

    def clear_notes(lang):
      self.note_map = {}
      for v in self.window.views():
        v.run_command("ensime_notes", 
                      {"lang": lang, 
                       "action": "clear"})

    def add_notes(lang, data):
      m = sexp.sexp_to_key_map(data)
      new_notes = [sexp.sexp_to_key_map(form) for form in m[":notes"]]

      for note in new_notes:
        key = os.path.realpath(str(note[":file"]))
        view_notes = self.note_map.get(key) or []
        view_notes.append(note)
        self.note_map[key] = view_notes

      for v in self.window.views():
        key = os.path.realpath(str(v.file_name()))
        notes = self.note_map.get(key) or []
        v.run_command(
          "ensime_notes",
          { "lang": lang, "action": 
            "add", "value": notes })

    # maps filenames to lists of notes
    self.note_map = {}

    self.settings = settings
    self.project_root = project_root
    self._ready = False
    self._readyLock = threading.RLock()
    self.window = window
    self.output_view = self.window.get_output_panel("ensime_messages")
    self.message_handlers = dict()
    self.procedure_handlers = dict()
    self._counter = 0
    self._procedure_counter = 0
    self._counterLock = threading.RLock()
    self.client = EnsimeServerClient(project_root, self)
    self._reply_handlers = {
      ":ok": lambda d: self.message_handlers[d[-1]](d),
      ":abort": lambda d: sublime.status_message(d[-1]),
      ":error": lambda d: sublime.error_message(d[-1])
    }
    self._server_message_handlers = {
      ":clear-all-scala-notes": lambda d: clear_notes("scala"),
      ":clear-all-java-notes": lambda d: clear_notes("java"),
      ":scala-notes": lambda d: add_notes("scala", d),
      ":java-notes": lambda d: add_notes("java", d),
      ":compiler-ready": 
      lambda d: self.window.run_command("random_words_of_encouragement"),
      ":full-typecheck-finished": ignore,
      ":indexer-ready": ignore,
      ":background-message": sublime.status_message
    }
      
  def ready(self):
    return self._ready

  def set_ready(self):
    self._readyLock.acquire()
    try:
      self._ready = True
      return self.ready()
    finally:
      self._readyLock.release()

  def set_not_ready(self):
    self._readyLock.acquire()
    try:
      self._ready = False
      return self.ready()
    finally:
      self._readyLock.release()

  def remove_handler(self, handler_id):
    del self.message_handlers[handler_id]

  def on_data(self, data):
    print "on_data: " + str(data)
    self.feedback(str(data))
    # match a message with a registered response handler.
    # if the message has no registered handler check if it's a 
    # background message.
    if data[0] == key(":return"):
      th = self._reply_handlers

      # if data[0][0][0][1:] == "procedure-id" and self.procedure_handlers.has_key(data[0][0][1]):
      #   self.procedure_handlers[data[0][0][1]](data)
      #   del self.proceure_handlers[data[0][0][1]]

      if self.message_handlers.has_key(data[-1]):
        reply_type = str(data[1][0])
        th[reply_type](data)
      else:
        print "Unhandled message: " + str(data)
    else:
        self.handle_server_message(data)

  def handle_server_message(self, data):
    print "handle_server_message: " + str(data)
    handled = self._server_message_handlers
    try:
      key = str(data[0])
      if handled.has_key(key):
        handled[key](data[-1])
      else:
        print "Received a message from the server:"
        print str(data)
    except Exception as e:
      print "Error when handling server message: " + str(data)
      traceback.print_exc(file=sys.stdout)

  def next_message_id(self):
    self._counterLock.acquire()
    try:
      self._counter += 1
      return self._counter
    finally:
      self._counterLock.release()

  def next_procedure_id(self):
    self._counterLock.acquire()
    try:
      self._procedure_counter += 1
      return self._procedure_counter
    finally:
      self._counterLock.release()

  def feedback(self, msg):
    self.window.run_command("ensime_update_messages_view", { 'msg': msg })

  def on_disconnect(self, reason = "client"):
    self._counterLock.acquire()
    try:
      self._counter = 0
      self._procedure_counter = 0
    finally:
      self._counterLock.release()
      
    if reason == "server":
      sublime.error_message("The ensime server was disconnected, you might want to restart it.")

  def project_file(self): 
    if self.ready:
      return os.path.join(self.project_root, ".ensime")
    else:
      return None

  def project_config(self):
    try:
      src = open(self.project_file()).read() if self.project_file() else "()"
      conf = sexp.read(src)
      return conf
    except StandardError:
      return []
    
  
  def prepend_length(self, data): 
    return "%06x" % len(data) + data

  def format(self, data, count = None):
    if count:
      return [key(":swank-rpc"), data, count]
    else:
      return [key(":swank-rpc"), data]

  
  def req(self, to_send, on_complete = None, msg_id = None): 
    msgcnt = msg_id
    if msg_id == None:
      msgcnt = self.next_message_id()
      
    if self.ready() and not self.client.connected:
      self.client.connect()

    msg = None
    if on_complete != None:
      self.message_handlers[msgcnt] = on_complete
      msg = self.format(to_send, msgcnt)
    else:
      msg = self.format(to_send)

    msg_str = sexp.to_string(msg)

    print "SEND: " + msg_str

    sublime.set_timeout(functools.partial(self.feedback, msg_str), 0)
    self.client.send(self.prepend_length(msg_str))

  def sync_req(self, to_send):
    msgcnt = self.next_message_id()
    msg_str = sexp.to_string(self.format(to_send, msgcnt))
    print "SEND: " + msg_str
    return self.client.sync_send(self.prepend_length(msg_str), msgcnt)
    

  def disconnect(self):
    self._counterLock.acquire()
    try:
      self._counter = 0
      self._procedure_counter = 0
    finally:
      self._counterLock.release()
    self.client.close()

  def handshake(self, on_complete): 
    self.req([sym("swank:connection-info")], on_complete)

  def __initialize_project(self, conf, subproj_name, on_complete):
    conf = conf + [key(":root-dir"), self.project_root]
    conf = conf + [key(":active-subproject"), subproj_name]
    self.req([sym("swank:init-project"), conf], on_complete)

  def initialize_project(self, on_complete):
    conf = self.project_config()
    m = sexp.sexp_to_key_map(conf)
    subprojects = [sexp.sexp_to_key_map(p) for p in m[":subprojects"]]
    names = [p[":name"] for p in subprojects]
    if len(names) > 1:
      self.window.show_quick_panel(
        names, lambda i: self.__initialize_project(conf,names[i],on_complete))
    elif len(names) == 1:
      self.__initialize_project(conf,names[0],on_complete)
    else:
      self.__initialize_project(conf,"NA",on_complete)

  def format_source(self, file_path, on_complete):
    self.req([sym("swank:format-source"),[file_path]], on_complete)

  def type_check_all(self, on_complete):
    self.req([sym("swank:typecheck-all")], on_complete)

  def type_check_file(self, file_path, on_complete):
    self.req([sym("swank:typecheck-file"), file_path], on_complete)

  def organize_imports(self, file_path, on_complete):
    self.req([sym("swank:perform-refactor"),
              self.next_procedure_id(),
              sym("organizeImports"), 
              [sym("file"),file_path], 
              True], on_complete)
  
  def perform_organize(self, previous_id, msg_id, on_complete):
    self.req([sym("swank:exec-refactor"),
              int(previous_id), 
              sym("organizeImports")], 
             on_complete, int(msg_id))

  def inspect_type_at_point(self, file_path, position, on_complete):
    self.req([sym("swank:type-at-point"),
              file_path,
              int(position)], 
             on_complete)
  
  def complete_member(self, file_path, position):
    return self.sync_req([sym("swank:completions"), file_path, position, 0])
