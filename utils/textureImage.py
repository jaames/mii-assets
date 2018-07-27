# convert textures to images using the Pillow image library

import numpy as np
from PIL import Image

class textureImage:

  def __init__(self, width, height, format):
    self.shape = (height, width)
    self.format = format
    self.image = None
  
  def set_pixels(self, pixels):
    if self.format == 0:
      pixels = np.reshape(pixels, self.shape)
      self.image = Image.fromarray(pixels, "L")

    elif self.format == 1:
      pixels = np.reshape(pixels, self.shape)
      # split pixels into seperate color and alpha maps
      luma = np.right_shift(pixels, 8).astype(np.uint8)
      alpha = np.bitwise_and(pixels, 0x00FF).astype(np.uint8)
      img = Image.fromarray(luma, "L")
      img.putalpha(Image.fromarray(alpha, "L"))
      self.image = img

    elif self.format == 2:
      pixels = np.reshape(pixels, self.shape)
      self.image = Image.fromarray(pixels, "RGBA")
  
  def save(self, path):
    if self.image:
      self.image.save(path)