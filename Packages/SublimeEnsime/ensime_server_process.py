import os
import thread
import functools
import subprocess
import killableprocess
from ensime_common import *

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
