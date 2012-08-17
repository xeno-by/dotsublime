import sublime
from sublime import *
from sublime_plugin import *
import os, threading, thread, socket, getpass, signal, glob
import subprocess, tempfile, datetime, time
import functools, inspect, traceback, random, re
from functools import partial as bind
import sexp
from sexp import key, sym
from string import strip
from types import *
import env
import dotensime
import diff
import json
import datetime
import paths
import zipfile

def environment_constructor(window):
  return EnsimeEnvironment(window)

class EnsimeApi:

  def type_check_file(self, file_path, on_complete = None):
    req = ensime_codec.encode_type_check_file(file_path)
    wrapped_on_complete = bind(self.type_check_file_on_complete_wrapper, on_complete) if on_complete else None
    self.env.controller.client.async_req(req, wrapped_on_complete, call_back_into_ui_thread = True)

  def type_check_file_on_complete_wrapper(self, on_complete, payload):
    return on_complete(ensime_codec.decode_type_check_file(payload))

  def add_notes(self, notes):
    self.env.notes += notes
    for v in self.w.views():
      EnsimeHighlights(v).add_notes(notes)

  def clear_notes(self, flavor = "all"):
    if flavor == "all":
      self.env.notes = []
    elif flavor == "java":
      self.env.notes = filter(lambda n: not n.file_name.endswith(".java"), self.env.notes)
    elif flavor == "scala":
      self.env.notes = filter(lambda n: not n.file_name.endswith(".scala"), self.env.notes)
    else:
      raise Exception("unknown flavor of notes: " + str(flavor))
    for v in self.w.views():
      EnsimeHighlights(v).refresh()

  def inspect_type_at_point(self, file_path, position, on_complete):
    req = ensime_codec.encode_inspect_type_at_point(file_path, position)
    wrapped_on_complete = bind(self.inspect_type_at_point_on_complete_wrapper, on_complete) if on_complete else None
    self.env.controller.client.async_req(req, wrapped_on_complete, call_back_into_ui_thread = True)

  def inspect_type_at_point_on_complete_wrapper(self, on_complete, payload):
    return on_complete(ensime_codec.decode_inspect_type_at_point(payload))

  def get_completions(self, file_path, position, max_results):
    if self.v.is_dirty():
      edits = diff.diff_view_with_disk(self.v)
      req = ensime_codec.encode_patch_source(
        self.v.file_name(), edits)
      self.env.controller.client.async_req(req)
    req = ensime_codec.encode_completions(file_path, position, max_results)
    timeout = self.env.settings.get("timeout_completion", 0.5)
    resp = self.env.controller.client.sync_req(req, timeout=timeout)
    if not resp: self.status_message("Ensime completion timed out")
    return ensime_codec.decode_completions(resp)

  def symbol_at_point(self, file_path, position, on_complete):
    req = ensime_codec.encode_symbol_at_point(file_path, position)
    wrapped_on_complete = bind(self.symbol_at_point_on_complete_wrapper, on_complete) if on_complete else None
    self.env.controller.client.async_req(req, wrapped_on_complete, call_back_into_ui_thread = True)

  def symbol_at_point_on_complete_wrapper(self, on_complete, payload):
    return on_complete(ensime_codec.decode_symbol_at_point(payload))

  @property
  def debugger(self):
    return self.env.debugger


class EnsimeBreakpoint(object):
  def __init__(self, file_name, line):
    self.file_name = file_name or ""
    self.line = line or 0

  def is_meaningful(self):
    return self.file_name != "" or self.line != 0

  def is_valid(self):
    return not not self.file_name and self.line != None

class EnsimeDebugOutput(object):
  def __init__(self, debugger):
    self.debugger = debugger
    self.contents = ""

  def is_meaningful(self):
    return self.debugger.online or self.contents

  def clear(self):
    pass

  def append(self, chunk):
    pass

  def show(self):
    pass

class EnsimeDebugFocus(object):
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

class EnsimeDebugDashboard(object):
  def __init__(self, debugger):
    self.debugger = debugger
    self.contents = ""

  def is_meaningful(self):
    return self.debugger.online or self.contents

  def clear(self):
    pass

  @property
  def focus(self):
    return self.debugger.focus

  @property
  def backtrace(self):
    pass

  @property
  def values(self):
    pass

  def show(self):
    pass

class EnsimeLaunchConfiguration(object):
  def __init__(self, name, main_class, args):
    self.name = name or ""
    self.main_class = main_class or ""
    self.args = args or ""

  def is_meaningful(self):
    return self.name != "" or self.main_class != "" or self.args != ""

  def is_valid(self):
    return not not self.main_class

  @property
  def command_line(self):
    cmdline = self.main_class
    if self.args:
      cmdline += (" " + self.args)
    return cmdline

class EnsimeDebugger(object):
  def __init__(self, env):
    self.env = env
    self.online = False
    self.event = None
    self.last_req = None
    self.steps = 0
    self.breakpoints = []
    self.launch_configs = {}
    self.current_launch_config = ""
    self.active_launch_config = None
    self.output = EnsimeDebugOutput(self)
    self.focus = None
    self.dashboard = EnsimeDebugDashboard(self)
    self.session_file = self.env.project_root + os.sep + ".ensime_session" if self.env.project_root else None
    self._load_session()

  def shutdown(self):
    self.online = False
    self._clean_slate()

  def _clean_slate(self, erase_output = True, erase_dashboard = True):
    self.event = None
    self.last_req = None
    self.steps = 0
    self.active_launch_config = None
    self.focus = None
    if erase_output: self.output.clear()
    if erase_dashboard: self.dashboard.clear()

  def _load_session(self):
    if self.session_file:
      try:
        session = None
        if os.path.exists(self.session_file):
          with open(self.session_file, "r") as f:
            contents = f.read()
            session = json.loads(contents)
        session = session or {}
        self.breakpoints = map(lambda b: EnsimeBreakpoint(paths.decode_path(b.get("file_name")), b.get("line")), session.get("breakpoints", []))
        self.breakpoints = filter(lambda b: b.is_meaningful(), self.breakpoints)
        launch_configs = map(lambda c: EnsimeLaunchConfiguration(c.get("name"), c.get("main_class"), c.get("args")), session.get("launch_configs", []))
        self.launch_configs = {}
        # todo. this might lose user data
        for c in launch_configs: self.launch_configs[c.name] = c
        self.current_launch_config = session.get("current_launch_config") or ""
        return True
      except:
        print "Ensime: " + str(self.session_file) + " has failed to load"
        exc_type, exc_value, exc_tb = sys.exc_info()
        detailed_info = '\n'.join(traceback.format_exception(exc_type, exc_value, exc_tb))
        print detailed_info

  def _save_session(self):
    if self.session_file:
      session = {}
      session["breakpoints"] = map(lambda b: {"file_name": paths.encode_path(b.file_name), "line": b.line}, self.breakpoints)
      session["launch_configs"] = map(lambda c: {"name": c.name, "main_class": c.main_class, "args": c.args}, self.launch_configs.values())
      session["current_launch_config"] = self.current_launch_config
      if not session["launch_configs"]:
        # create a dummy launch config, so that the user has easier time filling in the config
        session["launch_configs"] = [{"name": "", "main_class": "", "args": ""}]
      contents = json.dumps(session, sort_keys=True, indent=2)
      with open(self.session_file, "w") as f:
        f.write(contents)

  def _ensime_debug_set_break(self, file_name, line, on_complete = None):
    req = ensime_codec.encode_debug_set_break(file_name, line)
    wrapped_on_complete = bind(self._ensime_debug_set_break_on_complete_wrapper, on_complete) if on_complete else None
    self.env.controller.client.async_req(req, wrapped_on_complete, call_back_into_ui_thread = True)

  def _ensime_debug_set_break_on_complete_wrapper(self, on_complete, payload):
    return on_complete(ensime_codec.decode_debug_set_break(payload))

  def _ensime_debug_clear_break(self, file_name, line, on_complete = None):
    req = ensime_codec.encode_debug_clear_break(file_name, line)
    wrapped_on_complete = bind(self._ensime_debug_clear_break_on_complete_wrapper, on_complete) if on_complete else None
    self.env.controller.client.async_req(req, wrapped_on_complete, call_back_into_ui_thread = True)

  def _ensime_debug_clear_break_on_complete_wrapper(self, on_complete, payload):
    return on_complete(ensime_codec.decode_debug_clear_break(payload))

  def _ensime_debug_clear_all_breaks(self, on_complete = None):
    req = ensime_codec.encode_debug_clear_all_breaks()
    wrapped_on_complete = bind(self._ensime_debug_clear_all_breaks_on_complete_wrapper, on_complete) if on_complete else None
    self.env.controller.client.async_req(req, wrapped_on_complete, call_back_into_ui_thread = True)

  def _ensime_debug_clear_all_breaks_on_complete_wrapper(self, on_complete, payload):
    return on_complete(ensime_codec.decode_debug_clear_all_breaks(payload))

  def toggle_breakpoint(self, file_name, line):
    if file_name:
      old_breakpoints = self.breakpoints
      api = ensime_api(self.env.w.active_view())
      new_breakpoints = filter(lambda b: not (api.same_files(b.file_name, file_name) and b.line == line), self.breakpoints)
      if len(old_breakpoints) == len(new_breakpoints):
        # add
        new_breakpoints.append(EnsimeBreakpoint(file_name, line))
        if self.online: self._ensime_debug_set_break(file_name, line)
      else:
        # remove
        if self.online: self.encode_debug_clear_break(file_name, line)
      self.breakpoints = new_breakpoints
      self._save_session()
      for v in self.env.w.views():
        EnsimeHighlights(v).update_breakpoints()

  def clear_breakpoints(self):
    self.breakpoints = []
    if self.online: self._ensime_debug_clear_all_breaks()
    self._save_session()
    for v in self.env.w.views():
      EnsimeHighlights(v).update_breakpoints()

  def _handle(self, event):
    if event:
      self.event = event
      message = None
      focus_updated = False

      if event.type == "start":
        self.online = True
        active_launch_config = self.active_launch_config
        self._clean_slate()
        self.active_launch_config = active_launch_config
        message = "Debugger has successfully started"
      elif event.type == "death" or event.type == "disconnect":
        self.online = False
        self._clean_slate(erase_output = False, erase_dashboard = False) # so that people can take a look later
        message = "Debuggee has exited" if event.type == "death" else "Debugger has disconnected"
      elif event.type == "output":
        self.output.append(event.body)
      elif event.type == "exception" or event.type == "breakpoint" or event.type == "step":
        if event.type == "exception":
          # todo. how to I get to the details of this exception?
          rendered = "an exception has been thrown\n"
          self.output.append(rendered)
        self.steps += 1
        old_focus = self.focus
        new_focus = EnsimeDebugFocus(event.thread_id, event.thread_name, event.file_name, event.line)
        # if old_focus == new_focus:
        #   if self.last_req == "step_into":
        #     self.step_into()
        #     return
        #   elif self.last_req == "step_over":
        #     self.step_over()
        #     return
        # print str(new_focus)
        self.focus = new_focus
        focus_updated = True
        # message = "(step " + str(self.steps) + ") Debugger has stopped at " + str(event.file_name) + ", line " + str(event.line)
        message = "Debugger has stopped at " + str(event.file_name) + ", line " + str(event.line)

      self.event = event
      if focus_updated:
        v = self.env.w.open_file("%s:%d:%d" % (self.focus.file_name, self.focus.line, 1), sublime.ENCODED_POSITION)
      for v in self.env.w.views():
        EnsimeHighlights(v).update_status()
        EnsimeHighlights(v).update_debug_focus()
      if message:
        api = ensime_api(self.env.w.active_view())
        api.status_message(message)

  def _figure_out_launch_configuration(self):
    if not os.path.exists(self.session_file) or not os.path.getsize(self.session_file):
      message = "Launch configuration does not exist. "
      message += "Sublime will now create a configuration file for you. Do you wish to proceed?"
      if sublime.ok_cancel_dialog(message):
        self._save_session()
        self.env.w.run_command("ensime_modify_session")
      return None

    if not self._load_session():
      message = "Launch configuration could not be loaded. "
      message += "Maybe the config is not accessible, but most likely it's simply not a valid JSON. "
      message += "\n\n"
      message += "Sublime will now open the configuration file for you to fix. "
      message += "If you don't know how to fix the config, delete it and Sublime will recreate it from scratch. "
      message += "Do you wish to proceed?"
      if sublime.ok_cancel_dialog(message):
        self.env.w.run_command("ensime_modify_session")
      return None

    config_key = self.current_launch_config or ""
    if config_key: config_name = "launch configuration \"" + config_key + "\""
    else: config_name = "launch configuration"
    config = self.launch_configs.get(config_key, None)

    if not config:
      message = "Your current " + config_name + " is not present. "
      message += "\n\n"
      message += "This means that the \"current_launch_config\" field of the config "
      if config_key: config_status = "set to \"" + config_key + "\""
      else: config_status = "set to an empty string"
      message += "(which is currently " + config_status + ") "
      message += "doesn't correspond to any entries in the \"launch_configs\" field of the config."
      message += "\n\n"
      message += "Sublime will now open the configuration file for you to fix. Do you wish to proceed?"
      if sublime.ok_cancel_dialog(message):
        self.env.w.run_command("ensime_modify_session")
      return None

    if not config.is_valid():
      message = "Your current " + config_name + " doesn't specify the main class to start. "
      message += "\n\n"
      message += "This means that the entry with \"name\":  \"" + config_key + "\" in the \"launch_configs\" field of the config "
      message += "does not have the \"main_class\" attribute set."
      message += "\n\n"
      message += "Sublime will now open the configuration file for you to fix. Do you wish to proceed?"
      if sublime.ok_cancel_dialog(message):
        self.env.w.run_command("ensime_modify_session")
      return None

    return config

  def start(self):
    config = self._figure_out_launch_configuration()
    if config:
      api = ensime_api(self.env.w.active_view())
      api.status_message("Starting the debugger...")
      self._ensime_debug_clear_all_breaks(bind(self._start_after_clear_all_breaks, config))
    else:
      api = ensime_api(self.env.w.active_view())
      api.status_message("Bad debug configuration")

  def _start_after_clear_all_breaks(self, config, status):
    if status:
      self._start_debug_set_breaks(config, self.breakpoints, status)
    else:
      api = ensime_api(self.env.w.active_view())
      api.status_message("Could not set breakpoints")

  def _start_debug_set_breaks(self, config, breaks, status):
    if status:
      if breaks:
        head = breaks[0]
        tail = breaks[1:]
        self._ensime_debug_set_break(head.file_name, head.line, bind(self._start_debug_set_breaks, config, tail))
      else:
        self._start_debug_start(config)
    else:
      api = ensime_api(self.env.w.active_view())
      api.status_message("Could not set breakpoints")

  def _start_debug_start(self, config):
    req = ensime_codec.encode_debug_start(config.command_line)
    timeout = self.env.settings.get("timeout_debugger", 0.5)
    data = self.env.controller.client.sync_req(req, timeout=timeout)
    resp = ensime_codec.decode_debug_start(data)
    if not resp:
      api = ensime_api(self.env.w.active_view())
      if resp == None:
        api.error_message("Debugger has timed out")
        api.status_message("Debugger has timed out")
      else:
        api.error_message("Cannot start debugger because of " + resp.details)
        api.status_message("Cannot start debugger")
    else:
      self.active_launch_config = config.name

  def stop(self):
    req = ensime_codec.encode_debug_stop()
    self.env.controller.client.async_req(req)

  def step_into(self):
    self.last_req = "step_into"
    req = ensime_codec.encode_debug_step(self.focus.thread_id)
    self.env.controller.client.async_req(req)

  def step_over(self):
    self.last_req = "step_over"
    req = ensime_codec.encode_debug_next(self.focus.thread_id)
    self.env.controller.client.async_req(req)

  def resume(self):
    self.last_req = "resume"
    req = ensime_codec.encode_debug_continue(self.focus.thread_id)
    self.env.controller.client.async_req(req)


class EnsimeEnvironment(object):
  def __init__(self, window):
    self.w = window
    self.recalc()

  @property
  def project_root(self):
    return paths.decode_path(self._project_root)

  @property
  def project_config(self):
    config = self._project_config
    if self.settings.get("os_independent_paths_in_dot_ensime"):
      if type(config) == list:
        i = 0
        while i < len(config):
          key = config[i]
          literal_keys = [":root-dir", ":target"]
          list_keys = [":compile-deps", ":compile-jars", ":runtime-deps", ":runtime-jars", ":test-deps", ":sources"]
          if str(key) in literal_keys:
            config[i + 1] = paths.decode_path(config[i + 1])
          elif str(key) in list_keys:
            config[i + 1] = map(lambda path: paths.decode_path(path), config[i + 1])
          else:
            pass
          i += 2
    return config

  def recalc(self):
    # plugin-wide stuff (immutable)
    self.settings = sublime.load_settings("Ensime.sublime-settings")
    server_dir = self.settings.get("ensime_server_path", "Ensime" + os.sep + "server")
    self.server_path = (server_dir
                        if os.path.isabs(server_dir)
                        else os.path.join(sublime.packages_path(), server_dir))
    self.ensime_executable = (self.server_path + os.sep +
                              ("bin\\server.bat" if os.name == 'nt'
                               else "bin/server"))
    self.ensime_args = self.settings.get("ensime_server_args")
    self.plugin_root = os.path.normpath(os.path.join(self.server_path, ".."))
    self.log_root = os.path.normpath(os.path.join(self.plugin_root, "logs"))

    # instance-specific stuff (immutable)
    (root, conf, _) = dotensime.load(self.w)
    self._project_root = root
    self._project_config = conf
    self.valid = self.project_config != None

    # lifecycle (mutable)
    self.lifecycleLock = threading.RLock()
    self.in_transition = False
    self.controller = None

    # shared state (mutable)
    self.notes = []
    self.debugger = EnsimeDebugger(self)
    self.repl_last_insert = 0
    self.repl_last_fixup = 0
    self.repl_last_history = -1
    self.repl_lock = threading.RLock()
    self.sv = self.w.get_output_panel("ensime_server")
    self.sv.set_name("ensime_server")
    self.sv.settings().set("word_wrap", True)
    self.cv = self.w.get_output_panel("ensime_client")
    self.cv.set_name("ensime_client")
    self.cv.settings().set("word_wrap", True)
    self.rv = self.w.get_output_panel("ensime_repl")
    self.rv.set_name("ensime_repl")
    self.rv.settings().set("word_wrap", True)
    self.curr_sel = None
    self.prev_sel = None
    self.compiler_ready = False

    # Tracks the most recent completion prefix that has been shown to yield empty
    # completion results. Use this so we don't repeatedly hit ensime for results
    # that don't exist.
    self.completion_ignore_prefix = None


class EnsimeLog(object):

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
    if flavor in self.env.settings.get("log_to_console", {}):
      if flavor == "client":
        self.view_insert(self.env.cv, str(data))
      if flavor == "server":
        self.view_insert(self.env.sv, str(data))
      print str(data)
    if flavor in self.env.settings.get("log_to_file", {}):
      try:
        if not os.path.exists(self.env.log_root):
          os.mkdir(self.env.log_root)
        file_name = os.path.join(self.env.log_root, flavor + ".log")
        with open(file_name, "a") as f: f.write("[" + str(datetime.datetime.now()) + "]: " + data.strip() + "\n")
      except:
        pass

  def view_insert(self, v, what):
    sublime.set_timeout(bind(self.view_insert_on_ui_thread, v, what), 0)

  def view_insert_on_ui_thread(self, v, what):
    selection_was_at_end = (len(v.sel()) == 1 and v.sel()[0] == sublime.Region(v.size()))
    v.set_read_only(False)
    edit = v.begin_edit()
    v.insert(edit, v.size(), what or "")
    if selection_was_at_end:
      v.show(v.size())
    v.end_edit(edit)
    v.set_read_only(True)
    self.repl_insert(what)

  def view_show(self, v, focus = False):
    self.w.run_command("show_panel", {"panel": "output." + v.name()})
    if focus:
      sublime.set_timeout(bind(self.w.focus_view, v), 100)
    sublime.set_timeout(bind(v.show, v.size()), 200)

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
    sublime.set_timeout(bind(self.repl_insert_on_ui_thread, what, rewind), 0)

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
      self.env.rv.insert(edit, current, what or "")
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
    sublime.set_timeout(bind(self.repl_insert_fixup, what, last_insert), self.repl_fixup_timeout())

  def repl_insert_fixup(self, what, last_insert):
    self.env.repl_lock.acquire()
    try:
      if self.env.repl_last_fixup < last_insert:
        self.env.repl_last_fixup = last_insert
        hack = False
        if self.env.repl_last_insert == last_insert:
          selection_was_at_end = (len(self.env.rv.sel()) == 1 and self.env.rv.sel()[0] == sublime.Region(self.env.rv.size()))
          was_read_only = self.env.rv.is_read_only()
          self.env.rv.set_read_only(False)
          edit = self.env.rv.begin_edit()
          fixup = self.repl_prompt() + what
          last_char = self.env.rv.substr(sublime.Region(self.env.rv.size() - 1, self.env.rv.size()))
          if last_char != "\n":
            hack = True
            fixup = "\n" + fixup
          self.env.rv.insert(edit, self.env.rv.size(), fixup)
          if selection_was_at_end:
            self.env.rv.show(self.env.rv.size())
            self.env.rv.sel().clear()
            self.env.rv.sel().add(sublime.Region(self.env.rv.size()))
          self.env.rv.end_edit(edit)
          self.env.rv.set_read_only(was_read_only)
        self.repl_schedule_fixup(what, self.env.repl_last_insert)
        # don't ask me how this works - I should have not written this spaghetti in the first place
        if hack:
          self.env.repl_last_insert = self.env.repl_last_insert + 1
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

  def repl_previous_history(self):
    try:
      with open(os.path.join(self.env.log_root, "repl.history")) as f:
        lines = f.readlines() or [""]
        index = self.env.repl_last_history
        if index < 0: index += len(lines)
        index -= 1
        if index < 0: index = 0
        self.env.repl_last_history = index
        return lines[index]
    except:
      self.log(sys.exc_info()[1])

  def repl_next_history(self):
    try:
      with open(os.path.join(self.env.log_root, "repl.history")) as f:
        lines = f.readlines() or [""]
        index = self.env.repl_last_history
        if index < 0: index += len(lines)
        index += 1
        if index >= len(lines): index = len(lines) - 1
        self.env.repl_last_history = index
        return lines[index]
    except:
      self.log(sys.exc_info()[1])

class EnsimeBase(object):
  def __init__(self, owner):
    env.environment_constructor = environment_constructor
    self.owner = owner
    if type(owner) == Window:
      self.env = env.for_window(owner)
      self.w = owner
      self.v = owner.active_view()
    elif type(owner) == View:
      self.env = env.for_window(owner.window() or sublime.active_window())
      self.w = owner.window()
      self.v = owner
    else:
      raise Exception("unsupported owner of type: " + str(type(owner)))

  def same_files(self, filename1, filename2):
    if not filename1 or not filename2:
      return False
    filename1_normalized = os.path.normcase(os.path.realpath(filename1))
    filename2_normalized = os.path.normcase(os.path.realpath(filename2))
    return filename1_normalized == filename2_normalized

  def in_project(self, filename):
    if filename and (filename.endswith("scala") or filename.endswith("java")):
      root = os.path.normcase(os.path.realpath(self.env.project_root))
      wannabe = os.path.normcase(os.path.realpath(filename))
      return wannabe.startswith(root)

  def project_relative_path(self, filename):
    if not self.in_project(filename):
      return None
    root = os.path.realpath(self.env.project_root)
    wannabe = os.path.realpath(filename)
    return wannabe[len(root) + 1:]

class EnsimeCommon(EnsimeBase, EnsimeLog, EnsimeApi):
  pass

class EnsimeApiImpl(EnsimeCommon):
  def __nonzero__(self):
    controller = self.env and self.env.controller
    socket = controller and controller.client and controller.client.socket
    connected = socket and socket.connected
    return not not connected

def ensime_api(owner):
  return EnsimeApiImpl(owner)

class EnsimeWindowCommand(EnsimeCommon, WindowCommand):
  def __init__(self, window):
    super(EnsimeWindowCommand, self).__init__(window)
    self.window = window

class EnsimeTextCommand(EnsimeCommon, TextCommand):
  def __init__(self, view):
    super(EnsimeTextCommand, self).__init__(view)
    self.view = view

class EnsimeEventListener(EventListener):
  """Mixin for event listeners that require access to an ensime environment."""
  def with_api(self, view, what, default=None):
    api = ensime_api(view)
    if api and api.in_project(view.file_name()):
      return what(api)
    else:
      return default

class NotRunningOnly:
  def is_enabled(self):
    return self.env and not self.env.in_transition and self.env.valid and not (self.env.controller and self.env.controller.running)

class RunningOnly:
  def is_enabled(self):
    return self.env and not self.env.in_transition and self.env.valid and self.env.controller and self.env.controller.running

class NotDebuggingOnly:
  def is_enabled(self):
    return self.env and not self.env.in_transition and self.env.valid and self.env.controller and self.env.controller.running and not self.debugger.online

class DebuggingOnly:
  def is_enabled(self):
    return self.env and not self.env.in_transition and self.env.valid and self.env.controller and self.env.controller.running and self.debugger.online

class FocusedOnly:
  def is_enabled(self):
    return self.env and not self.env.in_transition and self.env.valid and self.env.controller and self.env.controller.running and self.debugger.focus

class ReadyEnsimeOnly:
  def is_enabled(self):
    return self.env and not self.env.in_transition and self.env.valid and self.env.controller and self.env.controller.ready

class ConnectedEnsimeOnly:
  def is_enabled(self):
    return self.env and not self.env.in_transition and self.env.valid and self.env.controller and self.env.controller.connected

class ProjectFileOnly:
  def is_enabled(self):
    return self.env and not self.env.in_transition and self.env.valid and self.env.controller and self.env.controller.connected and self.v and self.in_project(self.v.file_name())

class ProjectFileOnlyMaybeDisconnected:
  def is_enabled(self):
    return self.env and not self.env.in_transition and self.v and self.in_project(self.v.file_name())

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
    if key == "ensime_repl_enabled":
      try:
        return not not ensime_api(view).env.settings.get("log_to_console")
      except:
        return False
    if key == "ensime_repl_opened":
      return view.name() == "ensime_repl"
    return None

class EnsimeClientListener:
  def on_client_async_data(self, data):
    pass

class EnsimeClientSocket(EnsimeCommon):
  def __init__(self, owner, port, timeout, handlers):
    super(EnsimeClientSocket, self).__init__(owner)
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
        if self.env.controller:
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

# http://stackoverflow.com/questions/10067262/automatically-decorating-every-instance-method-in-a-class
def log_all_methods():
  def logged(wrappee):
    def wrapper(*args, **kwargs):
      try:
        return wrappee(*args, **kwargs)
      except Exception:
        # todo. strictly speaking we should pass env into codec
        # however that's too much of a hassle to implement at the moment
        api = ensime_api(sublime.active_window())
        # todo. how do I get the name of the method?
        # sure it'll be in the stack trace, but I want it to stand out in the log entry header
        s_callinfo = wrappee.func_name + "(" + str(args)
        if len(kwargs) != 0:
          if len(args) != 0:
            s_callinfo = s_callinfo + ", "
          s_callinfo = s_callinfo + str(kwargs)
        s_callinfo = s_callinfo + ")"
        s_excinfo =  traceback.format_exc()
        api.log_client("codec error when processing: " + s_callinfo + "\n" + s_excinfo)
        raise
    return wrapper

  def do_decorate(attr, value):
    return '__' not in attr and isinstance(value, FunctionType)

  class DecorateAll(type):
    def __new__(cls, name, bases, dct):
      for attr, value in dct.iteritems():
        if do_decorate(attr, value):
          dct[attr] = logged(value)
      return super(DecorateAll, cls).__new__(cls, name, bases, dct)
    def __setattr__(self, attr, value):
      if do_decorate(attr, value):
        value = logged(value)
      super(DecorateAll, self).__setattr__(attr, value)

  return DecorateAll

class EnsimeCodec:
  __metaclass__ = log_all_methods()

  def encode_initialize_project(self, conf):
    return [sym("swank:init-project"), conf]

  def encode_type_check_file(self, file_path):
    return [sym("swank:typecheck-file"), file_path]

  def decode_type_check_file(self, data):
    return True

  def decode_notes(self, data):
    if not data: return []
    m = sexp.sexp_to_key_map(data)
    return [self.decode_note(n) for n in m[":notes"]]

  def decode_note(self, data):
    if not data: return None
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
    if not data: return None
    return self.decode_type(data)

  def encode_completions(self, file_path, position, max_results):
    return [sym("swank:completions"),
            str(file_path), int(position), max_results, False, False]

  def decode_completions(self, data):
    if not data: return []
    m = sexp.sexp_to_key_map(data)
    return [self.decode_completion(p) for p in m.get(":completions", [])]

  def decode_completion(self, data):
    if not data: return None
    m = sexp.sexp_to_key_map(data)
    class EnsimeCompletion(object): pass
    completion = EnsimeCompletion()
    completion.name = m[":name"]
    completion.signature = m[":type-sig"]
    completion.is_callable = bool(m[":is-callable"]) if ":is-callable" in m else False
    completion.type_id = m[":type-id"]
    completion.to_insert = m[":to-insert"] if ":to-insert" in m else None
    return completion

  def encode_symbol_at_point(self, file_path, position):
    return [sym("swank:symbol-at-point"), str(file_path), int(position)]

  def encode_patch_source(self, file_path, edits):
    return [sym("swank:patch-source"), str(file_path), edits]

  def decode_symbol_at_point(self, data):
    if not data: return None
    return self.decode_symbol(data)

  def decode_position(self, data):
    if not data: return None
    m = sexp.sexp_to_key_map(data)
    class EnsimePosition(object): pass
    position = EnsimePosition()
    position.file_name = m[":file"] if ":file" in m else None
    position.offset = m[":offset"] if ":offset" in m else None
    position.start = m[":start"] if ":start" in m else None
    position.end = m[":end"] if ":end" in m else None
    return position

  def decode_types(self, data):
    if not data: return []
    return [self.decode_type(t) for t in data]

  def decode_type(self, data):
    if not data: return None
    m = sexp.sexp_to_key_map(data)
    class TypeInfo(object): pass
    info = TypeInfo()
    info.name = m[":name"]
    info.type_id = m[":type-id"]
    if ":arrow-type" in m:
      info.arrow_type = True
      info.result_type = self.decode_type(m[":result-type"])
      info.param_sections = self.decode_members(m[":param-sections"]) if ":param-sections" in m else []
    else:
      info.arrow_type = False
      info.full_name = m[":full-name"] if ":full-name" in m else None
      info.decl_as = m[":decl-as"] if ":decl-as" in m else None
      info.decl_pos = self.decode_position(m[":pos"]) if ":pos" in m else None
      info.type_args = self.decode_types(m[":type-args"]) if ":type-args" in m else []
      info.outer_type_id = m[":outer-type-id"] if ":outer-type-id" in m else None
      info.members = self.decode_members(m[":members"]) if ":members" in m else []
    return info

  def decode_symbol(self, data):
    if not data: return None
    m = sexp.sexp_to_key_map(data)
    class SymbolInfo(object): pass
    info = SymbolInfo()
    info.name = m[":name"]
    info.type = self.decode_type(m[":type"])
    info.decl_pos = self.decode_position(m[":decl-pos"]) if ":decl-pos" in m else None
    info.is_callable = bool(m[":is-callable"]) if ":is-callable" in m else False
    info.owner_type_id = m[":owner-type-id"] if ":owner-type-id" in m else None
    return info

  def decode_members(self, data):
    if not data: return []
    return [self.decode_member(m) for m in data]

  def decode_member(self, data):
    if not data: return None
    m = sexp.sexp_to_key_map(data)
    class MemberInfo(object): pass
    info = MemberInfo()
    # todo. implement this in accordance with SwankProtocol.scala
    return info

  def decode_param_sections(self, data):
    if not data: return []
    return [self.decode_param_section(ps) for ps in data]

  def decode_param_section(self, data):
    if not data: return None
    m = sexp.sexp_to_key_map(data)
    class ParamSectionInfo(object): pass
    info = ParamSectionInfo()
    info.is_implicit = bool(m[":is-implicit"]) if ":is-implicit" in m else False
    info.params = self.decode_params(m[":params"]) if ":params" in m else []
    return info

  def decode_params(self, data):
    if not data: return []
    return [self.decode_param(p) for p in data]

  def decode_param(self, data):
    # todo. implement this in accordance with SwankProtocol.scala
    return None

  def decode_debug_event(self, data):
    if not data: return None
    m = sexp.sexp_to_key_map(data)
    class EnsimeDebugEvent(object): pass
    event = EnsimeDebugEvent()
    event.type = str(m[":type"])
    if event.type == "output":
      event.body = m[":body"]
    elif event.type == "step":
      event.thread_id = m[":thread-id"]
      event.thread_name = m[":thread-name"]
      event.file_name = m[":file"]
      event.line = m[":line"]
    elif event.type == "breakpoint":
      event.thread_id = m[":thread-id"]
      event.thread_name = m[":thread-name"]
      event.file_name = m[":file"]
      event.line = m[":line"]
    elif event.type == "death":
      pass
    elif event.type == "start":
      pass
    elif event.type == "disconnect":
      pass
    elif event.type == "exception":
      event.exception_id = m[":exception"]
      event.thread_id = m[":thread-id"]
      event.thread_name = m[":thread-name"]
      event.file_name = m[":file"]
      event.line = m[":line"]
    elif event.type == "threadStart":
      event.thread_id = m[":thread-id"]
    elif event.type == "threadDeath":
      event.thread_id = m[":thread-id"]
    else:
      raise Exception("unexpected debug event of type " + str(event.type) + ": " + str(m))
    return event

  def decode_debug_backtrace(self, data):
    if not data: return None
    m = sexp.sexp_to_key_map(data)
    class EnsimeDebugBacktrace(object): pass
    backtrace = EnsimeDebugBacktrace()
    backtrace.frames = self.decode_debug_stack_frames(m[":frames"]) if ":frames" in m else []
    backtrace.thread_id = m[":thread-id"]
    backtrace.thread_name = m[":thread-name"]
    return backtrace

  def decode_debug_stack_frames(self, data):
    if not data: return []
    return [self.decode_debug_frame(f) for f in data]

  def decode_debug_stack_frame(self, data):
    if not data: return None
    m = sexp.sexp_to_key_map(data)
    class EnsimeDebugStackFrame(object): pass
    stackframe = EnsimeDebugStackFrame()
    stackframe.index = m[":index"]
    stackframe.locals = self.decode_debug_stack_locals(m[":locals"]) if ":locals" in m else []
    stackframe.num_args = m[":num-args"]
    stackframe.class_name = m[":class-name"]
    stackframe.method_name = m[":method-name"]
    stackframe.pc_location = self.decode_debug_source_position(m[":pc-location"])
    stackframe.this_object_id = m[":this-object-id"]
    return stackframe

  def decode_debug_source_position(self, data):
    if not data: return None
    m = sexp.sexp_to_key_map(data)
    class EnsimeDebugSourcePosition(object): pass
    position = EnsimeDebugSourcePosition()
    position.file_name = m[":file"]
    position.line = m[":line"]
    return position

  def decode_debug_stack_locals(self, data):
    if not data: return []
    return [self.decode_debug_stack_local(loc) for loc in data]

  def decode_debug_stack_local(self, data):
    if not data: return None
    m = sexp.sexp_to_key_map(data)
    class EnsimeDebugStackLocal(object): pass
    loc = EnsimeDebugStackLocal()
    loc.index = m[":index"]
    loc.name = m[":name"]
    loc.summary = m[":summary"]
    loc.type_name = m[":type-name"]
    return loc

  def decode_debug_value(self, data):
    if not data: return None
    m = sexp.sexp_to_key_map(data)
    class EnsimeDebugValue(object): pass
    value = EnsimeDebugValue()
    value.type = m[":val-type"]
    value.type_name = m[":type-name"]
    value.length = m[":length"] if ":length" in m else None
    value.element_type_name = m[":element-type-name"] if ":element-type-name" in m else None
    value.summary = m[":summary"] if ":summary" in m else None
    value.object_id = m[":object_id"] if ":object_id" in m else None
    value.fields = self.decode_debug_object_fields(m[":fields"]) if ":fields" in m else []
    if str(value.type) == "null" or str(value.type) == "prim" or str(value.type) == "obj" or str(value.type) == "str" or str(value.type) == "arr":
      pass
    else:
      raise Exception("unexpected debug value of type " + str(value.type) + ": " + str(m))
    return value

  def decode_debug_object_fields(self, data):
    if not data: return []
    return [self.decode_debug_object_field(f) for f in data]

  def decode_debug_object_field(self, data):
    if not data: return None
    m = sexp.sexp_to_key_map(data)
    class EnsimeDebugObjectField(object): pass
    field = EnsimeDebugObjectField()
    field.index = m[":index"]
    field.name = m[":name"]
    field.summary = m[":summary"]
    field.type_name = m[":type-name"]
    return field

  def encode_debug_clear_all_breaks(self):
    return [sym("swank:debug-clear-all-breaks")]

  def decode_debug_clear_all_breaks(self, data):
    return data

  def encode_debug_set_break(self, file_name, line):
    return [sym("swank:debug-set-break"), str(file_name), int(line)]

  def decode_debug_set_break(self, data):
    return data

  def encode_debug_clear_break(self, file_name, line):
    return [sym("swank:debug-clear-break"), str(file_name), int(line)]

  def decode_debug_clear_break(self, data):
    return data

  def encode_debug_start(self, command_line):
    return [sym("swank:debug-start"), str(command_line)]

  def decode_debug_start(self, data):
    if not data: return None
    m = sexp.sexp_to_key_map(data)
    status = m[":status"]
    if status == "success":
      return True
    elif status == "error":
      class EnsimeDebugStartError(object):
        def __nonzero__(self):
          return False
      error = EnsimeDebugStartError()
      error.code = m[":error-code"]
      error.details = m[":details"]
      return error
    else:
      raise Exception("unexpected status: " + str(status))

  def encode_debug_stop(self):
    return [sym("swank:debug-stop")]

  def encode_debug_continue(self, thread_id):
    return [sym("swank:debug-continue"), str(thread_id)]

  def encode_debug_step(self, thread_id):
    return [sym("swank:debug-step"), str(thread_id)]

  def encode_debug_next(self, thread_id):
    return [sym("swank:debug-next"), str(thread_id)]

ensime_codec = EnsimeCodec()

class EnsimeClient(EnsimeClientListener, EnsimeCommon):
  def __init__(self, owner, port_file, timeout):
    super(EnsimeClient, self).__init__(owner)
    with open(port_file) as f: self.port = int(f.read())
    self.timeout = timeout
    self.init_counters()
    methods = filter(lambda m: m[0].startswith("message_"), inspect.getmembers(self, predicate=inspect.ismethod))
    self.log_client("reflectively found " + str(len(methods)) + " message handlers: " + str(methods))
    self.handlers = dict((":" + m[0][len("message_"):].replace("_", "-"), (m[1], None, None)) for m in methods)

  def startup(self):
    self.log_client("Starting Ensime client")
    self.log_client("Launching Ensime client socket at port " + str(self.port))
    self.socket = EnsimeClientSocket(self.owner, self.port, self.timeout, [self, self.env.controller])
    self.socket.connect()

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
      if msg_id <= 2: # handshake and initialize project
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
    filename = self.env.plugin_root + os.sep + "Encouragements.txt"
    lines = [line.strip() for line in open(filename)]
    msg = lines[random.randint(0, len(lines) - 1)]
    self.status_message(msg + " This could be the start of a beautiful program, " + getpass.getuser().capitalize()  + ".")
    if self.v:
      EnsimeHighlights(self.v).refresh()
      if self.in_project(self.v.file_name()): self.v.run_command("save")
      self.env.compiler_ready = True

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

  @call_back_into_ui_thread
  def message_java_notes(self, msg_id, payload):
    notes = ensime_codec.decode_notes(payload)
    self.add_notes(notes)

  @call_back_into_ui_thread
  def message_scala_notes(self, msg_id, payload):
    notes = ensime_codec.decode_notes(payload)
    self.add_notes(notes)

  @call_back_into_ui_thread
  def message_clear_all_java_notes(self, msg_id, payload):
    self.clear_notes(flavor = "java")

  @call_back_into_ui_thread
  def message_clear_all_scala_notes(self, msg_id, payload):
    self.clear_notes(flavor = "scala")

  @call_back_into_ui_thread
  def message_debug_event(self, msg_id, payload):
    debug_event = ensime_codec.decode_debug_event(payload)
    self.debugger._handle(debug_event)

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
    detail += "\n\nCheck the server log at " + os.path.join(self.env.log_root, "server.log") + "."
    return detail

  def feedback(self, msg):
    msg = msg.replace("\r\n", "\n").replace("\r", "\n") + "\n"
    self.log_client(msg)

class EnsimeServerListener:
  def on_server_data(self, data):
    pass

class EnsimeServerProcess(EnsimeCommon):
  def __init__(self, owner, command, listeners):
    super(EnsimeServerProcess, self).__init__(owner)
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

class EnsimeServer(EnsimeServerListener, EnsimeCommon):
  def __init__(self, owner, port_file):
    super(EnsimeServer, self).__init__(owner)
    self.port_file = port_file

  def startup(self):
    ensime_command = self.get_ensime_command()
    if self.get_ensime_command() and self.verify_ensime_version():
      self.log_server("Starting Ensime server")
      self.log_server("Launching Ensime server process with command = " + str(ensime_command) + " and args = " + str(self.env.ensime_args))
      self.proc = EnsimeServerProcess(self.owner, ensime_command, [self, self.env.controller])
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
      detailed_info = '\n'.join(traceback.format_exception(exc_type, exc_value, exc_tb))
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

class EnsimeController(EnsimeCommon, EnsimeClientListener, EnsimeServerListener):
  def __init__(self, owner):
    super(EnsimeController, self).__init__(owner)
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
          self.ready = True # external server is deemed to be always ready
          sublime.set_timeout(bind(self.request_handshake), 0)
        else:
          _, port_file = tempfile.mkstemp("ensime_port")
          self.port_file = port_file
          self.server = EnsimeServer(self.owner, port_file)
          if not self.server.startup():
            self.env.controller = None
            self.running = False
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
      sublime.set_timeout(bind(self.request_handshake), 0)

  def request_handshake(self):
    timeout = self.env.settings.get("timeout_sync_roundtrip", 3)
    self.client = EnsimeClient(self.owner, self.port_file, timeout)
    self.client.startup()
    self.client.async_req([sym("swank:connection-info")],
                          self.__response_handshake,
                          call_back_into_ui_thread = True)

  def __response_handshake(self, server_info):
    self.status_message("Starting Ensime server... ")
    dotensime.select_subproject(self.env.project_config,
                                self.owner,
                                self.__initialize)

  def __initialize(self, subproject_name):
    if subproject_name:
      self.status_message("Starting subproject: " + str(subproject_name))
    conf = self.env.project_config + [key(":active-subproject"), subproject_name]
    req = ensime_codec.encode_initialize_project(conf)
    self.client.async_req(
      req,
      lambda _: self.status_message("Continuing to init project..."),
      call_back_into_ui_thread = True)


  def shutdown(self):
    self.env.lifecycleLock.acquire()
    try:
      if self.running:
        self.env.in_transition = True
        self.env.compiler_ready = False
        try:
          self.env.debugger.shutdown()
        except:
          self.log("Error shutting down ensime debugger:")
          self.log(traceback.format_exc())
        try:
          sublime.set_timeout(self.clear_notes, 0)
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
  def is_enabled(self):
    return not self.env.in_transition and not (self.env.controller and self.env.controller.running)

  def run(self):
    # refreshes the config (fixes #29)
    self.env.recalc()

    if not self.env.project_config:
      (_, _, error_handler) = dotensime.load(self.w)
      error_handler()
      return

    EnsimeController(self.w).startup()

class EnsimeShutdownCommand(RunningOnly, EnsimeWindowCommand):
  def run(self):
    self.env.controller.shutdown()

class EnsimeRestartCommand(RunningOnly, EnsimeWindowCommand):
  def run(self):
    self.w.run_command("ensime_shutdown")
    sublime.set_timeout(bind(self.w.run_command, "ensime_startup"), 100)

class EnsimeShowClientMessagesCommand(EnsimeWindowCommand):
  def is_enabled(self):
    return self.env.valid

  def run(self):
    # self.view_show(self.env.cv, False)
    client_log = os.path.join(self.env.log_root, "client.log")
    line = 1
    try:
     with open(client_log) as f: line = len(f.readlines())
    except:
      pass
    self.w.open_file("%s:%d:%d" % (client_log, line, 1), sublime.ENCODED_POSITION)

class EnsimeShowServerMessagesCommand(EnsimeWindowCommand):
  def is_enabled(self):
    return self.env.valid

  def run(self):
    # self.view_show(self.env.sv, False)
    server_log = os.path.join(self.env.log_root, "server.log")
    line = 1
    try:
     with open(server_log) as f: line = len(f.readlines())
    except:
      pass
    self.w.open_file("%s:%d:%d" % (server_log, line, 1), sublime.ENCODED_POSITION)

class EnsimeCreateProjectCommand(EnsimeWindowCommand):
  def is_enabled(self):
    return not dotensime.exists(self.w)

  def run(self):
    dotensime.create(self.w)

class EnsimeModifyProjectCommand(EnsimeWindowCommand):
  def is_enabled(self):
    return dotensime.exists(self.w)

  def run(self):
    dotensime.edit(self.w)

class EnsimeModifySessionCommand(EnsimeWindowCommand):
  def is_enabled(self):
    return dotensime.exists(self.w)

  def run(self):
    path = self.debugger.session_file
    self.w.open_file(path)

class EnsimeShowClientServerReplCommand(ReadyEnsimeOnly, EnsimeWindowCommand):
  def __init__(self, window):
    super(EnsimeShowClientServerReplCommand, self).__init__(window)
    self.visible = False
    self.window = window

  def run(self, toggle = True):
    self.visible = not self.visible if toggle else True
    if self.visible:
      self.repl_show()
    else:
      self.window.run_command("hide_panel", { "cancel": True })

class EnsimeReplEnterCommand(EnsimeTextCommand):
  def run(self, edit):
    user_input = self.repl_get_input().strip()
    self.env.repl_lock.acquire()
    try:
      if user_input == "":
        # prompt =  + self.repl_prompt()
        self.repl_insert("\n", True)
        self.env.repl_last_insert = self.env.rv.size()
        self.env.repl_last_fixup = self.env.repl_last_insert
        self.repl_insert(self.repl_prompt(), False)
      elif user_input == "cls":
        self.env.rv.replace(edit, Region(0, self.env.rv.size()), "")
        self.env.repl_last_insert = 0
        self.env.repl_last_fixup = 0
        self.repl_insert(self.repl_prompt(), False)
      else:
        if self.w.active_view():
          user_input = user_input.replace("$file", "\"" + self.w.active_view().file_name() + "\"")
          user_input = user_input.replace("$pos", str(self.w.active_view().sel()[0].begin()))
        try:
          _ = sexp.read_list(user_input)
          parsed_user_input = sexp.read(user_input)
          with open(os.path.join(self.env.log_root, "repl.history"), 'a') as f:
            f.write(user_input + "\n")
          with open(os.path.join(self.env.log_root, "repl.history"), 'r') as f:
            lines = f.readlines() or [""]
            self.env.repl_last_history = len(lines) - 1
        except:
          self.status_message(str(sys.exc_info()[1]))
          return
        self.env.repl_last_insert = self.env.rv.size()
        self.env.repl_last_fixup = self.env.repl_last_insert
        self.repl_insert("\n", True)
        # self.repl_insert(self.repl_prompt(), False)
        self.repl_schedule_fixup("", self.env.repl_last_fixup + 1)
        self.env.controller.client.async_req(parsed_user_input)
    finally:
      self.env.repl_lock.release()

class EnsimeReplEscapeCommand(EnsimeTextCommand):
  def run(self, edit):
    self.env.repl_lock.acquire()
    try:
      user_input = self.repl_get_input()
      if len(user_input) == 0:
        self.w.run_command("hide_panel", {"cancel": True})
      else:
        self.w.run_command("move_to", {"to": "eof", "extend": False})
        self.w.run_command("ensime_repl_shift_home")
        self.w.run_command("right_delete")
    finally:
      self.env.repl_lock.release()

class EnsimeReplBackspaceCommand(EnsimeTextCommand):
  def run(self, edit):
    self.env.repl_lock.acquire()
    try:
      delta = self.env.rv.sel()[0].begin() - self.env.repl_last_insert - len(self.repl_prompt())
      if delta < 0:
        self.w.run_command("left_delete")
      elif delta == 0:
        return
      else:
        self.w.run_command("left_delete")
    finally:
      self.env.repl_lock.release()

class EnsimeReplLeftCommand( EnsimeTextCommand):
  def run(self, edit):
    self.env.repl_lock.acquire()
    try:
      delta = self.env.rv.sel()[0].begin() - self.env.repl_last_insert - len(self.repl_prompt())
      if delta < 0:
        self.w.run_command("move", {"by": "characters", "forward": False, "extend": False})
      elif delta == 0:
        return
      else:
        self.w.run_command("move", {"by": "characters", "forward": False, "extend": False})
    finally:
      self.env.repl_lock.release()

class EnsimeReplShiftLeftCommand(EnsimeTextCommand):
  def run(self, edit):
    self.env.repl_lock.acquire()
    try:
      delta = self.env.rv.sel()[0].begin() - self.env.repl_last_insert - len(self.repl_prompt())
      if delta < 0:
        self.w.run_command("move", {"by": "characters", "forward": False, "extend": True})
      elif delta == 0:
        return
      else:
        self.w.run_command("move", {"by": "characters", "forward": False, "extend": True})
    finally:
      self.env.repl_lock.release()

class EnsimeReplHomeCommand(EnsimeTextCommand):
  def run(self, edit):
    self.env.repl_lock.acquire()
    try:
      delta = self.env.rv.sel()[0].begin() - self.env.repl_last_insert - len(self.repl_prompt())
      if delta < 0:
        self.w.run_command("move_to", {"to": "bol", "extend": False})
      else:
        for i in range(1, delta + 1):
          self.w.run_command("move", {"by": "characters", "forward": False, "extend": False})
    finally:
      self.env.repl_lock.release()

class EnsimeReplShiftHomeCommand(EnsimeTextCommand):
  def run(self, edit):
    self.env.repl_lock.acquire()
    try:
      delta = self.env.rv.sel()[0].begin() - self.env.repl_last_insert - len(self.repl_prompt())
      if delta < 0:
        self.w.run_command("move_to", {"to": "bol", "extend": True})
      else:
        for i in range(1, delta + 1):
          self.w.run_command("move", {"by": "characters", "forward": False, "extend": True})
    finally:
      self.env.repl_lock.release()

class EnsimeReplPreviousCommand(EnsimeTextCommand):
  def run(self, edit):
    self.env.rv.show(self.env.rv.line(self.env.rv.size()).begin())
    self.w.run_command("ensime_repl_escape")
    self.repl_insert(self.repl_previous_history(), False)
    self.repl_show()

class EnsimeReplNextCommand(EnsimeTextCommand):
  def run(self, edit):
    self.env.rv.show(self.env.rv.line(self.env.rv.size()).begin())
    self.w.run_command("ensime_repl_escape")
    self.repl_insert(self.repl_next_history(), False)
    self.repl_show()

ENSIME_ERROR_OUTLINE_REGION = "ensime-error"
ENSIME_ERROR_UNDERLINE_REGION = "ensime-error-underline"
ENSIME_BREAKPOINT_REGION = "ensime-breakpoint"
ENSIME_DEBUGFOCUS_REGION = "ensime-debugfocus"

class EnsimeHighlights(EnsimeCommon):

  def refresh(self):
    self.clear_all()
    if self.env:
      self.add_notes(self.env.notes)
    self.update_status()
    self.update_breakpoints()
    self.update_debug_focus()

  def clear_all(self):
    self.v.erase_regions(ENSIME_ERROR_OUTLINE_REGION)
    self.v.erase_regions(ENSIME_ERROR_UNDERLINE_REGION)
    self.v.erase_regions(ENSIME_DEBUGFOCUS_REGION)
    self.v.run_command("ensime_show_notes", {"refresh_only": True})
    self.update_status()

  def add_notes(self, notes):
    relevant_notes = filter(
      lambda note: self.same_files(note.file_name, self.v.file_name()), notes)

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

    # Now let's refresh ourselves
    self.v.run_command("ensime_show_notes", {"refresh_only": True})
    self.update_status()
    # breakpoints and debug focus should always have priority over red squiggles
    self.update_breakpoints()
    self.update_debug_focus()

  def update_status(self, custom_status = None):
    if custom_status:
      self._update_statusbar(custom_status)
    elif self.env and self.env.settings.get("ensime_statusbar_showerrors"):
      if self.v.sel():
        relevant_notes = filter(
          lambda note: self.same_files(
            note.file_name, self.v.file_name()),
          self.env.notes)
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
      heart_beats = self.env and self.env.valid and self.env.controller and self.env.controller.running
      if heart_beats:
        def calculate_heartbeat_message():
          def format_debugging_message(msg):
            active_config = (self.debugger.active_launch_config or "") if self.debugger.online else ""
            try: return msg % active_config
            except: return msg
          if self.v and self.in_project(self.v.file_name()):
            if self.debugger.online:
              return format_debugging_message(settings.get("ensime_statusbar_heartbeat_inproject_debugging"))
            else:
              return settings.get("ensime_statusbar_heartbeat_inproject_normal")
          else:
            if self.debugger.online:
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
          lambda breakpoint: self.same_files(
            breakpoint.file_name, self.v.file_name()),
          self.debugger.breakpoints)
        regions = [self.v.full_line(self.v.text_point(breakpoint.line - 1, 0))
                   for breakpoint in relevant_breakpoints]
        self.v.add_regions(
          ENSIME_BREAKPOINT_REGION,
          regions,
          self.env.settings.get("breakpoint_scope"),
          self.env.settings.get("breakpoint_icon"),
          sublime.HIDDEN)

  def update_debug_focus(self):
    self.v.erase_regions(ENSIME_DEBUGFOCUS_REGION)
    if self.v.is_loading():
      sublime.set_timeout(self.update_debug_focus, 100)
    else:
      if self.env:
        focus = self.debugger.focus
        if focus and self.same_files(focus.file_name, self.v.file_name()):
          focused_region = self.v.full_line(self.v.text_point(focus.line - 1, 0))
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

class EnsimeHighlightCommand(ProjectFileOnly, EnsimeWindowCommand):
  def run(self, enable = True):
    self.env.settings.set("error_highlight", not not enable)
    sublime.save_settings("Ensime.sublime-settings")
    EnsimeHighlights(self.v).clear_all()
    if enable:
      self.type_check_file(self.v.file_name())

class EnsimeShowNotesCommand(ProjectFileOnly, EnsimeTextCommand):
  def run(self, edit, refresh_only = False):
    file_name = self.v and self.v.file_name()
    w = self.v.window() or sublime.active_window()
    if file_name:
      ENSIME_NOTES = "Ensime notes"
      wannabes = filter(lambda v: v.name() == ENSIME_NOTES, w.views())
      if not wannabes and refresh_only: return
      v = wannabes[0] if wannabes else w.new_file()
      v.set_scratch(True)
      v.set_name(ENSIME_NOTES)
      edit = v.begin_edit()
      v.replace(edit, Region(0, v.size()), "")

      v.settings().set("result_file_regex", "([:.a-z_A-Z0-9\\\\/-]+[.](?:scala|java)):([0-9]+)")
      v.settings().set("result_line_regex", "")
      v.settings().set("result_base_dir", self.env.project_root)
      if not refresh_only:
        other_view = w.new_file()
        w.focus_view(other_view)
        w.run_command("close_file")
        w.focus_view(v)

      relevant_notes = self.env.notes
      relevant_notes = filter(lambda note: self.same_files(note.file_name, self.v.file_name()), self.env.notes)
      errors = [self.v.full_line(note.start) for note in relevant_notes]
      relevant_notes = filter(lambda note: self.same_files(note.file_name, self.v.file_name()), self.env.notes)
      for note in relevant_notes:
        loc = self.project_relative_path(note.file_name) + ":" + str(note.line)
        severity = note.severity
        message = note.message
        diagnostics = ": ".join(str(x) for x in [loc, severity, message])
        v.insert(edit, v.size(), diagnostics + "\n")
        v.insert(edit, v.size(), self.v.substr(self.v.full_line(note.start)))
        v.insert(edit, v.size(), " " * (note.col - 1) + "^" + "\n")
      v.end_edit(edit)
      v.sel().clear()
      v.sel().add(Region(0, 0))

class EnsimeDaemon(EnsimeEventListener):

  def on_load(self, view):
    self.with_api(view, lambda api: api.type_check_file(view.file_name()))

  def on_post_save(self, view):
    self.with_api(view, lambda api: api.type_check_file(view.file_name()))
    api = ensime_api(view)
    if api.same_files(view.file_name(), api.debugger.session_file):
      api.debugger._load_session()
      for v in api.w.views():
        EnsimeHighlights(v).update_breakpoints()

  def on_activated(self, view):
    EnsimeHighlights(view).refresh()
    self.with_api(view, lambda api: view.run_command("ensime_show_notes", {"refresh_only": True}))

  def on_selection_modified(self, view):
    EnsimeHighlights(view).update_status()

class EnsimeMouseCommand(EnsimeTextCommand):
  def run(self, target):
    raise Exception("abstract method: EnsimeMouseCommand.run")

  # note the underscore in "run_"
  def run_(self, args):
    self.old_sel = [(r.a, r.b) for r in self.view.sel()]
    # unfortunately, running a drag_select is our only way of getting the coordinates of the click
    # I didn't find a way to convert args["event"]["x"] and args["event"]["y"] to text coordinates
    # there are relevant APIs, but they refuse to yield correct results
    system_command = args["command"] if "command" in args else None
    if system_command:
      system_args = dict({"event": args["event"]}.items() + args["args"].items())
      self.view.run_command(system_command, system_args)
    self.new_sel = [(r.a, r.b) for r in self.v.sel()]
    self.diff = list((set(self.old_sel) - set(self.new_sel)) | (set(self.new_sel) - set(self.old_sel)))

    is_applicable = not self.env.in_transition and self.env.valid and self.env.controller and self.env.controller.connected and self.in_project(self.v.file_name())
    if is_applicable:
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
        sel = self.view.sel()
        sel.clear()
        sel.add(Region(self.diff[0][0], self.diff[0][1]))
        self.run(self.diff[0][0])
      else:
        # this shouldn't happen
        self.log("len(diff) > 1: command = " + str(type(self)) + ", old_sel = " + str(self.old_sel) + ", new_sel = " + str(self.new_sel))

class EnsimeCtrlClick(EnsimeMouseCommand):
  def run(self, target):
    self.v.run_command("ensime_go_to_definition", {"target": target})

class EnsimeAltClick(EnsimeMouseCommand):
  def run(self, target):
    self.v.run_command("ensime_inspect_type_at_point", {"target": target})

class EnsimeCtrlTilde(EnsimeWindowCommand):
  def run(self):
    self.w.run_command("ensime_show_client_server_repl", {"toggle": True})


class EnsimeCompletionsListener(EnsimeEventListener):

  def __init__(self):
    super(EnsimeCompletionsListener, self).__init__()

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

  def _query_completions(self, view, prefix, locations, api):
    """Query the ensime API for completions. Note: we must ask for _all_
    completions as sublime will not re-query unless this query returns an
    empty list."""
    # Short circuit for prefix that is known to return empty list
    # TODO(aemoncannon): Clear ignore prefix if the user
    # moves point to new context.
    if (api.env.completion_ignore_prefix and
        prefix.startswith(api.env.completion_ignore_prefix)):
      return self._completion_response([])
    else:
      api.env.completion_ignore_prefix = None
    if not view.match_selector(locations[0], "source.scala"): return []
    completions = api.get_completions(
      view.file_name(), locations[0], 0) if api else []
    if not completions:
      api.env.completion_ignore_prefix = prefix
    return self._completion_response(completions)

  def on_query_completions(self, view, prefix, locations):
    return self.with_api(view,
                         bind(self._query_completions, view, prefix, locations),
                         default=[])


class EnsimeInspectTypeAtPoint(ProjectFileOnly, EnsimeTextCommand):
  def run(self, edit, target= None):
    pos = int(target or self.v.sel()[0].begin())
    self.inspect_type_at_point(self.v.file_name(), pos, self.handle_reply)

  def handle_reply(self, tpe):
    if tpe and tpe.name != "<notype>":
      summary = tpe.full_name
      if tpe.type_args:
        summary += ("[" + ", ".join(map(lambda t: t.name, tpe.type_args)) + "]")
      self.status_message(summary)
    else:
      self.status_message("Cannot find out type")

class EnsimeGoToDefinition(ProjectFileOnly, EnsimeTextCommand):
  def run(self, edit, target= None):
    pos = int(target or self.v.sel()[0].begin())
    self.symbol_at_point(self.v.file_name(), pos, self.handle_reply)

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
        # doesn't support mixed line endings
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
          return w.open_file("%s:%d:%d" % (file_name, zb_row + 1, zb_col + 1), sublime.ENCODED_POSITION)

        w = self.w or sublime.active_window()
        g, i = (None, None)
        if self.v and self.v.file_name() == file_name:
          # open_file doesn't work, so we have to work around
          # open_file()

          # <workaround 1> close and then reopen
          # works fine but is hard on the eyes
          # g, i = w.get_view_index(self.v)
          # self.v.run_command("save")
          # w.run_command("close_file")
          # v = open_file()
          # w.set_view_index(v, g, i)

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

class EnsimeToggleBreakpoint(ProjectFileOnlyMaybeDisconnected, EnsimeTextCommand):
  def run(self, edit):
    if self.v.sel():
      row, col = self.v.rowcol(self.v.sel()[0].begin())
      self.debugger.toggle_breakpoint(self.v.file_name(), row + 1)

class EnsimeClearBreakpoints(ProjectFileOnlyMaybeDisconnected, EnsimeTextCommand):
  def run(self, edit):
    self.debugger.clear_breakpoints()

class EnsimeStartDebugger(NotDebuggingOnly, EnsimeWindowCommand):
  def run(self):
    self.debugger.start()

class EnsimeStopDebugger(DebuggingOnly, EnsimeWindowCommand):
  def run(self):
    self.debugger.stop()

class EnsimeStepInto(FocusedOnly, EnsimeWindowCommand):
  def run(self):
    self.debugger.step_into()

class EnsimeStepOver(FocusedOnly, EnsimeWindowCommand):
  def run(self):
    self.debugger.step_over()

class EnsimeResumeDebugger(FocusedOnly, EnsimeWindowCommand):
  def run(self):
    self.debugger.resume()

class EnsimeSmartRunDebugger(EnsimeWindowCommand):
  def __init__(self, window):
    super(EnsimeSmartRunDebugger, self).__init__(window)
    self.startup_attempts = 0

  def is_enabled(self):
    return not self.debugger.online or self.debugger.focus

  def run(self):
    if not self.debugger.online:
      if self.env.compiler_ready:
        self.startup_attempts = 0
        self.w.run_command("ensime_start_debugger")
      else:
        self.startup_attempts += 1
        if self.startup_attempts < 5:
          self.w.run_command("ensime_startup")
          sublime.set_timeout(self.run, 1000)
        else:
          self.startup_attempts = 0
    if self.debugger.focus:
      self.w.run_command("ensime_resume_debugger")

class EnsimeShowDebugOutput(EnsimeWindowCommand):
  def is_enabled(self):
    return self.debugger.output.is_meaningful()

  def run(self):
    self.debugger.output.show()

class EnsimeShowDebugDashboard(EnsimeWindowCommand):
  def is_enabled(self):
    return self.debugger.dashboard.is_meaningful()

  def run(self):
    self.debugger.dashboard.show()
