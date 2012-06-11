import os
import sublime
import sublime_plugin

class MyShellCompletionListener(sublime_plugin.EventListener):
  def on_query_completions(self, view, prefix, locations):
    v = view
    from sublimerepl import repl_view
    rv = repl_view(v)
    if v.settings().has("repl"):
      delta = v.sel()[0].begin() - rv._output_end
      if delta <= 0:
        return ([], sublime.INHIBIT_EXPLICIT_COMPLETIONS | sublime.INHIBIT_WORD_COMPLETIONS)
      else:
        bol = v.line(v.sel()[0]).begin()
        cwd = v.substr(sublime.Region(bol, rv._output_end - 1));
        input = rv.user_input()
        path = cwd + "\\" + input
        liof = path.rindex("\\")
        dir = path[:(liof + 1)]
        completee = path[(liof + 1):]
        liof = max(completee.rindex(" ") if " " in completee else -1, completee.rindex(";") if ";" in completee else -1)
        if liof != -1:
          completee = completee[(liof+1):]
        completee = completee.replace("/", "\\")
        liof = completee.rindex("\\") if "\\" in completee else -1
        if liof != -1:
          dir = dir + completee[:(liof + 1)]
          completee = completee[(liof + 1):]
        print "dir = " + dir + ", completee = " + completee
        print "files = " + str(os.listdir(dir))
        matches = [name for name in os.listdir(dir) if name.lower().startswith(completee.lower())]
        print "matches = " + str(matches)
        completions = [(m, m) for m in matches]
        return (completions, sublime.INHIBIT_EXPLICIT_COMPLETIONS | sublime.INHIBIT_WORD_COMPLETIONS)
    else:
      return ([], sublime.INHIBIT_EXPLICIT_COMPLETIONS | sublime.INHIBIT_WORD_COMPLETIONS)

class MyShellTabCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    v = self.view
    w = v.window()
    w.run_command("insert_best_completion", {"default": "", "exact": False})

class MyShellNextCompletionCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    v = self.view
    w = v.window()
    w.run_command("insert_best_completion", {"default": "", "exact": False})