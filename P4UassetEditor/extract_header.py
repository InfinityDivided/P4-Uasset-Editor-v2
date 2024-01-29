from json import loads
from sys import argv
from struct import unpack
from os import walk, path


def append_header(data, headers):  # Janky .json formatting
    to_append = "[\n  {\n"
    count = 0
    for header in headers:
        to_append += f'    "DataOffset": {header[1]},\n    "Header{count}": "!ENCODE UTF8 {header[0]}",\n'
        count += 1
    to_append = to_append[:-2]
    to_append += "\n  },\n"

    return to_append + data[2:]


def extract_header(uasset_path, data_path):
    with open(data_path, "r", encoding="utf-8") as data_file:
        initial_data = data_file.read()

    if "Header0" in initial_data[:100]:
        print(f"{path.basename(data_path)} already contains header information, skipped")
        return

    with open(uasset_path, "rb") as uasset_file:
        uasset = bytearray(uasset_file.read())

    # Obtained this information from https://github.com/gitMenv/UEcastoc/blob/master/CasTocFormats.md
    nm_offset = unpack("I", uasset[24:28])[0] + 1
    nm_size = unpack("I", uasset[28:32])[0]

    name_map = uasset[nm_offset:nm_offset + nm_size]
    length = name_map[0]
    extra_offset = 1
    headers = []

    while length > 0:
        headers.append((name_map[extra_offset:length + extra_offset].decode(), nm_offset + extra_offset))
        extra_offset += length + 2
        if extra_offset <= nm_size:
            length = name_map[extra_offset - 1]
        else:
            break

    extended_data = append_header(initial_data, headers)
    with open(data_path, "w") as output:
        output.write(extended_data)
        print(f"{path.basename(data_path)} was extended with {path.basename(uasset_path)}'s headers")


def extract_headers_dir(input_dir_path):
    for root, dirs, files in walk(input_dir_path):
        uasset_names = [file[:-7] for file in files if file.endswith(".uasset")]
        json_names = [file[:-5] for file in files if file.endswith(".json")]

        matches = set(uasset_names).intersection(json_names)

        for match in matches:
            extract_header(path.join(root, match + ".uasset"),
                           path.join(root, match + ".json"))


if len(argv) > 1:  # Old method
    u_path = argv[1]  # .uasset file
    d_path = argv[2]    # .json file

    extract_header(u_path, d_path)

else:  # New method
    with open(path.join("paths.json"), "r", encoding="utf-8") as path_file:
        paths = loads(path_file.read())

        input_dir = paths["INPUT"]

    extract_headers_dir(input_dir)
