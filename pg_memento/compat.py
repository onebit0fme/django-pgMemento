# -*- coding: utf-8 -*-
import os
from io import open

PROJECT_PATH = os.path.dirname(os.path.realpath(__file__))
PG_MEMENTO_PATH = os.path.join(PROJECT_PATH, 'scripts')


def read_file_content(path):
    f = open(path, encoding='utf-8')
    return f.read()
