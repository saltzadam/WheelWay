import math
def linestring_start(linestring):
    (l1,l2) = list(linestring.coords)[0]
    return (l1,l2)

def linestring_end(linestring):
    (l1,l2) = list(linestring.coords)[1]
    return (l1,l2)

def linestring_heading(linestring):
    # 0 is true north, 90 is east
    # so heading = 90 - usual_angle (in standard form)
    (l1,l2) = linestring_start(linestring)
    (m1,m2) = linestring_end(linestring)
    angle_deg = math.atan2(m2-l2, m1-l1) * 360 / (2 * math.pi)
    heading_deg = int((90 - angle_deg) % 360)
    return(heading_deg)

# Thank you Sean Gilles https://gist.github.com/sgillies/465156#file_cut.py
from shapely.geometry import LineString, Point

def cut(line, distance):
    # Cuts a line in two at a distance from its starting point
    if distance <= 0.0 or distance >= line.length:
        return [LineString(line)]
    coords = list(line.coords)
    for i, p in enumerate(coords):
        pd = line.project(Point(p))
        if pd == distance:
            return [
                LineString(coords[:i+1]),
                LineString(coords[i:])]
        if pd > distance:
            cp = line.interpolate(distance)
            return [
                LineString(coords[:i] + [(cp.x, cp.y)]),
                LineString([(cp.x, cp.y)] + coords[i:])]
        

# here's me
def recursive_cut(line, distance):
    if [line] == cut(line, distance):
        return [line]
    else:
        segment, rest = cut(line, distance)
        return [segment] + recursive_cut(rest, distance)
