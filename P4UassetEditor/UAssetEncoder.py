from struct import pack

from UAssetTranscoder import UAssetTranscoder

from constants import *


# TODO: How about rewriting this so we don't spam self.value, maybe flatten the syntax tree and use that instead

class UAssetEncoder(UAssetTranscoder):
    def __init__(self, data, parsers):
        super().__init__(data, parsers)
        self.value = data

    def encode_uasset(self):
        ret = bytearray([])
        self.value = self.data["Headers"]["InitialHeader"]
        ret += self.apply_parser("UAssetInitialHeader")
        self.value = self.data["Headers"]["NameMap"]
        ret += self.transcode_name_map()

        while len(ret) % 8 != 0:
            ret += bytearray([0])

        self.value = self.data["Headers"]["NameMapHashes"]["AlgorithmID"]
        ret += self.transcode_uint64()

        for name_hash in self.data["Headers"]["NameMapHashes"]["Hashes"]:
            self.value = name_hash
            ret += self.transcode_uint64()

        self.import_map = self.data["Headers"]["ImportMap"]
        for obj_import in self.import_map:
            self.value = obj_import
            ret += self.transcode_int64()

        export_map = self.data["Headers"]["ExportMap"]
        for obj_export in export_map:
            self.value = obj_export
            ret += self.apply_parser("ExportObject")

        ret += bytearray.fromhex(self.data["Extra"]["BlobOfData"])

        mode = "Normal"
        if "RowStruct" in self.name_map:
            mode = "DataTable"
        elif "BlueprintGeneratedClass" in self.name_map:
            mode = "Blueprint"

        content = self.data["Content"]

        # Alright, I need better ideas for this
        # TODO: Research the seemingly inconsistent structures so I can write a better parser

        if mode == "Normal":
            self.value = content[0]
            ret += self.transcode_name_iteration()
            ret += bytearray([0] * 4)

        elif mode == "DataTable":
            self.value = content[0]
            ret += self.transcode_name_iteration()
            ret += bytearray([0] * 4)
            row_count = content[1]["RowCount"]
            rows = content[1]["Rows"]
            self.value = row_count
            ret += self.transcode_uint32()
            for row in rows:
                self.value = row
                ret += self.transcode_name()
                self.value = rows[row]
                ret += self.transcode_name_iteration()

        elif mode == "Blueprint":
            for elem in content:
                if elem == "Null":
                    del ret[-4:]
                    ret += self.transcode_none()
                    ret += bytearray([0] * 8)
                    break

                component = elem["Properties"]
                true_index = elem["TrueIndex"]

                self.value = component
                ret += self.transcode_name_iteration()

                class_type = export_map[true_index]["ClassIndex"]
                if class_type in [BLUEPRINT_GENERATED_CLASS, FUNCTION]:
                    ret += bytearray([0] * 4)
                    self.value = elem["SuperStruct"]
                    ret += self.transcode_import()
                    self.value = elem["Children"]
                    ret += self.transcode_children()
                    self.value = elem["ChildProperties"]
                    ret += self.transcode_child_properties()
                    if class_type == FUNCTION:
                        self.value = elem["UnknownUINT32"]
                        ret += self.transcode_uint32()
                        self.value = elem["UnknownValuesLength"]
                        ret += self.transcode_uint32()
                        ret += bytearray.fromhex(elem["UnknownValues"])
                        self.value = elem["FunctionFlags"]
                        ret += self.transcode_uint64()
                        ret += bytearray([0] * 4)
                    elif class_type == BLUEPRINT_GENERATED_CLASS:
                        ret += bytearray([0] * 8)
                        self.value = elem["FuncMap"]
                        ret += self.transcode_func_map()
                        self.value = elem["ClassFlags"]
                        ret += self.transcode_uint32()
                        self.value = elem["ClassWithin"]
                        ret += self.transcode_import()
                        self.value = elem["ClassConfigName"]
                        ret += self.transcode_name()
                        ret += bytearray([0] * 12)
                        ret += self.transcode_none()
                        self.value = elem["bCooked"]
                        ret += self.transcode_bool()
                        ret += bytearray([0] * 3)
                        self.value = elem["ClassDefaultObject"]
                        ret += self.transcode_import()
                else:
                    ret += bytearray([0] * 4)

                    if export_map[true_index]["ClassIndex"] in [CIRCLE_SHADOW_MESH_COMPONENT,
                                                                CARROT_STATIC_MESH_COMPONENT,
                                                                STATIC_COLLISION_COMPONENT]:
                        ret += bytearray([0] * 4)

            del ret[-4:]

        return ret

    def transcode_primitive(self, primitive_format, length):
        return bytearray(pack(primitive_format, self.value))

    def transcode_byte(self):
        return bytearray([self.value])

    def transcode_bool(self):
        return self.transcode_byte()

    def transcode_guid(self):
        return bytearray.fromhex(self.value)

    def transcode_string_select(self):
        if self.value.isascii():
            return self.transcode_string()
        else:
            ret = self.transcode_wide_string()
            return ret + bytearray([0] * 2)

    def transcode_wide_string(self):
        return bytearray(self.value.encode("utf-16le"))

    def transcode_string(self, has_null_terminator=True):
        ret = bytearray(self.value.encode())
        if has_null_terminator and self.memory["StringLength"] != 0:
            ret += bytearray([0])
        return ret

    def transcode_name(self):
        name_weird = self.value.split("??")
        if len(name_weird) > 1:
            self.memory["WeirdIndex"] = int(name_weird[1])

        name_params = name_weird[0].split("!!")
        name_id = name_params[0]
        if name_id in SPECIAL_NAMES:
            self.special_name = name_id

        if len(name_params) > 1:
            name_index = int(name_params[1])
        else:
            name_index = 0

        ret = bytearray([])
        self.value = self.name_map[name_id]
        ret += self.transcode_uint32()
        self.value = name_index
        ret += self.transcode_uint32()
        return ret

    def transcode_import(self):
        import_id = self.value
        if import_id == 0:
            return bytearray([0] * 4)
        elif isinstance(import_id, str) and import_id.startswith("InternalRef"):
            self.value = int(import_id.split(":")[1]) + 1
        else:
            import_index = self.import_map.index(import_id)
            self.value = -import_index - 1
        return self.transcode_int32()

    def transcode_none(self):
        self.value = self.name_map["None"]
        return self.transcode_uint64()

    def transcode_name_iteration(self):
        self.memory["WeirdIndex"] = 0
        ret = bytearray([])
        name_dict = self.value
        for name in name_dict:
            self.value = name
            ret += self.transcode_name()
            class_name = name_dict[name]["Class"]
            self.value = class_name

            # Undo what we did
            if class_name == "WeirdByteProperty":
                self.value = "ByteProperty"

            ret += self.transcode_name()
            length = name_dict[name]["Length"]
            weird_index = self.memory["WeirdIndex"]
            self.value = name_dict[name]["Content"]
            content = self.apply_parser(class_name)

            if length == 0 and class_name != "BoolProperty":
                length = self.memory["TrueLength"]

            self.value = length
            ret += self.transcode_uint32()
            self.value = weird_index
            ret += self.transcode_uint32()
            ret += content
        ret += self.transcode_none()
        self.memory["WeirdIndex"] = 0

        return ret

    def transcode_name_map(self):
        ret = bytearray([])
        name_info = self.value
        names = name_info["Names"]
        name_lengths = name_info["Lengths"]
        name_flags = name_info["NameFlags"]

        self.name_map = {}
        for i in range(len(names)):
            self.name_map[names[i]] = i

        for item in zip(name_flags, name_lengths, names):
            self.value = item[0]
            ret += self.transcode_byte()
            self.value = item[1]
            ret += self.transcode_byte()
            self.value = item[2]
            if item[0] == 0:  # ASCII encoded string
                ret += self.transcode_string(False)
            elif item[0] == NON_ASCII_STRING:
                if len(ret) % 2 == 1:
                    ret += bytearray([0])  # Make it 0b10 aligned
                ret += self.transcode_wide_string()
            else:
                raise Exception("Unknown name flags")

        return ret

    def transcode_array(self):
        array_content = self.value
        array_inner_class = self.memory["ArrayInnerClass"]
        struct_in_array_class = ""
        if "StructInArrayStructClass" in self.memory:
            struct_in_array_class = self.memory["StructInArrayStructClass"]

        ret = bytearray([])
        for item in array_content:
            self.memory["StructClass"] = struct_in_array_class
            self.value = item
            ret += self.apply_parser(array_inner_class, parse_prefix=False)

        return ret

    def transcode_map(self):
        map_content = self.value
        map_from_class = self.memory["MapFromClass"]
        map_to_class = self.memory["MapToClass"]
        map_length = self.memory["MapLength"]

        if map_to_class == "BoolProperty":
            map_to_class = "ReducedBoolProperty"  # We have to undo the hack we did before

        ret = bytearray([])
        for i in range(map_length):
            self.value = map_content[i]["MapFrom"]
            ret += self.apply_parser(map_from_class, parse_prefix=False)
            self.value = map_content[i]["MapTo"]
            ret += self.apply_parser(map_to_class, parse_prefix=False)

        return ret

    def transcode_msd(self):
        msd_content = self.value
        msd_length = self.memory["MSDLength"]

        ret = bytearray([])
        for i in range(msd_length):
            self.value = msd_content[i]["Object"]
            ret += self.transcode_import()
            self.value = msd_content[i]["FunctionName"]
            ret += self.transcode_name()

        return ret

    def transcode_children(self):
        children = self.value
        self.value = children["ChildrenCount"]
        ret = self.transcode_uint32()

        for child in children["ChildList"]:
            self.value = child
            ret += self.transcode_import()

        return ret

    def transcode_child_properties(self):
        child_properties = self.value
        self.value = child_properties["ChildPropCount"]
        ret = self.transcode_uint32()

        for prop in child_properties["Properties"]:
            prop_type = prop["Type"]
            self.value = prop_type
            ret += self.transcode_name()
            self.value = prop["Content"]
            ret += self.apply_parser("Child" + prop_type)

        return ret

    def transcode_func_map(self):
        func_map = self.value
        self.value = func_map["FuncCount"]
        ret = self.transcode_uint32()

        for func in func_map["Functions"]:
            self.value = func["Name"]
            ret += self.transcode_name()
            self.value = func["Function"]
            ret += self.transcode_import()

        return ret

    # TODO: Refactor this thing too
    def apply_parser(self, parser_name, parsed_object=None, parse_prefix=True):
        def iterate_instructions(instructions, parsed):
            _special = ""
            _ret = bytearray([])
            for instruction in instructions.items():
                if _special == "SKIP":
                    _special = ""
                    continue
                res = self.apply_instruction(instruction, parsed)
                _special = res[1]
                _ret += res[0]
                if _special == "STOP":
                    break
            return _ret

        if parsed_object is None:
            parsed_object = self.value

        parser = self.parsers[parser_name]
        ret = bytearray([])
        if parse_prefix:
            ret += iterate_instructions(parser["Prefix"], parsed_object)
        main_content = iterate_instructions(parser["Content"], parsed_object)
        ret += main_content
        self.memory["TrueLength"] = len(main_content)
        return ret

    # TODO: Also also refactor this
    def apply_instruction(self, instruction, parsed):
        ret = bytearray([])
        key = instruction[0]
        if key.startswith("!NULL"):
            return bytearray([0] * instruction[1]), ""
        elif key.startswith("!JUMP"):
            if instruction[1] in self.memory:
                next_parser = self.memory[instruction[1]]
                if next_parser in self.parsers:
                    return self.apply_parser(next_parser, parsed), "STOP"
            return ret, ""
        elif key.startswith("!INCLUDE"):
            return self.apply_parser(instruction[1], parsed), ""
        elif key.startswith("!IFEQUALS"):
            key = key.split(" ")[1]
            if self.memory[key] == instruction[1]:
                return ret, ""
            else:
                return ret, "SKIP"

        if key.startswith("!SKIP"):
            return self.transcode_symbol(instruction[1]), ""
        elif key.startswith("!PURE"):
            self.value = parsed
            return self.transcode_symbol(instruction[1]), ""
        elif key.startswith("!STORE"):
            key = key.split(" ")[1]
            self.memory[key] = parsed[key]

        self.value = parsed[key]
        return self.transcode_symbol(instruction[1]), ""
