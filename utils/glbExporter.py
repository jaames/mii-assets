# quick and messy glb exporter -- only supports a single mesh / node / scene per file
# glb format spec: https://github.com/KhronosGroup/glTF/blob/master/specification/2.0/README.md#glb-file-format-specification

import numpy as np
from struct import pack
import json

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

  def add_accessor(self, buffer_view, compontent_type, count, type, min=None, max=None):
    accessor = {
      "bufferView": buffer_view,
      "byteOffset": 0,
      "componentType": compontent_type,
      "count": count,
      "type": type,
    }
    if min: accessor["min"] = min
    if max: accessor["min"] = max
    self.json["accessors"].append(accessor)

  def add_verts(self, verts, min=-1000, max=100):
    self.add_buffer_view(0, len(self.data), verts.nbytes)
    self.add_accessor(
      len(self.json["bufferViews"]) - 1, 
      5126, 
      len(verts), 
      "VEC3", 
      min=min, 
      max=max
    )
    self.data += verts.tobytes()
    self.primitive["attributes"]["POSITION"] = len(self.json["accessors"]) - 1

  def add_tex_coords(self, coords):
    self.add_buffer_view(0, len(self.data), coords.nbytes)
    self.add_accessor(
      len(self.json["bufferViews"]) - 1, 
      5126, 
      len(coords),
        "VEC2"
    )
    self.data += coords.tobytes()
    self.primitive["attributes"]["TEXCOORD_0"] = len(self.json["accessors"]) - 1

  def add_normals(self, normals):
    self.add_buffer_view(0, len(self.data), normals.nbytes)
    self.add_accessor(
      len(self.json["bufferViews"]) - 1,
      5126,
      len(normals),"VEC3"
    )
    self.data += normals.tobytes()
    self.primitive["attributes"]["NORMAL"] = len(self.json["accessors"]) - 1

  def add_vert_colors(self, colors):
    self.add_buffer_view(0, len(self.data), colors.nbytes)
    self.add_accessor(
      len(self.json["bufferViews"]) - 1,
      5121,
      len(colors),
      "VEC4"
    )
    self.data += colors.tobytes()
    self.primitive["attributes"]["COLOR_0"] = len(self.json["accessors"]) - 1

  def add_faces(self, faces):
    self.add_buffer_view(0, len(self.data), faces.nbytes)
    self.add_accessor(
      len(self.json["bufferViews"]) - 1,
      5123,
      len(faces) * 3,
      "SCALAR"
    )
    self.data += faces.tobytes()
    self.primitive["indices"] = len(self.json["accessors"]) - 1

  def save(self, path):
    with open(path, "wb") as f:
      self.json["buffers"][0]["byteLength"] = len(self.data)
      json_data = json.dumps(self.json)
      # pad json data with spaces
      json_data += " " * (4 - len(json_data) % 4)
      # pad binary data with null bytes
      self.data += bytes((4 - len(self.data) % 4))
      # write fileheader
      f.write(pack("<III", 0x46546C67, 2, len(json_data) + len(self.data) + 28))
      # write json chunk
      f.write(pack("<II", len(json_data), 0x4E4F534A))
      f.write(json_data.encode())
      # write data chunk
      f.write(pack("<II", len(self.data), 0x004E4942))
      f.write(self.data)