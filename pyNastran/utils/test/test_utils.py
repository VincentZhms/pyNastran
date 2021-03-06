# -*- coding: utf-8 -*-

import os
import sys
import unittest

from six import PY2, StringIO
import numpy as np

import pyNastran
from pyNastran.utils import is_binary_file, object_methods, object_attributes
from pyNastran.utils.numpy_utils import loadtxt_nice, augmented_identity, savetxt_nice
from pyNastran.utils.dev import list_print
from pyNastran.utils.mathematics import (
    get_abs_max, get_max_index, get_min_index, get_abs_index,
    is_list_ranged)


PKG_PATH = pyNastran.__path__[0]

class A1(object):
    def __init__(self):
        self.a = 5
        self._a = self.a**2

    def getA(self):
        return self.a

    def _getA(self):
        return self.a


class B1(A1):
    c = 7
    def __init__(self, b):
        A1.__init__(self)
        self.b = b
        self._b = b**2

    def getB(self):
        return self.b

    def _getB(self):
        return self.b


class TestUtils(unittest.TestCase):
    def test_augmented_identity(self):
        expected_array = np.array([
            [1., 0., 0., 0.],
            [0., 1., 0., 0.],
            [0., 0., 1., 0.],
        ])
        actual_array = augmented_identity(3, 4)
        msg = 'expected:\n%s\nactual:\n%s' % (expected_array, actual_array)
        assert np.array_equal(expected_array, actual_array), msg

    def test_is_list_ranged(self):
        """tests the is_list_ranged function"""
        self.assertTrue(is_list_ranged(0.0, [0.5], 1.0))
        self.assertTrue(is_list_ranged(0.0, [0.5, 0.6], 1.0))
        self.assertTrue(is_list_ranged(0.0, [0.0, 1.0, 0.5], 1.0))
        self.assertTrue(is_list_ranged(0.0, [1.0], 1.0))
        self.assertFalse(is_list_ranged(0.0, [1.1], 1.0))
        self.assertFalse(is_list_ranged(0.0, [0.5, 1.1], 1.0))

    def test_get_maxminabs_index(self):

        #def get_max_index(data, axis=1):
        """
        Gets the maximum values of a 2D array along an axis
        >>> data = [
                [4.0, 2.2, 3.0, 5.0, 2.2]  # subcase 1
                [4.1, 2.1, 3.1, 5.1, 2.1], # subcase 2
        >>> max_values, index = get_min_index(data, axis=1)
        >>> out   = [4.1, 2.2, 3.1, 5.1, 2.2]
        >>> index = [1, 0, 1, 1, 0]
        """
        data = np.array([
            [4.0, 2.2, 3.0, 5.0, 2.2],  # subcase 1
            [4.1, 2.1, 3.1, 5.1, 2.1],
        ])
        min_values, min_index = get_min_index(data, axis=1)
        max_values, max_index = get_max_index(data, axis=1)
        abs_values, abs_index = get_abs_index(data, axis=1)

        #print(min_index, min_values)
        #print(max_index, max_values)
        assert np.array_equal(min_index, [0, 1, 0, 0, 1]), min_index
        assert np.array_equal(max_index, [1, 0, 1, 1, 0]), max_index
        assert np.array_equal(abs_index, [1, 0, 1, 1, 0]), abs_index

        assert np.array_equal(min_values, [4.0, 2.1, 3.0, 5.0, 2.1]), min_values
        assert np.array_equal(max_values, [4.1, 2.2, 3.1, 5.1, 2.2]), max_values
        assert np.array_equal(abs_values, [4.1, 2.2, 3.1, 5.1, 2.2]), abs_values

    def test_is_binary(self):
        """tests if a file is binary"""
        bdf_filename = os.path.join(PKG_PATH, '..', 'models', 'solid_bending', 'solid_bending.bdf')
        op2_filename = os.path.join(PKG_PATH, '..', 'models', 'solid_bending', 'solid_bending.op2')
        self.assertTrue(is_binary_file(op2_filename))
        self.assertFalse(is_binary_file(bdf_filename))

    def test_list_print(self):
        #self.b = B(7)
        """tests the list_print method, which is a nice way to write a 2d array"""
        self.assertEqual(list_print(None), 'None')
        #self.assertRaises(TypeError, lambda: list_print(None))

        for ai, bi in [([], '[]'), (np.array([]), '[]'), (tuple(), '[]')]:
            self.assertEqual(list_print(ai), bi)
        expected_array_str = (
            '[[1         ,2         ,3         ],\n'
            ' [4         ,5         ,6         ],\n'
            ' [7         ,8         ,9         ]]'
        )
        self.assertEqual(
            list_print(np.array([(1, 2, 3), (4, 5, 6), (7, 8, 9)]), float_fmt='%-10g'),
            expected_array_str)
        self.assertEqual(
            list_print(np.array([(1., 2, 3.), (4., 5., 6), (7., 8, 9)]), float_fmt='%-10g'),
            expected_array_str)

        expected_array_str = (
            '[[1.1       ,2.234     ,3.00001   ],\n'
            ' [4.001     ,5         ,6.2       ]]'
        )
        self.assertEqual(
            list_print(np.array([(1.1, 2.234, 3.00001), (4.001, 5.0000005, 6.2)]), float_fmt='%-10g'),
            expected_array_str)

        self.assertEqual(list_print(['a', None, 11, '']), '[a, None, 11, ]')
        self.assertEqual(list_print(('a', None, 11, '')), '[a, None, 11, ]')

    def test_object_methods_introspection(self):
        """object methods determines the public/private methods of a class"""
        b = B1(7)
        methods = object_methods(b)
        self.assertEqual(methods, ['getA', 'getB'])

        methods = object_methods(b, "private")
        self.assertEqual(methods, ['_getA', '_getB'])

        methods = object_methods(b, "both")
        self.assertEqual(methods, ['_getA', '_getB', 'getA', 'getB'])

        methods = object_methods(b, "all")
        self.assertEqual(methods, ['__init__', '_getA', '_getB', 'getA',
                                   'getB'])

    def test_object_attributes_introspection(self):
        """object methods determines the public/private attributes of a class"""
        b = B1(7)
        attributes = object_attributes(b)
        self.assertEqual(attributes, ['a', 'b', 'c'])

        attributes = object_attributes(b, "private")
        self.assertEqual(attributes, ['_a', '_b'])

        attributes = object_attributes(b, "both")
        self.assertEqual(attributes, ['_a', '_b', 'a', 'b', 'c'])

    def test_object_attributes_introspection_3(self):
        """object methods determines the public/private attributes of a class"""
        b = B1(7)
        attributes = object_attributes(b, "all")
        version_info = sys.version_info
        if version_info < (3, 0):
            self.assertEqual(attributes, [
                '__class__', '__delattr__', '__dict__',
                '__doc__', '__format__', '__getattribute__', '__hash__',
                '__module__', '__new__', '__reduce__', '__reduce_ex__',
                '__repr__', '__setattr__', '__sizeof__', '__str__',
                '__subclasshook__', '__weakref__', '_a', '_b', 'a', 'b', 'c'])
        else:
            expected = [
                '__class__', '__delattr__', '__dict__',
                '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__',
                '__gt__', '__hash__', '__le__', '__lt__', '__module__',
                '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__',
                '__setattr__', '__sizeof__', '__str__', '__subclasshook__',
                '__weakref__', '_a', '_b', 'a', 'b', 'c']
            if version_info > (3, 3): # inclusive
                expected.append('__dir__')
            if version_info > (3, 6):
                expected.append('__init_subclass__')
                #print('\nactual   = %s' % ','.join(list(sorted(attributes))))
                #print('expected = %s' % ','.join(list(sorted(expected))))
            self.assertEqual(sorted(attributes), sorted(expected))

    def test_loadtxt_01(self):
        """tests that we can reimplement loadtxt so it doesn't suck"""
        c = StringIO("1,0,2\n3,0,4")
        x1, y1 = np.loadtxt(c, delimiter=',', usecols=(0, 2), unpack=True)
        x2, y2 = loadtxt_nice(c, delimiter=',', usecols=(0, 2), unpack=True)
        #print('x1=%s y1=%s' % (x1, y1))
        #print('x2=%s y2=%s\n+' % (x2, y2))
        assert np.array_equal(x1, x2), 'x1=%s x2=%s' % (x1, x2)
        assert np.array_equal(y1, y2), 'y1=%s y2=%s' % (y1, y2)

        c = StringIO("#1,0,2\n3,0,4")
        x1, y1 = np.loadtxt(c, delimiter=',', usecols=(0, 2), unpack=True)
        x2, y2 = loadtxt_nice(c, delimiter=',', usecols=(0, 2), unpack=True)
        #print('x1=%s y1=%s' % (x1, y1))
        #print('x2=%s y2=%s' % (x2, y2))
        assert np.array_equal(x1, x2), 'x1=%s x2=%s' % (x1, x2)
        assert np.array_equal(y1, y2), 'y1=%s y2=%s' % (y1, y2)

        c = StringIO("#1,0,2\n3,0,4")
        x1, y1 = np.loadtxt(c, delimiter=',', usecols=(0, 2), unpack=True, ndmin=1)
        x2, y2 = loadtxt_nice(c, delimiter=',', usecols=(0, 2), unpack=True, ndmin=1)
        #print('x1=%s y1=%s' % (x1, y1))
        #print('x2=%s y2=%s' % (x2, y2))
        assert np.array_equal(x1, x2), 'x1=%s x2=%s' % (x1, x2)
        assert np.array_equal(y1, y2), 'y1=%s y2=%s' % (y1, y2)

        c = StringIO("#1,0,2\n3,0,4")
        x1, y1 = np.loadtxt(c, delimiter=',', usecols=(0, 2), unpack=True, ndmin=2)
        x2, y2 = loadtxt_nice(c, delimiter=',', usecols=(0, 2), unpack=True, ndmin=2)
        #print('x1=%s y1=%s' % (x1, y1))
        #print('x2=%s y2=%s' % (x2, y2))
        assert np.array_equal(x1, x2), 'x1=%s x2=%s' % (x1, x2)
        assert np.array_equal(y1, y2), 'y1=%s y2=%s' % (y1, y2)

    def test_savetxt_nice(self):
        """tests that we can reimplement savetxt so it doesn't suck"""
        A = np.eye(10)
        csv_filename = 'savetxt_real.csv'
        savetxt_nice(csv_filename, A, fmt='%.18e', delimiter=',', newline='\n',
                     header='', footer='', comments='# ')

        with self.assertRaises(ValueError):
            loadtxt_nice(csv_filename, delimiter=' ', skiprows=0, comment='#',
                         dtype=np.float64, converters=None,
                         usecols=None, unpack=False, ndmin=0)

        A2 = loadtxt_nice(csv_filename, delimiter=',', skiprows=0, comment='#',
                          dtype=np.float64, converters=None,
                          usecols=None, unpack=False, ndmin=0)
        assert np.array_equal(A, A2), 'expected:\n%s\nactual:\n%s' % (A, A2)
        os.remove(csv_filename)

        csv_filename = 'savetxt_complex.csv'
        B = np.eye(10, dtype='complex128') - 2 * A*1j
        savetxt_nice(csv_filename, B, fmt='%.18e', delimiter=',', newline='\n',
                     header='', footer='', comments='# ')
        with self.assertRaises(ValueError):  ## TODO: mistake
            B2 = loadtxt_nice(csv_filename, delimiter=',', skiprows=0, comment='#',
                              dtype=np.float64, converters=None,
                              usecols=None, unpack=False, ndmin=0)
            #assert np.array_equal(B, B2), 'expected:\n%s\nactual:\n%s' % (B, B2)
        os.remove(csv_filename)

        if 0:  ## TODO: not done with filehandle test
            from codecs import open as codec_open
            with codec_open(csv_filename, 'w') as csv_file:
                savetxt_nice(csv_file, B, fmt='%.18e', delimiter=',', newline='\n',
                             header='', footer='', comments='# ')
            os.remove(csv_filename)

        if PY2:
            with self.assertRaises(IOError):
                B2 = loadtxt_nice('missing.txt', delimiter=',', skiprows=0, comment='#',
                                  dtype=np.float64, converters=None,
                                  usecols=None, unpack=False, ndmin=0)
        else:
            with self.assertRaises(FileNotFoundError):
                B2 = loadtxt_nice('missing.txt', delimiter=',', skiprows=0, comment='#',
                                  dtype=np.float64, converters=None,
                                  usecols=None, unpack=False, ndmin=0)

if __name__ == '__main__':  # pragma: no cover
    unittest.main()
