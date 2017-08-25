def fake_parse(files):
    def parse_file(filename):
        print('Parse', filename)
        return files[filename]
    return parse_file
