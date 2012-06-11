class EnsimeCodec:
  def encode_initialize_project(self, conf):
    return [sym("swank:init-project"), conf]

  def encode_type_check_file(self, file_path, on_complete):
    return [sym("swank:typecheck-file"), file_path]

  def decode_notes(self, data):
    m = sexp.sexp_to_key_map(data)
    notes = [sexp.sexp_to_key_map(form) for form in m[":notes"]]
    return [self.decode_note(n) for n in notes]

  def decode_note(self, data):
    class EnsimeNote(object): pass
    note = EnsimeNote()
    note.message = m[":msg"]
    note.file_name = m[":file"]
    note.severity = m[":severity"]
    note.start = m[":beg"]
    note.end = m[":end"]
    note.line = m[":line"]
    note.col = m[":col"]
    return note

  def encode_inspect_type_at_point(self, file_path, position):
    return [sym("swank:type-at-point"), str(file_path), int(position)]

  def decode_inspect_type_at_point(self, data):
    d = data[1][1]
    if d[1] != "<notype>":
      return "(" + str(d[7]) + ") " + d[5]
    else:
      return None

  def encode_complete_member(self, file_path, position):
    return [sym("swank:completions"), str(file_path), int(position), 0]

  def decode_completions(self, data):
    friend = sexp.sexp_to_key_map(data[1][1])
    comps = friend[":completions"] if ":completions" in friend else []
    comp_list = [ensime_completion(sexp.sexp_to_key_map(p)) for p in friend[":completions"]]

  def decode_completion(self, data):
    class EnsimeCompletion(object): pass
    completion = EnsimeCompletion()
    completion.name = m[":name"]
    completion.signature = m[":type-sig"]
    completion.is_callable = bool(m[":is-callable"]) if ":is-callable" in m else False
    completion.type_id = m[":type-id"]
    completion.to_insert = m[":to-insert"] if ":to-insert" in m else None
    return completion

ensime_codec = EnsimeCodec()