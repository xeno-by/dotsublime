import os

def encode_path(path):
  if not path:
    return path

  if os.name == "nt":
    if os.path.isabs(path):
      drive, rest = os.path.splitdrive(path)
      return "/" + drive[:-1].upper() + rest.replace("\\", "/")
    else:
      return path.replace("\\", "/")
  else:
    return path

def decode_path(path):
  if not path:
    return path

  if os.name == "nt":
    if path.startswith("/"):
      path = path[1:]
      iof = path.find("/")
      if iof == -1:
        drive = path
        rest = ""
      else:
        drive = path[:iof]
        rest = path[iof:]
      return (drive + ":" + rest).replace("/", "\\")
    else:
      return path.replace("/", "\\")
  else:
    return path