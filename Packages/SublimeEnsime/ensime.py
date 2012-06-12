import sublime
from sublime import *
from sublime_plugin import *
import os, threading, thread, socket, getpass, subprocess, killableprocess, tempfile
import functools, inspect, traceback, random, re
from sexp import sexp
from sexp.sexp import key, sym
from string import strip

class EnsimeApi:

  def type_check_file(self, file_path, on_complete = None):
    req = ensime_codec.encode_type_check_file(file_path)
    self.env.controller.client.async_req(req, on_complete)

  def add_notes(self, notes):
    self.env.notes += notes
    for i in range(0, self.w.num_groups()):
      v = self.w.active_view_in_group(i)
      EnsimeHighlights(v).refresh()

  def clear_notes(self):
    self.env.notes = []
    for i in range(0, self.w.num_groups()):
      v = self.w.active_view_in_group(i)
      EnsimeHighlights(v).refresh()

  def inspect_type_at_point(self, file_path, position, on_complete):
    req = ensime_codec.encode_inspect_type_at_point(file_path, position)
    self.env.controller.client.async_req(req, on_complete)

  def complete_member(self, file_path, position):
    print "hello"
    req = ensime_codec.encode_complete_member(file_path, position)
    resp = self.env.controller.client.sync_req(req)
    print "complete_member: " + str(resp)
    return ensime_codec.decode_completions(resp)

envLock = threading.RLock()
ensime_envs = {}

def get_ensime_env(window):
  if window:
    if window.id() in ensime_envs:
      return ensime_envs[window.id()]
    envLock.acquire()
    try:
      if not (window.id() in ensime_envs):
        ensime_envs[window.id()] = EnsimeEnvironment(window)
      return ensime_envs[window.id()]
    finally:
      envLock.release()
  return None

class EnsimeEnvironment(object):
  def __init__(self, window):
    # plugin-wide stuff (immutable)
    self.settings = sublime.load_settings("Ensime.sublime-settings")
    server_dir = self.settings.get("ensime_server_path", "sublime_ensime\\server" if os.name == 'nt' else "sublime_ensime/server")
    self.server_path = server_dir if server_dir.startswith("/") or (":/" in server_dir) or (":\\" in server_dir) else os.path.join(sublime.packages_path(), server_dir)
    self.ensime_executable = self.server_path + '/' + ("bin\\server.bat" if os.name == 'nt' else "bin/server")
    self.plugin_root = self.server_path + "/.." # we can do better
    self.log_root = self.plugin_root + "/logs"

    # instance-specific stuff (immutable)
    self.project_root = None
    self.project_file = None
    self.project_config = []
    prj_files = [(f + "/.ensime") for f in window.folders() if os.path.exists(f + "/.ensime")]
    if len(prj_files) > 0:
      self.project_file = prj_files[0]
      self.project_root = os.path.dirname(self.project_file)
      src = open(self.project_file).read() if self.project_file else "()"
      self.project_config = sexp.read(src)
      m = sexp.sexp_to_key_map(self.project_config)
      if m.get(":root-dir"):
        self.project_root = m[":root-dir"]
      else:
        self.project_config = self.project_config + [key(":root-dir"), self.project_root]
    self.valid = True

    # lifecycle (mutable)
    self.lifecycleLock = threading.RLock()
    self.in_transition = False
    self.controller = None

    # shared state (mutable)
    self.notes = []
    self.repl_last_insert = 0
    self.repl_last_fixup = 0
    self.repl_lock = threading.RLock()
    self.sv = window.get_output_panel("ensime_server")
    self.sv.set_name("ensime_server")
    self.sv.settings().set("word_wrap", True)
    self.cv = window.get_output_panel("ensime_client")
    self.cv.set_name("ensime_client")
    self.cv.settings().set("word_wrap", True)
    self.rv = window.get_output_panel("ensime_repl")
    self.rv.set_name("ensime_repl")
    self.rv.settings().set("word_wrap", True)

class EnsimeLog(object):

  def log(self, data):
    sublime.set_timeout(functools.partial(self.log_on_ui_thread, "ui", data), 0)

  def log_client(self, data, to_disk_only = False):
    sublime.set_timeout(functools.partial(self.log_on_ui_thread, "client", data, to_disk_only), 0)

  def log_server(self, data, to_disk_only = False):
    sublime.set_timeout(functools.partial(self.log_on_ui_thread, "server", data, to_disk_only), 0)

  def log_on_ui_thread(self, flavor, data, to_disk_only):
    if flavor in self.env.settings.get("log_to_console", {}):
      if not to_disk_only:
        print str(data)
    if flavor in self.env.settings.get("log_to_file", {}):
      try:
        if not os.path.exists(self.env.log_root):
          os.mkdir(self.env.log_root)
        file_name = os.path.join(self.env.log_root, flavor + ".log")
        with open(file_name, "a") as f: f.write(data + "\n")
      except:
        pass

  def view_insert(self, v, what):
    sublime.set_timeout(functools.partial(self.view_insert_on_ui_thread, v, what), 0)

  def view_insert_on_ui_thread(self, v, what):
    selection_was_at_end = (len(v.sel()) == 1 and v.sel()[0] == sublime.Region(v.size()))
    v.set_read_only(False)
    edit = v.begin_edit()
    v.insert(edit, v.size(), what)
    if selection_was_at_end:
      v.show(v.size())
    v.end_edit(edit)
    v.set_read_only(True)
    self.repl_insert(what)

  def view_show(self, v, focus = False):
    self.w.run_command("show_panel", {"panel": "output." + v.name()})
    if focus:
      self.w.focus_view(v)
    sublime.set_timeout(functools.partial(v.show, v.size()), 100)

  def repl_prompt(self):
    return "ensime>"

  def repl_fixup_timeout(self):
    return 500

  def repl_show(self):
    self.env.repl_lock.acquire()
    try:
      last = self.env.repl_last_insert
      current = self.env.rv.size()
      if (last == current):
        self.repl_insert(self.repl_prompt(), False)
      self.view_show(self.env.rv, True)
    finally:
      self.env.repl_lock.release()

  def repl_insert(self, what, rewind = True):
    sublime.set_timeout(functools.partial(self.repl_insert_on_ui_thread, what, rewind), 0)

  def repl_insert_on_ui_thread(self, what, rewind):
    self.env.repl_lock.acquire()
    try:
      selection_was_at_end = (len(self.env.rv.sel()) == 1 and self.env.rv.sel()[0] == sublime.Region(self.env.rv.size()))
      was_read_only = self.env.rv.is_read_only()
      self.env.rv.set_read_only(False)
      edit = self.env.rv.begin_edit()
      last = self.env.repl_last_insert
      current = self.env.rv.size()
      if rewind:
        user_input = ""
        if current - last >= len(self.repl_prompt()):
          user_input = self.env.rv.substr(sublime.Region(last + len(self.repl_prompt()), current))
      self.env.rv.insert(edit, current, what)
      if rewind:
        self.env.repl_last_insert = self.env.rv.size()
        if current - last >= len(self.repl_prompt()):
          self.repl_schedule_fixup(user_input, self.env.repl_last_insert)
      if selection_was_at_end:
        self.env.rv.show(self.env.rv.size())
        self.env.rv.sel().clear()
        self.env.rv.sel().add(sublime.Region(self.env.rv.size()))
      self.env.rv.end_edit(edit)
      self.env.rv.set_read_only(was_read_only)
    finally:
      self.env.repl_lock.release()

  def repl_schedule_fixup(self, what, last_insert):
    sublime.set_timeout(functools.partial(self.repl_insert_fixup, what, last_insert), self.repl_fixup_timeout())

  def repl_insert_fixup(self, what, last_insert):
    self.env.repl_lock.acquire()
    try:
      if self.env.repl_last_fixup < last_insert:
        self.env.repl_last_fixup = last_insert
        if self.env.repl_last_insert == last_insert:
          selection_was_at_end = (len(self.env.rv.sel()) == 1 and self.env.rv.sel()[0] == sublime.Region(self.env.rv.size()))
          was_read_only = self.env.rv.is_read_only()
          self.env.rv.set_read_only(False)
          edit = self.env.rv.begin_edit()
          self.env.rv.insert(edit, self.env.rv.size(), self.repl_prompt() + what)
          if selection_was_at_end:
            self.env.rv.show(self.env.rv.size())
            self.env.rv.sel().clear()
            self.env.rv.sel().add(sublime.Region(self.env.rv.size()))
          self.env.rv.end_edit(edit)
          self.env.rv.set_read_only(was_read_only)
        self.repl_schedule_fixup(what, self.env.repl_last_insert)
    finally:
      self.env.repl_lock.release()

  def repl_get_input(self):
    self.env.repl_lock.acquire()
    try:
      last = self.env.repl_last_insert
      current = self.env.rv.size()
      return self.env.rv.substr(sublime.Region(last, current))[len(self.repl_prompt()):]
    finally:
      self.env.repl_lock.release()

class EnsimeBase(object):
  def __init__(self, owner):
    self.owner = owner
    if type(owner) == Window:
      self.env = get_ensime_env(owner)
      self.w = owner
      self.v = owner.active_view()
      self.f = None
    elif type(owner) == View:
      self.env = get_ensime_env(owner.window() or sublime.active_window())
      self.w = owner.window()
      self.v = owner
      self.f = owner.file_name()
    else:
      raise "unsupported owner of type: " + str(type(owner))

  def in_project(self, filename):
    if filename and filename.endswith("scala"):
      root = os.path.normcase(os.path.realpath(self.env.project_root))
      wannabe = os.path.normcase(os.path.realpath(filename))
      return wannabe.startswith(root)

class EnsimeCommon(EnsimeBase, EnsimeLog, EnsimeApi):
  pass

def ensime_api(owner):
  return EnsimeCommon(owner)

class EnsimeWindowCommand(EnsimeCommon, WindowCommand):
  pass

class EnsimeTextCommand(EnsimeCommon, TextCommand):
  pass

class ScalaOnly:
  def is_enabled(self):
    return self.w and self.f and self.f.lower().endswith(".scala")

class NotRunningOnly:
  def is_enabled(self):
    return not self.env.in_transition and self.env.valid and not (self.env.controller and self.env.controller.running)

class RunningOnly:
  def is_enabled(self):
    return not self.env.in_transition and self.env.valid and self.env.controller and self.env.controller.running

class ReadyEnsimeOnly:
  def is_enabled(self):
    return not self.env.in_transition and self.env.valid and self.env.controller and self.env.controller.ready

class ConnectedEnsimeOnly:
  def is_enabled(self):
    return not self.env.in_transition and self.env.valid and self.env.controller and self.env.controller.connected

class EnsimeContextProvider(EventListener):
  def on_query_context(self, view, key, operator, operand, match_all):
    if key == "ensime_ready":
      try:
        return ensime_api(view).env.controller.ready
      except:
        return False
    if key == "ensime_connected":
      try:
        return ensime_api(view).env.controller.connected
      except:
        return False
    return None

class EnsimeClientListener:
  def on_client_async_data(self, data):
    pass

  def on_disconnect(self, reason):
    pass

class EnsimeClientSocket(EnsimeCommon):
  def __init__(self, owner, port, handlers):
    super(type(self).__mro__[0], self).__init__(owner)
    self.port = port
    self.connected = False
    self.disconnect_pending = False
    self.handlers = handlers
    self._lock = threading.RLock()
    self._connect_lock = threading.RLock()
    self._receiver = None

  def notify_async_data(self, data):
    for handler in self.handlers:
      if handler:
        sublime.set_timeout(functools.partial(handler.on_client_async_data, data), 0)

  def notify_disconnect(self, reason):
    for handler in self.handlers:
      if handler:
        sublime.set_timeout(functools.partial(handler.on_disconnect, reason), 0)

  def receive_loop(self):
    while self.connected:
      try:
        res = self.socket.recv(4096)
        self.log_client("RECV: " + unicode(res, "utf-8"))
        if res:
          len_str = res[:6]
          msglen = int(len_str, 16) + 6
          msg = res[6:msglen]
          nxt = strip(res[msglen:])
          while len(nxt) > 0 or len(msg) > 0:
            form = sexp.read(msg)
            self.notify_async_data(form)
            if len(nxt) > 0:
              msglen = int(nxt[:6], 16) + 6
              msg = nxt[6:msglen]
              nxt = strip(nxt[msglen:])
            else:
              msg = ""
              msglen = ""
        else:
          self.connected = False
      except Exception as e:
        self.log_client("*****    ERROR     *****")
        self.log_client("expected disconnect" if self.disconnect_pending else "unexpected disconnect")
        self.log_client(e)
        reason = "server" if not self.disconnect_pending else "client"
        self.disconnect_pending = False
        self.notify_disconnect(reason)
        self.connected = False

  def start_receiving(self):
    t = threading.Thread(name = "ensime-client-" + str(self.w.id()) + "-" + str(self.port), target = self.receive_loop)
    t.setDaemon(True)
    t.start()
    self._receiver = t

  def connect(self):
    self._connect_lock.acquire()
    try:
      s = socket.socket()
      s.connect(("127.0.0.1", self.port))
      self.socket = s
      self.connected = True
      self.start_receiving()
      return s
    except socket.error as e:
      # set sublime error status
      self.connected = False
      sublime.error_message("Can't connect to ensime server:  " + e.args[1])
    finally:
      self._connect_lock.release()

  def send(self, request):
    try:
      if not self.connected:
        self.connect()
      self.socket.send(request)
    except:
      self.notify_disconnect("server")
      self.set_connected(False)

  def sync_send(self, request, msg_id):
    self._connect_lock.acquire()
    try:
      s = socket.socket()
      s.connect(("127.0.0.1", self.port))
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
                self.notify_async_data(sexp.read(msg))
                msglen = int(nxt[:6], 16) + 6
                msg = nxt[6:msglen]
                nxt = strip(nxt[msglen:])
              else:
                nxt = ""
                break
            result = sexp.read(msg)
            keep_going = result == None or msg_id != result[-1]
            if keep_going:
              self.notify_async_data(result)
          else:
            nxt = res

        return result
      except Exception as error:
        self.log_client(error)
      finally:
        if s:
          s.close()
    except Exception as error:
      self.log_client(error)
    finally:
      self._connect_lock.release()

  def close(self):
    self._connect_lock.acquire()
    try:
      if self.socket:
        self.socket.close()
      self.connect = False
    finally:
      self._connect_lock.release()

class EnsimeCodec:
  def encode_initialize_project(self, conf):
    return [sym("swank:init-project"), conf]

  def encode_type_check_file(self, file_path):
    return [sym("swank:typecheck-file"), file_path]

  def decode_notes(self, data):
    m = sexp.sexp_to_key_map(data)
    return [self.decode_note(n) for n in m[":notes"]]

  def decode_note(self, data):
    m = sexp.sexp_to_key_map(data)
    class EnsimeNote(object): pass
    note = EnsimeNote()
    note.message = m[":msg"]
    note.file_name = m[":file"]
    note.severity = m[":severity"]
    note.start = m[":beg"]
    note.end = m[":end"]
    note.line = m[":line"]
    note.col = m[":col"]
    return note

  def encode_inspect_type_at_point(self, file_path, position):
    return [sym("swank:type-at-point"), str(file_path), int(position)]

  def decode_inspect_type_at_point(self, data):
    d = data[1][1]
    if d[1] != "<notype>":
      return "(" + str(d[7]) + ") " + d[5]
    else:
      return None

  def encode_complete_member(self, file_path, position):
    return [sym("swank:completions"), str(file_path), int(position), 0, False]

  def decode_completions(self, data):
    friend = sexp.sexp_to_key_map(data[1][1])
    comps = friend[":completions"] if ":completions" in friend else []
    comp_list = [self.decode_completion(p) for p in friend[":completions"]]

  def decode_completion(self, data):
    m = sexp.sexp_to_key_map(data)
    class EnsimeCompletion(object): pass
    completion = EnsimeCompletion()
    completion.name = m[":name"]
    completion.signature = m[":type-sig"]
    completion.is_callable = bool(m[":is-callable"]) if ":is-callable" in m else False
    completion.type_id = m[":type-id"]
    completion.to_insert = m[":to-insert"] if ":to-insert" in m else None
    return completion

ensime_codec = EnsimeCodec()

class EnsimeClient(EnsimeClientListener, EnsimeCommon):
  def __init__(self, owner, port_file):
    super(type(self).__mro__[0], self).__init__(owner)
    with open(port_file) as f: self.port = int(f.read())
    self.init_counters()
    methods = filter(lambda m: m[0].startswith("inbound_"), inspect.getmembers(self, predicate=inspect.ismethod))
    self.log_client("reflectively found " + str(len(methods)) + " handlers for inbound messages: " + str(methods))
    self._inbound_handlers = dict((":" + m[0][len("inbound_"):].replace("_", "-"), m[1]) for m in methods)
    self._outbound_handlers = {}

  def startup(self):
    self.log_server("Launching ENSIME client socket at port " + str(self.port))
    self.socket = EnsimeClientSocket(self.owner, self.port, [self, self.env.controller])
    self.socket.connect()

  def shutdown(self):
    self.sync_req([sym("swank:shutdown-server")])
    self.socket.close()
    self.socket = None

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
            if msg_id <= 2: # handshake and initialize project
              sublime.error_message(detail)
              sublime.status_message("ENSIME startup has failed")
              self.env.controller.shutdown()
            else:
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
          payload = data[1] if len(data) > 1 else None
          handler(payload)
        else:
          self.log_client("unexpected message type: " + message_type)
    except Exception as e:
      self.log_client("error when handling message: " + str(data))
      self.log_client(traceback.format_exc())

  def inbound_compiler_ready(self, payload):
    filename = self.env.plugin_root + "/Encouragements.txt"
    lines = [line.strip() for line in open(filename)]
    msg = lines[random.randint(0, len(lines) - 1)]
    sublime.status_message(msg + " This could be the start of a beautiful program, " + getpass.getuser().capitalize()  + ".")

  def inbound_indexer_ready(self, payload):
    pass

  def inbound_full_typecheck_finished(self, payload):
    pass

  def inbound_background_message(self, payload):
    sublime.status_message(str(payload))

  def inbound_scala_notes(self, payload):
    notes = ensime_codec.decode_notes(payload)
    self.add_notes(notes)

  def inbound_clear_notes(self, payload):
    self.clear_notes()

  ############### OUTBOUND MESSAGES ###############

  def async_req(self, to_send, on_complete = None, msg_id = None):
    msg_id = self.next_message_id()
    self._outbound_handlers[msg_id] = on_complete
    msg_str = sexp.to_string([key(":swank-rpc"), to_send, msg_id])
    msg_str = "%06x" % len(msg_str) + msg_str

    self.feedback(msg_str)
    self.log_client("SEND ASYNC REQ: " + msg_str)
    self.socket.send(msg_str)

  def sync_req(self, to_send):
    msg_id = self.next_message_id()
    msg_str = sexp.to_string([key(":swank-rpc"), to_send, msg_id])
    msg_str = "%06x" % len(msg_str) + msg_str

    self.feedback(msg_str)
    self.log_client("SEND SYNC REQ: " + msg_str)
    resp = self.socket.sync_send(msg_str, msg_id)
    self.log_client("SEND SYNC RESP: " + str(resp))
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
    self.log_client(msg.strip(), to_disk_only = True)
    self.view_insert(self.env.cv, msg)

class EnsimeServerListener:
  def on_server_data(self, data):
    pass

  def on_finished(self):
    pass

class EnsimeServerProcess(EnsimeCommon):
  def __init__(self, owner, command, listeners):
    super(type(self).__mro__[0], self).__init__(owner)
    self.killed = False
    self.listeners = listeners or []

    # ensure the subprocess is always killed when the editor exits
    # this doesn't work, so we have to go for hacks below
    # import atexit
    # atexit.register(self.kill)

    # HACK #1: kill ensime servers that are already running and were launched by this instance of sublime
    # this can happen when you press ctrl+s on sublime-ensime files, sublime reloads them
    # and suddenly SublimeServerCommand has a new singleton instance, and a process it hosts becomes a zombie
    processes = self.env.settings.get("processes", {})
    previous = processes.get(str(os.getpid()), None)
    if previous:
      self.log_server("killing orphaned ensime server process with pid " + str(previous))
      if os.name == "nt":
        try:
          job_name = "Global\\sublime-ensime-" + str(os.getpid())
          self.log_server("killing a job named: " + job_name)
          job = killableprocess.winprocess.OpenJobObject(0x1F001F, True, job_name)
          killableprocess.winprocess.TerminateJobObject(job, 127)
        except:
          self.log_server(sys.exc_info()[1])
      else:
        os.killpg(int(previous), signal.SIGKILL)

    # HACK #2: garbage collect ensime server processes that were started by sublimes, but weren't stopped
    # unfortunately, atexit doesn't work (see the commented code above), so we have to resort to this ugliness
    # todo. ideally, this should happen automatically from ensime
    # e.g. if -Densime.explode.when.zombied is set, then ensime automatically quits when it becomes a zombie
    if os.name == "nt":
      import ctypes
      EnumWindows = ctypes.windll.user32.EnumWindows
      EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
      GetWindowText = ctypes.windll.user32.GetWindowTextW
      GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
      IsWindowVisible = ctypes.windll.user32.IsWindowVisible
      GetWindowThreadProcessId = ctypes.windll.user32.GetWindowThreadProcessId
      active_sublimes = set()
      def foreach_window(hwnd, lParam):
        if IsWindowVisible(hwnd):
          length = GetWindowTextLength(hwnd)
          buff = ctypes.create_unicode_buffer(length + 1)
          GetWindowText(hwnd, buff, length + 1)
          title = buff.value
          if title.endswith("- Sublime Text 2"):
            pid = ctypes.c_int()
            tid = GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            active_sublimes.add(pid.value)
        return True
      EnumWindows(EnumWindowsProc(foreach_window), 0)
      for sublimepid in [sublimepid for sublimepid in processes.keys() if not int(sublimepid) in active_sublimes]:
        ensimepid = processes[sublimepid]
        del processes[sublimepid]
        self.log_server("found a zombie ensime server process with pid " + str(ensimepid))
        try:
          # todo. Duh, this no longer works on Windows, but I swear it worked.
          # Due to an unknown reason, job gets killed once Sublime quits, so we have no way to dispose of the zombies later.
          job_name = "Global\\sublime-ensime-" + str(sublimepid)
          self.log_server("killing a job named: " + job_name)
          job = killableprocess.winprocess.OpenJobObject(0x1F001F, True, job_name)
          killableprocess.winprocess.TerminateJobObject(job, 127)
        except:
          self.log_server(sys.exc_info()[1])
    else:
      # todo. Vlad, please, implement similar logic for Linux
      pass

    startupinfo = None
    if os.name == "nt":
      startupinfo = killableprocess.STARTUPINFO()
      startupinfo.dwFlags |= killableprocess.STARTF_USESHOWWINDOW
      startupinfo.wShowWindow |= 1 # SW_SHOWNORMAL
    creationflags = 0x0
    if os.name =="nt":
      creationflags = 0x8000000 # CREATE_NO_WINDOW
    self.proc = killableprocess.Popen(
      command,
      stdout = subprocess.PIPE,
      stderr = subprocess.PIPE,
      startupinfo = startupinfo,
      creationflags = creationflags,
      env = os.environ.copy(),
      cwd = self.env.server_path)
    self.log_server("started ensime server with pid " + str(self.proc.pid))
    processes[str(os.getpid())] = str(self.proc.pid)
    self.env.settings.set("processes", processes)
    # todo. this will leak pids if there are multiple sublimes launching ensimes simultaneously
    # and, in general, we should also address the fact that sublime-ensime assumes at most single ensime per window
    # finally, it's unclear whether to allow multiple ensimes for the same project launched by different sublimes
    sublime.save_settings("Ensime.sublime-settings")

    if self.proc.stdout:
      thread.start_new_thread(self.read_stdout, ())

    if self.proc.stderr:
      thread.start_new_thread(self.read_stderr, ())

  def kill(self):
    if not self.killed:
      self.killed = True
      self.proc.kill()
      self.listeners = []

  def poll(self):
    return self.proc.poll() == None

  def read_stdout(self):
    while True:
      data = os.read(self.proc.stdout.fileno(), 2**15)
      if data != "":
        for listener in self.listeners:
          if listener:
            sublime.set_timeout(functools.partial(listener.on_server_data, data), 0)
      else:
        self.proc.stdout.close()
        for listener in self.listeners:
          if listener:
            sublime.set_timeout(listener.on_finished, 0)
        break

  def read_stderr(self):
    while True:
      data = os.read(self.proc.stderr.fileno(), 2**15)
      if data != "":
        for listener in self.listeners:
          if listener:
            sublime.set_timeout(functools.partial(listener.on_server_data, data), 0)
      else:
        self.proc.stderr.close()
        break

class EnsimeServer(EnsimeServerListener, EnsimeCommon):
  def __init__(self, owner, port_file):
    super(type(self).__mro__[0], self).__init__(owner)
    self.port_file = port_file

  def startup(self):
    ensime_command = self.get_ensime_command()
    self.log_server("Launching ENSIME server process with: " + str(ensime_command))
    self.proc = EnsimeServerProcess(self.owner, ensime_command, [self, self.env.controller])

  def get_ensime_command(self):
    if not os.path.exists(self.env.ensime_executable):
      sublime.error_message("Ensime executable \"" + self.env.ensime_executable + "\" does not exist. Check your Ensime.sublime-settings.")
      return
    return [self.env.ensime_executable, self.port_file]

  def on_server_data(self, data):
    str_data = str(data).replace("\r\n", "\n").replace("\r", "\n")
    self.log_server(str_data.strip(), to_disk_only = True)
    self.view_insert(self.env.sv, str_data)

  def shutdown(self):
    self.proc.kill()
    self.proc = None
    self.view_insert(self.env.sv, "[Shut down]")

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
    raise AttributeError(str(self) + " does not have attribute " + name)

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
    sublime.status_message("Initializing... ")
    req = ensime_codec.encode_initialize_project(self.env.project_config)
    self.client.async_req(req, lambda _: sublime.status_message("Ensime ready!"))

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

class EnsimeStartupCommand(NotRunningOnly, EnsimeWindowCommand):
  def run(self):
    EnsimeController(self.w).startup()

class EnsimeShutdownCommand(RunningOnly, EnsimeWindowCommand):
  def run(self):
    self.env.controller.shutdown()

class EnsimeRestartCommand(RunningOnly, EnsimeWindowCommand):
  def run(self):
    self.w.run_command("ensime_shutdown")
    self.w.run_command("ensime_startup")

class EnsimeShowClientMessagesCommand(ReadyEnsimeOnly, EnsimeWindowCommand):
  def run(self):
    self.view_show(self.env.cv, False)

class EnsimeShowServerMessagesCommand(ReadyEnsimeOnly, EnsimeWindowCommand):
  def run(self):
    self.view_show(self.env.sv, False)

# support `cls`
# rebind Enter, Escape, Backspace, Left, ShiftLeft, Home, ShiftHome
# persistent command history and Ctrl+Up/Ctrl+Down like in SublimeREPL

class EnsimeShowClientServerReplCommand(ReadyEnsimeOnly, EnsimeWindowCommand):
  def __init__(self, window):
    super(type(self).__mro__[0], self).__init__(window)
    self.visible = False
    self.window = window

  def run(self, toggle = True):
    self.visible = not self.visible if toggle else True
    if self.visible:
      self.repl_show()
    else:
      self.window.run_command("hide_panel", { "cancel": True })

class EnsimeHighlights(EnsimeCommon):
  def hide(self):
    self.v.erase_regions("ensime-error")
    self.v.erase_regions("ensime-error-underline")

  def show(self):
    # filter notes against self.f
    # don't forget to use os.realpath to defeat symlinks
    errors = [self.v.full_line(note.start) for note in self.env.notes]
    underlines = []
    for note in self.env.notes:
      underlines += [sublime.Region(int(pos)) for pos in range(note.start, note.end)]
    if self.env.settings.get("error_highlight") and self.env.settings.get("error_underline"):
      self.v.add_regions(
        "ensime-error-underline",
        underlines,
        "invalid.illegal",
        sublime.DRAW_EMPTY_AS_OVERWRITE)
    if self.env.settings.get("error_highlight"):
      self.v.add_regions(
        "ensime-error",
        errors,
        "invalid.illegal",
        self.env.settings.get("error_icon"),
        sublime.DRAW_OUTLINED)

  def refresh(self):
    if self.env.settings.get("error_highlight"):
      self.show()
    else:
      self.hide()

class EnsimeHighlightCommand(ConnectedEnsimeOnly, EnsimeWindowCommand):
  def is_enabled(self, enable = True):
    now = not not self.env.settings.get("error_highlight")
    wannabe = not not enable
    return super(type(self).__mro__[0], self).is_enabled() and now != wannabe

  def run(self, enable = True):
    self.env.settings.set("error_highlight", not not enable)
    sublime.save_settings("Ensime.sublime-settings")
    EnsimeHighlights(self.v).hide()
    if enable:
      self.type_check_file(self.f)

class EnsimeHighlightDaemon(EventListener):
  def with_api(self, view, what):
    api = ensime_api(view)
    controller = api.env and api.env.controller
    socket = controller and controller.client and controller.client.socket
    connected = socket and socket.connected
    if connected and api.in_project(view.file_name()):
      what(api)

  def on_load(self, view):
    self.with_api(view, lambda api: api.type_check_file(view.file_name()))

  def on_post_save(self, view):
    self.with_api(view, lambda api: api.type_check_file(view.file_name()))

  def on_activate(self, view):
    self.with_api(view, lambda api: EnsimeHighlights(view).refresh())

  def on_selection_modified(self, view):
    self.with_api(view, self.display_errors_in_statusbar)

  def display_errors_in_statusbar(self, api):
    bol = api.v.line(api.v.sel()[0].begin()).begin()
    eol = api.v.line(api.v.sel()[0].begin()).end()
    # filter notes against self.f
    # don't forget to use os.realpath to defeat symlinks
    msgs = [note.message for note in api.env.notes if (bol <= note.start and note.start <= eol) or (bol <= note.end and note.end <= eol)]
    if msgs:
      api.v.set_status("ensime-typer", "; ".join(msgs))
    else:
      api.v.erase_status("ensime-typer")

class EnsimeCompletionsListener(EventListener):
  def on_query_completions(self, view, prefix, locations):
    if not view.match_selector(locations[0], "source.scala"):
      return []
    completions = ensime_api(view).complete_member(view.file_name(), locations[0])
    if completions is None:
      return []
    return ([(c.name + "\t" + c.signature, c.name) for c in completions], sublime.INHIBIT_EXPLICIT_COMPLETIONS | sublime.INHIBIT_WORD_COMPLETIONS)

class EnsimeInspectTypeAtPoint(ConnectedEnsimeOnly, EnsimeTextCommand):
  def run(self, edit):
    self.inspect_type_at_point(self.f, self.v.sel()[0].begin(), self.handle_reply)

  def handle_reply(self, tpe):
    if tpe:
      self.v.set_status("ensime-typer", tpe)
    else:
      self.v.erase_status("ensime-typer")