"""Topology helpers shared by OSM building and land-cover consumers."""
def member_rings(relation,osm,role):
    ways={w.id:w for w in osm.ways}
    pieces=[list(ways[m['ref']].nodes) for m in relation.members if m['type']=='way' and m.get('role','outer')==role and m['ref'] in ways]
    rings=[]
    while pieces:
        chain=pieces.pop()
        if not chain:continue
        while chain[0]!=chain[-1]:
            for i,p in enumerate(pieces):
                if chain[-1]==p[0]:chain+=p[1:]
                elif chain[-1]==p[-1]:chain+=p[-2::-1]
                elif chain[0]==p[-1]:chain=p[:-1]+chain
                elif chain[0]==p[0]:chain=p[:0:-1]+chain
                else:continue
                pieces.pop(i);break
            else:break
        if len(chain)>=4 and chain[0]==chain[-1] and all(n in osm.nodes for n in chain):
            rings.append([(osm.nodes[n].lat,osm.nodes[n].lon) for n in chain[:-1]])
    return rings

