#!/usr/bin/env python3

from typing import Dict, Tuple

PYTHON_VERSION_2 = '2'
PYTHON_VERSION_3 = '3'

PYBUILD_MAPPING = {
    PYTHON_VERSION_2: 'python',
    PYTHON_VERSION_3: 'python3',
}

PYVERSION_MAPPING = {
    PYTHON_VERSION_2: (
        ("PYTHON_VERSION_NUM", 'PYTHON_VERSION_2'),
    ),
    PYTHON_VERSION_3: (
        ("PYTHON_VERSION_NUM", 'PYTHON_VERSION_3'),
    ),
}


def pybuild_parameters(config: Dict[str, str]) -> Dict[str, Dict[str, str]]:
    pybuilds = config.get("PYBUILD", '').split(',')
    pybuilds = (ver for ver in pybuilds if ver in PYBUILD_MAPPING)
    configs_params = {}
    for py_ver in pybuilds:
        updated_config = dict(config)
        updated_config.update(
            (key, config.get(value))
            for key, value in PYVERSION_MAPPING[py_ver]
        )
        configs_params[PYBUILD_MAPPING[py_ver]] = updated_config
    return configs_params
