import sexp
from sexp import key, sym

class Rpc(object):
  def __init__(self, env):
    self.env = env

  def async_req(self, req, callback):
    return self.env.controller.client.async_req(req, callback, call_back_into_ui_thread = True)

  def initialize_project(self, conf, on_complete = None):
    req = [sym("swank:init-project"), conf]
    def callback(payload):
      data = not not payload
      if (on_complete): on_complete(data)
    self.async_req(req, callback)

  def type_check_file(self, file_name, on_complete = None):
    req = [sym("swank:typecheck-file"), str(file_name)]
    def callback(payload):
      data = not not payload
      if (on_complete): on_complete(data)
    self.async_req(req, callback)

  def get_completions(self, file_name, position, max_results):
    return []

  def inspect_type_at_point(self, file_name, position, on_complete):
    pass

  def symbol_at_point(self, file_name, position, on_complete):
    pass

  def debug_set_break(self, file_name, line):
    pass

  def debug_clear_break(self, file_name, line):
    pass

  def debug_clear_all_breaks(self):
    pass

  def debug_start(self, launch):
    pass

  def debug_step(self, thread_id):
    pass

  def debug_next(self, thread_id):
    pass

  def debug_continue(self, thread_id):
    pass

class ActiveRecord(object):
  @classmethod
  def parse_list(cls, raw):
    if not raw: return []
    if type(raw[0]) == type(key(":key")):
      m = sexp.sexp_to_key_map(raw)
      parse = getattr(cls, "parse")
      return [parse(raw) for raw in m[":" + cls.__name__.lower() + "s"]]
    else:
      [parse(raw) for raw in m]

class Note(ActiveRecord):
  @staticmethod
  def parse(raw):
    if not raw: return None
    m = sexp.sexp_to_key_map(raw)
    self = Note()
    self.message = m[":msg"]
    self.file_name = m[":file"]
    self.severity = m[":severity"]
    self.start = m[":beg"]
    self.end = m[":end"]
    self.line = m[":line"]
    self.col = m[":col"]
    return self

# class EnsimeApi:

#   def type_check_file(self, file_path, on_complete = None):
#     req = ensime_codec.encode_type_check_file(file_path)
#     wrapped_on_complete = bind(self.type_check_file_on_complete_wrapper, on_complete) if on_complete else None
#     self.env.controller.client.async_req(req, wrapped_on_complete, call_back_into_ui_thread = True)

#   def type_check_file_on_complete_wrapper(self, on_complete, payload):
#     return on_complete(ensime_codec.decode_type_check_file(payload))

#   def inspect_type_at_point(self, file_path, position, on_complete):
#     req = ensime_codec.encode_inspect_type_at_point(file_path, position)
#     wrapped_on_complete = bind(self.inspect_type_at_point_on_complete_wrapper, on_complete) if on_complete else None
#     self.env.controller.client.async_req(req, wrapped_on_complete, call_back_into_ui_thread = True)

#   def inspect_type_at_point_on_complete_wrapper(self, on_complete, payload):
#     return on_complete(ensime_codec.decode_inspect_type_at_point(payload))

#   def get_completions(self, file_path, position, max_results):
#     if self.v.is_dirty():
#       edits = diff.diff_view_with_disk(self.v)
#       req = ensime_codec.encode_patch_source(
#         self.v.file_name(), edits)
#       self.env.controller.client.async_req(req)
#     req = ensime_codec.encode_completions(file_path, position, max_results)
#     timeout = self.env.settings.get("timeout_completion", 0.5)
#     resp = self.env.controller.client.sync_req(req, timeout=timeout)
#     if not resp: self.status_message("Ensime completion timed out")
#     return ensime_codec.decode_completions(resp)

#   def symbol_at_point(self, file_path, position, on_complete):
#     req = ensime_codec.encode_symbol_at_point(file_path, position)
#     wrapped_on_complete = bind(self.symbol_at_point_on_complete_wrapper, on_complete) if on_complete else None
#     self.env.controller.client.async_req(req, wrapped_on_complete, call_back_into_ui_thread = True)

#   def symbol_at_point_on_complete_wrapper(self, on_complete, payload):
#     return on_complete(ensime_codec.decode_symbol_at_point(payload))

# class EnsimeApiImpl(EnsimeCommon):
#   def __nonzero__(self):
#     controller = self.env and self.env.controller
#     socket = controller and controller.client and controller.client.socket
#     connected = socket and socket.connected
#     return not not connected

# def ensime_api(owner):
#   return EnsimeApiImpl(owner)


# class EnsimeCodec:
#   __metaclass__ = log_all_exceptions()

#   def encode_initialize_project(self, conf):
#     return [sym("swank:init-project"), conf]

#   def encode_type_check_file(self, file_path):
#     return [sym("swank:typecheck-file"), file_path]

#   def decode_type_check_file(self, data):
#     return True

#   def decode_notes(self, data):
#     if not data: return []
#     m = sexp.sexp_to_key_map(data)
#     return [self.decode_note(n) for n in m[":notes"]]

#   def decode_note(self, data):
#     if not data: return None
#     m = sexp.sexp_to_key_map(data)
#     class EnsimeNote(object): pass
#     note = EnsimeNote()
#     note.message = m[":msg"]
#     note.file_name = m[":file"]
#     note.severity = m[":severity"]
#     note.start = m[":beg"]
#     note.end = m[":end"]
#     note.line = m[":line"]
#     note.col = m[":col"]
#     return note

#   def encode_inspect_type_at_point(self, file_path, position):
#     return [sym("swank:type-at-point"), str(file_path), int(position)]

#   def decode_inspect_type_at_point(self, data):
#     if not data: return None
#     return self.decode_type(data)

#   def encode_completions(self, file_path, position, max_results):
#     return [sym("swank:completions"),
#             str(file_path), int(position), max_results, False, False]

#   def decode_completions(self, data):
#     if not data: return []
#     m = sexp.sexp_to_key_map(data)
#     return [self.decode_completion(p) for p in m.get(":completions", [])]

#   def decode_completion(self, data):
#     if not data: return None
#     m = sexp.sexp_to_key_map(data)
#     class EnsimeCompletion(object): pass
#     completion = EnsimeCompletion()
#     completion.name = m[":name"]
#     completion.signature = m[":type-sig"]
#     completion.is_callable = bool(m[":is-callable"]) if ":is-callable" in m else False
#     completion.type_id = m[":type-id"]
#     completion.to_insert = m[":to-insert"] if ":to-insert" in m else None
#     return completion

#   def encode_symbol_at_point(self, file_path, position):
#     return [sym("swank:symbol-at-point"), str(file_path), int(position)]

#   def encode_patch_source(self, file_path, edits):
#     return [sym("swank:patch-source"), str(file_path), edits]

#   def decode_symbol_at_point(self, data):
#     if not data: return None
#     return self.decode_symbol(data)

#   def decode_position(self, data):
#     if not data: return None
#     m = sexp.sexp_to_key_map(data)
#     class EnsimePosition(object): pass
#     position = EnsimePosition()
#     position.file_name = m[":file"] if ":file" in m else None
#     position.offset = m[":offset"] if ":offset" in m else None
#     position.start = m[":start"] if ":start" in m else None
#     position.end = m[":end"] if ":end" in m else None
#     return position

#   def decode_types(self, data):
#     if not data: return []
#     return [self.decode_type(t) for t in data]

#   def decode_type(self, data):
#     if not data: return None
#     m = sexp.sexp_to_key_map(data)
#     class TypeInfo(object): pass
#     info = TypeInfo()
#     info.name = m[":name"]
#     info.type_id = m[":type-id"]
#     if ":arrow-type" in m:
#       info.arrow_type = True
#       info.result_type = self.decode_type(m[":result-type"])
#       info.param_sections = self.decode_members(m[":param-sections"]) if ":param-sections" in m else []
#     else:
#       info.arrow_type = False
#       info.full_name = m[":full-name"] if ":full-name" in m else None
#       info.decl_as = m[":decl-as"] if ":decl-as" in m else None
#       info.decl_pos = self.decode_position(m[":pos"]) if ":pos" in m else None
#       info.type_args = self.decode_types(m[":type-args"]) if ":type-args" in m else []
#       info.outer_type_id = m[":outer-type-id"] if ":outer-type-id" in m else None
#       info.members = self.decode_members(m[":members"]) if ":members" in m else []
#     return info

#   def decode_symbol(self, data):
#     if not data: return None
#     m = sexp.sexp_to_key_map(data)
#     class SymbolInfo(object): pass
#     info = SymbolInfo()
#     info.name = m[":name"]
#     info.type = self.decode_type(m[":type"])
#     info.decl_pos = self.decode_position(m[":decl-pos"]) if ":decl-pos" in m else None
#     info.is_callable = bool(m[":is-callable"]) if ":is-callable" in m else False
#     info.owner_type_id = m[":owner-type-id"] if ":owner-type-id" in m else None
#     return info

#   def decode_members(self, data):
#     if not data: return []
#     return [self.decode_member(m) for m in data]

#   def decode_member(self, data):
#     if not data: return None
#     m = sexp.sexp_to_key_map(data)
#     class MemberInfo(object): pass
#     info = MemberInfo()
#     # todo. implement this in accordance with SwankProtocol.scala
#     return info

#   def decode_param_sections(self, data):
#     if not data: return []
#     return [self.decode_param_section(ps) for ps in data]

#   def decode_param_section(self, data):
#     if not data: return None
#     m = sexp.sexp_to_key_map(data)
#     class ParamSectionInfo(object): pass
#     info = ParamSectionInfo()
#     info.is_implicit = bool(m[":is-implicit"]) if ":is-implicit" in m else False
#     info.params = self.decode_params(m[":params"]) if ":params" in m else []
#     return info

#   def decode_params(self, data):
#     if not data: return []
#     return [self.decode_param(p) for p in data]

#   def decode_param(self, data):
#     # todo. implement this in accordance with SwankProtocol.scala
#     return None

#   def decode_debug_event(self, data):
#     if not data: return None
#     m = sexp.sexp_to_key_map(data)
#     class EnsimeDebugEvent(object): pass
#     event = EnsimeDebugEvent()
#     event.type = str(m[":type"])
#     if event.type == "output":
#       event.body = m[":body"]
#     elif event.type == "step":
#       event.thread_id = m[":thread-id"]
#       event.thread_name = m[":thread-name"]
#       event.file_name = m[":file"]
#       event.line = m[":line"]
#     elif event.type == "breakpoint":
#       event.thread_id = m[":thread-id"]
#       event.thread_name = m[":thread-name"]
#       event.file_name = m[":file"]
#       event.line = m[":line"]
#     elif event.type == "death":
#       pass
#     elif event.type == "start":
#       pass
#     elif event.type == "disconnect":
#       pass
#     elif event.type == "exception":
#       event.exception_id = m[":exception"]
#       event.thread_id = m[":thread-id"]
#       event.thread_name = m[":thread-name"]
#       event.file_name = m[":file"]
#       event.line = m[":line"]
#     elif event.type == "threadStart":
#       event.thread_id = m[":thread-id"]
#     elif event.type == "threadDeath":
#       event.thread_id = m[":thread-id"]
#     else:
#       raise Exception("unexpected debug event of type " + str(event.type) + ": " + str(m))
#     return event

#   def decode_debug_backtrace(self, data):
#     if not data: return None
#     m = sexp.sexp_to_key_map(data)
#     class EnsimeDebugBacktrace(object): pass
#     backtrace = EnsimeDebugBacktrace()
#     backtrace.frames = self.decode_debug_stack_frames(m[":frames"]) if ":frames" in m else []
#     backtrace.thread_id = m[":thread-id"]
#     backtrace.thread_name = m[":thread-name"]
#     return backtrace

#   def decode_debug_stack_frames(self, data):
#     if not data: return []
#     return [self.decode_debug_stack_frame(f) for f in data]

#   def decode_debug_stack_frame(self, data):
#     if not data: return None
#     m = sexp.sexp_to_key_map(data)
#     class EnsimeDebugStackFrame(object): pass
#     stackframe = EnsimeDebugStackFrame()
#     stackframe.index = m[":index"]
#     stackframe.locals = self.decode_debug_stack_locals(m[":locals"]) if ":locals" in m else []
#     stackframe.num_args = m[":num-args"]
#     stackframe.class_name = m[":class-name"]
#     stackframe.method_name = m[":method-name"]
#     stackframe.pc_location = self.decode_debug_source_position(m[":pc-location"])
#     stackframe.this_object_id = m[":this-object-id"]
#     return stackframe

#   def decode_debug_source_position(self, data):
#     if not data: return None
#     m = sexp.sexp_to_key_map(data)
#     class EnsimeDebugSourcePosition(object): pass
#     position = EnsimeDebugSourcePosition()
#     position.file_name = m[":file"]
#     position.line = m[":line"]
#     return position

#   def decode_debug_stack_locals(self, data):
#     if not data: return []
#     return [self.decode_debug_stack_local(loc) for loc in data]

#   def decode_debug_stack_local(self, data):
#     if not data: return None
#     m = sexp.sexp_to_key_map(data)
#     class EnsimeDebugStackLocal(object): pass
#     loc = EnsimeDebugStackLocal()
#     loc.index = m[":index"]
#     loc.name = m[":name"]
#     loc.summary = m[":summary"]
#     loc.type_name = m[":type-name"]
#     return loc

#   def decode_debug_value(self, data):
#     if not data: return None
#     m = sexp.sexp_to_key_map(data)
#     class EnsimeDebugValue(object): pass
#     value = EnsimeDebugValue()
#     value.type = m[":val-type"]
#     value.type_name = m[":type-name"]
#     value.length = m[":length"] if ":length" in m else None
#     value.element_type_name = m[":element-type-name"] if ":element-type-name" in m else None
#     value.summary = m[":summary"] if ":summary" in m else None
#     value.object_id = m[":object_id"] if ":object_id" in m else None
#     value.fields = self.decode_debug_object_fields(m[":fields"]) if ":fields" in m else []
#     if str(value.type) == "null" or str(value.type) == "prim" or str(value.type) == "obj" or str(value.type) == "str" or str(value.type) == "arr":
#       pass
#     else:
#       raise Exception("unexpected debug value of type " + str(value.type) + ": " + str(m))
#     return value

#   def decode_debug_object_fields(self, data):
#     if not data: return []
#     return [self.decode_debug_object_field(f) for f in data]

#   def decode_debug_object_field(self, data):
#     if not data: return None
#     m = sexp.sexp_to_key_map(data)
#     class EnsimeDebugObjectField(object): pass
#     field = EnsimeDebugObjectField()
#     field.index = m[":index"]
#     field.name = m[":name"]
#     field.summary = m[":summary"]
#     field.type_name = m[":type-name"]
#     return field

#   def encode_debug_clear_all_breaks(self):
#     return [sym("swank:debug-clear-all-breaks")]

#   def decode_debug_clear_all_breaks(self, data):
#     return data

#   def encode_debug_set_break(self, file_name, line):
#     return [sym("swank:debug-set-break"), str(file_name), int(line)]

#   def decode_debug_set_break(self, data):
#     return data

#   def encode_debug_clear_break(self, file_name, line):
#     return [sym("swank:debug-clear-break"), str(file_name), int(line)]

#   def decode_debug_clear_break(self, data):
#     return data

#   def encode_debug_start(self, command_line):
#     return [sym("swank:debug-start"), str(command_line)]

#   def decode_debug_start(self, data):
#     if not data: return None
#     m = sexp.sexp_to_key_map(data)
#     status = m[":status"]
#     if status == "success":
#       return True
#     elif status == "error":
#       class EnsimeDebugStartError(object):
#         def __nonzero__(self):
#           return False
#       error = EnsimeDebugStartError()
#       error.code = m[":error-code"]
#       error.details = m[":details"]
#       return error
#     else:
#       raise Exception("unexpected status: " + str(status))

#   def encode_debug_stop(self):
#     return [sym("swank:debug-stop")]

#   def encode_debug_continue(self, thread_id):
#     return [sym("swank:debug-continue"), str(thread_id)]

#   def encode_debug_step(self, thread_id):
#     return [sym("swank:debug-step"), str(thread_id)]

#   def encode_debug_next(self, thread_id):
#     return [sym("swank:debug-next"), str(thread_id)]

#   def encode_debug_backtrace(self, thread_id, first_frame, num_frames):
#     return [sym("swank:debug-backtrace"), str(thread_id), int(first_frame), int(num_frames)]


# def _ensime_debug_set_break(self, file_name, line, on_complete = None):
#   req = ensime_codec.encode_debug_set_break(file_name, line)
#   wrapped_on_complete = bind(self._ensime_debug_set_break_on_complete_wrapper, on_complete) if on_complete else None
#   self.env.controller.client.async_req(req, wrapped_on_complete, call_back_into_ui_thread = True)

# def _ensime_debug_set_break_on_complete_wrapper(self, on_complete, payload):
#   return on_complete(ensime_codec.decode_debug_set_break(payload))

# def _ensime_debug_clear_break(self, file_name, line, on_complete = None):
#   req = ensime_codec.encode_debug_clear_break(file_name, line)
#   wrapped_on_complete = bind(self._ensime_debug_clear_break_on_complete_wrapper, on_complete) if on_complete else None
#   self.env.controller.client.async_req(req, wrapped_on_complete, call_back_into_ui_thread = True)

# def _ensime_debug_clear_break_on_complete_wrapper(self, on_complete, payload):
#   return on_complete(ensime_codec.decode_debug_clear_break(payload))

# def _ensime_debug_clear_all_breaks(self, on_complete = None):
#   req = ensime_codec.encode_debug_clear_all_breaks()
#   wrapped_on_complete = bind(self._ensime_debug_clear_all_breaks_on_complete_wrapper, on_complete) if on_complete else None
#   self.env.controller.client.async_req(req, wrapped_on_complete, call_back_into_ui_thread = True)

# def _ensime_debug_clear_all_breaks_on_complete_wrapper(self, on_complete, payload):
#   return on_complete(ensime_codec.decode_debug_clear_all_breaks(payload))

# def debug_start(breaks, launch, on_complete):
#   self.debug_clear_all_breaks(bind(self._debug_start_debug_set_breaks, launch, self.env.breakpoints, on_complete))

# def _debug_start_debug_set_breaks(self, launch, breaks, on_complete, status):
#   if status:
#     if breaks:
#       head = breaks[0]
#       tail = breaks[1:]
#       self.rpc.debug_set_break(head.file_name, head.line, bind(self._debug_start_debug_set_breaks, launch, tail, on_complete))
#     else:
#       self._debug_start_debug_start(launch, on_complete)
#   else:
#     if on_complete: on_complete(None)

# def _debug_start_debug_start(self, launch, on_complete):
#   req = ensime_codec.encode_debug_start(launch.command_line)
#   wrapped_on_complete = bind(self._debug_start_debug_start_on_complete_wrapper, on_complete) if on_complete else None
#   self.env.controller.client.async_req(req, wrapped_on_complete, call_back_into_ui_thread = True)

# def _debug_start_debug_start_on_complete_wrapper(self, on_complete, payload):
#   if on_complete: return on_complete(ensime_codec.decode_debug_start(payload))

# def stop(self):
#   req = ensime_codec.encode_debug_stop()
#   self.env.controller.client.async_req(req)

# def step_into(self):
#   self.last_req = "step_into"
#   req = ensime_codec.encode_debug_step(self.env.focus.thread_id)
#   self.env.controller.client.async_req(req)

# def step_over(self):
#   self.last_req = "step_over"
#   req = ensime_codec.encode_debug_next(self.env.focus.thread_id)
#   self.env.controller.client.async_req(req)

# def resume(self):
#   self.last_req = "resume"
#   req = ensime_codec.encode_debug_continue(self.env.focus.thread_id)
#   self.env.controller.client.async_req(req)
