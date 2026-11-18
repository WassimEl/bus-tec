"""Télécharge le GTFS du TEC et génère data.json (zone Charleroi).
Usage : python prep.py   -> crée data.json à mettre à côté de index.html"""
import csv, io, json, zipfile, urllib.request
from collections import defaultdict, Counter

URL = "https://data.gtfs.be/tec/gtfs/be-tec-gtfs.zip"
LAT, LON = (50.36, 50.49), (4.33, 4.56)  # Grand Charleroi (Courcelles, Gosselies, Fleurus, Châtelet, Montigny-le-Tilleul)

z = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(URL).read()))
rd = lambda n: csv.DictReader(io.TextIOWrapper(z.open(n), 'utf-8-sig'))
sec = lambda s: (lambda h, m, x: h * 3600 + m * 60 + x)(*map(int, s.split(':')))

stops, sx = {}, []
for r in rd('stops.txt'):
    a, o = float(r['stop_lat']), float(r['stop_lon'])
    if LAT[0] <= a <= LAT[1] and LON[0] <= o <= LON[1]:
        stops[r['stop_id']] = len(sx)
        sx.append([r['stop_id'], r['stop_name'], round(a, 5), round(o, 5)])

trips = {r['trip_id']: r for r in rd('trips.txt')}
st = defaultdict(list)
for r in rd('stop_times.txt'):
    if r['stop_id'] in stops:
        st[r['trip_id']].append((int(r['stop_sequence']), stops[r['stop_id']], sec(r['departure_time'])))

cal = {r['service_id']: [''.join(r[d] for d in 'monday tuesday wednesday thursday friday saturday sunday'.split()),
                         int(r['start_date']), int(r['end_date']), [], []] for r in rd('calendar.txt')}
for r in rd('calendar_dates.txt'):
    c = cal.setdefault(r['service_id'], ['0000000', 0, 0, [], []])
    c[3 if r['exception_type'] == '1' else 4].append(int(r['date']))
sid = list(cal)
sidx = {k: i for i, k in enumerate(sid)}

pl, pk, tr, sh = [], {}, [], defaultdict(Counter)
for tid, rows in st.items():
    t = trips[tid]
    if len(rows) < 2 or t['service_id'] not in sidx:
        continue
    rows.sort()
    ss = tuple(r[1] for r in rows)
    o0 = rows[0][2]
    off = tuple(r[2] - o0 for r in rows)
    k = (t['route_id'], ss, off)
    if k not in pk:
        pk[k] = len(pl)
        pl.append([t['route_id'], list(ss), list(off)])
    tr.append([pk[k], sidx[t['service_id']], o0])
    sh[t['route_id']][t.get('shape_id', '')] += 1

best = {r: c.most_common(1)[0][0] for r, c in sh.items()}
want, pts = set(best.values()), defaultdict(list)
for r in rd('shapes.txt'):
    if r['shape_id'] in want:
        pts[r['shape_id']].append((int(r['shape_pt_sequence']), round(float(r['shape_pt_lat']), 5), round(float(r['shape_pt_lon']), 5)))

R = {}
for r in rd('routes.txt'):
    if r['route_id'] in best:
        R[r['route_id']] = [r['route_short_name'], '#' + (r.get('route_color') or '555555'),
                            [p[1:] for p in sorted(pts[best[r['route_id']]])][::3]]

json.dump({'stops': sx, 'pats': pl, 'trips': tr, 'svc': [cal[s] for s in sid], 'R': R},
          open('data.json', 'w'), separators=(',', ':'))
print(len(sx), 'arrêts,', len(tr), 'trajets,', len(R), 'lignes')
