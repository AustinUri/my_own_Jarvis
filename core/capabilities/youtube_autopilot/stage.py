"""Original cutout-style garden cast. Coordinates use a 360-unit portrait stage."""
from __future__ import annotations

from dataclasses import dataclass
from math import atan2, cos, hypot, pi, sin, tau

from PIL import Image, ImageDraw


INK = '#343344'
METAL = '#4e7c7a'
BRASS = '#efbb71'
CREAM = '#fff1ce'


def _ease(t, start=0., end=1.):
    u = max(0., min(1., (t - start) / (end - start)))
    return u * u * (3 - 2 * u)


def _mix(a, b, f):
    return a + (b - a) * f


class Ink:
    """A drawing surface attached to one joint, with cubic outlines for cutouts."""

    def __init__(self, draw, x, y, scale, angle=0., facing=1):
        self.draw = draw
        self.x, self.y = x, y
        self.scale, self.facing = scale, facing
        self.c, self.s = cos(angle), sin(angle)

    def xy(self, x, y):
        x *= self.facing
        return (self.x + self.scale * (self.c*x - self.s*y),
                self.y + self.scale * (self.s*x + self.c*y))

    def child(self, x, y, scale=1., angle=0., facing=1):
        return Ink(self.draw, *self.xy(x, y), self.scale*scale,
                   atan2(self.s, self.c) + angle*self.facing, self.facing*facing)

    def stroke(self, points, color=INK, width=2):
        self.draw.line([self.xy(*point) for point in points], fill=color,
                       width=max(1, round(width*self.scale)), joint='curve')

    def path(self, nodes, fill, outline=INK, width=2):
        points = [nodes[0]]
        for node in nodes[1:]:
            if len(node) == 2:
                points.append(node)
                continue
            x, y = points[-1]
            ax, ay, bx, by, ex, ey = node
            for n in range(1, 9):
                b = n / 8
                a = 1 - b
                points.append((a**3*x + 3*a*a*b*ax + 3*a*b*b*bx + b**3*ex,
                               a**3*y + 3*a*a*b*ay + 3*a*b*b*by + b**3*ey))
        mapped = [self.xy(*point) for point in points]
        if fill:
            self.draw.polygon(mapped, fill=fill)
        if outline:
            if fill:
                mapped.append(mapped[0])
            self.draw.line(mapped, fill=outline, width=max(1, round(width*self.scale)), joint='curve')

    def oval(self, x, y, rx, ry, fill, outline=None, width=1.5):
        self.path([(x + rx*cos(i*tau/24), y + ry*sin(i*tau/24)) for i in range(24)],
                  fill, outline, width)


@dataclass(frozen=True)
class Pose:
    # World-space contact points let props follow the same joint that paints the hand.
    feet: tuple
    hand: tuple
    prop: tuple
    firefly: tuple
    unit: float
    size: float
    turn: float
    stride: float
    lift: float
    crouch: float
    lean: float
    gesture: float
    expression: str
    closed: bool
    time: float
    attached: bool
    roll: float


def drop_times(seconds):
    """Release and two ground contacts in seconds; short edits retain the entire gesture."""
    release = min(.95, .28*seconds)
    fall = min(.36, .21*seconds)
    return release, release + fall, release + 1.65*fall


def sample_pose(scene, progress, seconds, width=360, height=640):
    """Sample choreography relative to the line of narration, independent of frame rate."""
    p = max(0., min(1., progress))
    # The action settles when the line ends. Hover, wings and eyes continue
    # through the short silent reaction before the cut.
    t = max(0., progress) * seconds
    unit = min(width/360, height/560)
    w, h = width/unit, height/unit
    shot, action, key = scene['shot'], scene['action'], scene['prop']
    size = {'wide': 1., 'medium': 1.27, 'tracking': 1.12, 'close': 2.04}[shot]
    base = w * {'wide': .32, 'medium': .31, 'tracking': .34, 'close': .265}[shot]
    floor = h * (.792 if shot == 'close' else .765)
    x = base
    gaze = 1.
    stride = lift = crouch = lean = gesture = roll = 0.
    attached = False
    expression = 'curious'
    prop_x = w * (.72 if shot == 'close' else .705)
    prop_y = floor - size*15
    if key in ('kite', 'balloon', 'bubble'):
        prop_y = h*.44 + sin(t*1.7)*4
    elif key in ('moon', 'cloud', 'rainbow'):
        prop_y = h*.32
    elif key == 'ripple':
        prop_y = floor + size*2
    if action in ('enter', 'follow'):
        walk = _ease(p, .035, .82)
        start, end = (.04, base/w) if action == 'enter' else (.18, .48)
        if action == 'follow' and key == 'snail':
            end = .33
        x = w*_mix(start, end, walk)
        phase = (x - w*start) / (30*size) * pi
        gait = sin(pi*walk)**.45
        stride, lift = sin(phase)*gait, cos(phase)*gait
        lean = .035*gait
        if action == 'follow':
            if key == 'snail':
                prop_x = w*_mix(.51, .67, _ease(p, .01, .96))
            else:
                prop_x = w*_mix(.47, .84, _ease(p, .01, .77))
            if key == 'cloud':
                prop_x = min(w - 44*min(1.66,size), prop_x)
            if key in ('apple','acorn','pebble'):
                roll = (prop_x - w*.47)/(21*min(1.66,size))
                prop_y -= size*abs(sin(roll))*3
            expression = 'eager'
    elif action == 'search':
        gaze = _mix(-1, 1, _ease(p, .18, .75))
        lean = gaze*.09
        gesture = sin(pi*min(1., p/.94))**.45
        expression = 'puzzled' if p < .73 else 'curious'
    elif action == 'hop':
        flight = _ease(p, .27, .73)
        x += 24*size*flight
        lift = -34*sin(pi*flight)
        stride = .9*sin(pi*flight)
        crouch = 11*(sin(pi*_ease(p, .03, .30)) + .75*sin(pi*_ease(p, .69, .94)))
        gesture = sin(pi*flight)
        expression = 'joyful'
    elif action in ('point', 'watch', 'discover'):
        gesture = _ease(p, .12, .47) * (1 - .16*_ease(p, .78, 1))
        lean = (.095 if action == 'watch' else .045)*gesture
        if action == 'discover':
            lift = -9*sin(pi*_ease(p, .23, .52))
            expression = 'amazed' if .21 < p < .65 else 'joyful'
    elif action in ('cheer', 'wave'):
        gesture = _ease(p, .07, .29) * (1 - .74*_ease(p, .78, 1))
        if action == 'cheer':
            lift = -13*abs(sin(pi*2*_ease(p, .19, .85)))
        expression = 'joyful'
    elif action == 'carry':
        reach, hoist, walk = _ease(p, .06, .34), _ease(p, .36, .60), _ease(p, .63, .97)
        crouch = 24*reach*(1-hoist)
        x += w*.18*walk
        stride = sin(walk*2.7*pi)*sin(pi*walk)
        attached = p >= .34
        lean = .12*reach*(1-hoist)
        gesture = hoist
        expression = 'intent' if p < .54 else 'joyful'
    elif action == 'drop':
        release, impact, settle = drop_times(seconds)
        attached = t < release
        gesture = _ease(t, 0., release)
        recoil = sin(pi*_ease(t, release, impact))
        lean = .05*gesture - .08*recoil
        expression = 'intent' if attached else ('amazed' if t < settle else 'joyful')
    else:
        raise ValueError(f'Unknown stage action {action!r}')

    feet_y = floor + (lift if action in ('hop','discover','cheer') else -abs(stride)*2)*size
    hand_x, hand_y = 32 + stride*13, -51 + crouch
    if action == 'search':
        hand_x, hand_y = _mix(32, 27, gesture), _mix(-51, -126, gesture)
    elif action in ('point', 'watch', 'discover'):
        dx, dy = prop_x - x, prop_y - (feet_y - size*86)
        length = max(1, hypot(dx, dy))
        extension = {'point': 43, 'watch': 20, 'discover': 32}[action]
        hand_x = _mix(32, 22 + extension*dx/length, gesture)
        hand_y = _mix(-51, -86 + extension*dy/length, gesture)
    elif action in ('wave','cheer','hop'):
        hand_x = _mix(32, 53 + 7*sin(t*6), gesture)
        hand_y = _mix(-51, -115 - 4*cos(t*6), gesture)
    elif action == 'carry':
        hand_x = _mix(30, 43, reach)
        hand_y = _mix(_mix(-51, -22, reach), -77, hoist)
    elif action == 'drop':
        hand_x = 40 + 5*gesture - 13*recoil
        hand_y = -71 - 12*gesture - 9*recoil
    hand = (x + size*hand_x, feet_y + size*hand_y)
    if action == 'carry':
        if key in ('kite', 'balloon'):
            prop_x = min(w*.82, x + size*85)
            prop_y = floor - size*150 + 5*sin(t*1.4)
        elif attached:
            prop_x, prop_y = hand[0] + size*10, hand[1] + size*6
        else:
            prop_x, prop_y = base + size*53, floor - size*16
    elif action == 'drop':
        if attached:
            prop_x, prop_y = hand[0] + size*10, hand[1] + size*6
        else:
            start_x, start_y = x + size*55, floor - size*77
            ground = floor - size*16
            fall = min(1., (t-release)/(impact-release))
            bounce = max(0., min(1., (t-impact)/(settle-impact)))
            prop_x = start_x + size*(13*fall + 7*bounce)
            prop_y = _mix(start_y, ground, fall*fall) - size*10*4*bounce*(1-bounce)
            roll = .38*fall + .13*bounce
    swoop = _ease(p, .08, .75)
    bx = _mix(w*.54, min(w*.86, prop_x + 19*size), swoop)
    by = _mix(floor - size*171, max(h*.16, prop_y - size*69), swoop)
    if action == 'enter':
        bx += (1 - swoop)*w*.39
    if action == 'search':
        bx += sin(p*tau)*w*.075
    bx += 7*sin(t*2.1)
    by += 5*sin(t*2.7) - 20*sin(pi*swoop)
    if scene.get('cast_version') == 2:
        if action in ('cheer','hop'):
            arc = _ease(p, .19, .80)
            bx += size*24*sin(tau*arc)
            by -= size*31*sin(pi*arc)**2
        elif action == 'discover':
            surprise = sin(pi*_ease(p, .23, .57))
            bx += size*12*surprise
            by -= size*26*surprise
        elif action == 'watch':
            by += size*19*sin(pi*_ease(p, .22, .85))
        elif action == 'drop':
            by -= size*22*sin(pi*_ease(t, impact, settle+.25))
    return Pose((x, feet_y), hand, (prop_x, prop_y), (bx, by), unit, size, gaze,
                stride, lift, crouch, lean, gesture, expression,
                (t + scene.get('motion_variant',0)%13*.13) % 3.2 < .13, t, attached, roll)


def _tube(pen, a, b, c, color, width):
    pen.stroke((a, b, c), INK, width + 3)
    pen.oval(*b, (width+3)/2, (width+3)/2, INK)
    pen.stroke((a, b, c), color, width)
    pen.oval(*b, width/2, width/2, color)


def _boot(pen, x, y, tilt):
    boot = pen.child(x, y, angle=tilt)
    boot.path([(-8,-12),(4,-13),(6,-7),(17,-7,20,-3,19,0),
               (13,4,-6,4,-11,1),(-12,-3,-10,-9,-8,-12)], '#614852')
    boot.path([(-10,0),(-2,2,10,2,19,-1)], None, BRASS, 2.3)
    boot.stroke([(-4,-9),(3,-7)], '#e7ad80', 1.5)


def _hand(pen, x, y, point=False, angle=0., open_palm=False):
    mitten = pen.child(x,y,angle=angle)
    if open_palm:
        mitten.path([(-6,5),(-10,-1,-6,-9,-3,-8),(0,-6),(4,-12,8,-12,8,-8),
                     (7,-5),(13,-11,17,-8,14,-4),(10,0),(18,-4,21,0,16,4),
                     (11,8,4,10,-2,9)],CREAM)
    elif point:
        mitten.path([(-7,-3),(-6,-8,-3,-9,0,-6),(11,-9,19,-9,20,-6),
                     (20,-3,13,-2,7,-1),(8,6,3,9,-2,8),(-8,8,-10,1,-7,-3)], CREAM)
    else:
        mitten.path([(-7,-3),(-8,-8,-3,-11,0,-6),(3,-11,8,-9,8,-5),
                     (14,-5,13,1,10,5),(7,11,-3,11,-7,4),(-9,2,-9,-1,-7,-3)], CREAM)
        mitten.stroke([(5,-2),(5,2)], '#cd916e', 1.3)


def _nori(pen, pose, action):
    """Boots, sleeves, faceplate, cap and antenna can move independently."""
    x, y = pose.feet
    rig = pen.child(x, y, pose.size)
    stride, crouch, turn = pose.stride, pose.crouch, pose.turn
    for side in (-1,1):
        foot_x = side*14 + side*stride*13
        foot_y = -max(0, side*stride)*8
        knee = (side*15+4+side*stride*5 + crouch*.43, -22+crouch*.33)
        _tube(rig, (side*13,-42+crouch*.66), knee, (foot_x,foot_y-8), METAL, 7)
        _boot(rig, foot_x, foot_y, side*stride*.21)
    body = rig.child(0, crouch, angle=pose.lean)
    far_hand = (-29-stride*13, -52)
    if action in ('cheer','hop'):
        far_hand = (-34-12*pose.gesture, -52-57*pose.gesture)
    _tube(body,(-22,-83),(-37,-69),far_hand,'#568986',8)
    _hand(body,*far_hand)
    # Dark rim and contrasting stitched bib keep the body readable against foliage.
    body.path([(-21,-92),(-11,-98,10,-99,23,-91),(29,-82,31,-52,24,-41),
               (11,-34,-13,-35,-26,-42),(-31,-56,-30,-80,-21,-92)], '#396c70')
    body.path([(-22,-89),(-15,-87),(-10,-72,9,-71,16,-88),(23,-90),
               (23,-77,24,-53,22,-44),(10,-40,-11,-40,-23,-46)], '#74a798')
    body.path([(-13,-66),(13,-66),(13,-53,7,-49,0,-49),(-9,-50,-13,-53,-13,-66)], '#477f77', '#344c51', 1.4)
    body.path([(-1,-54),(-6,-60,-5,-63,-5,-63),(2,-63,6,-59,-1,-54)], '#f4d180', None)
    for sx in (-17,17):
        body.oval(sx,-83,2.5,2.5,BRASS,INK,1)
    body.path([(-16,-97),(-3,-91,12,-93,21,-97),(17,-85,6,-81,-3,-84),
               (-9,-85,-15,-90,-16,-97)], '#d96241')
    body.path([(-9,-90),(-13,-79,-22,-72,-31,-74),(-26,-80),(-33,-82),
               (-24,-84,-21,-92,-16,-94)], '#e77b49')
    # Two-link arm bends around an elbow instead of scaling to the target.
    shoulder = (x + pose.size*(22 + pose.lean*76), y + pose.size*(-76+crouch))
    hx, hy = pose.hand
    dx, dy = hx-shoulder[0], hy-shoulder[1]
    distance = max(1.,hypot(dx,dy))
    bend = min(14*pose.size, max(0, (57*pose.size-distance)*.51))
    elbow = ((hx+shoulder[0])/2 - bend*dy/distance, (hy+shoulder[1])/2 + bend*dx/distance)
    if action == 'search':
        elbow = (elbow[0]+13*pose.size*pose.gesture, elbow[1])
    # A dipped head, sliding three-quarter face and asymmetric brows sell a turn.
    head = body.child(0,-104,angle=(turn*.038 + (.09 if pose.expression=='puzzled' else 0)))
    head.oval(-30,-10,8,13,BRASS,INK,2.4)
    head.path([(-32,-26),(-28,-43,3,-47,25,-37),(39,-34,45,-20,42,-4),
               (40,10,30,21,11,23),(-12,26,-31,18,-35,5),(-38,-7,-37,-19,-32,-26)], '#c89b67')
    face = head.child(turn*3,0)
    face.path([(-28,-23),(-13,-35,18,-34,31,-25),(39,-17,39,0,32,11),
               (22,22,0,23,-16,17),(-28,13,-34,-7,-28,-23)], '#ffedcc', INK,2)
    face.path([(-25,5),(-21,11,-16,14,-7,16)], None,'#d6ae83',1.4)
    gaze_y = max(-1., min(1., (pose.prop[1]-y+pose.size*112)/(pose.size*70)))
    for ex in (-10,18):
        eye = ex + turn*2
        ey = -7 + (1 if ex<0 else 0)
        if pose.closed:
            face.path([(eye-5,ey),(eye-2,ey-2,eye+2,ey-2,eye+5,ey)],None,INK,2.6)
        else:
            face.oval(eye,ey,6.4,8.2,'#fff8df',INK,1.2)
            pupil = eye + turn*1.7
            face.oval(pupil,ey+gaze_y*1.5,4.1,5.6,INK)
            face.oval(pupil-.7,ey+gaze_y*1.5-2,1.3,1.5,'#fff8df')
        brow = -19 if pose.expression in ('amazed','puzzled') else -17
        end = brow-2 if ex>0 and pose.expression=='puzzled' else brow+.8
        face.path([(eye-5,brow),(eye-3,brow-2,eye+3,end-2,eye+5,end)], None, '#694e43', 1.7)
    for cheek in (-19,27):
        face.oval(cheek,4,5.8,2.8,'#edb291')
        face.oval(cheek-2,3.5,.8,.8,'#a36d5d')
    mx = 4 + turn*3
    if pose.expression == 'amazed':
        face.oval(mx,7,3.5,4.8,'#713f3e',INK,1)
    elif pose.expression in ('joyful','eager'):
        face.path([(mx-6,6),(mx-3,8,mx+2,8,mx+7,4),(mx+6,15,mx-4,17,mx-6,6)], '#934b46',INK,1.4)
    else:
        face.path([(mx-4,7),(mx-1,10,mx+4,9,mx+7,5)],None,INK,1.7)
    # Gardener's soft cap with piping, a stitched panel, and a sprung brass antenna.
    head.path([(-35,-21),(-41,-34,-35,-47,-22,-53),(-12,-57,0,-51,7,-54),
               (22,-53,32,-44,35,-29),(14,-34,-13,-24,-35,-21)], '#347c79')
    head.path([(-34,-26),(-23,-40,-16,-47,-11,-49)],None,'#77b4a2',2.4)
    head.path([(-2,-51),(10,-47,16,-43,19,-35)],None,'#2d605f',1.5)
    head.path([(-35,-25),(-21,-28,-5,-35,20,-37),(36,-39,45,-38,48,-33),
               (44,-28,34,-27,21,-28),(-5,-26,-23,-17,-34,-20)], BRASS)
    head.path([(-29,-24),(-15,-27,-5,-31,16,-33)],None,'#ffe3a0',1.7)
    head.oval(-30,-12,7.5,10,'#b59065',INK,1.8)
    head.oval(-30,-12,3.4,5,'#edc990','#816954',1)
    sway = sin(pose.time*3.8)*2 - stride*2
    head.path([(-22,-49),(-32,-55,-27,-62,-35+sway,-66)],None,INK,2.8)
    head.path([(-35+sway,-64),(-44+sway,-65,-47+sway,-72,-44+sway,-76),
               (-35+sway,-77,-29+sway,-71,-35+sway,-64)], '#f4bd6d', INK,1.8)
    _tube(pen,shoulder,elbow,pose.hand,'#5b9290',8*pose.size)
    pen.oval(*shoulder,4.6*pose.size,4.6*pose.size,'#69978d',INK,1.3*pose.size)
    pen.oval(*elbow,3.4*pose.size,3.4*pose.size,BRASS,INK,1.3*pose.size)
    _hand(rig,(hx-x)/pose.size,(hy-y)/pose.size,
          action == 'point' and pose.gesture>.5,
          atan2(hy-shoulder[1],hx-shoulder[0])*.65 if action == 'point' else 0.,
          open_palm=action == 'drop' and not pose.attached)


def _blink(pen, pose, scene, progress):
    x,y = pose.firefly
    facing = 1 if pose.prop[0] >= x else -1
    acting = scene.get('cast_version') == 2
    mood = pose.expression if acting else 'curious'
    bank = .075*sin(pose.time*3.1)
    pulse = 0.
    if acting:
        turn = sin(pi*_ease(progress, .14, .80))
        bank += facing*turn*(.30 if scene['action'] in ('search','watch','follow') else -.23)
        pulse = (1 + cos(6*pose.time))*.5 * (1 if mood in ('amazed','joyful') else .25)
    bug = pen.child(x,y, (.18+.76*pose.size), bank, facing)
    flap = .5+.5*cos(pose.time*(20 if mood in ('amazed','joyful') else 16))
    bug.oval(-16,8,20+flap+4*pulse,16+flap+3*pulse,(255,228,134,44+round(35*pulse)))
    bug.oval(-16,8,14,13,(255,229,131,72))
    for dx, tilt in ((-8,-.36),(0,.16)):
        wing = bug.child(dx,-5,angle=tilt - .32*flap)
        length = 12 + 16*flap
        wing.path([(0,3),(-12,-2,-23,-length,-14,-length-3),
                   (-5,-length-7,5,-7,0,3)],'#e3f3d4','#527b78',1.5)
        wing.path([(-1,0),(-5,-5,-8,-length*.76,-13,-length)],None,'#a8cfc1',1.2)
    bug.path([(0,2),(-7,0,-15,0,-22,5),(-27,9,-25,14,-18,15),
              (-8,18,2,12,4,7)],'#ffd270',INK,1.8)
    bug.path([(-22,8),(-21,12,-17,13,-14,12)],None,'#fff6b8',2.2)
    bug.path([(-9,3),(-4,6,-5,11,-6,13)],None,'#b6864d',2)
    for start,end in [((-3,11),(-6,16)),((2,10),(4,16))]:
        bug.stroke([start,end,(end[0]+2,end[1])],INK,1.4)
    bug.path([(0,-9),(7,-16,18,-13,21,-6),(26,2,19,10,11,11),
              (3,13,-3,6,-3,0)],'#dfa958',INK,1.7)
    if acting and (pose.time+.8) % 2.8 < .14:
        bug.path([(6,-1),(8,-4,11,-4,14,-1)],None,INK,1.7)
    else:
        height = 6.8 if mood == 'amazed' else 5.2
        bug.oval(10,-2,4.3,height,CREAM,INK,1)
        pupil_y = 0 if acting and scene['action'] in ('watch','drop','carry') else -1.7
        bug.oval(11.4,pupil_y,2,3,INK)
    bug.oval(20,-.8,1.7,2.6,INK)
    if mood == 'amazed':
        bug.oval(15.5,6.0,2.0,2.8,'#884c46',INK,1)
    elif mood == 'puzzled':
        bug.path([(6,-9),(8,-12,12,-11,14,-9)],None,INK,1.2)
        bug.path([(12,6),(15,3,17,4,18,5)],None,INK,1.3)
    else:
        bug.path([(12,5),(14,7,17,7,18,4)],None,INK,1.3)
    for ax,ay,tip in [(6,-11,2),(12,-12,17)]:
        bug.path([(ax,ay),(ax-2,-17,tip+2,-20,tip,-21)],None,INK,1.3)
        bug.oval(tip,-21,2,2,BRASS,INK,1)


def _prop(pen, pose, scene):
    key = scene['prop']
    x, y = pose.prop
    bob = sin(pose.time*2.5)
    s = min(1.66, pose.size)
    obj = pen.child(x,y,s,pose.roll)
    if key == 'leaf':
        leaf = obj.child(0,0,angle=bob*.08)
        leaf.path([(-28,7),(-21,-7,-19,-14,-8,-15),(3,-19,15,-12,30,-15),
                   (27,-1,20,14,1,15),(-9,16,-17,11,-28,7)], '#67aa75')
        leaf.path([(-32,12),(-15,3,9,1,26,-12)],None,'#375c50',2)
        for ax, ay, bx, by in [(-17,5,-12,-8),(-3,1,1,-11),(5,-1,17,2)]:
            leaf.stroke([(ax,ay),(bx,by)],'#d7dc91',1.4)
    elif key == 'snail':
        obj.path([(-27,11),(-16,13,-7,10,0,6),(9,0,11,-7,17,-8),
                  (24,-11,29,-6,30,-2),(27,3,21,5,18,7),(9,16,-6,19,-27,15)],'#eebb79')
        obj.path([(-22,6),(-30,-7,-20,-20,-9,-21),(4,-23,14,-13,12,-2),
                  (11,9,4,13,-8,12),(-15,12,-20,9,-22,6)],'#d27c64')
        obj.path([(-16,6),(-27,-4,-15,-18,-4,-15),(7,-13,10,0,0,5),
                  (-9,9,-15,-2,-8,-6),(-3,-9,2,-5,-1,-2)],None,'#713e4a',2)
        for ex,ey in ((19,-15+bob),(26,-12-bob)):
            obj.stroke([(18,-5),(ex,ey)],INK,1.8)
            obj.oval(ex,ey,2.1,2.4,INK)
    elif key == 'apple':
        obj.path([(0,-15),(-15,-24,-26,-13,-24,1),(-23,13,-16,22,-8,21),
                  (-3,19,0,18,5,20),(15,22,25,9,25,-4),(26,-16,13,-24,0,-15)],'#d8524c')
        obj.path([(-19,1),(-19,-6,-16,-12,-11,-13)],None,'#ffac78',3)
        obj.path([(1,-13),(0,-20,2,-25,6,-29)],None,'#614939',3)
        obj.path([(4,-21),(3,-29,15,-32,22,-29),(20,-23,11,-19,4,-21)],'#68a06d',INK,1.3)
    elif key in ('kite','balloon'):
        obj = obj.child(0,0,angle=.09*bob)
        if key == 'kite':
            obj.path([(0,-34),(25,-4),(1,33),(-26,-4)],'#e69a59')
            obj.path([(0,-34),(-26,-4),(0,0)],'#88c2b1',INK,1)
            obj.path([(0,0),(25,-4),(1,33)],'#e8cc75',INK,1)
            obj.stroke([(0,-34),(1,33)],'#665450',1.4)
            obj.path([(1,33),(18,44,-18,53,-8+bob*6,64)],None,'#704f4c',1.8)
            for k in range(2):
                knot = obj.child(2-k*6,41+k*12,angle=.12*bob)
                knot.path([(-6,-4),(0,-1),(6,-4),(5,4),(0,1),(-6,3)],'#ce6e62',INK,1)
        else:
            obj.path([(0,21),(-8,18,-23,7,-22,-9),(-23,-33,6,-40,18,-22),
                      (32,-4,12,17,0,21)],'#dc806b')
            obj.path([(-1,20),(-4,25),(4,25),(2,20)],'#b55b51',INK,1)
            obj.path([(-16,-9),(-17,-16,-13,-22,-8,-23)],None,'#ffdbb0',3)
            if scene['action'] != 'carry':
                obj.path([(0,25),(8,38,-8,44,2+bob*4,62)],None,'#735953',1.3)
        if scene['action'] == 'carry':
            hx,hy = pose.hand
            py = y+s*(0 if key=='kite' else 24)
            pen.path([(x,py),(x-4,py+25,hx+17,hy+2,hx,hy)],None,'#695754',1.5)
    elif key == 'bubble':
        obj.oval(0,0,22,22,None,'#486f85',2.4)
        obj.path([(-20,3),(-23,-13,-7,-23,6,-19)],None,'#fff5d4',3.6)
        obj.path([(20,-4),(24,6,15,20,4,21)],None,'#e5aaad',3.2)
        obj.oval(-9,-11,4.5,2.6,'#fff8de')
        obj.oval(12,10,2,2,'#f3e3e8')
    elif key == 'pebble':
        obj.path([(-23,8),(-26,0,-17,-10,-8,-13),(3,-17,16,-10,22,-3),
                  (30,7,23,13,9,14),(-4,16,-19,16,-23,8)],'#8a9caa')
        obj.path([(-18,2),(-12,-6,-4,-8,4,-7)],None,'#c4ceca',2.5)
        obj.path([(-8,11),(3,11,11,9,17,6)],None,'#617a89',1.5)
    elif key == 'acorn':
        obj.path([(-16,-4),(-17,10,-8,17,1,21),(3,24),(7,18,18,13,18,-4)],'#b66e45')
        obj.path([(0,14),(10,9,11,5,12,-1)],None,'#e6aa67',2)
        obj.path([(-21,-5),(-20,-25,15,-29,21,-11),(23,-7,21,-4,18,-4),
                  (8,-3,-11,-1,-21,-5)],'#79604c')
        for ax,ay in [(-12,-10),(-4,-14),(4,-11),(11,-14)]:
            obj.stroke([(ax-2,ay-1),(ax,ay+1),(ax+2,ay-1)],'#b89771',1.5)
        obj.path([(0,-21),(3,-24,1,-27,5,-30)],None,'#624e41',3)
    elif key == 'moon':
        obj.path([(13,-31),(-9,-24,-8,7,13,14),(23,17,29,13,33,8),
                  (29,32,-1,40,-21,23),(-48,0,-25,-40,3,-34),(8,-34,10,-33,13,-31)],'#f5d790')
        obj.path([(-23,-12),(-29,-1,-26,9,-19,14)],None,'#e3b974',2)
        for xx,yy in [(23,-19),(32,-3)]:
            obj.path([(xx,yy-4),(xx+1,yy-1),(xx+4,yy),(xx+1,yy+1),
                      (xx,yy+4),(xx-1,yy+1),(xx-4,yy),(xx-1,yy-1)],'#fff0bd',None)
    elif key == 'cloud':
        obj.path([(-36,7),(-43,-4,-35,-15,-25,-14),(-23,-28,-4,-31,4,-18),
                  (15,-25,30,-19,30,-8),(45,-7,45,10,34,13),
                  (19,15,-7,12,-21,14),(-28,15,-34,13,-36,7)],'#fff1d3')
        obj.path([(-29,8),(-12,11,13,6,31,8)],None,'#d8c8b6',2)
    elif key == 'ripple':
        for i in range(3):
            span = 12+12*i+2*bob
            obj.path([(-span,-4*i),(-span-2,6*i+4,span-4,7*i+3,span,-3*i)],
                     None,['#f1e8bd','#83c8bc','#458a94'][i],2.5)
        obj.path([(-2,-9),(0,-14,4,-17,3,-20),(9,-13,9,-7,4,-6)],'#80c9ce',INK,1.1)
    elif key == 'rainbow':
        rainbow = obj.child(0,0,.81)
        for i,col in enumerate(['#9e6764','#dc8071','#e9ac6c','#edce80','#8cba92','#76a6ae']):
            r = 46-i*4.5
            rainbow.path([(-r,9),(-r,-r*1.45,r,-r*1.45,r,9)],None,col,5.5)
    else:
        raise ValueError(f'Cannot draw story prop {key!r}')


def draw_stage(image, scene, progress, seconds, *, include_prop=True):
    """Composite one posed cast and the featured story object onto the set."""
    w,h = image.size
    pose = sample_pose(scene, progress, seconds, w,h)
    # Supersample small previews to retain curved silhouettes and fine ink details.
    ss = 2 if w < 720 else 1
    layer = Image.new('RGBA',(w*ss,h*ss))
    stage = Ink(ImageDraw.Draw(layer),0,0,pose.unit*ss)
    x,y = pose.feet
    shadow_y = h/pose.unit * (.792 if scene['shot']=='close' else .765)
    stage.oval(x,shadow_y+2,29*pose.size,4*pose.size,(50,51,55,57))
    if include_prop and scene['prop'] in ('leaf','pebble','snail','apple','acorn'):
        px,py = pose.prop
        stage.oval(px,shadow_y+1,20*pose.size,3.2*pose.size,(50,51,55,46))
    _nori(stage,pose,scene['action'])
    if include_prop:
        _prop(stage,pose,scene)
        if pose.attached and scene['prop'] not in ('kite','balloon'):
            hx,hy = pose.hand
            stage.oval(hx+pose.size*3,hy+pose.size*2,4*pose.size,2.7*pose.size,CREAM,INK,1.1*pose.size)
    _blink(stage,pose,scene,progress)
    if ss != 1:
        layer = layer.resize((w,h),Image.Resampling.LANCZOS)
    image.paste(layer,(0,0),layer)
    return pose
