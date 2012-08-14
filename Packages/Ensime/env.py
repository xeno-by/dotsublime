import sublime
from sublime import *
from sublime_plugin import *
import os, threading, thread, socket, getpass, subprocess
import killableprocess, tempfile, datetime, time
import functools, inspect, traceback, random, re
from sexp import sexp
from sexp.sexp import key, sym
from string import strip

envLock = threading.RLock()
ensime_envs = {}
environment_constructor = None

def for_window(window):
  if window:
    if window.id() in ensime_envs:
      return ensime_envs[window.id()]
    envLock.acquire()
    try:
      if not (window.id() in ensime_envs):
        # protection against reentrant environment_constructor calls
        ensime_envs[window.id()] = None
        ensime_envs[window.id()] = environment_constructor(window)
      return ensime_envs[window.id()]
    finally:
      envLock.release()
  return None



