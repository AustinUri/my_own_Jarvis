import collections
import math
import tempfile
import unittest
from pathlib import Path
from vision.stl_export import box_mesh, cylinder_mesh, write_stl


def check_mesh(mesh):
    edges = collections.Counter()
    directed = collections.Counter()
    volume = 0
    for a,b,c in mesh:
        for x,y in ((a,b),(b,c),(c,a)):
            edges[tuple(sorted((x,y)))] += 1
            directed[(x,y)] += 1
        volume += (a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])+a[2]*(b[0]*c[1]-b[1]*c[0]))/6
    return all(n==2 for n in edges.values()) and all(n==directed[(y,x)] for (x,y),n in directed.items()), volume

class STLTest(unittest.TestCase):
    def test_box(self):
        closed, volume = check_mesh(box_mesh(2,3,4))
        self.assertTrue(closed)
        self.assertAlmostEqual(volume,24)
    def test_cylinder(self):
        closed, volume = check_mesh(cylinder_mesh(10,20,64))
        self.assertTrue(closed)
        self.assertAlmostEqual(volume,64*25*math.sin(2*math.pi/64)/2*20)
    def test_invalid(self):
        for value in (0,-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError): box_mesh(value,2,3)
    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'part.stl'
            write_stl(path,box_mesh(1,2,3))
            self.assertEqual(path.read_text().count('facet normal'),12)
            with self.assertRaises(FileExistsError): write_stl(path,box_mesh(1,2,3))
