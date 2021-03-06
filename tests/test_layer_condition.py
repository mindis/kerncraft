"""
High-level tests for the overall functionallity and things in kc.py
"""
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import
from __future__ import division

import sys
import os
import unittest
import tempfile
import shutil
import pickle
from pprint import pprint
from io import StringIO
from distutils.spawn import find_executable
import platform

import six
import sympy

sys.path.insert(0, '..')
from kerncraft import kerncraft as kc
from kerncraft.prefixedunit import PrefixedUnit


def recursive_dict_get(d, key_path):
    if len(key_path) > 1:
        return recursive_dict_get(d[key_path[0]], key_path[1:])
    else:
        return d[key_path[0]]


class TestLayerCondition(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        # Remove the directory after the test
        shutil.rmtree(self.temp_dir)

    def _find_file(self, name):
        testdir = os.path.dirname(__file__)
        name = os.path.join(testdir, 'test_files', name)
        assert os.path.exists(name)
        return name

    def test_kernel_requirements(self):
        output_stream = StringIO()
        parser = kc.create_parser()
        args = parser.parse_args(['-m', self._find_file('phinally_gcc.yaml'),
                                  '-p', 'LC',
                                  self._find_file('2d-5pt-unrolled.c')])
        kc.check_arguments(args, parser)
        with self.assertRaises(ValueError) as cm:
            kc.run(parser, args, output_file=output_stream)

    def test_3d_7pt(self):
        store_file = os.path.join(self.temp_dir, 'test_3d7pt_LC.pickle')
        output_stream = StringIO()
        parser = kc.create_parser()
        args = parser.parse_args(['-m', self._find_file('phinally_gcc.yaml'),
                                  '-p', 'LC',
                                  self._find_file('3d-7pt.c'),
                                  '-D', 'N', '0',
                                  '-D', 'M', '0',
                                  '-vvv',
                                  '--store', store_file])
        kc.check_arguments(args, parser)
        kc.run(parser, args, output_file=output_stream)
        results = pickle.load(open(store_file, 'rb'))
        result = next(iter(results['3d-7pt.c'].values()))['LC']

        N = sympy.var('N')
        result_expected = {
            'dimensions': {
                1: {
                    'slices_sum': 2,
                    'slices_count': 6,
                    'caches': {
                        'L1': {'lt': True},
                        'L2': {'lt': True},
                        'L3': {'lt': True},
                    },
                    'cache_requirement_bytes': 64,
                },
                2: {
                    'slices_sum': 2*N,
                    'slices_count': 4,
                    'caches': {
                        'L1': {'lt': 48*N - 32 <= 32768},
                        'L2': {'lt': 48*N - 32 <= 262144},
                        'L3': {'lt': 48*N - 32 <= 20971520},
                    },
                    'cache_requirement_bytes': 48*N - 32,
                },
                3: {
                    'slices_sum': 2*N*(N-1)+2*N,
                    'slices_count': 2,
                    'caches': {
                        'L1': {'lt': 16*N**2 + 16*N*(N - 1) <= 32768},
                        'L2': {'lt': 16*N**2 + 16*N*(N - 1) <= 262144},
                        'L3': {'lt': 16*N**2 + 16*N*(N - 1) <= 20971520},
                    },
                    'cache_requirement_bytes': 16*N**2 + 16*N*(N - 1),
                },
            }
        }

        # Iterate over expected results and validate with generated results
        stack = [((k,), v) for k, v in result_expected.items()]
        while stack:
            key_path, value = stack.pop()
            if isinstance(value, dict):
                stack.extend([(key_path + (k,), v) for k, v in value.items()])
            else:
                self.assertEqual(value, recursive_dict_get(result, key_path),
                                 msg="at key_path={}".format(key_path))

if __name__ == '__main__':
    unittest.main()
