Nintendo's Face Library is responsible for rendering Mii characters across numerous games and devices. This project's goal is to reverse-engineer it and provide utilities for extracting the assets that it uses. Long-term, I'd like to be able to accurately render Miis for ourselves.

Credits:
 - **Jaames** - Python implementation and texture/model data
 - **[Kinnay](https://github.com/Kinnay)** - reverse-engineering resource archive format

#### fflExtract Usage

This utility can extract textures and 3D models from Face Library asset archives -- textures are converted to `.png` images and models are converted to binary [glTF](https://en.wikipedia.org/wiki/GlTF) (`.glb`) models. 

(Protip! You can import .glb files into Blender with [this plugin](https://github.com/ksons/gltf-blender-importer)).

Requirements:

 - Python 3 (tested with 3.7.0)
 - [numpy](http://www.numpy.org/)
 - [Pillow](https://pillow.readthedocs.io/en/latest/)

At the moment, Face Library asset archives from Miitomo can still be downloaded from its asset CDN:
 - [`AFLResHigh.dat`](http://download-cdn.miitomo.com/native/20180125111639/android/v2/asset_model_character_mii_AFLResHigh_dat.zip)
 - [`AFLResHigh_2_3.dat`](http://download-cdn.miitomo.com/native/20180125111639/android/v2/asset_model_character_mii_AFLResHigh_2_3_dat.zip)

Usage:

```bash
python3 fflExtract.py -i <face library archive> <tex count> <mesh count> -t <tex output dir> -m <mesh output dir>
```

`tex count` and `mesh count` depend on the file you're extracting:

* `FFLResHigh`, `FFLResMiddle` (Wii U): 317 textures and 857 meshes
* `AFLResHigh` (Miitomo):317 textures and 857 meshes
* `AFLResHigh_2_3` (Miitomo): 365 textures and 900 meshes (not confirmed)