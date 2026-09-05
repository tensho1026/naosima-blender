"""OpenStreetMap via the official map API (XML) with Overpass JSON fallback.

Cached under data/osm/. License: ODbL.
"""

from __future__ import annotations

import json
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from .config import OVERPASS_ENDPOINTS, LocationConfig
from .httputil import http_get, http_post
from .paths import osm_dir

Tags = Dict[str, str]


@dataclass
class OsmWay:
    id: int
    nodes: List[int]
    tags: Tags
    coords: List[Tuple[float, float]] = field(default_factory=list)  # (lat, lon)


@dataclass
class OsmNode:
    id: int
    lat: float
    lon: float
    tags: Tags


@dataclass
class OsmRelation:
    id: int
    tags: Tags
    members: List[dict]


@dataclass
class OsmData:
    nodes: Dict[int, OsmNode]
    ways: List[OsmWay]
    raw_path: str
    relations: List[OsmRelation] = field(default_factory=list)

    def ways_with(self, key: str, values: Optional[Sequence[str]] = None) -> List[OsmWay]:
        out = []
        for w in self.ways:
            if key not in w.tags:
                continue
            if values is None or w.tags[key] in values:
                out.append(w)
        return out

    def closed_ways_with(self, key: str, values: Optional[Sequence[str]] = None) -> List[OsmWay]:
        return [w for w in self.ways_with(key, values) if len(w.coords) >= 4 and w.coords[0] == w.coords[-1]]

    def nodes_named(self, hints: Sequence[str]) -> List[OsmNode]:
        hints_l = [h.lower() for h in hints]
        found = []
        for n in self.nodes.values():
            blob = " ".join(n.tags.get(k, "") for k in ("name", "name:ja", "name:en", "alt_name")).lower()
            if any(h.lower() in blob for h in hints):
                found.append(n)
        return found

    def ways_named(self, hints: Sequence[str]) -> List[OsmWay]:
        found = []
        for w in self.ways:
            blob = " ".join(w.tags.get(k, "") for k in ("name", "name:ja", "name:en", "alt_name"))
            if any(h.casefold() in blob.casefold() for h in hints):
                found.append(w)
        return found


OVERPASS_QUERY = """
[out:json][timeout:180];
(
  way["building"]({s},{w},{n},{e});
  relation["building"]({s},{w},{n},{e});
  relation["natural"~"^(wood|forest|scrub)$"]({s},{w},{n},{e});
  relation["landuse"="forest"]({s},{w},{n},{e});
  way["highway"]({s},{w},{n},{e});
  way["landuse"]({s},{w},{n},{e});
  way["natural"]({s},{w},{n},{e});
  way["leisure"]({s},{w},{n},{e});
  way["amenity"]({s},{w},{n},{e});
  way["tourism"]({s},{w},{n},{e});
  way["man_made"]({s},{w},{n},{e});
  way["waterway"]({s},{w},{n},{e});
  way["place"]({s},{w},{n},{e});
  node["place"]({s},{w},{n},{e});
  node["tourism"]({s},{w},{n},{e});
  node["amenity"]({s},{w},{n},{e});
  node["natural"]({s},{w},{n},{e});
  node["name"]({s},{w},{n},{e});
  node["harbour"]({s},{w},{n},{e});
  way["harbour"]({s},{w},{n},{e});
);
(._;>;);
out body;
"""


def _cache_path(cfg: LocationConfig):
    return osm_dir() / cfg.osm_filename


def fetch_overpass(cfg: LocationConfig) -> dict:
    s, w, n, e = cfg.bbox
    query = OVERPASS_QUERY.format(s=s, w=w, n=n, e=e).strip()
    body = urllib.parse.urlencode({"data": query}).encode("utf-8")
    last_err = None
    for endpoint in OVERPASS_ENDPOINTS:
        print(f"[osm] Overpass {endpoint}")
        try:
            raw = http_post(endpoint, body, timeout=180)
            return json.loads(raw.decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 — try next mirror
            last_err = exc
            print(f"[osm] failed: {exc}")
    raise RuntimeError(f"Overpass failed: {last_err}")


def _xml_cache_path(cfg: LocationConfig):
    name = cfg.osm_filename.replace(".json", "").replace(".osm", "")
    return osm_dir() / f"{name}.osm"


def fetch_osm_xml(cfg: LocationConfig) -> bytes:
    s, w, n, e = cfg.bbox
    url = f"https://api.openstreetmap.org/api/0.6/map?bbox={w},{s},{e},{n}"
    print(f"[osm] OSM map API {url}")
    return http_get(url, timeout=180, retries=4)


def parse_osm_xml(xml_bytes: bytes, raw_path: str) -> OsmData:
    root = ET.fromstring(xml_bytes)
    nodes: Dict[int, OsmNode] = {}
    ways: List[OsmWay] = []
    relations: List[OsmRelation] = []
    for el in root:
        tag = el.tag.split("}")[-1]
        if tag == "node":
            tags = {c.attrib["k"]: c.attrib["v"] for c in el if c.tag.split("}")[-1] == "tag"}
            nodes[int(el.attrib["id"])] = OsmNode(
                id=int(el.attrib["id"]),
                lat=float(el.attrib["lat"]),
                lon=float(el.attrib["lon"]),
                tags=tags,
            )
        elif tag == 'relation':
            tags={c.attrib['k']:c.attrib['v'] for c in el if c.tag.split('}')[-1]=='tag'}
            members=[dict(type=c.attrib['type'],ref=int(c.attrib['ref']),role=c.attrib.get('role','')) for c in el if c.tag.split('}')[-1]=='member']
            relations.append(OsmRelation(int(el.attrib['id']),tags,members))
        elif tag == "way":
            nds = [int(c.attrib["ref"]) for c in el if c.tag.split("}")[-1] == "nd"]
            tags = {c.attrib["k"]: c.attrib["v"] for c in el if c.tag.split("}")[-1] == "tag"}
            ways.append(OsmWay(id=int(el.attrib["id"]), nodes=nds, tags=tags))
    for w in ways:
        coords = []
        ok = True
        for nid in w.nodes:
            node = nodes.get(nid)
            if node is None:
                ok = False
                break
            coords.append((node.lat, node.lon))
        if ok:
            w.coords = coords
    print(f"[osm] XML nodes={len(nodes)} ways={len(ways)}")
    return OsmData(nodes=nodes, ways=ways, raw_path=raw_path, relations=relations)


def load_or_fetch_osm(cfg: LocationConfig) -> OsmData:
    xml_path = _xml_cache_path(cfg)
    json_path = _cache_path(cfg)
    if xml_path.exists() and xml_path.stat().st_size > 1000:
        print(f"[osm] cache hit {xml_path}")
        return parse_osm_xml(xml_path.read_bytes(), str(xml_path))
    if json_path.exists() and json_path.stat().st_size > 1000:
        print(f"[osm] cache hit {json_path}")
        data = json.loads(json_path.read_text(encoding="utf-8"))
        return parse_osm(data, str(json_path))
    try:
        raw = fetch_osm_xml(cfg)
        xml_path.write_bytes(raw)
        print(f"[osm] wrote {xml_path} ({xml_path.stat().st_size} bytes)")
        return parse_osm_xml(raw, str(xml_path))
    except Exception as exc:  # noqa: BLE001
        print(f"[osm] map API failed ({exc}); trying Overpass")
        data = fetch_overpass(cfg)
        json_path.write_text(json.dumps(data), encoding="utf-8")
        print(f"[osm] wrote {json_path} ({json_path.stat().st_size} bytes)")
        return parse_osm(data, str(json_path))


def parse_osm(data: dict, raw_path: str) -> OsmData:
    nodes: Dict[int, OsmNode] = {}
    ways: List[OsmWay] = []
    relations: List[OsmRelation] = []
    for el in data.get("elements", []):
        t = el.get("type")
        if t == "node":
            nodes[el["id"]] = OsmNode(
                id=el["id"],
                lat=float(el["lat"]),
                lon=float(el["lon"]),
                tags=el.get("tags") or {},
            )
        elif t == "way":
            ways.append(
                OsmWay(
                    id=el["id"],
                    nodes=list(el.get("nodes") or []),
                    tags=el.get("tags") or {},
                )
            )
        elif t == "relation":
            relations.append(OsmRelation(el['id'],el.get('tags') or {},el.get('members') or []))
    for w in ways:
        coords = []
        ok = True
        for nid in w.nodes:
            node = nodes.get(nid)
            if node is None:
                ok = False
                break
            coords.append((node.lat, node.lon))
        if ok:
            w.coords = coords
    print(f"[osm] nodes={len(nodes)} ways={len(ways)}")
    return OsmData(nodes=nodes, ways=ways, raw_path=raw_path, relations=relations)


def way_centroid(way: OsmWay) -> Optional[Tuple[float, float]]:
    if not way.coords:
        return None
    coords = way.coords[:-1] if way.coords[0] == way.coords[-1] else way.coords
    lat = sum(c[0] for c in coords) / len(coords)
    lon = sum(c[1] for c in coords) / len(coords)
    return lat, lon
