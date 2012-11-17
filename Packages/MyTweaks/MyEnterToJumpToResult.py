import sublime, sublime_plugin

class EnterToJumpToResultListener(sublime_plugin.EventListener):
  def on_query_context(self, view, key, operator, operand, match_all):
    if key == "in_results_file":
      return view.settings().has("result_file_regex") and not view.settings().get("repl")

    return None

class JumpToResultUnderCursorCommand(sublime_plugin.WindowCommand):
  def run(self):
    view = self.window.active_view()
    cur_line = view.lines(view.sel()[0])[0]
    pt = cur_line.a
    view.sel().clear()
    view.sel().add(sublime.Region(pt))
    view.show(pt)
    self.window.run_command("next_result")
