import sublime_plugin

def foo():
  print "bar"

class NestedCommand(sublime_plugin.WindowCommand):
  def run(self):
    print "works"
