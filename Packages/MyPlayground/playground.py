from sublime import *
from sublime_plugin import *

lines = [[str(i), str(i+1)] for i in range(1, 100000)]
# lines = [str(i) for i in range(1, 100000)]

# class MyPlaygroundCommand(WindowCommand):
#   def run(self):
#     sublime.set_timeout(self.foo, 3000)
#     self.window.show_quick_panel(lines, lambda _: None)

#   def foo(self):
#     self.window.new_file()
#     self.window.show_quick_panel(lines, lambda _: None)

class MyPlaygroundCommand(TextCommand):
  def run(self, edit):
    sel = self.view.sel()[0]
    lines = self.view.substr(sel).split("\n")
    for idx, line in enumerate(lines[:-1]):
      lines[idx] = str(idx + 1) + ") " + lines[idx]
    self.view.replace(edit, sel, "\n".join(lines))

# class FuzzyEventListener(EventListener):
#   def on_activated(self, view):
#     print "on_activated"

#   def on_query_context(self, view, key, operator, operand, match_all):
#     print "on_query_context"
#     return False

#   def on_modified(self, view):
#     print "on_modified"
#     print view.substr(Region(0, view.size()))
