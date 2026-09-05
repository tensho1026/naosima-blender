import math,unittest
from collections import Counter
from src.building_geometry import extrude,pitched_outline
class GeometryTests(unittest.TestCase):
    def check_closed(self,ring,gable):
        v,f=extrude(ring,10,6,gable)
        edges=Counter(tuple(sorted((a,b))) for face in f for a,b in zip(face,face[1:]+face[:1]))
        self.assertTrue(all(n==2 for n in edges.values()),edges)
        self.assertAlmostEqual(max(p[2] for p in v),16)
        self.assertAlmostEqual(min(p[2] for p in v),10)
        # Signed closed volume must be positive, ensuring outward winding.
        volume=0
        for face in f:
            a=v[face[0]]
            for i in range(1,len(face)-1):
                b,c=v[face[i]],v[face[i+1]]
                volume+=sum(a[k]*(b[(k+1)%3]*c[(k+2)%3]-b[(k+2)%3]*c[(k+1)%3]) for k in range(3))/6
        self.assertGreater(volume,0)
    def test_gables_rotation_and_winding(self):
        for angle in (0,0.4,1.8):
            r=[(x*math.cos(angle)-y*math.sin(angle),x*math.sin(angle)+y*math.cos(angle)) for x,y in [(0,0),(12,0),(12,7),(0,7)]]
            self.check_closed(r,True);self.check_closed(r[::-1],True)
    def test_concave_outline_preserved(self):
        r=[(0,0),(12,0),(12,4),(4,4),(4,10),(0,10)]
        self.check_closed(r,True)
        v,f=extrude(r,10,6,True)
        self.assertEqual(len(v),12)
    def test_nonrectangular_pitched_roof(self):
        for ring in [[(0,0),(10,0),(10,4),(4,4),(4,10),(0,10)],[(20,22),(-4,32),(-24,-23),(-14,-27),(2,-26)]]:
            v,f=pitched_outline(ring,10,6.5,3.2)
            edges=Counter(tuple(sorted((a,b))) for face in f for a,b in zip(face,face[1:]+face[:1]))
            self.assertTrue(all(n==2 for n in edges.values()))
            self.assertAlmostEqual(max(p[2] for p in v),16.5)

    def test_degenerate_skipped(self):
        self.assertEqual(extrude([(0,0),(1,0),(1,1)],0,6),(None,None))
if __name__=='__main__':unittest.main()
