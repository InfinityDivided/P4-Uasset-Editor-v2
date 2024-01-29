from constants import SPECIAL_STRUCT_NAMES


# TODO: Make this a class and break simplify_tree_standard down

def input_class_info(name_classes, name, class_param, value, file_name):
    if name not in name_classes:
        name_classes[name] = {"Default": {},
                              file_name: {}}

    if file_name not in name_classes[name]:
        name_classes[name][file_name] = {}

    if class_param in name_classes[name][file_name] and name_classes[name][file_name][class_param] != value:
        name_classes[name][file_name]["Annoying"] = True
        return True
    else:
        name_classes[name][file_name][class_param] = value
        name_classes[name]["Default"][class_param] = value

    return False


def simplify_tree(tree, name_classes, global_names, file_name):
    if "Rows" in tree:
        simplify_tree_rows(tree, name_classes, global_names, file_name)
    elif "TrueIndex" in tree:
        simplify_tree_blueprint(tree, name_classes, global_names, file_name)
    elif "Null" in tree:
        return "Null"
    else:
        simplify_tree_standard(tree, name_classes, global_names, file_name)


def simplify_tree_standard(tree, name_classes, global_names, file_name):
    for name in tree:
        content = tree[name]["Content"]
        class_name = tree[name]["Class"]

        # Extremely annoying edge case I didn't account for. Don't bother to reduce this part of the tree
        if input_class_info(name_classes, name, "Class", class_name, file_name):
            continue

        if class_name == "StructProperty":
            struct_class = content["StructClass"]

            # Yeah, yeah, another even rarer edge case
            if input_class_info(name_classes, name, "StructClass", struct_class, file_name):
                continue

            input_class_info(name_classes, name, "StructClass", struct_class, file_name)
            if struct_class not in SPECIAL_STRUCT_NAMES:
                simplify_tree_standard(content["StructContent"], name_classes, global_names, file_name)
                tree[name] = content["StructContent"]
            else:
                del content["StructClass"]
                tree[name] = content

        elif class_name == "ArrayProperty":
            array_inner_class = content["ArrayInnerClass"]
            input_class_info(name_classes, name, "ArrayInnerClass", array_inner_class, file_name)

            if array_inner_class == "StructProperty":
                struct_in_array_name = content["StructInArrayName"]
                struct_in_array_class = content["StructInArrayClass"]
                struct_in_array_struct_class = content["StructInArrayStructClass"]
                input_class_info(name_classes, name, "StructInArrayName", struct_in_array_name, file_name)
                input_class_info(name_classes, name, "StructInArrayClass", struct_in_array_class, file_name)
                input_class_info(name_classes, name, "StructInArrayStructClass", struct_in_array_struct_class, file_name)

                if struct_in_array_struct_class not in SPECIAL_STRUCT_NAMES:
                    for i in range(len(content["ArrayContent"])):
                        simplify_tree_standard(content["ArrayContent"][i]["StructContent"],
                                               name_classes, global_names, file_name)
                        content["ArrayContent"][i] = content["ArrayContent"][i]["StructContent"]

            tree[name] = content["ArrayContent"]

        elif class_name == "MapProperty":
            input_class_info(name_classes, name, "MapFromClass", content["MapFromClass"], file_name)
            input_class_info(name_classes, name, "MapToClass", content["MapToClass"], file_name)
            if content["MapToClass"] == "StructProperty":
                for elem in content["MapContent"]:
                    simplify_tree_standard(elem["MapTo"]["StructContent"], name_classes, global_names, file_name)
            tree[name] = content["MapContent"]

        elif class_name == "EnumProperty":
            input_class_info(name_classes, name, "EnumClass", content["EnumClass"], file_name)
            tree[name] = content["EnumValue"]

        elif class_name == "ObjectProperty":
            tree[name] = id_to_object(content, global_names)

        elif class_name == "StrProperty":
            tree[name] = content["StringContent"]

        else:
            tree[name] = content


def simplify_tree_rows(tree, name_classes, global_names, file_name):
    for row in tree["Rows"]:
        simplify_tree_standard(tree["Rows"][row], name_classes, global_names, file_name)

    del tree["RowCount"]


def simplify_tree_blueprint(tree, name_classes, global_names, file_name):
    simplify_tree_standard(tree["Properties"], name_classes, global_names, file_name)


def id_to_object(name_id, global_names):
    if name_id == 0:
        return "Null"

    if str(name_id).startswith("InternalRef"):
        return {"InternalRef": name_id}

    name_id = str(name_id)  # JSON keys are strings
    if name_id in global_names:
        path_id = str(global_names[name_id][1])
        return {"ObjectName": global_names[name_id][0],
                "ObjectPath": global_names[path_id][0]}
    else:
        return {"UnknownImport": name_id}


def simplify_global_ucas(tree):
    ret = {-1: ["None", -1, -1]}
    names = tree["NameMap"]["Names"]

    for (nm_index, id_1, id_2, id_3) in tree["Identifiers"]:
        ret[id_1] = [names[nm_index], id_2, id_3]

    return ret
