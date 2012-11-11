import sublime, sublime_plugin

class MyHackCommand(sublime_plugin.ApplicationCommand):
  def run(self):
    print "my_hack"