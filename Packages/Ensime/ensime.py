import sublime
from sublime import *
from sublime_plugin import *
import os, threading, thread, socket, getpass, signal, glob
import subprocess, tempfile, datetime, time, json, zipfile
import functools, inspect, traceback, random, re, sys
from functools import partial as bind
from string import strip
from types import *
import env, diff, dotensime, dotsession, rpc
import sexp
from sexp import key, sym
from constants import *
from paths import *

class EnsimeCommon(object):
  def __init__(self, owner):
    self.owner = owner
    if type(owner) == Window:
      self._env = env.for_window(owner)
      self.w = owner
    elif type(owner) == View:
      # todo. find out why this is necessary
      w = owner.window() or sublime.active_window()
      self._env = env.for_window(w)
      self.w = w
      self.v = owner
    else:
      raise Exception("unsupported owner of type: " + str(type(owner)))

  @property
  def env(self):
    if not self._env:
      self._env = env.for_window(self.w)
    return self._env

  @property
  def rpc(self):
    return self.env.rpc

  def status_message(self, msg):
    sublime.set_timeout(bind(sublime.status_message, msg), 0)

  def error_message(self, msg):
    sublime.set_timeout(bind(sublime.error_message, msg), 0)

  def log(self, data):
    sublime.set_timeout(bind(self.log_on_ui_thread, "ui", data), 0)

  def log_client(self, data):
    sublime.set_timeout(bind(self.log_on_ui_thread, "client", data), 0)

  def log_server(self, data):
    sublime.set_timeout(bind(self.log_on_ui_thread, "server", data), 0)

  def log_on_ui_thread(self, flavor, data):
    if flavor in self.env.settings.get("log_to_file", {}):
      try:
        if not os.path.exists(self.env.log_root):
          os.mkdir(self.env.log_root)
        file_name = self.env.log_root + os.sep + flavor + ".log"
        with open(file_name, "a") as f: f.write("[" + str(datetime.datetime.now()) + "]: " + data.strip() + "\n")
      except:
        exc_type, exc_value, exc_tb = sys.exc_info()
        detailed_info = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        print detailed_info

  def is_valid(self):
    return self.env and self.env.valid

  def is_running(self):
    return self.is_valid() and self.env.running

  def _filename_from_wannabe(self, wannabe):
    if type(wannabe) == type(None):
      v = self.v if hasattr(self, "v") else self.w.active_view()
      return self._filename_from_wannabe(v) if v != None else None
    if type(wannabe) == sublime.View:
      return wannabe.file_name()
    return wannabe

  def in_project(self, wannabe = None):
    filename = self._filename_from_wannabe(wannabe)
    extension_ok = filename and (filename.endswith("scala") or filename.endswith("java"))
    subpath_ok = self.env and is_subpath(self.env.project_root, filename)
    return extension_ok and subpath_ok

  def project_relative_path(self, wannabe):
    filename = self._filename_from_wannabe(wannabe)
    if not self.in_project(filename): return None
    return relative_path(self.env.project_root, filename)

  def _invoke_view_colorer(self, method, *args):
    view = args[0]
    args = args[1:]
    if view == "default": view = self.v
    if view != None:
      colorer = Colorer(view)
      getattr(colorer, method)(*args)

  def _invoke_all_colorers(self, method, *args):
    # todo. only invoke colorer on visible views
    # because invisible views will be recolorized on activation
    for v in self.w.views():
      colorer = Colorer(v)
      getattr(colorer, method)(*args)

  def colorize(self, view = "default"): self._invoke_view_colorer("refresh", view)
  def colorize_all(self): self._invoke_all_colorers("refresh")
  def uncolorize(self, view = "default"): self._invoke_view_colorer("clear_all", view)
  def uncolorize_all(self): self._invoke_all_colorers("clear_all")
  def redraw_highlights(self, view = "default"): self._invoke_view_colorer("update_highlights", view)
  def redraw_all_highlights(self): self._invoke_all_colorers("update_highlights")
  def redraw_status(self, view = "default"): self._invoke_view_colorer("update_status", view)
  def redraw_breakpoints(self, view = "default"): self._invoke_view_colorer("update_breakpoints", view)
  def redraw_all_breakpoints(self): self._invoke_all_colorers("update_breakpoints")
  def redraw_debug_focus(self, view = "default"): self._invoke_view_colorer("update_debug_focus", view)
  def redraw_all_debug_focuses(self): self._invoke_all_colorers("update_debug_focus")

class EnsimeWindowCommand(EnsimeCommon, WindowCommand):
  def __init__(self, window):
    super(EnsimeWindowCommand, self).__init__(window)
    self.window = window

class EnsimeTextCommand(EnsimeCommon, TextCommand):
  def __init__(self, view):
    super(EnsimeTextCommand, self).__init__(view)
    self.view = view

class EnsimeEventListener(EnsimeCommon):
  pass

class EnsimeEventListenerProxy(EventListener):
  def __init__(self):
    def is_ensime_event_listener(member):
      return inspect.isclass(member) and member != EnsimeEventListener and issubclass(member, EnsimeEventListener)
    self.listeners = map(lambda info: info[1], inspect.getmembers(sys.modules[__name__], is_ensime_event_listener))

  def _invoke(self, view, handler_name, *args):
    for listener in self.listeners:
      instance = listener(view)
      try: handler = getattr(instance, handler_name)
      except: handler = None
      if handler: return handler(*args)

  def on_new(self, view):
    return self._invoke(view, "on_new")

  def on_clone(self, view):
    return self._invoke(view, "on_clone")

  def on_load(self, view):
    return self._invoke(view, "on_load")

  def on_close(self, view):
    return self._invoke(view, "on_close")

  def on_pre_save(self, view):
    return self._invoke(view, "on_pre_save")

  def on_post_save(self, view):
    return self._invoke(view, "on_post_save")

  def on_modified(self, view):
    return self._invoke(view, "on_modified")

  def on_selection_modified(self, view):
    return self._invoke(view, "on_selection_modified")

  def on_activated(self, view):
    return self._invoke(view, "on_activated")

  def on_deactivated(self, view):
    return self._invoke(view, "on_deactivated")

  def on_query_context(self, view, key, operator, operand, match_all):
    return self._invoke(view, "on_query_context", key, operator, operand, match_all)

  def on_query_completions(self, view, prefix, locations):
    return self._invoke(view, "on_query_completions", prefix, locations)

class EnsimeMouseCommand(EnsimeTextCommand):
  def run(self, target):
    raise Exception("abstract method: EnsimeMouseCommand.run")

  def _run_underlying(self, args):
    system_command = args["command"] if "command" in args else None
    if system_command:
      system_args = dict({"event": args["event"]}.items() + args["args"].items())
      self.v.run_command(system_command, system_args)

  # note the underscore in "run_"
  def run_(self, args):
    is_applicable = self.is_running() and self.in_project()
    if is_applicable:
      self.old_sel = [(r.a, r.b) for r in self.v.sel()]
      # unfortunately, running an additive drag_select is our only way of getting the coordinates of the click
      # I didn't find a way to convert args["event"]["x"] and args["event"]["y"] to text coordinates
      # there are relevant APIs, but they refuse to yield correct results
      self.v.run_command("drag_select", {"event": args["event"], "additive": True})
      self.new_sel = [(r.a, r.b) for r in self.v.sel()]
      self.diff = list((set(self.old_sel) - set(self.new_sel)) | (set(self.new_sel) - set(self.old_sel)))

      if len(self.diff) == 0:
        if len(self.new_sel) == 1:
          self.run(self.new_sel[0][0])
        else:
          # this is a tough one
          # here's how we possibly could arrive here
          # we have a multi selection, and then ctrl+click on one the active cursors
          # there's no way we can guess the exact point of click, so we bail
          pass
      elif len(self.diff) == 1:
        sel = self.v.sel()
        sel.clear()
        sel.add(Region(self.diff[0][0], self.diff[0][1]))
        self.run(self.diff[0][0])
      else:
        # this shouldn't happen
        self.log("len(diff) > 1: command = " + str(type(self)) + ", old_sel = " + str(self.old_sel) + ", new_sel = " + str(self.new_sel))
    else:
      self._run_underlying(args)

class ValidOnly:
  def is_enabled(self):
    return self.is_valid()

class ProjectDoesntExist:
  def is_enabled(self):
    return not dotensime.exists(self.w)

class ProjectExists:
  def is_enabled(self):
    return dotensime.exists(self.w)

class RunningOnly:
  def is_enabled(self):
    return self.is_running()

class RunningProjectFileOnly:
  def is_enabled(self):
    return self.is_running() and self.in_project()

class ProjectFileOnly:
  def is_enabled(self):
    return self.in_project()

class NotDebuggingOnly:
  def is_enabled(self):
    return self.is_running() and not self.env.profile

class DebuggingOnly:
  def is_enabled(self):
    return self.is_running() and self.env.profile

class FocusedOnly:
  def is_enabled(self):
    return self.is_running() and self.env.focus

class EnsimeToolView(EnsimeCommon):
  def __init__(self, env):
    super(EnsimeToolView, self).__init__(env.w)

  def can_show(self):
    raise Exception("abstract method: EnsimeToolView.can_show(self)")

  @property
  def name(self):
    raise Exception("abstract method: EnsimeToolView.name(self)")

  def render(self):
    raise Exception("abstract method: EnsimeToolView.render(self)")

  @property
  def v(self):
    wannabes = filter(lambda v: v.name() == self.name, self.w.views())
    return wannabes[0] if wannabes else None

  def _mk_v(self):
    v = self.w.new_file()
    v.set_scratch(True)
    v.set_name(self.name)
    v.settings().set("result_file_regex", "([:.a-z_A-Z0-9\\\\/-]+[.](?:scala|java)):([0-9]+)")
    v.settings().set("result_line_regex", "")
    v.settings().set("result_base_dir", self.env.project_root)
    other_view = self.w.new_file()
    self.w.focus_view(other_view)
    self.w.run_command("close_file")
    self.w.focus_view(v)
    return v

  def _update_v(self, content):
    if self.v != None:
      v = self.v
      edit = v.begin_edit()
      v.replace(edit, Region(0, v.size()), content)
      v.end_edit(edit)
      v.sel().clear()
      v.sel().add(Region(0, 0))

  def clear(self):
    self._update_v("")

  def refresh(self):
    if self.v != None:
      content = self.render() or ""
      self._update_v(content)

  def show(self):
    if self.v == None:
      self._mk_v()
      self.refresh()
    self.w.focus_view(self.v)

############################## LOW-LEVEL: CLIENT & SERVER ##############################

class ClientListener:
  def on_client_async_data(self, data):
    pass

class ClientSocket(EnsimeCommon):
  def __init__(self, owner, port, timeout, handlers):
    super(ClientSocket, self).__init__(owner)
    self.port = port
    self.timeout = timeout
    self.connected = False
    self.handlers = handlers
    self._lock = threading.RLock()
    self._connect_lock = threading.RLock()
    self._receiver = None
    self.socket = None

  def notify_async_data(self, data):
    for handler in self.handlers:
      if handler:
        handler.on_client_async_data(data)

  def receive_loop(self):
    while self.connected:
      try:
        msglen = self.socket.recv(6)
        if msglen:
          msglen = int(msglen, 16)
          # self.log_client("RECV: incoming message of " + str(msglen) + " bytes")

          buf = ""
          while len(buf) < msglen:
            chunk = self.socket.recv(msglen - len(buf))
            if chunk:
              # self.log_client("RECV: received a chunk of " + str(len(chunk)) + " bytes")
              buf += chunk
            else:
              raise Exception("fatal error: recv returned None")
          self.log_client("RECV: " + buf)

          try:
            s = buf.decode('utf-8')
            form = sexp.read(s)
            self.notify_async_data(form)
          except:
            self.log_client("failed to parse incoming message")
            raise
        else:
          raise Exception("fatal error: recv returned None")
      except Exception:
        self.log_client("*****    ERROR     *****")
        self.log_client(traceback.format_exc())
        self.connected = False
        self.status_message("Ensime server has disconnected")
        self.env.controller.shutdown()

  def start_receiving(self):
    t = threading.Thread(name = "ensime-client-" + str(self.w.id()) + "-" + str(self.port), target = self.receive_loop)
    t.setDaemon(True)
    t.start()
    self._receiver = t

  def connect(self):
    self._connect_lock.acquire()
    try:
      s = socket.socket()
      s.settimeout(self.timeout)
      s.connect(("127.0.0.1", self.port))
      s.settimeout(None)
      self.socket = s
      self.connected = True
      self.start_receiving()
      return s
    except socket.error as e:
      self.connected = False
      self.log_client("Cannot connect to Ensime server:  " + str(e.args))
      self.status_message("Cannot connect to Ensime server")
      self.env.controller.shutdown()
    finally:
      self._connect_lock.release()

  def send(self, request):
    try:
      if not self.connected:
        self.connect()
      self.socket.send(request)
    except:
      self.connected = False

  def close(self):
    self._connect_lock.acquire()
    try:
      if self.socket:
        self.socket.close()
    finally:
      self.connected = False
      self._connect_lock.release()

class Client(ClientListener, EnsimeCommon):
  def __init__(self, owner, port_file, timeout):
    super(Client, self).__init__(owner)
    with open(port_file) as f: self.port = int(f.read())
    self.timeout = timeout
    self.init_counters()
    methods = filter(lambda m: m[0].startswith("message_"), inspect.getmembers(self, predicate=inspect.ismethod))
    self.log_client("reflectively found " + str(len(methods)) + " message handlers: " + str(methods))
    self.handlers = dict((":" + m[0][len("message_"):].replace("_", "-"), (m[1], None, None)) for m in methods)

  def startup(self):
    self.log_client("Starting Ensime client")
    self.log_client("Launching Ensime client socket at port " + str(self.port))
    self.socket = ClientSocket(self.owner, self.port, self.timeout, [self, self.env.controller])
    return self.socket.connect()

  def shutdown(self):
    if self.socket.connected:
      self.sync_req([sym("swank:shutdown-server")])
    self.socket.close()
    self.socket = None

  def async_req(self, to_send, on_complete = None, call_back_into_ui_thread = None):
    if on_complete is not None and call_back_into_ui_thread is None:
      raise Exception("must specify a threading policy when providing a non-empty callback")
    if not self.socket:
      raise Exception("socket is either not yet initialized or is already destroyed")

    msg_id = self.next_message_id()
    self.handlers[msg_id] = (on_complete, call_back_into_ui_thread, time.time())
    msg_str = sexp.to_string([key(":swank-rpc"), to_send, msg_id])
    msg_str = "%06x" % len(msg_str) + msg_str

    self.feedback(msg_str)
    self.log_client("SEND ASYNC REQ: " + msg_str)
    self.socket.send(msg_str.encode('utf-8'))

  def sync_req(self, to_send, timeout=0):
    msg_id = self.next_message_id()
    event = threading.Event()
    self.handlers[msg_id] = (event, None, time.time())
    msg_str = sexp.to_string([key(":swank-rpc"), to_send, msg_id])
    msg_str = "%06x" % len(msg_str) + msg_str

    self.feedback(msg_str)
    self.log_client("SEND SYNC REQ: " + msg_str)
    self.socket.send(msg_str)

    max_wait = timeout or self.timeout
    event.wait(max_wait)
    if hasattr(event, "payload"):
      return event.payload
    else:
      self.log_client("sync_req #" + str(msg_id) +
                      " has timed out (didn't get a response after " +
                      str(max_wait) + " seconds)")
      return None

  def on_client_async_data(self, data):
    self.log_client("SEND ASYNC RESP: " + str(data))
    self.feedback(str(data))
    self.handle_message(data)

  # examples of responses can be seen here:
  # http://docs.sublimescala.org
  def handle_message(self, data):
    # (:return (:ok (:pid nil :server-implementation (:name "ENSIMEserver") :machine nil :features nil :version "0.0.1")) 1)
    # (:background-message "Initializing Analyzer. Please wait...")
    # (:compiler-ready t)
    # (:typecheck-result (:lang :scala :is-full t :notes nil))
    msg_type = str(data[0])
    handler = self.handlers.get(msg_type)

    if handler:
      handler, _, _ = handler
      msg_id = data[-1] if msg_type == ":return" else None
      data = data[1:-1] if msg_type == ":return" else data[1:]
      payload = None
      if len(data) == 1: payload = data[0]
      if len(data) > 1: payload = data
      return handler(msg_id, payload)
    else:
      self.log_client("unexpected message type: " + msg_type)

  def message_return(self, msg_id, payload):
    handler, call_back_into_ui_thread, req_time = self.handlers.get(msg_id)
    if handler: del self.handlers[msg_id]

    resp_time = time.time()
    self.log_client("request #" + str(msg_id) + " took " + str(resp_time - req_time) + " seconds")

    reply_type = str(payload[0])
    # (:return (:ok (:project-name nil :source-roots ("D:\\Dropbox\\Scratchpad\\Scala"))) 2)
    if reply_type == ":ok":
      payload = payload[1]
      if handler:
        if callable(handler):
          if call_back_into_ui_thread:
            sublime.set_timeout(bind(handler, payload), 0)
          else:
            handler(payload)
        else:
          handler.payload = payload
          handler.set()
      else:
        self.log_client("warning: no handler registered for message #" + str(msg_id) + " with payload " + str(payload))
    # (:return (:abort 210 "Error occurred in Analyzer. Check the server log.") 3)
    elif reply_type == ":abort":
      detail = payload[2]
      if msg_id <= 1: # initialize project
        self.error_message(self.prettify_error_detail(detail))
        self.status_message("Ensime startup has failed")
        self.env.controller.shutdown()
      else:
        self.status_message(detail)
    # (:return (:error NNN "SSS") 4)
    elif reply_type == ":error":
      detail = payload[2]
      self.error_message(self.prettify_error_detail(detail))
    else:
      self.log_client("unexpected reply type: " + reply_type)

  def call_back_into_ui_thread(vanilla):
    def wrapped(self, msg_id, payload):
      sublime.set_timeout(bind(vanilla, self, msg_id, payload), 0)
    return wrapped

  @call_back_into_ui_thread
  def message_compiler_ready(self, msg_id, payload):
    self.env.compiler_ready = True
    filename = self.env.plugin_root + os.sep + "Encouragements.txt"
    lines = [line.strip() for line in open(filename)]
    msg = lines[random.randint(0, len(lines) - 1)]
    self.status_message(msg + " This could be the start of a beautiful program, " + getpass.getuser().capitalize()  + ".")
    self.colorize_all()
    v = self.w.active_view()
    if self.in_project(v): v.run_command("save")

  @call_back_into_ui_thread
  def message_indexer_ready(self, msg_id, payload):
    pass

  @call_back_into_ui_thread
  def message_full_typecheck_finished(self, msg_id, payload):
    pass

  @call_back_into_ui_thread
  def message_background_message(self, msg_id, payload):
    # (:background-message 105 "Initializing Analyzer. Please wait...")
    self.status_message(payload[1])

  def _update_note_ui(self):
    self.redraw_all_highlights()
    v = self.w.active_view()
    if v != None:
      self.env.notee = v
      self.env.notes.refresh()

  @call_back_into_ui_thread
  def message_java_notes(self, msg_id, payload):
    self.env._notes += rpc.Note.parse_list(payload)
    self._update_note_ui()

  @call_back_into_ui_thread
  def message_scala_notes(self, msg_id, payload):
    self.env._notes += rpc.Note.parse_list(payload)
    self._update_note_ui()

  @call_back_into_ui_thread
  def message_clear_all_java_notes(self, msg_id, _):
    self.env._notes = filter(lambda n: not n.file_name.endswith(".java"), self.env._notes)
    self._update_note_ui()

  @call_back_into_ui_thread
  def message_clear_all_scala_notes(self, msg_id, _):
    self.env._notes = filter(lambda n: not n.file_name.endswith(".scala"), self.env._notes)
    self._update_note_ui()

  @call_back_into_ui_thread
  def message_debug_event(self, msg_id, payload):
    debug_event = rpc.DebugEvent.parse(payload)
    if debug_event: self.env.debugger.handle(debug_event)

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

  def prettify_error_detail(self, detail):
    detail = "Ensime server has encountered a fatal error: " + detail
    if detail.endswith(". Check the server log."):
      detail = detail[0:-len(". Check the server log.")]
    if not detail.endswith("."): detail += "."
    detail += "\n\nCheck the server log at " + self.env.log_root + os.sep + "server.log" + "."
    return detail

  def feedback(self, msg):
    msg = msg.replace("\r\n", "\n").replace("\r", "\n") + "\n"
    self.log_client(msg)

class ServerListener:
  def on_server_data(self, data):
    pass

class ServerProcess(EnsimeCommon):
  def __init__(self, owner, command, listeners):
    super(ServerProcess, self).__init__(owner)
    self.killed = False
    self.listeners = listeners or []

    env = os.environ.copy()
    args = self.env.ensime_args or "-Xms256M -Xmx1512M -XX:PermSize=128m -Xss1M -Dfile.encoding=UTF-8"
    if not "-Densime.explode.on.disconnect" in args: args += " -Densime.explode.on.disconnect=1"
    env["ENSIME_JVM_ARGS"] = str(args) # unicode not supported here

    if os.name =="nt":
      startupinfo = subprocess.STARTUPINFO()
      startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
      startupinfo.wShowWindow |= 1 # SW_SHOWNORMAL
      creationflags = 0x8000000 # CREATE_NO_WINDOW
      self.proc = subprocess.Popen(
        command,
        stdout = subprocess.PIPE,
        stderr = subprocess.PIPE,
        startupinfo = startupinfo,
        creationflags = creationflags,
        env = env,
        cwd = self.env.server_path)
    else:
      self.proc = subprocess.Popen(
        command,
        stdout = subprocess.PIPE,
        stderr = subprocess.PIPE,
        env = env,
        cwd = self.env.server_path)
    self.log_server("started ensime server with pid " + str(self.proc.pid))

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
            listener.on_server_data(data)
      else:
        self.proc.stdout.close()
        break

  def read_stderr(self):
    while True:
      data = os.read(self.proc.stderr.fileno(), 2**15)
      if data != "":
        for listener in self.listeners:
          if listener:
            listener.on_server_data(data)
      else:
        self.proc.stderr.close()
        break

class Server(ServerListener, EnsimeCommon):
  def __init__(self, owner, port_file):
    super(Server, self).__init__(owner)
    self.port_file = port_file

  def startup(self):
    ensime_command = self.get_ensime_command()
    if self.get_ensime_command() and self.verify_ensime_version():
      self.log_server("Starting Ensime server")
      self.log_server("Launching Ensime server process with command = " + str(ensime_command) + " and args = " + str(self.env.ensime_args))
      self.proc = ServerProcess(self.owner, ensime_command, [self, self.env.controller])
      return True

  def get_ensime_command(self):
    if not os.path.exists(self.env.ensime_executable):
      message = "Ensime server executable \"" + self.env.ensime_executable + "\" does not exist."
      message += "\n\n"
      message += "If you haven't yet installed Ensime server, download it from http://download.sublimescala.org, "
      message += "and unpack it into the \"server\" subfolder of the SublimeEnsime plugin home, which is usually located at " + sublime.packages_path() + os.sep + "sublime-ensime. "
      message += "Your installation is correct if inside the \"server\" subfolder there are folders named \"bin\" and \"lib\"."
      message += "\n\n"
      message += "If you have already installed Ensime server, check your Ensime.sublime-settings (accessible via Preferences > Package Settings > Ensime) "
      message += "and make sure that the \"ensime_server_path\" entry points to a valid location relative to " + sublime.packages_path() + " "
      message += "(currently it points to the path shown above)."
      self.error_message(message)
      return
    return [self.env.ensime_executable, self.port_file]

  def verify_ensime_version(self):
    self.log_server("Verifying Ensime server version")
    ensime_jar_dir = self.env.server_path + os.sep + "lib"
    ensime_jars = filter(os.path.isfile, glob.glob(ensime_jar_dir + os.sep + "ensime*.jar"))
    if len(ensime_jars) != 1:
      self.log_server("Error: no ensime*.jar files found in " + ensime_jar_dir)
      self.log_server("Warning: skipping the version check, proceeding with starting up the server")
      return True
    ensime_jar = None
    try:
      ensime_jar = zipfile.ZipFile(ensime_jars[0], "r")
      manifest = ensime_jar.open("META-INF/MANIFEST.MF", "r").readlines()
      def parse_line(line):
        try:
          m = re.match(r"^(.*?):(.*)$", line)
          return (m.group(1).strip(), m.group(2).strip())
        except:
          self.log_server("Problems parsing line: " + line)
      manifest = dict(parse_line(line) for line in manifest if line.strip())
      def parse_version(s):
        try:
          m = re.match(r"^(\d+)\.(\d+)(?:.(\d+)(?:.(\d+))?)?$", s)
          return map(lambda s: int(s), filter(lambda s: s, m.groups()))
        except:
          self.log_server("Problems parsing version: " + s)
      aversion = parse_version(manifest["Implementation-Version"])
      rversion = parse_version(self.env.settings.get("min_ensime_server_version"))
      self.log_server("Required version: " + str(rversion) + ", actual version: " + str(aversion))
      if aversion < rversion:
        message = "Ensime server version is " + manifest["Implementation-Version"] + ", "
        message += "required version is at least " + str(self.env.settings.get("min_ensime_server_version")) + "."
        message += "\n\n"
        message += "To update your Ensime server, download a suitable version from http://download.sublimescala.org, "
        message += "and unpack it into the \"server\" subfolder of the SublimeEnsime plugin home, which is usually located at " + sublime.packages_path() + os.sep + "sublime-ensime. "
        message += "Your installation is correct if inside the \"server\" subfolder there are folders named \"bin\" and \"lib\"."
        self.error_message(message)
        return
      return True
    except:
      exc_type, exc_value, exc_tb = sys.exc_info()
      detailed_info = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
      self.log_server("Error verifying Ensime server version:" + detailed_info)
      self.log_server("Warning: skipping the version check, proceeding with starting up the server")
      return True
    finally:
      if ensime_jar: ensime_jar.close()

  def on_server_data(self, data):
    str_data = str(data).replace("\r\n", "\n").replace("\r", "\n")
    self.log_server(str_data)

  def shutdown(self):
    self.proc.kill()
    self.proc = None

class Controller(EnsimeCommon, ClientListener, ServerListener):
  def __init__(self, env):
    super(Controller, self).__init__(env.w)
    self.client = None
    self.server = None

  def startup(self):
    try:
      if not self.env.running:
        if self.env.settings.get("connect_to_external_server", False):
          self.port_file = self.env.settings.get("external_server_port_file")
          if not self.port_file:
            message = "\"connect_to_external_server\" in your Ensime.sublime-settings is set to true, "
            message += "however \"external_server_port_file\" is not specified. "
            message += "Set it to a meaningful value and restart Ensime."
            sublime.set_timeout(bind(sublime.error_message, message), 0)
            raise Exception("external_server_port_file not specified")
          if not os.path.exists(self.port_file):
            message = "\"connect_to_external_server\" in your Ensime.sublime-settings is set to true, "
            message += ("however \"external_server_port_file\" is set to a non-existent file \"" + self.port_file + "\" . ")
            message += "Check the configuration and restart Ensime."
            sublime.set_timeout(bind(sublime.error_message, message), 0)
            raise Exception("external_server_port_file not specified")
          self.server = None
          self.env.running = True
          sublime.set_timeout(self.ignition, 0)
        else:
          _, port_file = tempfile.mkstemp("_ensime_port")
          self.port_file = port_file
          self.server = Server(self.owner, port_file)
          self.server.startup() # delay handshake until the port number has been written
    except:
      self.env.running = False
      raise

  def on_server_data(self, data):
    if not self.env.running and re.search("Wrote port", data):
      self.env.running = True
      sublime.set_timeout(self.ignition, 0)

  def ignition(self):
    timeout = self.env.settings.get("timeout_sync_roundtrip", 3)
    self.client = Client(self.owner, self.port_file, timeout)
    self.client.startup()
    self.status_message("Initializing Ensime server... ")
    def init_project(subproject_name):
      conf = self.env.project_config + [key(":active-subproject"), subproject_name]
      self.rpc.init_project(conf)
    dotensime.select_subproject(self.env.project_config, self.owner, init_project)

  def shutdown(self):
    try:
      if self.env.running:
        try:
          self.env.debugger.shutdown()
        except:
          self.log("Error shutting down ensime debugger:")
          self.log(traceback.format_exc())
        try:
          self.env._notes = []
          sublime.set_timeout(self.uncolorize_all, 0)
          sublime.set_timeout(self.env.notes.clear, 0)
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
      self.port_file = None
      self.env.running = False
      self.env.compiler_ready = False
      self.client = None
      self.server = None

############################## ENSIME <-> SUBLIME ADAPTER ##############################

class Daemon(EnsimeEventListener):

  def on_load(self):
    # print "on_load"
    if self.is_running() and self.in_project():
      self.rpc.typecheck_file(self.v.file_name())

  def on_post_save(self):
    # print "on_post_save"
    if self.is_running() and self.in_project():
      self.rpc.typecheck_file(self.v.file_name())
    if same_paths(self.v.file_name(), self.env.session_file):
      self.env.load_session()
      self.redraw_all_breakpoints()

  def on_activated(self):
    # print "on_activated"
    self.colorize()
    if self.in_project():
      self.env.notee = self.v
      self.env.notes.refresh()

  def on_selection_modified(self):
    # print "on_selection_modified"
    self.redraw_status()

  def on_modified(self):
    # print "on_modified"
    rs = self.v.get_regions(ENSIME_BREAKPOINT_REGION)
    if rs:
      irrelevant_breakpoints = filter(
        lambda b: not same_paths(b.file_name, self.v.file_name()),
        self.env.breakpoints)
      def new_breakpoint_position(r):
        lines = self.v.lines(r)
        if lines:
          (linum, _) = self.v.rowcol(lines[0].begin())
          return dotsession.Breakpoint(self.v.file_name(), linum + 1)
      relevant_breakpoints = filter(lambda b: b, map(new_breakpoint_position, rs))
      self.env.breakpoints = irrelevant_breakpoints + relevant_breakpoints
      self.env.save_session()
      self.redraw_breakpoints()

class Colorer(EnsimeCommon):

  def refresh(self):
    self.clear_all()
    self.update_highlights()
    self.update_status()
    self.update_breakpoints()
    self.update_debug_focus()

  def clear_all(self):
    self.v.erase_regions(ENSIME_ERROR_OUTLINE_REGION)
    self.v.erase_regions(ENSIME_ERROR_UNDERLINE_REGION)
    # don't erase breakpoints, they should be permanent regardless of whether ensime is running or not
    # self.v.erase_regions(ENSIME_BREAKPOINT_REGION)
    self.v.erase_regions(ENSIME_DEBUGFOCUS_REGION)
    self.update_status()

  def update_highlights(self):
    self.v.erase_regions(ENSIME_ERROR_OUTLINE_REGION)
    self.v.erase_regions(ENSIME_ERROR_UNDERLINE_REGION)

    if self.env:
      relevant_notes = filter(
        lambda note: same_paths(note.file_name, self.v.file_name()), self.env._notes)

      # Underline specific error range
      underlines = [sublime.Region(note.start, note.end) for note in relevant_notes]
      if self.env.settings.get("error_highlight") and self.env.settings.get("error_underline"):
        self.v.add_regions(
          ENSIME_ERROR_UNDERLINE_REGION,
          underlines + self.v.get_regions(ENSIME_ERROR_UNDERLINE_REGION),
          self.env.settings.get("error_scope"),
          sublime.DRAW_EMPTY_AS_OVERWRITE)

      # Outline entire errored line
      errors = [self.v.full_line(note.start) for note in relevant_notes]
      if self.env.settings.get("error_highlight"):
        self.v.add_regions(
          ENSIME_ERROR_OUTLINE_REGION,
          errors + self.v.get_regions(ENSIME_ERROR_OUTLINE_REGION),
          self.env.settings.get("error_scope"),
          self.env.settings.get("error_icon"),
          sublime.DRAW_OUTLINED)

      # we might need to add/remove/refresh the error message in the status bar
      self.redraw_status()

      # breakpoints and debug focus should always have priority over red squiggles
      self.update_breakpoints()
      self.update_debug_focus()

  def update_status(self, custom_status = None):
    if custom_status:
      self._update_statusbar(custom_status)
    elif self.env and self.env.settings.get("ensime_statusbar_showerrors"):
      if self.v.sel():
        relevant_notes = filter(
          lambda note: same_paths(note.file_name, self.v.file_name()),
          self.env._notes)
        bol = self.v.line(self.v.sel()[0].begin()).begin()
        eol = self.v.line(self.v.sel()[0].begin()).end()
        msgs = [note.message for note in relevant_notes
                if (bol <= note.start and note.start <= eol) or
                (bol <= note.end and note.end <= eol)]
        self._update_statusbar("; ".join(msgs))
    else:
      self._update_statusbar(None)

  def _update_statusbar(self, status):
    sublime.set_timeout(bind(self._update_statusbar_callback, status), 100)

  def _update_statusbar_callback(self, status):
    settings = self.env.settings if self.env else sublime.load_settings("Ensime.sublime-settings")
    statusgroup = settings.get("ensime_statusbar_group", "ensime")
    status = str(status)
    if settings.get("ensime_statusbar_heartbeat_enabled", True):
      heart_beats = self.is_running()
      if heart_beats:
        def calculate_heartbeat_message():
          def format_debugging_message(msg):
            try: return msg % (self.env.profile.name or "")
            except: return msg
          if self.in_project():
            if self.env.profile:
              return format_debugging_message(settings.get("ensime_statusbar_heartbeat_inproject_debugging"))
            else:
              return settings.get("ensime_statusbar_heartbeat_inproject_normal")
          else:
            if self.env.profile:
              return format_debugging_message(settings.get("ensime_statusbar_heartbeat_notinproject_debugging"))
            else:
              return settings.get("ensime_statusbar_heartbeat_notinproject_normal")
        heartbeat_message = calculate_heartbeat_message()
        if heartbeat_message:
          heartbeat_message = heartbeat_message.strip()
          if not status:
            status = heartbeat_message
          else:
            heartbeat_joint = settings.get("ensime_statusbar_heartbeat_joint")
            status = heartbeat_message + heartbeat_joint + status
    if status:
      maxlength = settings.get("ensime_statusbar_maxlength", 150)
      if len(status) > maxlength:
        status = status[0:maxlength] + "..."
      self.v.set_status(statusgroup, status)
    else:
      self.v.erase_status(statusgroup)

  def update_breakpoints(self):
    self.v.erase_regions(ENSIME_BREAKPOINT_REGION)
    if self.v.is_loading():
      sublime.set_timeout(self.update_breakpoints, 100)
    else:
      if self.env:
        relevant_breakpoints = filter(
          lambda breakpoint: same_paths(
            breakpoint.file_name, self.v.file_name()),
          self.env.breakpoints)
        regions = [self.v.full_line(self.v.text_point(breakpoint.line - 1, 0))
                   for breakpoint in relevant_breakpoints]
        self.v.add_regions(
          ENSIME_BREAKPOINT_REGION,
          regions,
          self.env.settings.get("breakpoint_scope"),
          self.env.settings.get("breakpoint_icon"),
          sublime.HIDDEN)
          # sublime.DRAW_OUTLINED)

  def update_debug_focus(self):
    self.v.erase_regions(ENSIME_DEBUGFOCUS_REGION)
    if self.v.is_loading():
      sublime.set_timeout(self.update_debug_focus, 100)
    else:
      if self.env and self.env.focus and same_paths(self.env.focus.file_name, self.v.file_name()):
          focused_region = self.v.full_line(self.v.text_point(self.env.focus.line - 1, 0))
          self.v.add_regions(
            ENSIME_DEBUGFOCUS_REGION,
            [focused_region],
            self.env.settings.get("debugfocus_scope"),
            self.env.settings.get("debugfocus_icon"))
          w = self.v.window() or sublime.active_window()
          w.focus_view(self.v)
          self.update_breakpoints()
          sublime.set_timeout(bind(self._scroll_viewport, self.v, focused_region), 0)

  def _scroll_viewport(self, v, region):
    # thanks to Fredrik Ehnbom
    # see https://github.com/quarnster/SublimeGDB/blob/master/sublimegdb.py
    # Shouldn't have to call viewport_extent, but it
    # seems to flush whatever value is stale so that
    # the following set_viewport_position works.
    # Keeping it around as a WAR until it's fixed
    # in Sublime Text 2.
    v.viewport_extent()
    # v.set_viewport_position(data, False)
    v.sel().clear()
    v.sel().add(region.begin())
    v.show(region)

class Completer(EnsimeEventListener):

  def _signature_doc(self, signature):
    """Given a ensime CompletionSignature structure, returns a short
    string suitable for showing in the help section of the completion
    pop-up."""
    sections = signature[0] or []
    section_param_strs = [[param[1] for param in params] for params in sections]
    section_strs = ["(" + ", ".join(tpes) + ")" for tpes in
                    section_param_strs]
    return ", ".join(section_strs)

  def _signature_snippet(self, signature):
    """Given a ensime CompletionSignature structure, returns a Sublime Text
    snippet describing the method parameters."""
    snippet = []
    sections = signature[0] or []
    section_snippets = []
    i = 1
    for params in sections:
      param_snippets = []
      for param in params:
        name,tpe = param
        param_snippets.append("${%s:%s:%s}" % (i, name, tpe))
        i += 1
      section_snippets.append("(" + ", ".join(param_snippets) + ")")
    return ", ".join(section_snippets)

  def _completion_response(self, ensime_completions):
    """Transform list of completions from ensime API to a the structure
    necessary for returning to sublime API."""
    return ([(c.name + "\t" + self._signature_doc(c.signature),
              c.name + self._signature_snippet(c.signature))
             for c in ensime_completions],
            sublime.INHIBIT_EXPLICIT_COMPLETIONS |
            sublime.INHIBIT_WORD_COMPLETIONS)

  def _query_completions(self, prefix, locations):
    """Query the ensime API for completions. Note: we must ask for _all_
    completions as sublime will not re-query unless this query returns an
    empty list."""
    # Short circuit for prefix that is known to return empty list
    # TODO(aemoncannon): Clear ignore prefix if the user
    # moves point to new context.
    if (self.env.completion_ignore_prefix and
        prefix.startswith(self.env.completion_ignore_prefix)):
      return self._completion_response([])
    else:
      self.env.completion_ignore_prefix = None
    if self.v.is_dirty():
      edits = diff.diff_view_with_disk(self.v)
      self.rpc.patch_source(self.v.file_name(), edits)
    completions = self.rpc.completions(self.v.file_name(), locations[0], 0, False, False)
    if not completions:
      self.env.completion_ignore_prefix = prefix
    return self._completion_response(completions)

  def on_query_completions(self, prefix, locations):
    if self.env.running and self.in_project():
      return self._query_completions(prefix, locations)
    else:
      return []

############################## SUBLIME COMMANDS: MAINTENANCE ##############################

class EnsimeStartup(EnsimeWindowCommand):
  def is_enabled(self):
    return not self.env.running

  def run(self):
    # refreshes the config (fixes #29)
    self.env.recalc()

    if not self.env.project_config:
      (_, _, error_handler) = dotensime.load(self.w)
      error_handler()
      return

    self.env.controller = Controller(self.env)
    self.env.controller.startup()

class EnsimeShutdown(RunningOnly, EnsimeWindowCommand):
  def run(self):
    self.env.controller.shutdown()

class EnsimeRestart(RunningOnly, EnsimeWindowCommand):
  def run(self):
    self.w.run_command("ensime_shutdown")
    sublime.set_timeout(bind(self.w.run_command, "ensime_startup"), 100)

class EnsimeCreateProject(ProjectDoesntExist, EnsimeWindowCommand):
  def run(self):
    dotensime.create(self.w)

class EnsimeShowProject(ProjectExists, EnsimeWindowCommand):
  def run(self):
    dotensime.edit(self.w)

class EnsimeShowSession(EnsimeWindowCommand):
  def is_enabled(self):
    return self.is_valid()

  def run(self):
    dotsession.edit(self.env)

def _show_log(self, file_name):
  log = self.env.log_root + os.sep + file_name
  line = 1
  try:
   with open(log) as f: line = len(f.readlines())
  except:
    pass
  self.w.open_file("%s:%d:%d" % (log, line, 1), sublime.ENCODED_POSITION)

class EnsimeShowClientLog(EnsimeWindowCommand):
  def is_enabled(self):
    return self.is_valid()

  def run(self):
    _show_log(self, "client.log")

class EnsimeShowServerLog(EnsimeWindowCommand):
  def is_enabled(self):
    return self.is_valid()

  def run(self):
    _show_log(self, "server.log")

class EnsimeHighlight(RunningOnly, EnsimeWindowCommand):
  def run(self, enable = True):
    self.env.settings.set("error_highlight", not not enable)
    sublime.save_settings("Ensime.sublime-settings")
    self.refresh_all_highlights()

############################## SUBLIME COMMANDS: DEVELOPMENT ##############################

class EnsimeShowNotes(EnsimeWindowCommand):
  def is_enabled(self):
    return self.env.notes.can_show()

  def run(self):
    self.env.notes.show()

class Notes(EnsimeToolView):
  def can_show(self):
    return self.is_running() and self.in_project(self.w.active_view())

  @property
  def name(self):
    return ENSIME_NOTES_VIEW

  def clear(self):
    self.env.notee = None
    super(Notes, self).clear()

  def render(self):
    lines = []
    # print "notee: " + str(self.env.notee.file_name() or self.env.notee.name())
    if self.env.notee:
      relevant_notes = filter(
        lambda note: same_paths(note.file_name, self.env.notee.file_name()),
        self.env._notes)
      for note in relevant_notes:
        loc = self.project_relative_path(note.file_name) + ":" + str(note.line)
        severity = note.severity
        message = note.message
        diagnostics = ": ".join(str(x) for x in [loc, severity, message])
        lines += [diagnostics]
        lines += [self.env.notee.substr(self.env.notee.line(note.start))]
        lines += [" " * (note.col - 1) + "^"]
    return "\n".join(lines)

class EnsimeAltClick(EnsimeMouseCommand):
  def run(self, target):
    self.v.run_command("ensime_inspect_type_at_point", {"target": target})

class EnsimeInspectTypeAtPoint(RunningProjectFileOnly, EnsimeTextCommand):
  def run(self, edit, target= None):
    pos = int(target or self.v.sel()[0].begin())
    self.rpc.type_at_point(self.v.file_name(), pos, self.handle_reply)

  def handle_reply(self, tpe):
    if tpe and tpe.name != "<notype>":
      if tpe.arrow_type:
        summary = "method type"
      else:
        summary = tpe.full_name
        if tpe.type_args:
          summary += ("[" + ", ".join(map(lambda t: t.name, tpe.type_args)) + "]")
      self.status_message(summary)
    else:
      self.status_message("Cannot find out type")

class EnsimeCtrlClick(EnsimeMouseCommand):
  def run(self, target):
    self.v.run_command("ensime_go_to_definition", {"target": target})

class EnsimeGoToDefinition(RunningProjectFileOnly, EnsimeTextCommand):
  def run(self, edit, target= None):
    pos = int(target or self.v.sel()[0].begin())
    self.rpc.symbol_at_point(self.v.file_name(), pos, self.handle_reply)

  def handle_reply(self, info):
    if info and info.decl_pos:
      # fails from time to time, because sometimes self.w is None
      # v = self.w.open_file(info.decl_pos.file_name)

      # <the first attempt to make it work, gave rise to #31>
      # v = sublime.active_window().open_file(info.decl_pos.file_name)
      # # <workaround 1> this one doesn't work, because of the pervasive problem with `show`
      # # v.sel().clear()
      # # v.sel().add(Region(info.decl_pos.offset, info.decl_pos.offset))
      # # v.show(info.decl_pos.offset)
      # # <workaround 2> this one ignores the second open_file
      # # row, col = v.rowcol(info.decl_pos.offset)
      # # sublime.active_window().open_file("%s:%d:%d" % (info.decl_pos.file_name, row + 1, col + 1), sublime.ENCODED_POSITION)

      file_name = info.decl_pos.file_name
      contents = None
      with open(file_name, "rb") as f: contents = f.read().decode("utf8")
      if contents:
        # todo. doesn't support mixed line endings
        def detect_newline():
          if "\n" in contents and "\r" in contents: return "\r\n"
          if "\n" in contents: return "\n"
          if "\r" in contents: return "\r"
          return None
        zb_offset = info.decl_pos.offset
        newline = detect_newline()
        zb_row = contents.count(newline, 0, zb_offset) if newline else 0
        zb_col = zb_offset - contents.rfind(newline, 0, zb_offset) - len(newline) if newline else zb_offset
        def open_file():
          return self.w.open_file("%s:%d:%d" % (file_name, zb_row + 1, zb_col + 1), sublime.ENCODED_POSITION)

        w = self.w or sublime.active_window()
        g, i = (None, None)
        if self.v != None and same_paths(self.v.file_name(), file_name):
          # open_file doesn't work, so we have to work around
          # open_file()

          # <workaround 1> close and then reopen
          # works fine but is hard on the eyes
          # g, i = w.get_view_index(self.v)
          # self.v.run_command("save")
          # self.w.run_command("close_file")
          # v = open_file()
          # self.w.set_view_index(v, g, i)

          # <workaround 2> v.show
          # has proven to be very unreliable
          # but let's try and use it
          offset_in_editor = self.v.text_point(zb_row, zb_col)
          region_in_editor = Region(offset_in_editor, offset_in_editor)
          sublime.set_timeout(bind(self._scroll_viewport, self.v, region_in_editor), 100)
        else:
          open_file()
      else:
        self.status_message("Cannot open " + file_name)
    else:
      self.status_message("Cannot locate " + (str(info.name) if info else "symbol"))

  def _scroll_viewport(self, v, region):
    v.sel().clear()
    v.sel().add(region.begin())
    v.show(region)

############################## SUBLIME COMMANDS: DEBUGGING ##############################

class EnsimeToggleBreakpoint(ProjectFileOnly, EnsimeTextCommand):
  def run(self, edit):
    file_name = self.v.file_name()
    if file_name and len(self.v.sel()) == 1:
      zb_line, _ = self.v.rowcol(self.v.sel()[0].begin())
      line = zb_line + 1
      old_breakpoints = self.env.breakpoints
      new_breakpoints = filter(
        lambda b: not (same_paths(b.file_name, file_name) and b.line == line),
        self.env.breakpoints)
      if len(old_breakpoints) == len(new_breakpoints):
        # add
        new_breakpoints.append(dotsession.Breakpoint(file_name, line))
        if self.env.profile: self.rpc.debug_set_break(file_name, line)
      else:
        # remove
        if self.env.profile: self.rpc.debug_clear_break(file_name, line)
      self.env.breakpoints = new_breakpoints
      self.env.save_session()
      self.redraw_all_breakpoints()

class EnsimeClearBreakpoints(EnsimeWindowCommand):
  def run(self):
    self.env.load_session()
    if self.env.breakpoints and sublime.ok_cancel_dialog("This will delete all breakpoints. Do you wish to continue?"):
      self.env.breakpoints = []
      if self.online: self.rpc.clear_all_breaks()
      self.env.save_session()
      self.redraw_all_breakpoints()

class EnsimeStartDebugger(NotDebuggingOnly, EnsimeWindowCommand):
  def run(self):
    self.env.debugger.start()

class EnsimeStopDebugger(DebuggingOnly, EnsimeWindowCommand):
  def run(self):
    self.env.debugger.stop()

class EnsimeStepInto(FocusedOnly, EnsimeWindowCommand):
  def run(self):
    self.env.debugger.step_into()

class EnsimeStepOver(FocusedOnly, EnsimeWindowCommand):
  def run(self):
    self.env.debugger.step_over()

class EnsimeResumeDebugger(FocusedOnly, EnsimeWindowCommand):
  def run(self):
    self.env.debugger.resume()

class EnsimeSmartRunDebugger(EnsimeWindowCommand):
  def __init__(self, window):
    super(EnsimeSmartRunDebugger, self).__init__(window)
    self.startup_attempts = 0

  def is_enabled(self):
    return not self.env.profile or self.env.focus

  def run(self):
    if not self.env.profile:
      if self.env.compiler_ready:
        self.startup_attempts = 0
        sublime.set_timeout(bind(self.w.run_command, "ensime_start_debugger"), 1000)
      else:
        self.startup_attempts += 1
        if self.startup_attempts < 10:
          self.w.run_command("ensime_startup")
          sublime.set_timeout(self.run, 1000)
        else:
          self.startup_attempts = 0
    if self.env.focus:
      self.w.run_command("ensime_resume_debugger")

class EnsimeShowOutput(EnsimeWindowCommand):
  def is_enabled(self):
    return self.env.output.can_show()

  def run(self):
    self.env.output.show()

class EnsimeShowStack(EnsimeWindowCommand):
  def is_enabled(self):
    return self.env.stack.can_show()

  def run(self):
    self.env.stack.show()

class EnsimeShowLocals(EnsimeWindowCommand):
  def is_enabled(self):
    return self.env.locals.can_show()

  def run(self):
    self.env.locals.show()

class Debugger(EnsimeCommon):
  def __init__(self, env):
    super(Debugger, self).__init__(env.w)

  def shutdown(self, erase_dashboard = False):
    self.env.profile = None
    self.env.focus = None
    if erase_dashboard:
      self.env.output.clear()
      self.env.stack.clear()
      self.env.locals.clear()

  def handle(self, event):
    if event.type == "start":
      self.shutdown(erase_dashboard = True)
      self.env.profile = self.env.profile_being_launched
      self.status_message("Debugger has successfully started")
    elif event.type == "death" or event.type == "disconnect":
      self.shutdown(erase_dashboard = False) # so that people can take a look later
      self.status_message("Debuggee has died" if event.type == "death" else "Debugger has disconnected")
    elif event.type == "output":
      self.env.output.append(event.body)
    elif event.type == "exception" or event.type == "breakpoint" or event.type == "step":
      if event.type == "exception":
        # todo. how to I get to the details of this exception?
        rendered = "an exception has been thrown\n"
        self.env.output.append(rendered)
      # sometimes thrown exceptions don't have file_name and/or line set
      # I think it's best to ignore them for the time being
      if event.file_name and event.line:
        self.env.focus = Focus(event.thread_id, event.thread_name, event.file_name, event.line)
        self.env.w.open_file("%s:%d:%d" % (self.env.focus.file_name, self.env.focus.line, 1), sublime.ENCODED_POSITION)
        self.redraw_all_debug_focuses()
        self.env.stack.refresh()
        self.env.locals.refresh()
        self.status_message("Debugger has stopped at " + str(event.file_name) + ", line " + str(event.line))
    self.redraw_status(self.w.active_view())

  def start(self):
    launch = dotsession.load_launch(self.env)
    if launch:
      self.status_message("Starting the debugger...")
      self.env.profile_being_launched = launch
      def callback(status):
        if status: self.status_message("Debugger has successfully started")
        else: self.status_message("Debugger has failed to start")
      self.rpc.debug_start(launch, self.env.breakpoints, callback)
    else:
      self.status_message("Bad debug configuration")

  def stop(self):
    self.rpc.debug_stop()

  def step_into(self):
    self.rpc.debug_step(self.env.focus.thread_id)

  def step_over(self):
    self.rpc.debug_next(self.env.focus.thread_id)

  def resume(self):
    self.rpc.debug_continue(self.env.focus.thread_id)

class Focus(object):
  def __init__(self, thread_id, thread_name, file_name, line):
    self.thread_id = thread_id
    self.thread_name = thread_name
    self.file_name = file_name
    self.line = line

  def __eq__(self, other):
    return (type(self) == type(other) and
           self.thread_id == other.thread_id and
           self.thread_name == other.thread_name and
           self.file_name == other.file_name and
           self.line == other.line)

  def __str__(self):
    return "%s:%s:%s:%s" % (self.thread_id, self.thread_name, self.file_name, self.line)

class Output(EnsimeToolView):
  def can_show(self):
    return self.env._output

  @property
  def name(self):
    return ENSIME_OUTPUT_VIEW

  def clear(self):
    self.env._output = ""
    super(Output, self).clear()

  def append(self, data):
    if data:
      self.env._output += data
      if self.v:
        selection_was_at_end = len(self.v.sel()) == 1 and self.v.sel()[0] == sublime.Region(self.v.size())
        edit = v.begin_edit()
        v.insert(edit, v.size(), data)
        if selection_was_at_end:
          v.show(v.size())
        v.end_edit(edit)

  def render(self):
    return self.env._output

class Stack(EnsimeToolView):
  def can_show(self):
    return self.env and self.env.focus

  def name(self):
    return ENSIME_STACK_VIEW

  def render(self):
    pass

class Locals(EnsimeToolView):
  def can_show(self):
    return self.env and self.env.focus

  @property
  def name(self):
    return ENSIME_LOCALS_VIEW

  def render(self):
    pass
