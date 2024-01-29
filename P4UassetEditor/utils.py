from os import walk, mkdir, path


def apply_function_to_dir(input_dir_path,
                          output_dir_path,
                          input_extension,
                          output_extension,
                          applied_function,
                          extra_params):

    for root, dirs, files in walk(input_dir_path):
        input_names = [file[:-len(input_extension)] for file in files if file.endswith(input_extension)]
        output_root = path.join(output_dir_path, path.relpath(root, input_dir_path))

        if not path.exists(output_root):
            mkdir(output_root)

        for input_name in input_names:
            try:
                applied_function(path.join(root, input_name + input_extension),
                                 path.join(output_root, input_name + output_extension),
                                 extra_params)
            except Exception as e:
                print(f"Couldn't process {input_name}")
                print(e)
                raise e
