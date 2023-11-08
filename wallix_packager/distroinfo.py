class DistroInfo:
    _id = ''
    _name = ''
    _version = ''
    _codename = ''

    def __init__(self):
        with open('/etc/os-release') as f:
            s = f.read()
        patt = r'(?:^|\n)(NAME|VERSION_CODENAME|ID|VERSION_ID)="?([^\n"]+)'
        for m in re.finditer(patt, s):
            k = m.group(1)
            v = m.group(2)
            if k == 'NAME':
                self._name = v
            elif k == 'ID':
                self._id = v
            elif k == 'VERSION_ID':
                self._version = v
            elif k == 'VERSION_CODENAME':
                self._codename = v

    def id(self) -> str:
        return self._id

    def name(self) -> str:
        return self._name

    def version(self) -> str:
        return self._version

    def codename(self) -> str:
        return self._codename
