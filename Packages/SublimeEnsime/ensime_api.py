from ensime_codec import ensime_codec

class EnsimeApi:

  def type_check_file(self, file_path, on_complete = None):
    req = ensime_codec.encode_type_check_file(file_path)
    self.async_req(req, on_complete)

  def add_notes(self, notes):
    self.notes += notes
    for i in range(0, self.w.num_groups):
      v = active_view_in_group(i)
      EnsimeHighlights(v).refresh()

  def clear_notes(self):
    self.notes = []
    for i in range(0, self.w.num_groups):
      v = active_view_in_group(i)
      EnsimeHighlights(v).refresh()

  def inspect_type_at_point(self, file_path, position, on_complete):
    req = ensime_codec.encode_inspect_type_at_point(file_path, position)
    self.async_req(req, on_complete)

  def complete_member(self, file_path, position):
    req = ensime_codec.encode_complete_member(file_path, position)
    resp = self.sync_req(req)
    return ensime_codec.decode_completions(resp)
