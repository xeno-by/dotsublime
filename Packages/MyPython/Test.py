import sublime_plugin

class Env(object):
  def __init__(self):
    self.x = 2

class Base(object):
  def __init__(self, window):
    self.env = Env()
    self.y = 100
#    foo()
    print str(window)

  def __getattr__(self, name):
    print "__getattr__(" + name + ")"
    return self.env.__getattribute__(name)

# class CommonCommand(Base, sublime_plugin.WindowCommand):
#   def run(self):
#     print self.x
#     self.x = 3
#     print self.x
#     print self.y
#     self.y = 200
#     print self.y

# class Common2Command(Base, sublime_plugin.TextCommand):
#   def __init__(self, view):
#     print "boo"
#     Base.__init__(self, view)

#   def run(self):
#     print "works"