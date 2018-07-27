import numpy as np
from struct import unpack
from io import BytesIO
import zlib

from ffl.FFLiResourceTexture import FFLiResourceTexture
from ffl.FFLiResourceShape import FFLiResourceShape

class FFLiResource:
  def __init__(self, stream, texture_count, shape_count):
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
    #   0xC - 0x10: Total uncompressed size?
    #   0x10 - 0x14: Unknown, always 0?
    self.magic, self.version, self.uncompressed_size = unpack(">II4xI4x", stream.read(0x14))
    # FFLiResourceTextureHeader:
    #   0x0 - 0x2C: Maximum size for each FFLiTexturePartsType
    #   The size of the allocated buffer is determined from this value
    #   0x2C - 0x13FC: FFLiResourcePartsInfo [317]
    # 	Stores the FFLiResourcePartsInfo for each FFLiTexturePartsType
    self.texture_buffer_sizes = np.fromstring(self.stream.read(0x2C), dtype=">u4")
    self.textures = self.read_parts_info(texture_count)
    # FLiResourceShapeHeader:
    #   0x0 - 0x30: Maximum size for each FFLiShapePartsType
    #   The size of the allocated buffer is determined from this value
    #   0x30 - 0x3590: FFLiResourcePartsInfo [857]
    # 	Stores the FFLiResourcePartsInfo for each FFLiShapePartsType
    self.shape_buffer_sizes = np.fromstring(self.stream.read(0x30), dtype=">u4")
    self.shapes = self.read_parts_info(shape_count)

  def read_parts_info(self, count):
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
      ("uncompressed_size", ">u4"),
      ("compressed_size", ">u4"),
      ("unknown1", "u1"),
      ("flags", "u1"),
      ("unknown2", "u1"),
      ("compression", "u1"),
    ])
    return np.fromstring(self.stream.read(count * 16), dtype=dt)

  def get_resource_data(self, type, index):
    resource = self.shapes[index] if type == "shape" else self.textures[index]
    offset = resource["offset"]
    if offset == 0:
      return None
    else:
      self.stream.seek(offset)
      data = self.stream.read(resource["uncompressed_size"])
      if resource["compression"] == 5 or resource["compression"] > 100:
        return data
      else:
        return zlib.decompress(data)

  def get_texture(self, index):
    data = self.get_resource_data("texture", index)
    if not data:
      return None
    else:
      return FFLiResourceTexture(BytesIO(data))

  def get_shape(self, index):
    data = self.get_resource_data("shape", index)
    if not data:
      return None
    else:
      return FFLiResourceShape(BytesIO(data))

  @classmethod
  def parse(cls, stream, texture_count, shape_count):
    return cls(stream, texture_count, shape_count)