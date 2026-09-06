import unittest
from src.plan_clipping import subtract_rectangle,area
class PlanClippingTests(unittest.TestCase):
    def test_surrounding_polygon_retains_outside_area(self):
        p=[(-5,-5,-5),(5,-5,5),(5,5,5),(-5,5,-5)]
        out=subtract_rectangle(p,(-2,-1,2,1))
        self.assertAlmostEqual(sum(area(q) for q in out),92)
        for q in out:
            for x,y,z in q:self.assertAlmostEqual(x,z)
    def test_inside_removed_and_disjoint_preserved(self):
        p=[(0,0,0),(1,0,0),(1,1,0),(0,1,0)]
        self.assertEqual(subtract_rectangle(p,(-1,-1,2,2)),[])
        self.assertAlmostEqual(sum(area(q) for q in subtract_rectangle(p,(2,2,3,3))),1)
    def test_repeated_clipping_preserves_area(self):
        p=[(-4,-2,0),(4,-2,0),(4,2,0),(-4,2,0)]
        out=subtract_rectangle(p,(-1,-1,1,1))
        again=[r for q in out for r in subtract_rectangle(q,(-1,-1,1,1))]
        self.assertAlmostEqual(sum(area(q) for q in again),28)
if __name__=='__main__':unittest.main()
