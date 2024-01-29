from UAssetDecoder import UAssetDecoder
from UAssetEncoder import UAssetEncoder
from simplify_tree import simplify_tree, simplify_global_ucas
from extend_tree import deduce_base_name_map, \
    complete_name_map, extend_tree, obtain_import_names, invert_global_name_map
from utils import apply_function_to_dir

from os import path
from json import loads, dumps
from sys import argv

OUTPUT_COMPLETE_DATA = False


def decode_uasset(input_path, output_path, extra_params):
    parsers, name_classes, global_names = extra_params
    file_name = path.basename(input_path)[:-7]

    with open(input_path, "rb") as uasset_file:
        uasset = bytearray(uasset_file.read())

    uasset_decoder = UAssetDecoder(uasset, parsers, file_name)
    info = uasset_decoder.decode_uasset()

    if OUTPUT_COMPLETE_DATA:
        with open(output_path + "ext", "w") as output:
            output.write(dumps(info, indent=2))

    new_content = []
    for elem in info["Content"]:
        simplify_tree(elem, name_classes, global_names, file_name)
        new_content.append(elem)
    reduced_info = {"Content": new_content, "Extra": info["Extra"]}

    with open(output_path, "w") as output:
        output.write(dumps(reduced_info, indent=2))

    print(f"Decoded {path.basename(input_path)}")


def encode_uasset(input_path, output_path, extra_params):
    parsers, name_classes, global_names, global_names_inverse = extra_params
    file_name = path.basename(output_path)[:-7]

    with open(input_path, "r") as json_file:
        reduced_info = loads(json_file.read())

    base_name_map = deduce_base_name_map(reduced_info["Content"], name_classes, file_name)
    import_names = obtain_import_names(reduced_info["Extra"]["ExImports"], global_names)
    name_map = complete_name_map(base_name_map, import_names, name_classes,
                                 reduced_info["Extra"]["FileReferences"], file_name)
    extended_info = extend_tree(reduced_info, name_map, name_classes, global_names_inverse, file_name)

    if OUTPUT_COMPLETE_DATA:
        with open(output_path[:-6] + "json", "w") as output:
            output.write(dumps(extended_info, indent=2))

    uasset_encoder = UAssetEncoder(extended_info, parsers)
    data = uasset_encoder.encode_uasset()

    with open(output_path, "wb") as uasset_file:
        uasset_file.write(data)

    print(f"Encoded {path.basename(input_path)}")


def decode_global_ucas(input_path, output_path):
    with open(input_path, "rb") as global_ucas_file:
        global_ucas = bytearray(global_ucas_file.read())

    uasset_decoder = UAssetDecoder(global_ucas, {}, "")
    info = uasset_decoder.decode_global_ucas()
    reduced_info = simplify_global_ucas(info)

    with open(output_path, "w") as output:
        output.write(dumps(reduced_info, indent=2))

    print(f"Extracted global names from {path.basename(input_path)}")


def test_identity(input_path, output_path, extra_params):
    print(extra_params)

    with open(input_path, "rb") as input_file:
        input_content = bytes(input_file.read())
    with open(output_path, "rb") as output_file:
        output_content = bytes(output_file.read())

    print(f"Results for {input_path}")
    if len(input_content) == len(output_content):
        print("Lengths match")
    else:
        print("Lengths don't match")

    if input_content == output_content:
        print("Contents match")
    else:
        print("Contents don't match")


with open(path.join("paths.json"), "r", encoding="utf-8") as path_file:
    paths = loads(path_file.read())

with open("parsers.json", "r") as parsers_file:
    parsers_info = loads(parsers_file.read())

with open("name_classes.json", "r") as name_classes_file:
    name_classes_info = loads(name_classes_file.read())

if len(argv) > 1:
    mode = argv[1]
else:
    mode = "test"
    print("Missing command")

input_dir = paths["INPUT"]
edit_dir = paths["EDIT"]
output_dir = paths["OUTPUT"]
global_ucas_dir = paths["GLOBAL_UCAS"]

if mode in ["decode", "encode"]:
    with open(path.join(global_ucas_dir, "global.json"), "r") as global_names_file:
        global_names_info = loads(global_names_file.read())

if mode == "decode":
    apply_function_to_dir(input_dir, edit_dir, ".uasset", ".json", decode_uasset,
                          (parsers_info, name_classes_info, global_names_info))

    with open("name_classes.json", "w") as name_classes_file:
        name_classes_file.write(dumps(name_classes_info, indent=2))

elif mode == "encode":
    global_names_inverse_info = invert_global_name_map(global_names_info)
    apply_function_to_dir(edit_dir, output_dir, ".json", ".uasset", encode_uasset, (parsers_info,
                                                                                    name_classes_info,
                                                                                    global_names_info,
                                                                                    global_names_inverse_info))

elif mode == "decode_global_ucas":
    decode_global_ucas(path.join(global_ucas_dir, "global.ucas"), path.join(global_ucas_dir, "global.json"))

elif mode == "test":
    apply_function_to_dir(input_dir, output_dir, ".uasset", ".uasset", test_identity, ())
