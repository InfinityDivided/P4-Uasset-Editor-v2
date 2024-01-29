class UAssetTranscoder:
    def __init__(self, data, parsers):
        self.data = data
        self.parsers = parsers
        self.special_name = None
        self.name_map = None
        self.import_map = None
        self.memory = {}

    def transcode_primitive(self, primitive_format, length):
        pass

    def transcode_symbol(self, symbol):
        return {"NONE": self.transcode_none,
                "BOOL": self.transcode_bool,
                "BYTE": self.transcode_byte,
                "UINT16": self.transcode_uint16,
                "INT32": self.transcode_int32,
                "UINT32": self.transcode_uint32,
                "UINT64": self.transcode_uint64,
                "FLOAT": self.transcode_float,
                "GUID": self.transcode_guid,
                "STRING": self.transcode_string_select,
                "NAME": self.transcode_name,
                "IMPORT": self.transcode_import,
                "NAMEITER": self.transcode_name_iteration,
                "NAMEMAP": self.transcode_name_map,
                "ARRAY": self.transcode_array,
                "MAP": self.transcode_map,
                "MSD": self.transcode_msd}[symbol]()

    def transcode_none(self):
        pass

    def transcode_bool(self):
        pass

    def transcode_byte(self):
        pass

    def transcode_uint16(self):
        return self.transcode_primitive("H", 2)

    def transcode_int32(self):
        return self.transcode_primitive("i", 4)

    def transcode_uint32(self):
        return self.transcode_primitive("I", 4)

    def transcode_int64(self):
        return self.transcode_primitive("q", 8)

    def transcode_uint64(self):
        return self.transcode_primitive("Q", 8)

    def transcode_float(self):
        return self.transcode_primitive("f", 4)

    def transcode_guid(self):
        pass

    def transcode_string_select(self):
        pass

    def transcode_string(self):
        pass

    def transcode_wide_string(self):
        pass

    def transcode_name(self):
        pass

    def transcode_import(self):
        pass

    def transcode_name_iteration(self):
        pass

    def transcode_name_map(self):
        pass

    def transcode_array(self):
        pass

    def transcode_map(self):
        pass

    def transcode_msd(self):
        pass
