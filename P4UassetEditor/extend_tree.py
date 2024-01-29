from cityhash import CityHash64

from constants import RESERVED_NAMES, SPECIAL_STRUCT_NAMES, NON_ASCII_STRING, ALGORITHM_ID


# TODO: Same things as in simplify_tree.py

def deduce_base_name_map(info, name_classes, file_name):
    ret = set()
    if isinstance(info, dict):
        for name in info:
            ret.add(name)
            if name in ["UnknownImport", "UnknownValues"] or name in name_classes and (
                    output_class_info(name_classes, name, "Class", file_name) in ["StrProperty"] or (
                    output_class_info(name_classes, name, "Class", file_name) == "StructProperty" and
                    output_class_info(name_classes, name, "StructClass", file_name) == "Guid")):
                continue
            ret = ret.union(deduce_base_name_map(info[name], name_classes, file_name))

    elif isinstance(info, list):
        for elem in info:
            ret = ret.union(deduce_base_name_map(elem, name_classes, file_name))

    elif isinstance(info, str):
        if not info.lstrip('-').isdigit():
            ret.add(info)

    # There aren't any names to add otherwise

    return ret


def obtain_import_names(import_map, global_names):
    import_names = set()
    for obj_id in import_map:
        if str(obj_id) in global_names:
            import_names.add(global_names[str(obj_id)][0])
    return import_names


def complete_name_map(name_map, import_names, name_classes, file_references, file_name):
    class_names = set()
    sub_names = set()
    pre_names = set()
    bad_names = set()
    for name in name_map:
        if "!!" in name:
            pre_names.add(name.split("!!")[0])
            bad_names.add(name)
        if "??" in name:
            pre_names.add(name.split("??")[0])
            bad_names.add(name)
        if name.startswith("InternalRef"):
            bad_names.add(name)

    name_map = name_map.difference(bad_names)
    name_map = name_map.union(pre_names)

    for name in name_map:
        if "." in name and "'" not in name:  # Wacky rule, probably doesn't hold in general
            sub_names.add(name.split(".")[0])
        if "::" in name:  # Wacky rule, probably doesn't hold in general
            sub_names.add(name.split("::")[0])

        if name in name_classes:
            if file_name not in name_classes[name]:
                file_name = "Default"
            for class_key in name_classes[name][file_name]:
                if isinstance(name_classes[name][file_name][class_key], str):
                    class_names.add(name_classes[name][file_name][class_key])

    name_map = name_map.union(sub_names)
    name_map = name_map.union(import_names)
    name_map = name_map.union(class_names)

    name_map = name_map.union({"/Script/CoreUObject",
                               "Class",
                               "Package",
                               "None"})
    name_map = name_map.union(set(file_references))

    name_map = name_map.difference(RESERVED_NAMES)
    return sorted(list(name_map), key=str.casefold)


def get_primitive_length(class_name):
    return {"BoolProperty": 0,
            "ByteProperty": 1,
            "UInt16Property": 2,
            "IntProperty": 4,
            "UInt32Property": 4,
            "UInt64Property": 8,
            "FloatProperty": 4,
            "NameProperty": 8,
            "EnumProperty": 4,
            "WeirdByteProperty": 8,
            "SoftObjectProperty": 12,
            "Vector2D": 8,
            "Vector": 12,
            "Vector4": 16,
            "Quat": 16,
            "Color": 4,
            "LinearColor": 16,
            "Rotator": 12,
            "SoftObjectPath":  12,
            "Guid": 16,
            "SetProperty": 0,
            "MulticastSparseDelegateProperty": 0}[class_name]


def get_city_hash(name):
    if name.isascii():
        return CityHash64(name.lower())
    else:
        return CityHash64(name.encode("utf-16le"))


def extend_tree(reduced_info, name_map, name_classes, global_names_inverse, file_name):
    # Jank precaution until I completely figure out imports, extra names shouldn't crash the game
    name_map = sorted(list(set(name_map).union(set(reduced_info["Extra"]["ExNameMap"]))), key=str.casefold)

    # Debug
    # name_map = reduced_info["Extra"]["ExNameMap"]

    # TODO: Do something to decode the dependency graph, maybe modify the UCAS/UTOC packer

    lengths = [len(name) for name in name_map]
    name_flags = [(not name.isascii()) * NON_ASCII_STRING for name in name_map]

    name_info = {"Names": name_map,
                 "Lengths": lengths,
                 "NameFlags": name_flags}

    headers = {"InitialHeader": reduced_info["Extra"]["ExInitialHeader"],
               "NameMap": name_info,
               "NameMapHashes": {"AlgorithmID": ALGORITHM_ID}}  # Seems to always be that number

    headers["NameMapHashes"]["Hashes"] = [get_city_hash(name) for name in name_map]

    new_name_map_size = 0
    for name in name_map:
        new_name_map_size += 2
        if name.isascii():
            new_name_map_size += len(name)
        else:
            if new_name_map_size % 2 == 1:
                new_name_map_size += 1
            new_name_map_size += 2 * len(name)
    padding = (8 - new_name_map_size) % 8

    ex_name_map_hashes_size = headers["InitialHeader"]["NameMapHashesSize"]
    new_name_map_hashes_size = 8 * (len(name_map) + 1)

    ex_name_map_hashes_offset = headers["InitialHeader"]["NameMapHashesOffset"]
    new_name_map_hashes_offset = padding + new_name_map_size + 64  # 64 bytes from the initial header
    offset_diff = new_name_map_hashes_offset - ex_name_map_hashes_offset

    total_diff = offset_diff + (new_name_map_hashes_size - ex_name_map_hashes_size)
    headers["InitialHeader"]["NameMapSize"] = new_name_map_size
    headers["InitialHeader"]["NameMapHashesOffset"] = new_name_map_hashes_offset
    headers["InitialHeader"]["NameMapHashesSize"] = new_name_map_hashes_size
    headers["InitialHeader"]["ImportMapOffset"] += total_diff
    headers["InitialHeader"]["ExportMapOffset"] += total_diff
    headers["InitialHeader"]["ExportBundlesOffset"] += total_diff
    headers["InitialHeader"]["GraphDataOffset"] += total_diff

    headers["ImportMap"] = reduced_info["Extra"]["ExImports"]  # Doesn't change anything for now
    headers["ExportMap"] = reduced_info["Extra"]["ExExports"]

    new_content = []
    for elem in reduced_info["Content"]:
        if "Rows" in elem:
            extend_tree_row_struct(elem, name_classes, global_names_inverse, file_name)
        elif "TrueIndex" in elem:
            extend_tree_blueprint(elem, name_classes, global_names_inverse, file_name)
        elif "Null" in elem:
            pass
        else:
            extend_tree_branch(elem, name_classes, global_names_inverse, file_name)
        new_content.append(elem)

    extended_info = {"Headers": headers,
                     "Content": new_content,
                     "Extra": reduced_info["Extra"]}

    return extended_info


def invert_global_name_map(global_names):
    global_names_inverse = {}
    for obj_id in global_names:
        name = global_names[obj_id][0]
        path_id = str(global_names[obj_id][1])
        path = global_names[path_id][0]
        global_names_inverse[(name, path)] = obj_id

    return global_names_inverse


def output_class_info(name_classes, name, class_param, file_name):
    if file_name not in name_classes[name] or class_param not in name_classes[name][file_name]:
        return name_classes[name]["Default"][class_param]
    elif "Annoying" in name_classes[name][file_name] and class_param in ["Class", "StructClass"]:
        return "Annoying" + name_classes[name][file_name][class_param]
    else:
        return name_classes[name][file_name][class_param]


def extend_tree_branch(tree, name_classes, global_names_inverse, file_name):
    for name in tree:
        class_name = output_class_info(name_classes, name, "Class", file_name)

        # Hack due to unforeseen ambiguous classes
        if class_name.startswith("Annoying"):
            if isinstance(tree[name], dict) and "Class" in tree[name]:
                continue
            else:
                class_name = class_name[len("Annoying"):]
        length = 0

        if class_name == "StructProperty":
            struct_class = output_class_info(name_classes, name, "StructClass", file_name)

            if struct_class.startswith("Annoying"):
                if isinstance(tree[name], dict) and "Class" in tree[name]:
                    continue
                else:
                    struct_class = struct_class[len("Annoying"):]

            if struct_class not in SPECIAL_STRUCT_NAMES:
                content = {"StructContent": extend_tree_branch(tree[name], name_classes,
                                                               global_names_inverse, file_name)}
            else:
                content = tree[name]
                length = get_primitive_length(struct_class)
            content.update({"StructClass": struct_class})

        elif class_name == "ArrayProperty":
            array_inner_class = output_class_info(name_classes, name, "ArrayInnerClass", file_name)
            array_content = []

            content = {"ArrayInnerClass": array_inner_class,
                       "ArrayLength": len(tree[name])}

            if array_inner_class == "StructProperty":
                struct_in_array_struct_class = output_class_info(name_classes, name, "StructInArrayStructClass", file_name)

                content["StructInArrayName"] = output_class_info(name_classes, name, "StructInArrayName", file_name)
                content["StructInArrayClass"] = output_class_info(name_classes, name, "StructInArrayClass", file_name)
                content["StructInArrayLength"] = 0  # The game doesn't seem to care
                content["StructInArrayStructClass"] = struct_in_array_struct_class

                if struct_in_array_struct_class not in SPECIAL_STRUCT_NAMES:
                    for elem in tree[name]:
                        array_content.append({"StructContent": extend_tree_branch(elem,
                                                                                  name_classes,
                                                                                  global_names_inverse,
                                                                                  file_name)})
                else:
                    for elem in tree[name]:
                        array_content.append(elem)

            else:
                for elem in tree[name]:
                    array_content.append(elem)

            content["ArrayContent"] = array_content

        elif class_name == "MapProperty":
            map_from_class = output_class_info(name_classes, name, "MapFromClass", file_name)
            map_to_class = output_class_info(name_classes, name, "MapToClass", file_name)

            map_content = tree[name]
            if map_to_class == "StructProperty":
                for elem in map_content:
                    new_map_to = extend_tree_branch(elem["MapTo"]["StructContent"], name_classes, global_names_inverse, file_name)
                    elem["MapTo"]["StructContent"] = new_map_to

            content = {"MapFromClass": map_from_class,
                       "MapToClass": map_to_class,
                       "MapLength": len(tree[name]),
                       "MapContent": map_content}

        elif class_name == "EnumProperty":
            length = 8
            enum_value = tree[name]
            content = {"EnumClass": output_class_info(name_classes, name, "EnumClass", file_name),
                       "EnumValue": enum_value}

        elif class_name == "ObjectProperty":
            length = 4
            if tree[name] == "Null":
                content = 0
            elif "UnknownImport" in tree[name]:
                content = int(tree[name]["UnknownImport"])
            elif "InternalRef" in tree[name]:
                content = tree[name]["InternalRef"]
            else:
                obj_name = tree[name]["ObjectName"]
                obj_path = tree[name]["ObjectPath"]
                content = int(global_names_inverse[obj_name, obj_path])

        elif class_name == "StrProperty":
            string_content = tree[name]
            length = 4  # Just the length of the StringLength field
            if string_content == "":
                string_length = 0
            elif string_content.isascii():
                string_length = len(string_content) + 1  # Includes null terminator
                length += string_length
            else:  # UTF-16 LE encoding
                string_length = -len(string_content) - 1  # Negative in this case
                length -= 2 * string_length

            content = {"StringLength": string_length,
                       "StringContent": string_content}

        else:
            content = tree[name]
            length = get_primitive_length(class_name)

        tree[name] = {"Class": class_name,
                      "Length": length,
                      "Content": content}
    return tree


def extend_tree_row_struct(tree, name_classes, global_names_inverse, file_name):
    tree.update({"RowCount": len(tree["Rows"])})
    for row in tree["Rows"]:
        extend_tree_branch(tree["Rows"][row], name_classes, global_names_inverse, file_name)

    return tree


def extend_tree_blueprint(tree, name_classes, global_names_inverse, file_name):
    extend_tree_branch(tree["Properties"], name_classes, global_names_inverse, file_name)
