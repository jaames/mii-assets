# TODO: mipmaps

import numpy as np
from struct import unpack

class FFLiResourceTexture:
  def __init__(self, stream):
    self.stream = stream
    # FFLiResourceTextureFooter:
    # 	0x0 - 0x4: Mipmap offset
    # 	0x4 - 0x6: Width
    # 	0x6 - 0x8: Height
    # 	0x8: Number of mipmaps
    # 	0x9: FFLiTextureFormat
    # 	0xA - 0xC: Unknown
    self.stream.seek(-0xC, 2)
    self.mipmap_offset, self.width, self.height, self.mipmaps, self.format = unpack(">IHHBBxx", self.stream.read(0xC))

  def get_pixels(self):
    self.stream.seek(0)
    shape = (self.height, self.width)
    # Texture formats:
    #   0 => 8 bit greyscale
    #   1 => 16 bit (8 bit greyscale with 8 bit alpha)
    #   2 => 32 bit RGBA
    if self.format == 0:
      return np.fromstring(self.stream.read(self.width * self.height), dtype=np.uint8)

    elif self.format == 1:
      return np.fromstring(self.stream.read(self.width * self.height * 2), dtype=np.uint16)

    elif self.format == 2:
      return np.fromstring(self.stream.read(self.width * self.height * 4), dtype=np.uint32)

    else:
      print("unknown image format:", self.format)
      return None
