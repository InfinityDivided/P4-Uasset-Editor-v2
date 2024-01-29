# P4-Uasset-Editor-v2

Pikmin 4 .uasset data editor

If there are any issues, contact .infinitydivided on Discord.


Requirements:

- Python 3.7 or later
- Python "cityhash" package (see https://packaging.python.org/en/latest/tutorials/installing-packages/ for installing packages)


Initial setup:

1. Place a copy of the global.ucas file of Pikmin 4 in its corresponding folder (_GLOBAL_UCAS by default, can be changed by editing P4UassetEditor/paths.json)
   This file can be produced by any RomFS dump of the game.

2. Run generate_global_names.bat (or run "python main.py decode_global_ucas" in a terminal in the P4UassetEditor folder)


How to use:

1. Use any method to obtain the .uasset files you want to edit, for example:

a) In FModel, navigate to the folder or .uasset file you want to modify, then right click it and select "Export Raw Data (.uasset)"

b) In the Pikmin 4 UCAS UTOC Packing tool, copy and paste the folder or files you want to modify from the UNPACKOUTPUT folder

2. Move the obtained folder or files to the input folder (_INPUT by defualt)

3. Run decode.bat (or run "python main.py decode" in a terminal in the P4UassetEditor folder)

3. Edit the .json files (this can be done with most text editors) found in the editing folder (_EDIT by defualt)

5. Run encode.bat (or run "python main.py encode" in a terminal in the P4UassetEditor folder)

6. The directory structure of the edit folder will be copied into the output folder (_OUTPUT by default) with the corresponding .uasset files


IMPORTANT: Currently only these types of files are supported:

- ActorPlacementInfoAsset (these have names that start with "AP")
- DataTable (these have names that start with "DT")
- BlueprintGeneratedClass (these have names that start with "G", partially supported)

For the BlueprintGeneratedClass file, only those found in these directories were tested:
- Carrot4/Content/Carrot4/Placeables/Teki
- Carrot4/Content/Carrot4/Placeables/Pikmin
- Carrot4/Content/Carrot4/Placeables/Objects/Otakara


Special thanks to the authors of these resources:

UAsset Header Format: https://github.com/gitMenv/UEcastoc/blob/master/CasTocFormats.md
UAsset UExp Format: https://wiki.xentax.com/index.php/Unreal_Engine_4_UASSET_UEXP


