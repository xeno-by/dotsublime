import sublime, sublime_plugin
import subprocess, os, time, re, json

class GaikaCommand(sublime_plugin.WindowCommand):
  def run(self, cmd, args=[]):
    window = self.window
    view = self.window.active_view()
    self.view = view
    self.cmd = cmd
    self.args = args or (view.settings().get("gaika_args") if view else None) or []
    # how do I reliably detect the currently open project?!
    self.project_root = (view.settings().get("gaika_project_root") if view else None) or self.window.folders()[1] + "/.."
    self.current_file = view.file_name() if view else None
    # TODO: looks like I can't reasonably get away without gaika supporting multiple compilation scenarios
    if self.current_file and self.current_file.endswith(".tex"): self.args.append(self.current_file)
    self.current_dir = os.path.dirname(self.current_file) if self.current_file else self.project_root
    self.launch_gaika()

  def launch_gaika(self):
    view_name = "gaika " + self.cmd
    wannabes = filter(lambda v: v.name() == view_name, self.window.views())
    prev_active_group = self.window.active_group()
    if wannabes:
      wannabe = wannabes[0]
    else:
      # this should be done by the layout daemon, but this way we prevent flickering
      if self.window.num_groups() == 2:
        self.window.focus_group(1)
      wannabe = self.window.new_file()
    wannabe.set_name(view_name)
    wannabe.settings().set("gaika_project_root", self.project_root)
    wannabe.settings().set("gaika_cmd", self.cmd)
    wannabe.settings().set("gaika_args", self.args)
    wannabe.settings().set("prev_time", time.time())
    wannabe.settings().set("prev_active_group", prev_active_group)
    cmd = ["gaika", self.cmd, "--sublime"] + self.args
    self.window.run_command("exec", {
      "title": view_name,
      "cmd": cmd,
      "cont": "gaika_continuation",
      "working_dir": self.current_dir,
      "file_regex": "dummy set by gaika",
      "line_regex": "dummy set by gaika"
    })

class GaikaContinuationCommand(sublime_plugin.TextCommand):
  def run(self, edit, returncode):
    view = self.view
    window = self.view.window()

    dotgaika = os.path.expandvars("$HOME/.gaika")
    with open(dotgaika, "r") as f: env = json.load(f)

    cont = env["continuation"] if "continuation" in env else None
    if cont:
      cont = env["continuation"]
      window.run_command("exec", {"title": view.name(), "cmd": [cont], "cont": "gaika_continuation", "shell": "true"})
      return

    success = True if env["status"] == 0 else False
    meaningful = env["meaningful"] == 1 if "meaningful" in env else None
    auto_close = success and not meaningful
    if not success:
      line = self.view.substr(self.view.line(0))
      if re.match("unsupported action", line):
        auto_close = True
    if auto_close:
      active = window.active_view()
      if not active or active.id() == self.view.id():
        prev_active_group = self.view.settings().get("prev_active_group")
        delta = time.time() - self.view.settings().get("prev_time")
        window.run_command("close_file")
        window.focus_group(prev_active_group)
      else:
        window.focus_view(view)
        window.run_command("close_file")
        window.focus_view(active)

    result_file_regex = env["result_file_regex"] if "result_file_regex" in env else ""
    result_line_regex = env["result_line_regex"] if "result_line_regex" in env else ""
    result_base_dir = env["result_base_dir"] if "result_base_dir" in env else (env["working_dir"] or "")
    if result_file_regex or result_line_regex:
      view.settings().set("result_file_regex", result_file_regex)
      view.settings().set("result_line_regex", result_line_regex)
      view.settings().set("result_base_dir", result_base_dir)
      other_view = window.new_file()
      window.focus_view(other_view)
      window.run_command("close_file")
      window.focus_view(view)

    view.settings().erase("no_history")
#    pt = view.text_point(1, 1)
#    view.sel().clear()
#    view.sel().add(sublime.Region(pt))
#    view.show(pt)

    message = "Gaika " + env["action"]
    args = env["args"] if "args" in env else None
    if args: message = "%s with args %s" % (message, args)
    message = "%s has completed with code %s" % (message, env["status"])
    GaikaStatusMessageDisplay(window.active_view(), message)

class GaikaStatusMessageListener(sublime_plugin.EventListener):
  def on_deactivated(self, view):
    self.disable_status_message(view)

  # commented out to workaround the bug described at:
  # http://www.sublimetext.com/forum/viewtopic.php?f=2&t=10518&p=41638#p41638
  # def on_selection_modified(self, view):
  #   self.disable_status_message(view)

  def disable_status_message(self, view):
    view.settings().set("gaika_status_message", None)

class GaikaStatusMessageDisplay():
  def __init__(self, view, message):
    view.settings().set("gaika_status_message", message)
    sublime.set_timeout(lambda: self.run(view), 1000)

  def run(self, view):
    message = view.settings().get("gaika_status_message")
    if message:
      sublime.status_message(message)
      sublime.set_timeout(lambda: self.run(view), 1000)
