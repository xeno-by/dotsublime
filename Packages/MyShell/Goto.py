import sublime
import sublime_plugin

class MyShellCompletionListener(sublime_plugin.EventListener):
  def on_modified(self, view):
    v = view
    w = v.window()
    if v.settings().has("repl") and not v.settings().has("repl_completions_assigned"):
      v.settings().set("result_file_regex", "([:.a-z_A-Z0-9\\\\/-]+[.]scala):([0-9]+)")
      v.settings().set("result_line_regex", "")
      v.settings().set("result_base_dir", "")
      other_view = w.new_file()
      w.focus_view(other_view)
      w.run_command("close_file")
      w.focus_view(v)
      v.settings().set("repl_completions_assigned", "")
