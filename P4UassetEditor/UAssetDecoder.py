from struct import unpack

from UAssetTranscoder import UAssetTranscoder

from constants import *


class UAssetDecoder(UAssetTranscoder):
    def __init__(self, data, parsers, file_name):
        super().__init__(data, parsers)
        self.file_name = file_name
        self.offset = 0

    def decode_uasset(self):
        # TODO: This is getting unwieldy, refactor this after doing DT support
        # Actually, just do it after BP Generated class support, who knows how that'll change the code
        # Good call, had to rethink a lot of parts
        # Hopefully there are no more surprises

        self.memory["NameCount"] = float('inf')
        headers = {"InitialHeader": self.apply_parser("UAssetInitialHeader"),
                   "NameMap": self.transcode_name_map()}

        self.offset = self.memory["NameMapHashesOffset"]
        algorithm_id = self.transcode_uint64()
        hashes = []
        while self.offset < self.memory["ImportMapOffset"]:
            hashes.append(self.transcode_uint64())

        headers["NameMapHashes"] = {"AlgorithmID": algorithm_id,
                                    "Hashes": hashes}

        imports = []
        while self.offset < self.memory["ExportMapOffset"]:
            imports.append(self.transcode_int64())
        self.import_map = imports
        headers["ImportMap"] = imports

        exports = []
        while self.offset < self.memory["ExportBundlesOffset"]:
            export_obj = self.apply_parser("ExportObject")
            exports.append(export_obj)
        headers["ExportMap"] = exports

        # Ad hoc decoding

        read_order = []
        mode = "Normal"
        if "RowStruct" in self.name_map:
            mode = "DataTable"
        elif "BlueprintGeneratedClass" in self.name_map:
            mode = "Blueprint"
            self.offset += 8  # Just skip those, believe me
            while self.offset < self.memory["GraphDataOffset"]:
                maybe_next = self.transcode_uint32()
                is_next = self.transcode_uint32()
                if is_next:
                    read_order.append(maybe_next)
            self.offset = self.memory["ExportBundlesOffset"]

        end_of_blob = self.memory["GraphDataOffset"] + self.memory["GraphDataSize"]
        extra = {"BlobOfData": self.data[self.offset: end_of_blob].hex(),
                 "ExInitialHeader": headers["InitialHeader"],
                 "ExNameMap": self.name_map,
                 "ExImports": imports,
                 "ExExports": exports}

        self.offset = end_of_blob

        content = None
        if mode == "Normal":
            content = [self.transcode_name_iteration()]
        elif mode == "DataTable":
            content = [self.transcode_name_iteration()]

            self.offset += 4  # Not sure what those null bytes are for
            row_count = self.transcode_uint32()
            rows = {}
            for i in range(row_count):
                row_name = self.transcode_name()
                rows[row_name] = self.transcode_name_iteration()

            content.append({"RowCount": row_count,
                            "Rows": rows})
        elif mode == "Blueprint":
            content = []
            for true_index in read_order:
                # This fixes some files. Not sure why they are like that
                if self.offset == len(self.data) - 8:
                    content.append("Null")
                    break

                # noinspection PyTypeChecker
                new_component = {"TrueIndex": true_index,
                                 "Name": exports[true_index]["ObjectName"],
                                 "Properties": self.transcode_name_iteration()}

                # noinspection PyTypeChecker
                class_type = exports[true_index]["ClassIndex"]
                if class_type in [BLUEPRINT_GENERATED_CLASS, FUNCTION]:
                    self.offset += 4
                    new_component["SuperStruct"] = self.transcode_import()
                    new_component["Children"] = self.transcode_children()
                    new_component["ChildProperties"] = self.transcode_child_properties()
                    if class_type == FUNCTION:
                        new_component["UnknownUINT32"] = self.transcode_uint32()
                        new_component["UnknownValuesLength"] = self.transcode_uint32()
                        unknown_hex = self.data[self.offset: self.offset + new_component["UnknownValuesLength"]].hex()
                        self.offset += new_component["UnknownValuesLength"]
                        new_component["UnknownValues"] = unknown_hex
                        new_component["FunctionFlags"] = self.transcode_uint64()
                        self.offset += 4
                    elif class_type == BLUEPRINT_GENERATED_CLASS:
                        self.offset += 8
                        new_component["FuncMap"] = self.transcode_func_map()
                        new_component["ClassFlags"] = self.transcode_uint32()
                        new_component["ClassWithin"] = self.transcode_import()
                        new_component["ClassConfigName"] = self.transcode_name()
                        self.offset += 12
                        self.transcode_none()
                        new_component["bCooked"] = self.transcode_bool()
                        self.offset += 3
                        new_component["ClassDefaultObject"] = self.transcode_import()
                else:
                    self.offset += 4

                    # noinspection PyTypeChecker
                    if exports[true_index]["ClassIndex"] in [CIRCLE_SHADOW_MESH_COMPONENT,
                                                             CARROT_STATIC_MESH_COMPONENT,
                                                             STATIC_COLLISION_COMPONENT]:
                        # It totally works
                        self.offset += 4

                content.append(new_component)

        file_references = []
        for name in self.name_map:
            if name.endswith(self.file_name):
                file_references.append(name)
        extra["FileReferences"] = file_references

        return {"Headers": headers,
                "Content": content,
                "Extra": extra}

    def decode_global_ucas(self):
        identifier_count = self.transcode_uint32()
        identifiers = []
        max_index = 0
        for i in range(identifier_count):
            name_map_index = self.transcode_uint16()
            max_index = max(max_index, name_map_index)
            self.offset += 6  # Skip what seems to always be 00 80 00 00 00 00
            identifiers.append((name_map_index, self.transcode_int64(), self.transcode_int64(), self.transcode_int64()))

        self.offset += 12  # Skip identifier_count again and 00 80 00 00 00 00 00 00
        self.memory["NameCount"] = max_index + 1
        self.memory["NameMapHashesOffset"] = float('inf')
        return {"Identifiers": identifiers,
                "NameMap": self.transcode_name_map()}

    def transcode_primitive(self, primitive_format, length):
        ret = unpack(primitive_format, self.data[self.offset:self.offset + length])[0]
        self.offset += length
        return ret

    def transcode_byte(self):
        ret = self.data[self.offset]
        self.offset += 1
        return ret

    def transcode_bool(self):
        return bool(self.transcode_byte())

    def transcode_guid(self):
        ret = self.data[self.offset: self.offset + 16].hex()
        self.offset += 16
        return ret

    def transcode_string_select(self):
        if self.memory["StringLength"] > 0:
            return self.transcode_string()
        elif self.memory["StringLength"] < 0:
            self.memory["StringLength"] = -self.memory["StringLength"] - 1  # No idea why
            ret = self.transcode_wide_string()
            self.offset += 2  # Two null bytes now
            return ret
        return ""

    def transcode_string(self, has_null_terminator=True):
        string_length = self.memory["StringLength"]
        new_offset = self.offset + string_length

        if has_null_terminator:
            string_length -= 1
        ret = self.data[self.offset:self.offset + string_length].decode()

        self.offset = new_offset
        return ret

    def transcode_wide_string(self):
        ret = self.data[self.offset:self.offset + 2 * self.memory["StringLength"]].decode("utf-16le")
        self.offset += 2 * self.memory["StringLength"]
        return ret

    def transcode_name(self):
        name_id = self.transcode_uint32()
        name_index = self.transcode_uint32()
        name = str(self.name_map[name_id])
        if name in SPECIAL_NAMES:
            self.special_name = name

        if name_index > 0:
            return name + f"!!{name_index}"
        else:
            return name

    def transcode_import(self):
        import_id = self.transcode_int32()
        if import_id > 0:  # Internal import
            return f"InternalRef:{import_id - 1}"
        if import_id < 0:  # External import
            return self.import_map[-import_id - 1]
        else:
            return 0

    def transcode_none(self):
        self.offset += 8
        return "None"

    def transcode_name_iteration(self):
        ret = {}
        while True:
            name = self.transcode_name()
            if name == "None":
                return ret
            else:
                new_content = {}
                class_name = self.transcode_name()
                new_content["Length"] = self.transcode_uint32()

                # Huh? Why did they do this?
                if class_name == "ByteProperty" and new_content["Length"] == 8:
                    class_name = "WeirdByteProperty"

                new_content["Class"] = class_name
                weird_index = self.transcode_uint32()
                new_content["Content"] = self.apply_parser(class_name)
                if weird_index > 0:
                    name += f'??{weird_index}'
                ret[name] = new_content

    def transcode_name_map(self):
        ret = {"Names": [],
               "Lengths": [],
               "NameFlags": []}

        current_count = 0
        while self.offset < self.memory["NameMapHashesOffset"]:
            name_flags = self.transcode_byte()
            name_length = self.transcode_byte()  # Read name length
            if name_length == 0:
                break

            self.memory["StringLength"] = name_length
            if name_flags == 0:
                name = self.transcode_string(False)
            elif name_flags == NON_ASCII_STRING:
                if self.offset % 2 == 1:
                    self.offset += 1  # Make it 0b10 aligned
                name = self.transcode_wide_string()
            else:
                raise Exception("Unknown name flags")

            ret["Names"].append(name)
            ret["Lengths"].append(name_length)
            ret["NameFlags"].append(name_flags)
            current_count += 1
            if current_count >= self.memory["NameCount"]:
                break

        self.name_map = ret["Names"]

        return ret

    def transcode_array(self):
        array_inner_class = self.memory["ArrayInnerClass"]
        array_length = self.memory["ArrayLength"]
        struct_in_array_class = ""
        if "StructInArrayStructClass" in self.memory:
            struct_in_array_class = self.memory["StructInArrayStructClass"]

        ret = []
        for i in range(array_length):
            self.memory["StructClass"] = struct_in_array_class
            ret.append(self.apply_parser(array_inner_class, parse_prefix=False))
        return ret

    def transcode_map(self):
        map_from_class = self.memory["MapFromClass"]
        map_to_class = self.memory["MapToClass"]
        map_length = self.memory["MapLength"]

        if map_to_class == "BoolProperty":
            map_to_class = "ReducedBoolProperty"  # A hack because bools behave weirdly

        ret = []
        for i in range(map_length):
            map_from = self.apply_parser(map_from_class, parse_prefix=False)
            map_to = self.apply_parser(map_to_class, parse_prefix=False)
            ret.append({"MapFrom": map_from,
                        "MapTo": map_to})
        return ret

    def transcode_msd(self):
        msd_length = self.memory["MSDLength"]

        ret = []
        for i in range(msd_length):
            ret.append({"Object": self.transcode_import(),
                        "FunctionName": self.transcode_name()})
        return ret

    def transcode_children(self):
        children_count = self.transcode_uint32()
        child_list = []
        for i in range(children_count):
            child_list.append(self.transcode_import())

        return {"ChildrenCount": children_count,
                "ChildList": child_list}

    def transcode_child_properties(self):
        child_prop_count = self.transcode_uint32()
        properties = []
        for i in range(child_prop_count):
            prop_type = self.transcode_name()
            child_prop = self.apply_parser("Child" + prop_type)
            properties.append({"Type": prop_type,
                               "Content": child_prop})

        return {"ChildPropCount": child_prop_count,
                "Properties": properties}

    def transcode_func_map(self):
        func_count = self.transcode_uint32()
        functions = []
        for i in range(func_count):
            functions.append({"Name": self.transcode_name(),
                              "Function": self.transcode_import()})

        return {"FuncCount": func_count,
                "Functions": functions}

    # TODO: Reminder to refactor this later
    def apply_parser(self, parser_name, ret=None, parse_prefix=True):
        def iterate_instructions(instructions, _ret):
            _special = ""
            for instruction in instructions.items():
                if _special == "SKIP":
                    _special = ""
                    continue
                _ret, _special = self.apply_instruction(instruction, _ret)
                if _special == "STOP":
                    break
            return _ret

        parser = self.parsers[parser_name]
        if ret is None:
            ret = {}
        if parse_prefix:
            ret = iterate_instructions(parser["Prefix"], ret)
        return iterate_instructions(parser["Content"], ret)

    # TODO: Refactor this too
    def apply_instruction(self, instruction, ret):
        key = instruction[0]
        if key.startswith("!NULL"):
            self.offset += instruction[1]
            return ret, ""
        elif key.startswith("!JUMP"):
            if instruction[1] in self.memory:
                next_parser = self.memory[instruction[1]]
                if next_parser in self.parsers:
                    return self.apply_parser(next_parser, ret), "STOP"
            return ret, ""
        elif key.startswith("!INCLUDE"):
            return self.apply_parser(instruction[1], ret), ""
        elif key.startswith("!IFEQUALS"):
            key = key.split(" ")[1]
            if self.memory[key] == instruction[1]:
                return ret, ""
            else:
                return ret, "SKIP"

        value = self.transcode_symbol(instruction[1])
        if key.startswith("!SKIP"):
            return ret, ""
        elif key.startswith("!PURE"):
            return value, ""
        elif key.startswith("!STORE"):
            key = key.split(" ")[1]
            self.memory[key] = value

        ret[key] = value
        return ret, ""
