from ffl.FFLiResource import FFLiResource
from utils.glbExporter import glbExporter
from utils.textureImage import textureImage
import sys
import os

VERSION = "1.0.0"

def print_help():
  print("\n".join([
    "",
    "===========================",
    "fflExtract.py version " + str(VERSION),
    "===========================",
    "Extract resource files used by Nintendo's Mii Face Library",
    "By Jaames (github.com/jaames)",
    "FFL archive structure reverse-engineered by Kinnay (https://github.com/Kinnay)",
    "",
    "Usage:",
    "======",
    "Extract meshes and textures (refer to docs for texture_count and mesh_count):",
    "python3 ffl.py -i <input resource file> <texture count> <mesh count> -m <mesh output path> -t <texture output path>",
    "",
    "Issues:",
    "=======",
    "If you find any bugs in this script, please report them here:",
    "https://github.com/jaames/mii/issues",
    ""
  ]))


if __name__ == "__main__":

  args = sys.argv[1::]
  argIndex = 0

  if "-v" in args:
    print(VERSION)
    sys.exit()

  if "-h" in args:
    print_help()
    sys.exit()

  if "-i" not in args:
    print("Error: no input file specified")
    print_help()
    sys.exit()

  resource_path = False
  texture_count = False
  shape_count = False
  shape_export_dir = False
  texture_export_dir = False

  while argIndex < len(args):
    arg = args[argIndex]

    if arg == "-i":
      resource_path = args[argIndex + 1]
      texture_count = int(args[argIndex + 2])
      shape_count = int(args[argIndex + 3])
      argIndex += 4

    elif arg == "-m":
      shape_export_dir = args[argIndex + 1]
      argIndex += 2

    elif arg == "-t":
      texture_export_dir = args[argIndex + 1]
      argIndex += 2
    
    else:
      print("Unrecognised arg:", arg)
      sys.exit()

  if all([resource_path, texture_count, shape_count]) and any([shape_export_dir, texture_export_dir]):
    with open(resource_path, "rb") as ffl:
      res = FFLiResource.parse(ffl, texture_count, shape_count)

      # extract meshes
      if shape_export_dir:
        print("Extracting meshes...")
        os.makedirs(shape_export_dir, exist_ok=True)
        for index in range(len(res.shapes)):
          shape = res.get_shape(index)
          if shape:
            shape_path = os.path.join(shape_export_dir, "shape_{index}.glb".format(index=index))
            glb = glbExporter()
            verts = shape.get_verts()[["x", "y", "z"]]
            uvs = shape.get_tex_coords()
            colors = shape.get_vert_colors()
            faces = shape.get_faces()
            glb.add_verts(verts.byteswap())
            glb.add_faces(faces.byteswap())
            if len(uvs) > 0:
              glb.add_tex_coords(uvs.byteswap())
            if len(colors) > 1:
              glb.add_vert_colors(colors.byteswap())
            glb.save(shape_path)
        print("Done!")

      # extract textures
      if texture_export_dir:
        print("Extracting textures...")
        os.makedirs(texture_export_dir, exist_ok=True)
        for index in range(len(res.textures)):
          texture = res.get_texture(index)
          if texture:
            texture_path = os.path.join(texture_export_dir, "tex_{index}.png".format(index=index))
            image = textureImage(texture.width, texture.height, texture.format)
            image.set_pixels(texture.get_pixels())
            image.save(texture_path)
        print("Done!")