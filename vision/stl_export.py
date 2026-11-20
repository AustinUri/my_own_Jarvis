"""Export closed primitive meshes in millimetres (STL, not parametric CAD)."""
from __future__ import annotations

import argparse
import math
from pathlib import Path


def _dimension(value):
    value = float(value)
    if not math.isfinite(value) or not 0 < value <= 5000:
        raise ValueError('Dimensions must be finite and in (0, 5000] mm')
    return value


def box_mesh(width, height, depth):
    x, y, z = map(_dimension, (width, height, depth))
    v = [(0,0,0),(x,0,0),(x,y,0),(0,y,0),(0,0,z),(x,0,z),(x,y,z),(0,y,z)]
    faces = [(0,2,1),(0,3,2),(4,5,6),(4,6,7),(0,1,5),(0,5,4),
             (1,2,6),(1,6,5),(2,3,7),(2,7,6),(3,0,4),(3,4,7)]
    return [tuple(v[i] for i in face) for face in faces]


def cylinder_mesh(diameter, height, segments=64):
    r = _dimension(diameter)/2
    h = _dimension(height)
    if not isinstance(segments, int) or not 12 <= segments <= 512:
        raise ValueError('Segments must be an integer in [12, 512]')
    bottom = [(r*math.cos(2*math.pi*i/segments),r*math.sin(2*math.pi*i/segments),0) for i in range(segments)]
    top = [(x,y,h) for x,y,_ in bottom]
    out = []
    for i in range(segments):
        j = (i+1)%segments
        out.extend([((0,0,0),bottom[j],bottom[i]),((0,0,h),top[i],top[j]),
                    (bottom[i],bottom[j],top[j]),(bottom[i],top[j],top[i])])
    return out


def _normal(a,b,c):
    u = [y-x for x,y in zip(a,b)]
    v = [y-x for x,y in zip(a,c)]
    n = (u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
    length = math.sqrt(sum(x*x for x in n))
    if length == 0:
        raise ValueError('Degenerate triangle')
    return tuple(x/length for x in n)


def write_stl(path, triangles):
    path = Path(path)
    if path.suffix.lower() != '.stl':
        raise ValueError('Output extension must be .stl')
    lines = ['solid jarvis_primitive_mm']
    for a,b,c in triangles:
        lines.append('  facet normal ' + ' '.join(format(x,'.15g') for x in _normal(a,b,c)))
        lines.append('    outer loop')
        for vertex in (a,b,c):
            lines.append('      vertex ' + ' '.join(format(x,'.15g') for x in vertex))
        lines += ['    endloop','  endfacet']
    lines.append('endsolid jarvis_primitive_mm')
    # Refuse overwriting an existing design.
    with path.open('x',encoding='ascii',newline='\n') as stream:
        stream.write('\n'.join(lines)+'\n')
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='shape',required=True)
    box = sub.add_parser('box')
    for name in ('width','height','depth'):
        box.add_argument('--'+name,type=float,required=True)
    cyl = sub.add_parser('cylinder')
    cyl.add_argument('--diameter',type=float,required=True)
    cyl.add_argument('--height',type=float,required=True)
    cyl.add_argument('--segments',type=int,default=64)
    for p in (box,cyl):
        p.add_argument('--out',type=Path,required=True)
    a = parser.parse_args()
    try:
        mesh = box_mesh(a.width,a.height,a.depth) if a.shape=='box' else cylinder_mesh(a.diameter,a.height,a.segments)
        result = write_stl(a.out,mesh)
    except (ValueError,OSError) as exc:
        parser.error(str(exc))
    print(f'Exported {len(mesh)} triangles to {result} (millimetres; STL units implicit).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
