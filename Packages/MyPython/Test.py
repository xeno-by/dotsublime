# from sublime_plugin import *

# class EnsimeApi(object):
#   pass

# class EnsimeBase(object):
#   def __init__(self, owner):
#     print "EnsimeBase: " + str(owner)

# class EnsimeCommon(EnsimeBase, EnsimeApi):
#   pass

# class EnsimeWindowCommand(EnsimeCommon, WindowCommand):
#   def __init__(self, window):
#     EnsimeCommon.__init__(self, window)
#     WindowCommand.__init__(self, window)

# class EnsimeTextCommand(EnsimeCommon, TextCommand):
#   def __init__(self, view):
#     EnsimeCommon.__init__(self, view)
#     TextCommand.__init__(self, view)

# class MyWC(EnsimeWindowCommand):
#   pass

# class MyTC(EnsimeTextCommand):
#   pass