from importlib.machinery import ModuleSpec, SourceFileLoader


class PundlerFinder(object):
    def __init__(self, basepath):
        self.basepath = basepath
        self.pundles = defaultdict(list)
        # TODO remove all this shit and use parser
        for line in open('freezed.txt').readlines():
            if not line.strip():
                continue
            if '###' in line:
                pundle = json.loads(line.split('###')[1].strip())
            else:
                pundle = dict(zip(
                    ['name', 'version'],
                    [item.strip() for item in line.split('==')]
                ))
                pundle['top_level'] = [pundle['name']]
            base_dir = op.join('Pundledir', pundle['path'])
            for top in pundle['top_level']:
                top_pundle = pundle.copy()
                top_pundle['path'] = op.join('Pundledir', pundle['path'], top)
                if not op.exists(top_pundle['path']):
                    top_pundle['path'] = op.join('Pundledir', pundle['path'], top + '.py')
                if not op.exists(top_pundle['path']):
                    continue
                self.pundles[top].append(top_pundle)

    def find_spec(self, fullname, path, target_module):
        if path is not None:
            return None
        if fullname not in self.pundles:
            return None
        pundle = self.pundles[fullname][0]
        if pundle['path'].endswith('.py'):
            path = pundle['path']
            is_package = False
        else:
            path = op.join(pundle['path'], '__init__.py')
            is_package = True
        spec = ModuleSpec(fullname, SourceFileLoader(fullname, path), origin=path, is_package=is_package)
        if is_package:
            spec.submodule_search_locations = [pundle['path']]
        return spec


def install_finder():
    sys.meta_path.insert(0, PundlerFinder('.'))

