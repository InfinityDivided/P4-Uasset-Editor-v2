from utils import decode_uint16, decode_uint32, decode_uint64
from json import dumps

input_path = "global.ucas"

with open(input_path, "rb") as uasset_file:
    uasset = bytearray(uasset_file.read())

offset = 0
total_imports, offset = decode_uint32(uasset, offset)

some_ids = []
names = []
max_index = -1
for i in range(total_imports):
    next_index, offset = decode_uint16(uasset, offset)
    offset += 6
    next_id, offset = decode_uint64(uasset, offset)
    if next_index > max_index:
        some_ids.append(next_id)
    max_index = max(max_index, next_index)
    offset += 16


offset = 692113

for i in range(20680):
    name_length = uasset[offset]  # Read name length
    if name_length == 0:
        break
    offset += 1
    names.append(uasset[offset:offset + name_length].decode())
    offset += name_length + 1  # Go to next name length byte

things = dict(zip(some_ids, names))

with open("global.json", "w") as output:
    output.write(dumps(things, indent=2))
