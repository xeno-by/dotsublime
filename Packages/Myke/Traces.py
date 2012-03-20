import sublime, sublime_plugin
import subprocess
import os

class MykeLastTrace(sublime_plugin.WindowCommand):
  def run(self):
    incantation = "last"
    print("Running " + incantation)
    subprocess.Popen(incantation, shell = True)

class MykePrevTrace(sublime_plugin.WindowCommand):
  def run(self):
    incantation = "prev"
    print("Running " + incantation)
    subprocess.Popen(incantation, shell = True)

class MykeNextTrace(sublime_plugin.WindowCommand):
  def run(self):
    incantation = "next"
    print("Running " + incantation)
    subprocess.Popen(incantation, shell = True)
