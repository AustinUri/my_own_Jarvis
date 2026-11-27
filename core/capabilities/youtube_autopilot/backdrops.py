"""Original storybook sets, painted once per location and camera setup."""
from __future__ import annotations

import math
import random
from functools import lru_cache

from PIL import Image, ImageChops, ImageColor, ImageDraw


# Zenith, horizon, distant hills, wooded hills, meadow, stage floor, foliage.
PALETTES = {
    "woodland": ("#75a7a6", "#fae1a8", "#acc3a4", "#719c81", "#698968", "#d6b484", "#345f59"),
    "stream": ("#8fcbd2", "#ffe6b1", "#b8cbaa", "#82ac95", "#95af7d", "#e2c390", "#46766c"),
    "pond": ("#8fbfc8", "#ffddb1", "#b7c4b1", "#88ac9c", "#95ad7f", "#d3ba89", "#476b5f"),
    "orchard": ("#9ac8c7", "#ffe7bb", "#bfcc9c", "#98ad81", "#99ab76", "#e9bf8d", "#526f55"),
    "meadow": ("#95cbd3", "#ffe6b9", "#afc8ae", "#9bb99e", "#a6ba83", "#e6c38f", "#577f70"),
    "sunset": ("#5d6488", "#ffbe98", "#c39bad", "#977f9b", "#958593", "#d3aa9a", "#555b70"),
    "flower-field": ("#a8c9d2", "#ffe7c0", "#c3c6b2", "#a8b795", "#b4b584", "#ebc593", "#658471"),
    "hill": ("#8fb8c9", "#ffe5b7", "#b0b8b1", "#88a797", "#97b083", "#dfbd8e", "#547466"),
    "garden": ("#9ccdd0", "#ffe6bd", "#b6cab1", "#8faf96", "#9bb887", "#e8c393", "#4e786a"),
}


def _spline(points):
    """Catmull–Rom contour through art-directed knots."""
    knots = [points[0], *points, points[-1]]
    result = []
    for a, b, c, d in zip(knots, knots[1:], knots[2:], knots[3:]):
        for i in range(8):
            t = i / 8
            result.append(tuple(.5 * (2*q + (-p+r)*t + (2*p-5*q+4*r-s)*t*t +
                                      (-p+3*q-3*r+s)*t**3) for p,q,r,s in zip(a,b,c,d)))
    return [*result, points[-1]]


class _Painter:
    # All original contours use a common 400 x 700 drawing board.
    def __init__(self, image):
        self.pen = ImageDraw.Draw(image)
        self.sx, self.sy = image.width / 400, image.height / 700

    def points(self, points):
        return [(round(x*self.sx), round(y*self.sy)) for x,y in points]

    def shape(self, points, fill):
        self.pen.polygon(self.points(points), fill)

    def stroke(self, points, fill, width=1):
        self.pen.line(self.points(points), fill, max(1, round(width*self.sx)), joint="curve")

    def oval(self, x, y, rx, ry, fill):
        self.pen.ellipse(self.points([(x-rx,y-ry), (x+rx,y+ry)]), fill)

    def bank(self, points, fill):
        self.shape([*_spline(points), (440,740), (-40,740)], fill)


def _blade(p, x, y, dx, dy, width, color):
    length = max(1, math.hypot(dx,dy))
    nx, ny = -dy/length*width, dx/length*width
    p.shape(_spline([(x,y),(x+dx*.44+nx,y+dy*.44+ny),(x+dx,y+dy),
                     (x+dx*.60-nx*.65,y+dy*.60-ny*.65),(x,y)]), color)


def _tree(p, rng, x, y, size, palette, fruit=False):
    """Forked trunk and a scalloped crown with small directional brush marks."""
    def at(coords):
        return [(x+a*size,y+b*size) for a,b in coords]
    p.shape(at([(-13,2),(-5,-15),(-7,-111),(-42,-163),(-38,-167),(-6,-136),
                (-13,-199),(-7,-202),(2,-139),(29,-177),(34,-176),(6,-119),
                (10,-18),(15,0),(6,-3),(1,2),(-5,-2)]), "#716858")
    p.stroke(at([(-3,-10),(-1,-65),(-4,-116)]), "#bc9b73", 1.8*size)
    for cx,cy,r in [(-26,-170,35),(21,-183,40),(-5,-210,36)]:
        points = []
        for i in range(90):
            a = i*math.tau/90
            radial = r*(1+.06*math.cos(11*a)+.07*math.sin(3*a+cx))
            points.append((cx+radial*math.cos(a),cy+radial*.85*math.sin(a)))
        p.shape(at(points), palette)
        for _ in range(25):
            u,v = rng.uniform(-.8,.8),rng.uniform(-.76,.7)
            if u*u+v*v>.7:
                continue
            lx,ly=at([(cx+r*u,cy+r*v)])[0]
            _blade(p,lx,ly,4*size,-3*size,1.2*size,"#90aa82")
        if fruit:
            for _ in range(4):
                fx,fy=at([(cx+r*rng.uniform(-.6,.6),cy+r*rng.uniform(-.35,.55))])[0]
                p.oval(fx,fy,3*size,3.8*size,"#d98667")


def _flower(p, x, y, size, color, bend):
    tx,ty=x+bend*size,y-19*size
    p.stroke(_spline([(x,y),(x+size,y-8*size),(tx,ty)]),"#65856c",1.4*size)
    _blade(p,x,y-3*size,6*size,-7*size,1.8*size,"#789574")
    for i in range(5):
        a=i*math.tau/5
        p.oval(tx+math.cos(a)*2.5*size,ty+math.sin(a)*2.5*size,2.3*size,2.1*size,color)
    p.oval(tx,ty,1.5*size,1.5*size,"#c29261")


def _water(p, rng, setting):
    if setting == "stream":
        p.bank([(-25,438),(82,422),(216,410),(350,390),(425,400)],"#77a8a2")
        p.bank([(-25,518),(87,509),(173,481),(288,473),(425,431)],"#dcc49b")
        p.bank([(-25,523),(87,513),(173,484),(288,476),(425,434)],"#c6b789")
        for i in range(42):
            x=rng.uniform(0,400)
            y=rng.uniform(444,495)-x*.13
            p.stroke([(x,y),(x+rng.uniform(4,17),y-.8)],"#aed0c0",1.3)
    else:
        p.shape(_spline([(-20,425),(60,392),(160,382),(239,377),(348,390),(438,410),
                         (462,620),(352,601),(239,574),(181,536),(150,466),(55,456),(-20,450)]),"#79aba7")
        for _ in range(50):
            x,y=rng.uniform(0,400),rng.uniform(399,442)
            p.stroke([(x,y),(x+rng.uniform(2,12),y)],"#bed7c5",1.2)
        for _ in range(50):
            x,y=rng.uniform(205,425),rng.uniform(443,548)
            p.stroke([(x,y),(x+7,y+.6),(x+14,y)],"#98bfb1",1)
        for x,y in [(49,413),(34,422),(294,439),(332,433)]:
            p.oval(x,y,10,2.8,"#799e76")
    for x in [0, 21, 365, 394]:
        y=492 if setting=="stream" and x<40 else 445
        for i in range(6):
            dx=rng.uniform(-16,16)
            _blade(p,x,y,dx,-rng.uniform(17,39),2,"#648973")
        p.stroke([(x,y),(x+4,y-34)],"#718969",1.7)
        p.stroke([(x+4,y-34),(x+5,y-42)],"#a4785d",3.5)


def _fence(p, x, y, length, scale):
    for offset in (8,17):
        p.stroke([(x,y-offset*scale),(x+length,y-offset*scale-3)],"#b09371",2.7*scale)
    for i in range(8):
        u=x+i*length/7
        p.shape([(u-2*scale,y),(u-2*scale,y-21*scale),(u,y-25*scale),
                 (u+2*scale,y-22*scale),(u+2*scale,y)],"#ab8b68")


def _glasshouse(p):
    p.shape([(200,362),(200,312),(227,279),(281,282),(309,315),(309,361)],"#c9d3b7")
    p.shape([(200,312),(227,279),(251,313),(251,361),(200,362)],"#a9c0ae")
    for xs in (200,214,231,250,265,280,295,309):
        p.stroke([(xs,361),(xs,313)],"#f0d8ac",2.5)
    for yy in (314,332,350):
        p.stroke([(200,yy),(308,yy+2)],"#ead4ac",2)
    p.stroke([(194,315),(226,276),(283,279),(314,315)],"#967b63",3)
    p.stroke([(227,278),(251,313),(309,315)],"#ae9476",2)
    p.shape([(212,361),(212,336),(216,328),(223,327),(229,335),(229,361)],"#829c89")


def _willow(p, rng, shade):
    p.shape(_spline([(-30,399),(-5,333),(16,254),(2,183),(-23,117),(-21,72),
                     (7,158),(30,212),(57,193),(72,166),(59,203),(29,237),
                     (20,307),(13,367),(34,396),(-30,399)]),"#776d59")
    for i in range(38):
        x=rng.uniform(-42,88)
        y=94+abs(x)*.65+rng.uniform(-20,25)
        length=rng.uniform(72,148)
        stem=_spline([(x,y),(x+17,y+length*.35),(x+9,y+length*.72),(x+3,y+length)])
        p.stroke(stem,shade,1.8)
        for j in range(1,len(stem),2):
            bx,by=stem[j]
            _blade(p,bx,by,(-1 if j%4==1 else 1)*6,12,2.0,"#739682" if i%3 else shade)


def _conifers(p, rng, shade):
    for x in [-9,5,28,48,331,356,371,396,420]:
        y=rng.uniform(335,376)
        height=rng.uniform(45,115)
        for j in range(4):
            tip=y-height+height*j*.16
            r=(6+j*2.8)*height/90
            p.shape([(x,tip),(x+r*.6,tip+height*.22),(x+r*.47,tip+height*.21),
                     (x+r,tip+height*.37),(x+1,tip+height*.33),(x-r,tip+height*.39),
                     (x-r*.62,tip+height*.23)],shade)


@lru_cache(maxsize=12)
def _plate(setting, width, height):
    sky,glow,far,mid,grass,floor,shade=PALETTES[setting]
    rng=random.Random("nori painted set "+setting)
    # Render scenic contours above preview resolution to retain fine ink lines.
    size=(max(560,width),max(980,height))
    im=Image.new("RGB",size)
    p=_Painter(im)
    top,bottom=ImageColor.getrgb(sky),ImageColor.getrgb(glow)
    for y in range(im.height):
        k=min(1,y/(im.height*.66))
        p.pen.line((0,y,im.width,y),tuple(round(a+(b-a)*k) for a,b in zip(top,bottom)))
    evening=setting=="sunset"
    sx,sy=rng.uniform(60,335),rng.uniform(96,238)
    if not evening and setting!="woodland":
        p.oval(sx,sy,26,26,"#fff1cd")
    if evening:
        for _ in range(42):
            x,y=rng.uniform(0,400),rng.uniform(0,220)
            p.oval(x,y,.8,.9,"#f8e5c0")
    else:
        for cx,cy,s in [(46,126,.7),(181,80,.43),(360,204,.59)]:
            points=[(-56,5),(-42,0),(-34,-6),(-22,-7),(-13,-18),(-2,-19),
                    (10,-9),(18,-10),(31,-2),(40,-1),(58,5),(21,7),(-23,8),(-56,5)]
            p.shape(_spline([(cx+x*s,cy+y*s) for x,y in points]),"#f6edd7")
    ridge=90 if setting=="hill" else 0
    p.bank([(-24,335+45*rng.random()),(35,293+34*rng.random()),(100,300+40*rng.random()),
            (207,277-ridge),(311,255+58*rng.random()),(430,252-ridge)],far)
    p.bank([(-25,350),(63,367),(175,325),(246,346),(340,318),(431,324)],mid)
    # Distant cypress and hedge silhouettes break the horizon.
    for _ in range(52):
        x=rng.uniform(-5,405)
        y=348+math.sin(x/67)*8
        p.oval(x,y,rng.uniform(2,5),rng.uniform(4,15),mid)
    p.bank([(-25,398),(80,367),(179,376),(274,356),(425,373)],grass)
    p.bank([(-25,510),(62,493),(176,505),(279,481),(425,479)],floor)

    if evening:
        _conifers(p,rng,shade)
    if setting in {"stream","pond"}:
        _water(p,rng,setting)
        if setting=="pond":
            _willow(p,rng,shade)
        else:
            # A single masonry span crosses the upstream reach.
            p.shape(_spline([(-22,383),(31,370),(71,367),(121,371),(149,380),(148,395),
                             (124,392),(116,384),(94,381),(79,385),(68,399),
                             (50,403),(42,388),(26,385),(12,391),(5,407),(-22,411)]),"#b39e80")
            p.stroke(_spline([(-18,382),(40,369),(86,367),(147,379)]),"#e0c6a3",3)
    if setting in {"woodland","orchard"}:
        trees=[(-7,428,1.66),(74,390,.80),(314,392,.83),(410,429,1.86)]
        if setting=="orchard":
            trees=[(-13,422,1.15),(59,394,.57),(132,378,.37),(279,372,.38),(347,392,.62),(419,432,1.25)]
        for x,y,s in trees:
            _tree(p,rng,x,y,s,shade,setting=="orchard")
        if setting=="woodland":
            _willow(p,rng,shade)
        else:
            for x in (307,322):
                p.stroke([(x,404),(x+24,321)],"#9e8061",3)
            for j in range(6):
                p.stroke([(309+3.7*j,397-12*j),(323+3.7*j,397-12*j)],"#b3926b",2)
    elif setting in {"garden","meadow","hill"}:
        _fence(p,-20,397,156,.75)
        if setting=="garden":
            _glasshouse(p)
            _fence(p,275,388,145,1)
            _tree(p,rng,1,422,.9,shade,True)
        if setting=="hill":
            p.shape(_spline([(-40,614),(30,558),(139,518),(217,495),(234,465),(301,419),
                             (302,416),(271,459),(266,495),(196,531),(108,576),(35,628),(-40,670)]),"#edce9e")
            # A small mill on the far ridge establishes the hill's scale.
            p.shape([(305,319),(311,286),(320,285),(325,317)],"#dac5a0")
            p.shape([(308,287),(316,279),(323,288)],"#987964")
            for i in range(4):
                a=.48+math.pi*i/2
                x,y=math.cos(a),math.sin(a)
                p.shape([(316,289),(316+21*x,289+21*y),(316+20*x-3*y,289+20*y+3*x),
                         (316+7*x-2*y,289+7*y+2*x)],"#9b8670")
    for _ in range(360):
        x,y=rng.uniform(-5,405),rng.uniform(448,720)
        if setting in {"pond","stream"} and y<520:
            continue
        n=rng.uniform(.6,1.8)*(y/650)
        p.stroke([(x,y),(x+n*3,y-.7*n)],"#c6aa83",n)
    if setting in {"flower-field","meadow","garden","orchard"}:
        for _ in range(130 if setting=="flower-field" else 34):
            x,y=rng.uniform(-10,410),rng.uniform(395,488)
            s=(y-361)/108
            _flower(p,x,y,s,rng.choice(("#f1c2ab","#eee0b0","#cf9788","#c3b3cb")),rng.uniform(-6,6))
    # Large foreground seedlings frame the stage, like ink at the edge of a page.
    for side in (0,400):
        for _ in range(42):
            inset=rng.uniform(-9,51)
            x=inset if side==0 else 400-inset
            y=600+1.6*inset+rng.uniform(-15,55)
            _blade(p,x,y,rng.uniform(-34,34),-rng.uniform(15,68),rng.uniform(2.8,8.0),
                   rng.choice((shade,grass,"#839977")))
        for _ in range(11):
            x=side+rng.uniform(-25,25)
            _flower(p,x,rng.uniform(560,670),rng.uniform(.8,1.6),"#f4d5ac",rng.uniform(-7,7))

    # Low-amplitude, fixed paper grain. Identical scene frames never acquire flicker.
    small=Image.frombytes("L",(180,315),rng.randbytes(180*315)).resize(im.size,Image.Resampling.BILINEAR)
    grain=small.point(lambda v: 124+v//32).convert("RGB")
    im=ImageChops.add(im,grain,offset=-128)
    return im.resize((width,height),Image.Resampling.LANCZOS)


def backdrop(setting, shot, progress, width, height):
    plate=_plate(setting,width,height)
    if shot=="wide":
        return plate.copy()
    zoom={"medium":1.10,"close":1.29,"tracking":1.14}[shot]
    view_w,view_h=round(width/zoom),round(height/zoom)
    pan=.18+.62*progress if shot=="tracking" else .55
    left,top=round((width-view_w)*pan),round((height-view_h)*.57)
    return plate.resize((width,height),Image.Resampling.BILINEAR,
                        box=(left,top,left+view_w,top+view_h))
