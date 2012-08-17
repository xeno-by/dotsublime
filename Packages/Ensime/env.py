import threading

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
