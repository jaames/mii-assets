import numpy as np
from struct import unpack

class FFLiResourceShape:
  def __init__(self, stream):
    self.stream = stream
    self.offsets = np.fromstring(self.stream.read(24), dtype=">u4")
    self.lengths = np.fromstring(self.stream.read(24), dtype=">u4")
    self.n_verts = self.lengths[0] // 16
    self.n_faces = self.lengths[5] // 3

  def get_section(self, index):
    # sections 1 - 5
    if index < 6:
      offset = self.offsets[index]
      length = int(self.lengths[index])
      # the length of section type 5 has to be doubled, because of course?
      if index == 5: length *= 2
    # other sections use hardcoded offsets + lengths
    elif index == 6:
      offset = 0x48
      length = 0x24
    elif index == 7:
      offset = 0x48
      length = 0x48
    elif index == 8:
      offset = 0x30
      length = 0x18
    self.stream.seek(offset)
    return self.stream.read(length)

  def get_verts(self, up="z", forward="y", sideways="x"):
    full_verts = np.fromstring(self.get_section(0), dtype=np.dtype([
      (sideways, ">f4"),
      (forward, ">f4"),
      (up, ">f4"),
      ("w", ">f4"),
    ]))
    
    verts = np.array(full_verts[[sideways, forward, up]], dtype=np.dtype([
      (sideways, ">f4"),
      (forward, ">f4"),
      (up, ">f4")
    ]))

    return verts

  def get_vert_normals(self):
    packed_normals = np.fromstring(self.get_section(1), dtype=">u4")
    # unknown format
    return None

  def get_tex_coords(self):
    coords = np.fromstring(self.get_section(2), dtype=np.dtype([
      ("u", ">f4"),
      ("v", ">f4"),
    ]))
    # fix v direction
    coords["v"] = np.subtract(coords["v"], 1)
    return coords

  def get_vert_colors(self):
    return np.fromstring(self.get_section(4), dtype=">u4")

  def get_faces(self):
    return np.fromstring(self.get_section(5), dtype=">u2").reshape((-1, 3))

  def get_data(self):
    self.stream.seek(0)
    return self.stream.read()