# quick and messy glb exporter -- only supports a single mesh / node / scene per file
# glb format spec: https://github.com/KhronosGroup/glTF/blob/master/specification/2.0/README.md#glb-file-format-specification

import numpy as np
from struct import pack
import json

class NpEncoder(json.JSONEncoder):
  def default(self, obj):
      if isinstance(obj, np.integer):
          return int(obj)
      elif isinstance(obj, np.floating):
          return float(obj)
      elif isinstance(obj, np.ndarray):
          return obj.tolist()
      else:
          return super(NpEncoder, self).default(obj)

class glbExporter:
  def __init__(self):
    self.data = bytes()
    self.json = {
      "asset": {"version": "2.0", },
      "scene": 0,
      "scenes": [{"nodes": [0]}],
      "nodes": [{"name": "shape", "mesh": 0}],
      "buffers": [{"byteLength": 0}],
      "bufferViews": [],
      "accessors": [],
      "meshes": [{"primitives": [{"attributes": {}, "mode": 4}]}]
    }
    self.primitive = self.json["meshes"][0]["primitives"][0]

  def add_buffer_view(self, index, offset, length):
    self.json["bufferViews"].append({
      "buffer": index,
      "byteOffset": offset,
      "byteLength": length,
    })

  def add_accessor(self, buffer_view, compontent_type, count, type, min=None, max=None, normalized=False):
    accessor = {
      "bufferView": buffer_view,
      "byteOffset": 0,
      "componentType": compontent_type,
      "count": count,
      "type": type,
    }
    if min: accessor["min"] = min
    if max: accessor["max"] = max
    if normalized: accessor["normalized"] = normalized
    self.json["accessors"].append(accessor)

  def add_verts(self, verts):
    if len(verts) == 0:
      return

    self.add_buffer_view(0, len(self.data), len(verts)*12)
    self.add_accessor(
      len(self.json["bufferViews"]) - 1, 
      5126, 
      len(verts),
      "VEC3", 
      min=[verts['x'].min(), verts['y'].min(), verts['z'].min()],
      max=[verts['x'].max(), verts['y'].max(), verts['z'].max()]
    )
    self.data += verts.byteswap().tobytes()
    self.primitive["attributes"]["POSITION"] = len(self.json["accessors"]) - 1

  def add_tex_coords(self, coords):
    if len(coords) == 0:
      return

    self.add_buffer_view(0, len(self.data), len(coords)*8)
    self.add_accessor(
      len(self.json["bufferViews"]) - 1, 
      5126, 
      len(coords),
      "VEC2"
    )
    self.data += coords.byteswap().tobytes()
    self.primitive["attributes"]["TEXCOORD_0"] = len(self.json["accessors"]) - 1

  def add_normals(self, normals):
    if len(normals) == 0:
      return

    self.add_buffer_view(0, len(self.data), len(normals)*12)
    self.add_accessor(
      len(self.json["bufferViews"]) - 1,
      5126,
      len(normals),
      "VEC3"
    )
    self.data += normals.byteswap().tobytes()
    self.primitive["attributes"]["NORMAL"] = len(self.json["accessors"]) - 1

  def add_vert_colors(self, colors):
    if len(colors) == 0:
      return

    self.add_buffer_view(0, len(self.data), len(colors)*4)
    self.add_accessor(
      len(self.json["bufferViews"]) - 1,
      5121,
      len(colors),
      "VEC4",
      normalized=True
    )
    self.data += colors.byteswap().tobytes()
    self.primitive["attributes"]["COLOR_0"] = len(self.json["accessors"]) - 1

  def add_faces(self, faces):
    if len(faces) == 0:
      return

    self.add_buffer_view(0, len(self.data), faces.nbytes)
    self.add_accessor(
      len(self.json["bufferViews"]) - 1,
      5123,
      len(faces) * 3,
      "SCALAR",
      min=[faces.min()],
      max=[faces.max()]
    )
    self.data += faces.byteswap().tobytes()
    self.primitive["indices"] = len(self.json["accessors"]) - 1

  def save(self, path):
    with open(path, "wb") as f:
      self.json["buffers"][0]["byteLength"] = len(self.data)
      json_data = json.dumps(self.json, cls=NpEncoder)
      # pad json data with spaces
      json_data += " " * (4 - len(json_data) % 4 if len(json_data) % 4 > 0 else 0)
      # pad binary data with null bytes
      self.data += bytes((4 - len(self.data) % 4) if len(self.data) % 4 > 0 else 0)

      # write fileheader
      f.write(pack("<III", 0x46546C67, 2, len(json_data) + len(self.data) + 28))
      # write json chunk
      f.write(pack("<II", len(json_data), 0x4E4F534A))
      f.write(json_data.encode())
      # write data chunk
      f.write(pack("<II", len(self.data), 0x004E4942))
      f.write(self.data)