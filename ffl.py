import zlib
import numpy as np
from PIL import Image
from struct import pack, unpack
from io import BytesIO
import json
import os

# add 48 for afl resh high 2 3
TEXTURE_COUNT = 317 # + 48
SHAPE_COUNT = 857 #+ 3

class FFLiResourceTexture:
  def __init__(self, stream):
    self.stream = stream
    # FFLiResourceTextureFooter:
    # 	0x0 - 0x4: Mip map offset
    # 	0x4 - 0x6: Width
    # 	0x6 - 0x8: Height
    # 	0x8: Number of mip maps
    # 	0x9: FFLiTextureFormat
    # 	0xA - 0xC: Unknown
    self.stream.seek(-0xC, 2)
    self.mipmapOffset, self.width, self.height, self.mipmaps, self.format = unpack(">IHHBBxx", self.stream.read(0xC))

  def getImage(self):
    self.stream.seek(0)
    shape = (self.height, self.width)
    # Texture formats:
    #   0 => 8 bit greyscale
    #   1 => 16 bit (8 bit greyscale with 8 bit alpha)
    #   2 => 32 bit RGBA
    if self.format == 0:
      pixels = np.fromstring(self.stream.read(self.width * self.height), dtype=np.uint8)
      pixels = np.reshape(pixels, shape)
      return Image.fromarray(pixels, "L")

    elif self.format == 1:
      data = np.fromstring(self.stream.read(self.width * self.height * 2), dtype=np.uint16)
      data = np.reshape(data, shape)
      pixels = np.right_shift(data, 8).astype(np.uint8)
      alpha = np.bitwise_and(data, 0x00FF).astype(np.uint8)
      img = Image.fromarray(pixels, "L")
      img.putalpha(Image.fromarray(alpha, "L"))
      return img

    elif self.format == 2:
      pixels = np.fromstring(self.stream.read(self.width * self.height * 4), dtype=np.uint32)
      pixels = np.reshape(pixels, shape)
      return Image.fromarray(pixels, "RGBA")

    else:
      print("unknown image format:", self.format)
      return None

class FFLiResourceShape:
  def __init__(self, stream):
    self.stream = stream
    self.offsets = np.fromstring(self.stream.read(24), dtype=">u4")
    self.lengths = np.fromstring(self.stream.read(24), dtype=">u4")
    self.vertCount = self.lengths[0] // 16
    self.faceCount = self.lengths[5] // 3

  def getSection(self, index):
    self.stream.seek(self.offsets[index])
    size = int(self.lengths[index])
    # the length of section type 5 has to be doubled but i mean that was already totaly obvious right ha ha
    if index == 5: size *= 2
    return self.stream.read(size)

  def getSection6(self):
    self.stream.seek(0x48)
    return self.stream.read(0x24)

  def getSection7(self):
    self.stream.seek(0x48)
    return self.stream.read(0x48)

  def getSection8(self):
    self.stream.seek(0x30)
    return self.stream.read(0x18)

  def getVerts(self, up="z", forward="y", sideways="x"):
    verts = np.fromstring(self.getSection(0), dtype=np.dtype([
      (sideways, ">f4"),
      (forward, ">f4"),
      (up, ">f4"),
      ("w", ">f4"),
    ]))
    return verts

  def getVertNormals(self):
    packedNormals = np.fromstring(self.getSection(1), dtype=">u4")
    normals = np.ones((len(packedNormals), 4), dtype=np.float32)
    for (index, v) in enumerate(packedNormals):
      # output in order of x, y z, w
      normals[index][0] = (v >> 20) & 0x3FF
      normals[index][1] = (v >> 10) & 0x3FF
      normals[index][2] = (v >> 0) & 0x3FF
      normals[index][3] = (v >> 30) & 0x3
    normals[:,[0,1,2]] = np.interp(normals[:,[0,1,2]], (0, 0x3FF), (-1, +1))
    return normals

  def getTexCoords(self):
    coords = np.fromstring(self.getSection(2), dtype=np.dtype([
      ("x", ">f4"),
      ("y", ">f4"),
    ]))
    # correct y direction
    coords["y"] = np.subtract(coords["y"], 1)
    return coords

  def getVertColors(self):
    return np.fromstring(self.getSection(4), dtype=">u4")

  def getFaces(self):
    return np.fromstring(self.getSection(5), dtype=">u2").reshape((-1, 3))

  def getData(self):
    self.stream.seek(0)
    return self.stream.read()

class FFLiResource:
  def __init__(self, stream):
    # Format:
    #   0x0 - 0x14: Header
    #   0x14 - 0x1410: FFLiResourceTextureHeader
    #   0x1410 - 0x49A0: FFLiResourceShapeHeader
    #   0x49A0 - ...: File data
    self.stream = stream
    # Header:
    #   0x0 - 0x4: Magic number ("FFRA")
    #   0x4 - 0x8: Version, always 0x00070000
    #   0x8 - 0xC: Unknown, 0x0000CC29 in FFLResHigh, 0x000028D1 in FFLResMiddle
    #   0xC - 0x10: Unknown, seems to grow along with the filesize
    #   			maybe total uncompressed size or something?
    #   0x10 - 0x14: Unknown, always 0?
    self.magic, self.version, self.uncompressedSize = unpack(">II4xI4x", stream.read(0x14))
    # FFLiResourceTextureHeader:
    #   0x0 - 0x2C: Maximum size for each FFLiTexturePartsType
    #   The size of the allocated buffer is determined from this value
    #   0x2C - 0x13FC: FFLiResourcePartsInfo [317]
    # 	Stores the FFLiResourcePartsInfo for each FFLiTexturePartsType
    # self.stream.seek(0x14)
    self.textureTypeSizes = np.fromstring(self.stream.read(0x2C), dtype=">u4")
    self.textureTypeCount = np.cumsum([
      3,
      132,
			62,
			24,
			12,
			12,
			9,
			2,
			37,
			6,
			18,
    ], dtype=np.uint16)
    self.textures = self.readPartsInfo(TEXTURE_COUNT)
    # FLiResourceShapeHeader:
    #   0x0 - 0x30: Maximum size for each FFLiShapePartsType
    #   The size of the allocated buffer is determined from this value
    #   0x30 - 0x3590: FFLiResourcePartsInfo [857]
    # 	Stores the FFLiResourcePartsInfo for each FFLiShapePartsType
    # self.stream.seek(0x1410)
    self.shapeTypeSizes = np.fromstring(self.stream.read(0x30), dtype=">u4")
    self.shapeTypeCount = np.cumsum([
      4,
      132,
      # 2 - placeholders + 1 head shape
      132,
      # 3 - head shapes
      12,
      # 4 - face wrapper mesh lol
      1,
      # 5 - face wraper mesh
      12,
      # 6 - planes?
      18,
      # 7 - nose mesh
      18,
      # 8 - hair (f?)
      132,
      # 9 - hair (m?)
      132,
      # 10 - forehead meshes (f?)
      132,
      # 11 - more forehead meshes (m?)
      132,
    ], dtype=np.uint16)
    self.shapes = self.readPartsInfo(SHAPE_COUNT)

  def readPartsInfo(self, count):
    # FFLiResourcePartsInfo:
    #   0x0 - 0x4: Offset
    #   0x4 - 0x8: Uncompressed size
    #   0x8 - 0xC: Compressed size
    #   0xC: Unknown
    #   0xD: FFLiResourceWindowBits
    #   0xE: Unknown
    #   0xF: Compression type (5=Uncompressed, anything else is zlib)
    dt = np.dtype([
      ("offset", ">u4"),
      ("uncompressedSize", ">u4"),
      ("compressedSize", ">u4"),
      ("unknown1", "u1"),
      ("flags", "u1"),
      ("unknown2", "u1"),
      ("compression", "u1"),
    ])
    return np.fromstring(self.stream.read(count * 16), dtype=dt)

  def getResourceCategory(self, type, index):
    l = self.shapeTypeCount if type == "shape" else self.textureTypeCount
    i = 0
    while i < len(l):
      if l[i] >= index:
        return i
      i += 1
    return None

  def getResourceData(self, type, index):
    resource = self.shapes[index] if type == "shape" else self.textures[index]
    offset = resource["offset"]
    if offset == 0:
      return None
    else:
      self.stream.seek(offset)
      data = self.stream.read(resource["uncompressedSize"])
      if resource["compression"] == 5 or resource["compression"] > 100:
        return data
      else:
        return zlib.decompress(data)

  def getTexture(self, index):
    data = self.getResourceData("texture", index)
    if not data:
      return None
    else:
      return FFLiResourceTexture(BytesIO(data))

  def getShape(self, index):
    data = self.getResourceData("shape", index)
    if not data:
      return None
    else:
      return FFLiResourceShape(BytesIO(data))
    
  @classmethod
  def parse(cls, stream):
    instance = cls(stream)
    return instance

class glbMesh:
  def __init__(self):
    self.data = bytes()
    self.json = {
      "asset": {"version": "2.0",},
      "scene": 0,
      "scenes": [{ "nodes": [0] }],
      "nodes": [{ "name": "shape", "mesh": 0 }],
      "buffers": [{ "byteLength": 0 }],
      "bufferViews": [],
      "accessors": [],
      "meshes": [{ "primitives": [{ "attributes": {}, "mode": 4 }] }]
    }

  def addBufferView(self, index, offset, length):
    self.json["bufferViews"].append({
      "buffer": index,
      "byteOffset": offset,
      "byteLength": length,
    })

  def addAccessor(self, bufferView, compontentType, count, type, min=None, max=None):
    accessor = {
      "bufferView": bufferView,
      "byteOffset": 0,
      "componentType": compontentType,
      "count": count,
      "type": type,
    }
    if min: accessor["min"] = min
    if max: accessor["min"] = max
    self.json["accessors"].append(accessor)

  def addVerts(self, verts):
    self.addBufferView(0, len(self.data), verts.nbytes)
    self.addAccessor(len(self.json["bufferViews"]) - 1, 5126, len(verts), "VEC3", min=-1000, max=1000)
    self.data += verts.tobytes()
    self.json["meshes"][0]["primitives"][0]["attributes"]["POSITION"] = len(self.json["accessors"]) - 1

  def addTexCoords(self, coords):
    self.addBufferView(0, len(self.data), coords.nbytes)
    self.addAccessor(len(self.json["bufferViews"]) - 1, 5126, len(coords), "VEC2")
    self.data += coords.tobytes()
    self.json["meshes"][0]["primitives"][0]["attributes"]["TEXCOORD_0"] = len(self.json["accessors"]) - 1

  def addNormals(self, normals):
    self.addBufferView(0, len(self.data), normals.nbytes)
    self.addAccessor(len(self.json["bufferViews"]) - 1, 5126, len(normals), "VEC3")
    self.data += normals.tobytes()
    self.json["meshes"][0]["primitives"][0]["attributes"]["NORMAL"] = len(self.json["accessors"]) - 1

  def addVertColors(self, colors):
    self.addBufferView(0, len(self.data), colors.nbytes)
    self.addAccessor(len(self.json["bufferViews"]) - 1, 5121, len(colors), "VEC4")
    self.data += colors.tobytes()
    self.json["meshes"][0]["primitives"][0]["attributes"]["COLOR_0"] = len(self.json["accessors"]) - 1

  def addFaces(self, faces):
    self.addBufferView(0, len(self.data), faces.nbytes)
    self.addAccessor(len(self.json["bufferViews"]) - 1, 5123, len(faces) * 3, "SCALAR")
    self.data += faces.tobytes()
    self.json["meshes"][0]["primitives"][0]["indices"] = len(self.json["accessors"]) - 1

  def save(self, buffer):
    self.json["buffers"][0]["byteLength"] = len(self.data)
    jsonData = json.dumps(self.json)
    jsonData += " " * (4 - len(jsonData) % 4)
    self.data += bytes((4 - len(self.data) % 4))
    # write fileheader
    buffer.write(pack("<III", 0x46546C67, 2, len(jsonData) + len(self.data) + 28))
    # write json chunk
    buffer.write(pack("<II", len(jsonData), 0x4E4F534A))
    buffer.write(jsonData.encode())
    # write data chunk
    buffer.write(pack("<II", len(self.data), 0x004E4942))
    buffer.write(self.data)


with open("./FFLResHigh.dat", "rb") as ffl:
  res = FFLiResource.parse(ffl)

  # for i in range(0, len(res.textures)):
  #   texture = res.getTexture(i)
  #   if texture:
  #     texCat = res.getResourceCategory("texture", i)
  #     texture.getImage().save("./{0}_{1}.png".format(texCat, i))

  for i in range(0, len(res.shapes)):

    shape = res.getShape(i)
    shapeCat = res.getResourceCategory("shape", i)
    if shape:
      os.makedirs("./shape/{0}".format(shapeCat), exist_ok=True)
      with open("./shape/{0}/{1}.glb".format(shapeCat, i), "wb") as glb:
        export = glbMesh()
        verts = shape.getVerts()[["x", "y", "z"]]
        texCoords = shape.getTexCoords()
        vertColors = shape.getVertColors()
        faces = shape.getFaces()
        export.addVerts(verts.byteswap())
        export.addFaces(faces.byteswap())
        if len(texCoords) > 0: export.addTexCoords(texCoords.byteswap())
        if len(vertColors) > 1: 
          print(i, shapeCat, "vertColors added")
          export.addVertColors(vertColors.byteswap())
        export.save(glb)

      # root = root = ET.Element("COLLADA", xmlns="http://www.collada.org/2005/11/COLLADASchema", version="1.4.1")
      
      # geometryLibrary = ET.SubElement(root, "library_geometries")
      # geometry = ET.SubElement(geometryLibrary, "geometry", id="shape", name="shape")
      # mesh = ET.SubElement(geometry, "mesh")

      # positionSource = ET.SubElement(mesh, "source", id="shape-positions", name="position")
      # array = ET.SubElement(positionSource, "float_array", id="shape-positions-array", count=str(shape.vertCount * 3))
      # array.text = ""
      # for vert in shape.getVerts(up="y", forward="z"):
      #   array.text += "{0:.10f} {1:.10f} {2:.10f} ".format( vert["x"], vert["y"], vert["z"] )
      # technique = ET.SubElement(positionSource, "technique_common")
      # accessor = ET.SubElement(technique, "accessor", source="#shape-positions-array", count=str(shape.vertCount), offset="0", stride="3")
      # for param in ["X", "Y", "Z"]:
      #   ET.SubElement(accessor, "param", name=param, type="float")

      # normalSource = ET.SubElement(mesh, "source", id="shape-normal", name="normal")
      # array = ET.SubElement(normalSource, "float_array", id="shape-normal-array", count=str(shape.vertCount * 3))
      # array.text = ""
      # for vert in shape.getVertNormals():
      #   array.text += "{0:.10f} {1:.10f} {2:.10f} ".format( 0, 0, 0 )
      # technique = ET.SubElement(normalSource, "technique_common")
      # accessor = ET.SubElement(technique, "accessor", source="#shape-normal-array", count=str(shape.vertCount), offset="0", stride="3")
      # for param in ["X", "Y", "Z"]:
      #   ET.SubElement(accessor, "param", name=param, type="float")

      # mapSource = ET.SubElement(mesh, "source", id="shape-map", name="map")
      # array = ET.SubElement(mapSource, "float_array", id="shape-map-array", count=str(shape.vertCount * 2))
      # array.text = ""
      # for coord in shape.getTexCoords():
      #   array.text += "{0:.10f} {1:.10f} ".format( coord["x"], coord["y"] )
      # technique = ET.SubElement(mapSource, "technique_common")
      # accessor = ET.SubElement(technique, "accessor", source="#shape-map-array", count=str(shape.vertCount), offset="0", stride="2")
      # for param in ["S", "T"]:
      #   ET.SubElement(accessor, "param", name=param, type="float")

      # vertices = ET.SubElement(mesh, "vertices", id="shape-vertices")
      # ET.SubElement(vertices, "input", semantic="POSITION", source="#shape-positions")
      # ET.SubElement(vertices, "input", semantic="NORMAL", source="#shape-normal")

      # triangles = ET.SubElement(mesh, "triangles", count=str(shape.faceCount))
      # ET.SubElement(triangles, "input", offset="0", semantic="VERTEX", source="#shape-vertices")
      # ET.SubElement(triangles, "input", offset="1", semantic="TEXCOORD", set="0", source="#shape-map")
      # p = ET.SubElement(triangles, "p")
      # p.text = ""
      # for face in shape.getFaces():
      #   p.text += "{0} {0} {1} {1} {2} {2} ".format( face[0], face[1], face[2] )

      # visualSceneLibrary = ET.SubElement(root, "library_visual_scenes")
      # visualScene = ET.SubElement(visualSceneLibrary, "visual_scene", id="scene", name="untitled")

      # node = ET.SubElement(visualScene, "node")
      # geometryInstance = ET.SubElement(node, "instance_geometry", url="#shape")

      # scene = ET.SubElement(root, "scene")
      # instance = ET.SubElement(scene, "instance_visual_scene", url="#scene")

      # tree = ET.ElementTree(root)
      # tree.write("./shape_{0}_{1}.dae".format(shapeCat, i))
    