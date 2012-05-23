import os, sys, stat, time, datetime, re, random
from ensime_client import *
import ensime_environment
import functools, socket, threading
import sublime_plugin, sublime
import thread
import logging
import subprocess
import sexp
from sexp import key,sym

class ProcessListener(object):
  def on_data(self, proc, data):
    pass

  def on_finished(self, proc):
    pass

class AsyncProcess(object):
  def __init__(self, arg_list, listener, cwd = None):

    # ensure the subprocess is always killed when the editor exits
    # import atexit
    # atexit.register(self.kill)

    self.listener = listener
    self.killed = False

    # Hide the console window on Windows
    startupinfo = None
    if os.name == "nt":
      startupinfo = subprocess.STARTUPINFO()
      startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    proc_env = os.environ.copy()

    self.proc = subprocess.Popen(arg_list, stdout=subprocess.PIPE,
      stderr=subprocess.PIPE, startupinfo=startupinfo, env=proc_env, cwd = cwd)

    if self.proc.stdout:
      thread.start_new_thread(self.read_stdout, ())

    if self.proc.stderr:
      thread.start_new_thread(self.read_stderr, ())

  def kill(self):
    if not self.killed:
      self.killed = True
      self.proc.kill()
      self.listener = None

  def poll(self):
    return self.proc.poll() == None

  def read_stdout(self):
    while True:
      data = os.read(self.proc.stdout.fileno(), 2**15)

      if data != "":
        if self.listener:
          self.listener.on_data(self, data)
      else:
        self.proc.stdout.close()
        if self.listener:
          self.listener.on_finished(self)
        break

  def read_stderr(self):
    while True:
      data = os.read(self.proc.stderr.fileno(), 2**15)

      if data != "":
        if self.listener:
          self.listener.on_data(self, data)
      else:
        self.proc.stderr.close()
        break

# if this doesn't work well enough as it's a bit hacky use the chardet egg to drive this home.
guess_list = ["us-ascii", "utf-8", "utf-16", "utf-7", "iso-8859-1", "iso-8859-2", "windows-1250", "windows-1252"]
def decode_string(data):
  for best_enc in guess_list:
    try:
      unicode(data, best_enc, "strict")
    except:
      pass
    else:
      break
  return unicode(data, best_enc)

class ScalaOnly:
  def is_enabled(self):
    return (bool(self.window and self.window.active_view().file_name() != "" and
    self._is_scala(self.window.active_view().file_name())))

  def _is_scala(self, file_name):
    _, fname = os.path.split(file_name)
    return fname.lower().endswith(".scala")

class EnsimeOnly:
  def ensime_project_file(self):
    prj_files = [(f + "/.ensime") for f in self.window.folders() if os.path.exists(f + "/.ensime")]
    if len(prj_files) > 0:
      return prj_files[0]
    else:
      #sublime.error_message("There are no open folders. Please open a folder containing a .ensime file.")
      return None

  def is_enabled(self, kill = False):
    return bool(ensime_environment.ensime_env.client()) and ensime_environment.ensime_env.client.ready() and bool(self.ensime_project_file())

class EnsimeServerCommand(sublime_plugin.WindowCommand, 
                          ProcessListener, ScalaOnly, EnsimeOnly):

  def ensime_project_root(self):
    prj_dirs = [f for f in self.window.folders() if os.path.exists(f + "/.ensime")]
    if len(prj_dirs) > 0:
      return prj_dirs[0]
    else:
      return None

  def is_started(self):
    return hasattr(self, 'proc') and self.proc and self.proc.poll()

  def is_enabled(self, **kwargs):
    start, kill, show_output = (kwargs.get("start", False), 
                                kwargs.get("kill", False), 
                                kwargs.get("show_output", False))
    return (((kill or show_output) and self.is_started()) or 
            (start and bool(self.ensime_project_file())))
                
  def show_output_window(self, show_output = False):
    if show_output:
      self.window.run_command("show_panel", {"panel": "output.ensime_server"})

  def ensime_command(self): 
    if os.name == 'nt':
      return "bin\\server.bat"
    else: 
      return "bin/server"

  def default_ensime_install_path(self):
    if os.name == 'nt':
      return "Ensime\\server"
    else: 
      return "Ensime/server"    


  def run(self, encoding = "utf-8", env = {}, 
          start = False, quiet = True, kill = False, 
          show_output = True):
    print "Running: " + self.__class__.__name__
    self.show_output = show_output
    if not hasattr(self, 'settings'):
      self.settings = sublime.load_settings("Ensime.sublime-settings")

    server_dir = self.settings.get("ensime_server_path", self.default_ensime_install_path())
    server_path = server_dir if server_dir.startswith("/") else os.path.join(sublime.packages_path(), server_dir)

    if kill:
      ensime_environment.ensime_env.client().sync_req([sym("swank:shutdown-server")])
      ensime_environment.ensime_env.client().disconnect()
      if self.proc:
        self.proc.kill()
        self.proc = None
        self.append_data(None, "[Cancelled]")
      return
    else:
      if self.is_started():
        self.show_output_window(show_output)
        if start and not self.quiet:
          print "Ensime server is already running!"
        return

    if not hasattr(self, 'output_view'):
      self.output_view = self.window.get_output_panel("ensime_server")

    self.quiet = quiet

    self.proc = None
    if not self.quiet:
      print "Starting Ensime Server."

    if show_output:
      self.show_output_window(show_output)

    # Change to the working dir, rather than spawning the process with it,
    # so that emitted working dir relative path names make sense
    if self.ensime_project_root() and self.ensime_project_root() != "":
      os.chdir(self.ensime_project_root())

    err_type = OSError
    if os.name == "nt":
      err_type = WindowsError

    try:
      self.show_output = show_output
      if start:
        cl = EnsimeClient(
          ensime_environment.ensime_env.settings, 
          self.window, self.ensime_project_root())
        sublime.set_timeout(
          functools.partial(ensime_environment.ensime_env.set_client, cl), 0)
        vw = self.window.active_view()
        self.proc = AsyncProcess([server_path + '/' + self.ensime_command(),
				  self.ensime_project_root() + "/.ensime_port"],
				  self,
				  server_path)
    except err_type as e:
      print str(e)
      self.append_data(None, str(e) + '\n')

  def perform_handshake(self):
    self.window.run_command("ensime_handshake")


  def append_data(self, proc, data):
    if proc != self.proc:
      # a second call to exec has been made before the first one
      # finished, ignore it instead of intermingling the output.
      if proc:
        proc.kill()
      return

    str_data = str(data).replace("\r\n", "\n").replace("\r", "\n")

    if not ensime_environment.ensime_env.client().ready() and re.search("Wrote port", str_data):
      ensime_environment.ensime_env.client().set_ready()
      self.perform_handshake()

    selection_was_at_end = (len(self.output_view.sel()) == 1
      and self.output_view.sel()[0]
        == sublime.Region(self.output_view.size()))
    self.output_view.set_read_only(False)
    edit = self.output_view.begin_edit()
    self.output_view.insert(edit, self.output_view.size(), str_data)
    if selection_was_at_end:
      self.output_view.show(self.output_view.size())
    self.output_view.end_edit(edit)
    self.output_view.set_read_only(True)

  def finish(self, proc):
    if proc != self.proc:
      return

    # Set the selection to the start, so that next_result will work as expected
    edit = self.output_view.begin_edit()
    self.output_view.sel().clear()
    self.output_view.sel().add(sublime.Region(0))
    self.output_view.end_edit(edit)

  def on_data(self, proc, data):
    sublime.set_timeout(functools.partial(self.append_data, proc, data), 0)

  def on_finished(self, proc):
    sublime.set_timeout(functools.partial(self.finish, proc), 0)


class EnsimeUpdateMessagesView(sublime_plugin.WindowCommand, EnsimeOnly):
  def run(self, msg):
    if msg != None:
      ov = ensime_environment.ensime_env.client().output_view
      msg = msg.replace("\r\n", "\n").replace("\r", "\n")

      selection_was_at_end = (len(ov.sel()) == 1
        and ov.sel()[0]
            == sublime.Region(ov.size()))
      ov.set_read_only(False)
      edit = ov.begin_edit()
      ov.insert(edit, ov.size(), str(msg) + "\n")
      if selection_was_at_end:
          ov.show(ov.size())
      ov.end_edit(edit)
      ov.set_read_only(True)

class CreateEnsimeClientCommand(sublime_plugin.WindowCommand, EnsimeOnly):

  def run(self):
    cl = EnsimeClient(self.window, u"/Users/ivan/projects/scapulet")
    cl.set_ready()
    self.window.run_command("ensime_handshake")

class EnsimeShowMessageViewCommand(sublime_plugin.WindowCommand, EnsimeOnly):

  def run(self):
    self.window.run_command("show_panel", {"panel": "output.ensime_messages"})

class EnsimeHandshakeCommand(sublime_plugin.WindowCommand, EnsimeOnly):

  def handle_init_reply(self, init_info):
    sublime.status_message("Ensime ready!")

  def handle_reply(self, server_info):
    if server_info[1][0] == key(":ok"):
      sublime.status_message("Initializing... ")
      ensime_environment.ensime_env.client().initialize_project(self.handle_init_reply)
    else:
      sublime.error_message("There was problem initializing ensime, msgno: " + 
                            str(server_info[2]) + ".")

  def run(self):
    if (ensime_environment.ensime_env.client().ready()):
      ensime_environment.ensime_env.client().handshake(self.handle_reply)

