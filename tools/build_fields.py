"""Draw the twelve career-library field plates. Requires Pillow and NumPy.

Run python -B tools/build_fields.py with optional field names to render a subset.
"""
import argparse
import math
from PIL import Image

from build_art import ROOT, STOCKS, backing, grain, mix, oval, path

PAPER = 'f4ecd6'


def rounded(x, y, w, h, r):
    points = []
    for cx, cy, angle in [(x+w-r, y+r, -90), (x+w-r, y+h-r, 0),
                          (x+r, y+h-r, 90), (x+r, y+r, 180)]:
        points.extend(oval(cx, cy, r, r, angle, angle+90))
    return points


def cut(p, outline, fill, ink, slope=-.75, spacing=4):
    p.shape(outline, fill, ink, 1.12)
    p.hatch(outline, mix(fill, ink, .38), spacing, slope, .49)


def software(p, stock):
    _, ink, sage, amber = stock
    q = p.at(214, 57, -3)
    shell = 'c9cbb5'
    # The taper of the enclosure and a curved phosphor screen date the terminal.
    q.shape([(0,6),(20,-9),(121,-9),(147,0),(139,72),(124,85),(5,84)], shell, ink, 1.3)
    cut(q, [(122,4),(147,0),(139,72),(124,85)], '9ba994', ink, -.9, 3.8)
    q.shape(rounded(0,2,126,82,6), 'd8d9c5', ink, 1.35)
    q.shape(rounded(8,10,110,60,9), sage, ink, 1.05)
    q.shape(path((15,19),(22,13,100,12,109,18),(114,23,113,52,108,59),
                 (99,65,29,66,17,60),(12,55,11,27,15,19)), '4b665b', ink, 1.1)
    for y in range(22,59,4):
        q.line([(18,y),(108,y)], '647d6b', .45)
    # A bracketed block of instructions stays clear even without rendered text.
    for left, y, widths in [(23,26,[12,9]),(30,33,[6,16,8]),(36,40,[19,10]),(30,47,[12]),(23,54,[5])]:
        for width in widths:
            q.line([(left,y),(left+width,y)], 'e2dfb6', 1.4)
            left += width+4
    q.el(114,76,2,2,amber,ink,.7)
    q.box(12,74,22,2.2, '98a58e')
    q.shape([(24,84),(108,84),(104,94),(22,94)],sage,ink,.95)
    # Sloped keyboard unit with recessed, staggered keycaps.
    q.shape([(-10,99),(108,98),(135,119),(5,122),(-12,114)],sage,ink,1.25)
    q.shape([(-11,99),(104,96),(133,114),(4,118)],'d8d6bc',ink,1)
    key = q.at(-3,101,-1,1,1,.87)
    for row, count in enumerate([13,12,11]):
        for col in range(count):
            key.box(col*7.6+row*.8,row*4.2,5.9,2.85,'e6e5ce',ink,.55)
    key.box(29,12.3,40,2.7,'c7ccb5',ink,.55)
    # Write-protect tab, metal shutter, label and rivets of a floppy disk.
    disk = p.at(381,105,9)
    disk.shape([(0,0),(52,0),(59,7),(59,60),(0,60)],'83978a',ink,1.32)
    disk.box(12,0,34,18,'c0c5af',ink,.8)
    disk.box(33,3,7,12,ink)
    disk.box(7,28,46,26,PAPER,ink,.75)
    disk.box(8,28,44,4,amber)
    for y in [39,44,49]:disk.line([(12,y),(47,y)],sage,.56)
    for x in [3,54]:disk.box(x,54,2.8,2.8,ink)


def finance(p, stock):
    _, ink, mid, gold = stock
    q=p.at(195,89,-5)
    # A printing calculator with the ribbon threading behind its display.
    tape=path((60,7),(65,-11,36,-10,35,-28),(34,-40,42,-46,51,-52),(98,-52),
              (88,-43,82,-37,84,-27),(86,-13,109,-12,108,7))
    q.shape(tape,PAPER,ink,1.05)
    for i in range(6):
        y=-41+6*i
        x=48+abs(i-2)*2
        q.line([(x,y),(x+8,y)],mid,.67)
        q.line([(x+21,y),(x+31,y)],ink,.65)
    q.shape([(7,0),(124,0),(136,79),(132,90),(0,91),(-1,81)],'998a70',ink,1.3)
    q.shape([(7,0),(121,0),(132,79),(1,81)],'c4b69a',ink,1.15)
    q.box(22,6,82,5,'877c69',ink,.85)
    q.shape([(20,15),(111,15),(113,31),(18,31)],'706f60',ink,1)
    for x in range(31,107,11):
        q.box(x,18,6,10,None,'dedbc2',.62)
        q.line([(x+1,23),(x+5,23)],'dedbc2',.55)
    for row in range(4):
        for col in range(6):
            x=16+col*15.7-row*.8
            y=39+row*9.4
            tone=gold if col==5 else (mid if col==4 else 'e9dfc6')
            q.shape(rounded(x,y,11.2,6.2,1),tone,ink,.78)
            q.line([(x+3,y+2.5),(x+7,y+2.5)],ink,.53)
    def coins(x,y,r,count):
        c=p.at(x,y,-4)
        for n in range(count):
            h=-4*n
            c.shape([(u,v+h+2.9) for u,v in oval(0,0,r,6)],'b39c74',ink,.8)
            c.el(0,h,r,6,'d4bf91',ink,.84)
            for a in range(-int(r)+3,int(r),4):
                v=6*(1-(a/r)**2)**.5
                c.line([(a,h+v),(a,h+v+2)],ink,.5)
        c.el(0,h,r*.78,4.1,None,mid,.63)
        c.shape([(-4,h),(0,h-2),(4,h),(0,h+2)],mid)
    coins(400,156,27,9)
    coins(374,174,25,5)
    coins(437,175,22,2)


def law(p, stock):
    _, ink, mid, gold = stock
    # Two cloth-bound reference volumes. Page edges turn at the fore-edge.
    def volume(x,y,angle,w,h,cover):
        b=p.at(x,y,angle)
        b.shape([(0,0),(22,-12),(w+21,-12),(w,0)],cover,ink,1.15)
        b.shape([(0,0),(w,0),(w,h),(0,h)],cover,ink,1.05)
        b.shape([(w,1),(w+20,-10),(w+20,h-11),(w,h-1)],PAPER,ink,.77)
        for yy in range(3,int(h)-1,3):b.line([(w+1,yy),(w+18,yy-9)],mid,.58)
        for xx in [9,14,w-15,w-10]:b.line([(xx,1),(xx,h-1)],gold,.94)
        b.box(24,3,w-50,h-6,None,gold,.65)
    volume(165,158,-3,110,18,'9e937b')
    volume(173,137,1,102,15,'a5aa94')
    q=p.at(367,165)
    # Turned brass pedestal and a level beam with individual pan suspensions.
    base=path((-39,8),(-38,4,-33,2,-25,1),(-18,-3,-13,-4,-9,-5),
              (-5,-8,-4,-14,-4,-16),(4,-16),(4,-9,8,-5,13,-4),
              (26,-1,36,2,39,7),(39,11),(-39,11))
    q.shape(base,'b8a17b',ink,1.2)
    q.line(path((-34,6),(-13,2,15,2,34,6)),PAPER,.9)
    q.shape([(-4,-12),(-2.7,-95),(2.7,-95),(4,-12)],'ccb78e',ink,1.05)
    for yy in [-90,-87,-19,-16]:q.box(-5,yy,10,2.4,gold,ink,.65)
    beam=path((-66,-94),(-54,-90,-36,-90,-8,-98),(-5,-103,5,-103,9,-98),
              (37,-91,52,-90,66,-94),(67,-90),(50,-85,29,-87,7,-92),
              (-7,-92),(-33,-86,-51,-84,-67,-90))
    q.shape(beam,'c6ae82',ink,1.08)
    for x in [-65,65]:
        q.el(x,-94,2.2,2.2,gold,ink,.7)
        for end in [-24,0,24]:q.line([(x,-91),(x+end,-43)],ink,.77)
        pan=path((x-25,-43),(x-17,-24,x+17,-24,x+25,-43))
        q.shape(pan,'c3ae86',ink,1)
        q.el(x,-43,25,3.2,'ded4b4',ink,.85)
        q.line(path((x-19,-39),(x-10,-31,x+9,-31,x+19,-39)),PAPER,.75)
    q.el(0,-98,5,5,gold,ink,.85)
    q.el(0,-98,2,2,PAPER,ink,.61)
    q.shape(path((-2,-102),(-4,-109,0,-114,0,-117),(4,-110,5,-107,2,-102)),gold,ink,.8)


def education(p, stock):
    _, ink, mid, gold=stock
    q=p.at(266,91,-13)
    q.el(0,0,54,54,'d5dfce',ink,1.15)
    # A classroom globe with invented coastlines kept clear of the graticule.
    for longitude in [19,37]:q.el(0,0,longitude,53,None,mid,.55)
    for latitude in [-30,-15,0,16,32]:
        r=(53**2-latitude**2)**.5
        q.line(path((-r,latitude),(-r*.5,latitude+7,r*.5,latitude+7,r,latitude)),mid,.56)
    for points in [[(-42,-22),(-32,-36),(-18,-42),(-9,-39),(-13,-31),(-5,-27),(-14,-17),(-20,-16),(-22,-8),(-28,-10),(-32,-3),(-38,-8)],
                   [(-29,-2),(-22,-1),(-13,7),(-6,10),(-6,18),(-12,24),(-15,33),(-22,40),(-24,45),(-27,36),(-26,18),(-31,6)],
                   [(0,-23),(7,-33),(17,-31),(22,-36),(33,-33),(41,-26),(43,-19),(36,-15),(35,-6),(26,-11),(22,-4),(17,-9),(12,-8),(5,-16)],
                   [(0,-10),(13,-12),(18,-6),(20,2),(14,13),(9,23),(4,20),(2,10),(-6,0)],
                   [(29,22),(38,17),(44,22),(40,29),(31,31)]]:
        q.shape(points,'a7b69a',ink,.75)
        q.hatch(points,'879781',4,-.68,.43)
    arc=oval(0,0,61,61,90,270)+oval(0,0,57,57,270,90)
    q.shape(arc,gold,ink,.95)
    for y in [-55,55]:q.el(0,y,3,3,'c4b188',ink,.8)
    s=p.at(252,151)
    s.shape(path((-3,-3),(4,-3),(4,9,5,14,17,16),(28,18),(28,22),(-24,22),(-24,18),(-10,16,-3,12,-3,-3)), 'b6a589',ink,1.1)
    b=p.at(325,110,6,1,.95,-.08)
    edges=path((0,5),(20,-2,38,-4,58,3),(79,-5,99,-4,119,1),(119,67),
               (99,62,77,62,59,70),(38,62,18,64,0,71))
    b.shape([(x+1,y+4) for x,y in edges],mid,ink,1.15)
    b.shape(edges,PAPER,ink,1.03)
    b.line(path((58,4),(56,30,59,52,59,69)),ink,.9)
    for y in range(13,59,6):
        b.line(path((7,y),(18,y-3,34,y-4,49,y)),mid,.69)
        b.line(path((67,y),(80,y-4,98,y-4,111,y-2)),mid,.68)
    b.shape([(81,61),(88,60),(88,77),(84,74),(80,78)],gold,ink,.65)


def medicine(p, stock):
    _, ink, mid, gold = stock
    bag = p.at(181,88,-4)
    leather='8ca19d'
    handle=path((41,0),(40,-14,43,-37,62,-40),(78,-43,102,-43,113,-35),
                (124,-29,125,-11,122,0),(115,0),(115,-19,111,-31,98,-32),
                (88,-34,70,-34,61,-32),(49,-30,49,-14,48,1))
    bag.shape(handle,'798f8a',ink,1.4)
    bag.line(path((45,-9),(45,-28,51,-35,66,-37),(77,-39,93,-40,101,-37)),PAPER,.78)
    body=path((10,2),(32,-3,119,-5,145,2),(153,8,164,28,166,52),
              (170,69,165,80,155,84),(115,92,39,94,10,85),(-2,81,-1,66,1,52),(2,28,6,11,10,2))
    bag.shape(body,leather,ink,1.32)
    gusset=path((139,5),(144,20,147,32,144,53),(140,64,141,77,153,83),
                (169,81,170,68,166,49),(165,30,155,10,146,3))
    cut(bag,gusset,'718780',ink,-.65,3.3)
    bag.line(path((5,63),(13,53,18,54,22,32),(24,20,21,14,24,8)),mid,1.05)
    bag.line(path((3,76),(25,86,105,88,145,79)),mix(ink,leather,.32),1.1)
    bag.dash(path((8,74),(29,80,95,84,137,78)),PAPER,.65,2.3,2.4)
    bag.shape(path((8,2),(40,-5,118,-7,143,-1),(150,0,152,4,149,7),(104,3,40,5,9,10)),gold,ink,1.0)
    for x in [43,113]:
        bag.box(x,-6,9,13,'cbb78d',ink,.84)
        bag.el(x+4.5,2,1.2,1.2,ink)
    bag.box(73,1,14,15,'bda67b',ink,.85)
    bag.box(76,3,8,4,PAPER,ink,.62)
    # A hand-stitched green cross on a leather doctor's bag.
    patch=rounded(51,24,48,42,7)
    bag.shape(patch,'dde1ce',ink,1)
    bag.dash(rounded(54,27,42,36,5),mid,.65,2.2,2.3)
    bag.shape([(70,32),(80,32),(80,40),(89,40),(89,50),(80,50),(80,59),
               (70,59),(70,50),(61,50),(61,40),(70,40)],'68877a',ink,.7)
    # A pocket sphygmomanometer provides a second, clearly clinical silhouette.
    p.line(path((381,106),(385,131,353,162,376,171),(397,180,407,156,426,150)),ink,4)
    p.line(path((381,106),(385,131,353,162,376,171),(397,180,407,156,426,150)),mid,2.15)
    dial=p.at(385,87,12)
    dial.box(-4,19,8,9,gold,ink,.85)
    for r,col in [(24,'9daaa1'),(21.5,PAPER),(19,'ede9d4')]:dial.el(0,0,r,r,col,ink,.72)
    for j in range(29):
        a=math.radians(144+9*j)
        inner=12.5 if j%4==0 else 15
        dial.line([(inner*math.cos(a),inner*math.sin(a)),(17.7*math.cos(a),17.7*math.sin(a))],ink,.65)
    dial.line([(-3,4),(9,-13)],ink,1.18)
    dial.el(0,0,1.8,1.8,gold,ink,.65)
    bulb=p.at(428,149,-26)
    bulb.box(-8,-2,13,5,'b5ab8c',ink,.82)
    bulb.shape(path((3,-3),(9,-5,11,-11,22,-12),(39,-13,48,-4,46,2),
                    (45,13,27,15,17,11),(10,9,8,4,3,3)), '83948e',ink,1.05)
    bulb.line(path((11,-4),(23,-14,37,-9,40,-6)),PAPER,.82)


def engineering(p, stock):
    _, ink, mid, gold=stock
    # Rolled graph-paper plan behind a sectional model of a riveted bridge.
    sheet=p.at(327,71,-13,1,1,-.12)
    sheet.shape([(0,1),(112,0),(118,86),(3,90)],'e8e9d7',ink,1.05)
    for x in range(9,112,8):sheet.line([(x,6),(x+2,83)],'c3cdbb',.5)
    for y in range(9,85,8):sheet.line([(6,y),(109,y-1)],'c3cdbb',.5)
    for r in [11,16,23]:sheet.el(83,51,r,r*.68,None,mid,.78)
    sheet.dash([(53,51),(109,51)],ink,.59,3,2)
    sheet.dash([(83,28),(83,72)],ink,.59,3,2)
    curl=path((-3,5),(-7,0,-4,-7,3,-8),(109,-10),(116,-10,121,-5,120,-1),
              (120,6,116,9,111,8),(9,10),(1,11,-2,9,-3,5))
    sheet.shape(curl,'d2d8c5',ink,.97)
    sheet.el(115,0,5.1,7.7,'adb9a9',ink,.73)
    sheet.line(path((0,-3),(34,-6,83,-6,109,-6)),PAPER,1.1)
    bridge=p.at(162,157,-3)
    for x in [15,192]:
        bridge.shape([(x,-8),(x+20,-8),(x+25,25),(x-4,25)],'b2b5a2',ink,1.0)
        bridge.box(x-6,24,33,4,'c8c9b2',ink,.83)
        for y in range(0,23,5):bridge.line([(x+1,y),(x+19,y)],mid,.5)
    def girder(a,b,color,width=4):
        bridge.line([a,b],ink,width+1.35)
        bridge.line([a,b],color,width)
    def truss(dx,dy,color):
        rail=[(dx,dy),(dx+34,dy-46),(dx+76,dy-65),(dx+150,dy-65),(dx+190,dy-46),(dx+222,dy)]
        for a,b in zip(rail,rail[1:]):girder(a,b,color)
        for xx,yy in [(34,-46),(76,-65),(112,-65),(150,-65),(190,-46)]:
            girder((dx+xx,dy+yy),(dx+xx,dy),color,2.3)
        for a,b in [((34,-46),(76,0)),((76,-65),(112,0)),((112,0),(150,-65)),((150,0),(190,-46))]:
            girder((dx+a[0],dy+a[1]),(dx+b[0],dy+b[1]),color,2.45)
    truss(14,-9,'b1beab')
    bridge.shape([(0,-1),(15,-9),(237,-9),(222,0)],'c0c4ac',ink,1.0)
    for xx,yy in [(0,0),(34,-46),(76,-65),(112,-65),(150,-65),(190,-46),(222,0)]:
        girder((xx,yy),(xx+14,yy-9),mid,2.2)
    truss(0,0,'91a28f')
    bridge.box(-3,-2,230,6,'b4b9a1',ink,1)
    for xx,yy in [(34,-46),(76,-65),(112,-65),(150,-65),(190,-46)]:
        bridge.el(xx,yy,2.2,2.2,'c1b99b',ink,.72)
        bridge.el(xx,0,1.55,1.55,gold,ink,.57)


def trade(p,stock):
    _,ink,mid,gold=stock
    # A port crane in elevation contrasts with the freighter seen broadside.
    q=p.at(382,57)
    q.shape([(-8,0),(1,-8),(14,-8),(17,0),(17,107),(12,107),(8,10),(2,107),(-3,107),(-2,3)],'b6b59f',ink,1.05)
    cut(q,[(-44,-1),(77,-9),(78,-3),(-42,6)],'c8baa0',ink,.81,4)
    q.line([(-38,-1),(3,-23),(12,-22),(74,-9)],ink,1)
    q.line([(3,-23),(3,-4),(12,-5),(12,-22)],ink,.98)
    q.box(-40,-1,13,13,mid,ink,.8)
    q.box(-8,-4,15,12,'d3cbaa',ink,.86)
    q.box(-5,-2,7,4,'98aaa5',ink,.55)
    for x in (46,50):q.line([(x,-5),(x,31)],ink,.72)
    q.line([(48,29),(43,38),(55,38),(48,29)],ink,.8)
    q.box(32,38,32,12,'bf9f76',ink,.9)
    for x in range(35,63,4):q.line([(x,40),(x,48)],ink,.5)
    ship=p.at(158,165,-2)
    ship.shape(path((0,-15),(22,-12),(176,-12),(182,-18),(240,-22),
                    (234,-14,226,-8,223,-1),(220,12,209,14,198,14),
                    (34,14),(18,15,5,6,0,-15)), '879b90',ink,1.28)
    ship.line(path((12,1),(45,9,188,6,222,4)),PAPER,1.18)
    ship.line([(21,-9),(192,-9),(229,-16)],ink,.9)
    for i in range(4):ship.el(192+i*8,-11-i*.8,1.35,1.35,ink)
    for row,starts in enumerate([[53,88,123,158],[62,97,132],[103]]):
        for i,x in enumerate(starts):
            y=-29-15*row
            tone=[gold,'a4af9b','b99172'][(row+i)%3]
            ship.box(x,y,33,14,tone,ink,.95)
            for line in range(x+3,x+32,4):ship.line([(line,y+2),(line,y+12)],mix(tone,ink,.5),.6)
    ship.box(11,-42,35,28,'e8e1cb',ink,.97)
    ship.box(8,-47,40,8,'cad3bd',ink,.86)
    for i in range(6):ship.box(11+i*5.6,-45,3.5,3,'7b9490',ink,.45)
    ship.shape([(19,-48),(17,-60),(27,-60),(30,-48)],mid,ink,.85)
    ship.line([(34,-48),(34,-70)],ink,1.05)
    ship.line([(27,-64),(40,-64)],ink,.7)
    for yy in [-33,-23]:
        for xx in range(15,43,7):ship.el(xx,yy,1.35,1.35,mid,ink,.5)
    for j in range(5):
        x=169+j*55
        p.line(path((x,184),(x+8,184,x+8,181,x+15,182),(x+23,184,x+30,183,x+35,182)),mid,.62)


def hospitality(p,stock):
    _,ink,mid,gold=stock
    bell=p.at(265,142)
    # Polished bell metal is shaded with meridian cuts around a reserved highlight.
    bell.el(0,17,72,11,'8c8170',ink,1.25)
    bell.el(0,12,72,11,'b4a28b',ink,1.2)
    bell.el(0,8,66,9,'cab591',ink,.88)
    dome=path((-60,4),(-53,-1,-57,-13,-50,-30),(-44,-47,-27,-62,-5,-63),
              (22,-66,46,-49,54,-28),(59,-15,55,-2,62,4),(54,17,-47,17,-60,4))
    bell.shape(dome,'cbb38c',ink,1.22)
    for k in range(12):
        x=20+3*k
        bell.line(path((7+k*1.15,-60+k*.8),(x,-52,x+10,-23,x+7,4)),mix('cbb38c',ink,.42),.6)
    for idx in range(4):
        bell.line(path((-11-3*idx,-57+idx),(-30-idx*2,-50,-43-idx*2,-27,-43-idx*1.8,-10)),PAPER,.9)
    bell.line(path((-55,0),(-27,12,35,12,58,0)),ink,.78)
    bell.el(0,-61,12,4.2,gold,ink,.85)
    bell.box(-4,-75,8,13,'c6b18a',ink,.85)
    bell.el(0,-76,13.5,4.8,'dcc8a2',ink,1)
    bell.line(oval(0,-76,10.5,2.5,183,300),PAPER,.8)
    # Brass room key, a leather fob and their split ring.
    fob=p.at(393,108,-18)
    fob.shape(path((0,-4),(3,-9,10,-8,13,-3),(29,28),(30,32,29,36,25,38),
                   (6,53),(3,55,-1,54,-3,51),(-18,35),(-20,32,-20,28,-17,25)), 'bd957f',ink,1.14)
    fob.dash(path((5,0),(23,29),(5,46),(-14,31),(5,0)),'e8d1ad',.8,2,2)
    fob.el(5,-1,2.5,2.5,'cab18c',ink,.73)
    fob.shape([(4,19),(13,27),(3,35),(-5,27)],None,ink,.74)
    key=p.at(408,88,39)
    key.shape([(-2,-3),(66,-3),(68,-1),(68,7),(63,7),(63,3),(59,3),(59,8),(54,8),(54,2),(-2,2)],'bda377',ink,1.02)
    key.line([(10,-1),(63,-1)],PAPER,.7)
    key.el(0,0,13,11,'ccb58a',ink,1.1)
    key.el(-1,0,7.5,6.4,stock[0],ink,.8)
    p.line(path((397,106),(387,107,380,99,382,91),(385,81,395,80,401,86)),ink,2.8)
    p.line(path((397,106),(387,107,380,99,382,91),(385,81,395,80,401,86)),PAPER,1.05)


def maintenance(p, stock):
    _,ink,mid,gold=stock
    # Adjustable spanner with a visible sliding jaw, worm screw and ring end.
    q=p.at(191,62,17)
    spanner=path((0,3),(8,-10,25,-16,38,-13),(42,-12),(32,-1),(23,0),(20,11),
                 (29,16),(42,5),(50,6),(47,17,41,24,33,25),(31,32,37,36,45,38),
                 (153,58),(163,61,165,69,161,75),(157,80,150,79,144,76),(45,49),
                 (30,44,25,38,19,34),(5,30,-5,20,0,3))
    q.shape(spanner,'afbba9',ink,1.3)
    q.line(path((41,43),(71,49,117,61,144,68)),PAPER,1)
    q.line(path((46,47),(88,57,122,68,143,72)),mid,.8)
    q.el(153,69,5.2,4.8,stock[0],ink,1.02)
    q.shape([(3,10),(15,-2),(25,0),(19,10),(12,15),(23,22),(16,28),(6,21)],'c9d0bc',ink,.94)
    q.shape([(19,24),(25,18),(35,26),(29,33)],mid,ink,.86)
    for j in range(5):q.line([(21+j*1.75,24-j*.65),(26+j*1.75,29-j*.65)],ink,.61)
    driver=p.at(304,151,-41)
    driver.shape([(0,-2),(9,-3),(13,-1.7),(83,-1.7),(83,2.2),(13,2.2),(9,3),(0,2)],'b7c0af',ink,.96)
    handle=path((77,-6),(81,-9,86,-9,92,-7),(99,-11,106,-13,113,-12),
                (143,-12),(153,-11,156,-7,156,0),(156,9,150,13,141,13),
                (109,13),(100,13,98,10,92,8),(86,10,80,9,77,5))
    driver.shape(handle,'b59a71',ink,1.24)
    driver.box(77,-5,7,10,'c1c2a8',ink,.8)
    for y in [-7,-.5,6]:driver.line(path((97,y),(111,y-2,133,y-2,146,y)),mix(ink,gold,.36),1.05)
    driver.line(path((108,-9),(123,-10,141,-10,147,-9)),PAPER,.8)
    for x,y,r in [(408,144,14),(429,163,12)]:
        n=p.at(x,y,13)
        face=[(r*math.cos(a*math.pi/3),r*.77*math.sin(a*math.pi/3)) for a in range(6)]
        n.shape([(u,v+4) for u,v in face],mid,ink,.94)
        n.shape(face,'c4cbb8',ink,1)
        n.el(0,0,r*.46,r*.34,stock[0],ink,1)
        n.line(oval(0,1,r*.42,r*.30,175,340),mid,.8)


def environment(p, stock):
    _,ink,mid,gold=stock
    # A herbarium mount with individually cut veins and paper straps.
    q=p.at(192,44,-5,1,1,-.065)
    q.box(2,3,166,144,'b6c2aa',ink,.8)
    q.box(0,0,166,144,PAPER,ink,1.05)
    q.box(6,6,154,132,None,'c5c6ad',.62)
    stem=path((49,129),(64,107,83,92,86,77),(91,57,108,42,116,19))
    q.line(stem,ink,2.45)
    q.line(stem,'a4a57f',1)
    def leaf(x,y,angle,length,width):
        leaf_pen=q.at(x,y,angle)
        outline=path((0,0),(length*.13,-width*.85,length*.63,-width,length,0),
                     (length*.71,width*.49,length*.30,width*1.13,0,0))
        leaf_pen.shape(outline,'a1b495',ink,.93)
        leaf_pen.line(path((0,0),(length*.27,0,length*.62,-1.2,length,0)),ink,.77)
        for j in range(1,8):
            t=j/9
            end=math.sin(t*math.pi)*width*.62
            leaf_pen.line(path((length*t-3,0),(length*t+1,-1,length*t+3,-end*.8,length*t+6,-end)),mid,.59)
            leaf_pen.line(path((length*t-3,.4),(length*t,1,length*t+4,end*.75,length*t+7,end*.84)),ink,.52)
    for data in [(66,106,-143,39,10),(73,99,4,43,11),(82,83,-141,43,12),(86,77,-13,47,12),
                 (93,60,-137,39,11),(99,50,-11,42,11),(108,37,-120,34,8),(113,25,-39,32,8)]:leaf(*data)
    for x,y in [(59,117),(101,47)]:
        q.shape([(x-7,y-4),(x+10,y+1),(x+9,y+5),(x-8,y)],'ded4ad',mid,.63)
    q.box(108,110,43,17,'e3e4cc',mid,.6)
    for row in range(3):q.line([(112,114+row*4),(142-row*6,114+row*4)],mid,.6)
    # A graduated water-sample bottle, seen through two pale layers of glass.
    v=p.at(391,93,7)
    bottle=path((-15,-3),(15,-3),(15,7),(14,14,27,14,27,27),(27,69),
                (27,74,23,77,18,78),(-18,78),(-23,77,-27,74,-27,70),(-27,27),
                (-27,15,-15,15,-15,7))
    v.shape(bottle,'dbe5d6',ink,1.15)
    v.shape(path((-24,33),(-12,36,9,31,24,33),(24,69),(24,73,20,74,17,74),
                 (-18,74),(-23,73,-24,71,-24,68)), 'b6c9b7',mid,.76)
    v.shape(rounded(-17,-12,34,12,2),gold,ink,.95)
    for x in range(-14,17,3):v.line([(x,-10),(x,-2)],ink,.55)
    v.line(path((-20,28),(-19,18,-12,22,-12,7)),PAPER,1.6)
    v.line([(-20,36),(-20,65)],PAPER,1.23)
    for j in range(7):
        x=10 if j%2 else 6
        v.line([(x,31+6*j),(20,31+6*j)],ink,.62)


def people(p, stock):
    _,ink,mid,gold=stock
    def profile(q,x,y,r,shirt):
        q.el(x,y,r,r,'e3e1c9',ink,.7)
        q.el(x,y-r*.23,r*.29,r*.35,shirt,ink,.7)
        shoulders=path((x-r*.69,y+r*.55),(x-r*.53,y+r*.02,x+r*.53,y+r*.02,x+r*.69,y+r*.55),
                       (x+r*.30,y+r*.84,x-r*.30,y+r*.84,x-r*.69,y+r*.55))
        q.shape(shoulders,shirt,ink,.7)
    # A card index of people, with staggered tabs and individual portrait cards.
    tray=p.at(174,110,-5)
    tray.shape([(0,0),(33,-18),(172,-18),(153,40),(134,68),(0,66)],'ae9479',ink,1.18)
    for level in range(5):
        right=146-level*2
        x=12+(4-level)*4
        y=-31-level*4
        tab=12+level*21
        card=path((x,y+6),(x,y+1,x+2,y,x+6,y),(tab+x,y),
                  (tab+x+1,y-7),(tab+x+20,y-7),(tab+x+23,y),
                  (right+13,y),(right+18,y+1,right+18,y+4,right+17,y+9),
                  (right+9,y+60),(x-1,y+61))
        tray.shape(card,mix(PAPER,mid,.10+level*.035),ink,.85)
    front=tray.at(5,-28,0,1,1,-.07)
    front.shape(rounded(0,0,140,64,2),PAPER,ink,1.05)
    profile(front,23,21,14,'b89b80')
    for row,length in enumerate([48,71,58]):front.line([(47,12+row*6),(47+length,12+row*6)],mid,1 if row==0 else .72)
    for row in range(2):front.line([(11,43+row*6),(127-row*16,43+row*6)],mid,.55)
    tray.shape([(0,5),(23,13),(121,14),(138,8),(137,68),(0,66)],'b7a18a',ink,1.14)
    tray.shape([(138,8),(168,-8),(164,46),(137,68)],'9d8e7d',ink,1)
    tray.line([(1,11),(24,19),(122,20),(136,14)],PAPER,.78)
    tray.box(47,30,47,17,'d0b990',ink,.83)
    tray.box(53,34,35,8,'eee4c9',ink,.58)
    for xx in (50,91):tray.el(xx,39,1,1,ink)
    # A meeting card makes the link between records and face-to-face conversation.
    c=p.at(355,81,10)
    c.box(3,5,86,72,'c1ae92',ink,.87)
    c.shape(rounded(0,0,86,72,3),PAPER,ink,1)
    def bubble(x,y,w,h,side,tone):
        c.shape(rounded(x,y,w,h,6),tone,ink,.83)
        if side=='left': lip=[(x+6,y+h-2),(x+5,y+h+6),(x+15,y+h-2)]
        else: lip=[(x+w-18,y+h-2),(x+w-6,y+h+5),(x+w-8,y+h-2)]
        c.shape(lip,tone)
        c.line(lip,ink,.86)
        for j in range(3):c.el(x+w/2-6+j*6,y+h/2,1.3,1.3,ink)
    bubble(10,11,35,18,'left','d4c2a2')
    bubble(40,33,35,18,'right','afbdab')
    c.line([(10,61),(55,61)],mid,.7)


def culture(p, stock):
    _,ink,mid,gold=stock
    q=p.at(267,49,-2)
    # A celadon vase with a continuous hand-cut vine frieze.
    vase=path((-18,-4),(-20,1,-17,3,-14,5),(-12,13,-13,24,-18,32),
              (-31,41,-46,50,-46,72),(-48,99,-33,110,-23,119),
              (-22,123),(-23,126),(24,126),(23,121),(34,111,46,100,46,75),
              (46,52,33,44,19,34),(12,25,12,13,15,5),(20,2,21,-2,18,-4))
    glaze='b3c6ba'
    q.shape(vase,glaze,ink,1.35)
    q.el(0,-4,19.2,4.6,'d1d6bd',ink,1)
    q.el(0,-4,14.3,2.5,'81968a',ink,.64)
    q.line(path((-14,9),(-6,12,7,12,14,9)),ink,.75)
    for dy in (0,3,38,41):q.line(path((-43,56+dy),(-30,63+dy,29,63+dy,43,56+dy)),mid,.8)
    q.line(path((-44,78),(-27,87,-23,65,-9,72),(1,77,4,88,14,79),(25,69,35,72,44,77)),ink,1.02)
    for x,y,a in [(-32,78,-44),(-22,73,-112),(-12,72,-46),(-4,76,40),(8,82,147),(16,78,-62),(27,74,-29),(36,74,48)]:
        leaf=q.at(x,y,a)
        leaf.shape(path((0,0),(2,-3,8,-4,12,0),(8,3,3,4,0,0)),'7b9989',ink,.56)
    for j in range(7):
        x=23+2*j
        q.line(path((14+j*.55,31+j*.55),(x,49,x+5,48,x+6,55)),mid,.56)
        q.line(path((x+6,103-j*.5),(x+4,110,x-3,115,x-6,118)),mid,.56)
    q.line(path((-34,55),(-39,61,-40,68,-40,72)),'e6e9d6',1.4)
    q.line(path((-22,120),(-15,123,14,123,23,120)),ink,.75)
    s=p.at(337,143,-9)
    s.shape(path((0,0),(16,0,55,-4,79,3),(89,4,98,1,104,-3),
                 (105,21),(93,26,84,28,76,25),(59,19,21,26,0,23)),PAPER,ink,.95)
    for j in range(5):s.line(path((12+j*4,17-j*1.8),(27+j*3,15,29+j*4,3,37+j*6,9+j)),mid,.6)
    s.shape(path((-1,-3),(3,-5,9,-1,10,3),(11,25),(7,30,0,28,-2,23)), 'd7c1a0',ink,.89)
    s.el(4,24,6.8,3.2,'d8cbb0',ink,.78)
    brush=p.at(354,137,-44)
    brush.shape(path((0,0),(11,-.4,15,-9,22,-8),(29,-8,33,-5,36,-4),
                     (36,3),(26,5,18,4,12,3),(6,2,4,1,0,0)),'796d5d',ink,.93)
    for j in range(3):brush.line(path((3+j*3,.4),(14,-1,22,-7+j,31,-4+j)),mid,.61)
    brush.box(32,-4,15,7.6,'c4b28c',ink,.85)
    brush.shape([(47,-3.3),(146,-2),(151,0),(146,2.2),(47,3.3)],'b99873',ink,.9)
    for x in (35,38,43):brush.line([(x,-3.8),(x,3.2)],ink,.55)
    brush.line([(50,-1.2),(145,-.5)],PAPER,.69)


FIELDS = {
    'software': (software, 0),
    'finance': (finance, 4),
    'law': (law, 7),
    'education': (education, 5),
    'medicine': (medicine, 2),
    'engineering': (engineering, 3),
    'trade': (trade, 7),
    'hospitality': (hospitality, 1),
    'maintenance': (maintenance, 3),
    'environment': (environment, 0),
    'people': (people, 4),
    'culture': (culture, 6),
}


def render(name):
    draw, stock = FIELDS[name]
    pen = backing(stock)
    draw(pen, STOCKS[stock])
    plate = pen.im.resize((650, 220), Image.Resampling.LANCZOS)
    image = grain(plate, 720 + list(FIELDS).index(name))
    image.save(ROOT / f'field-{name}.webp', quality=95, method=6)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fields', nargs='*', metavar='FIELD')
    args = parser.parse_args()
    for name in args.fields:
        if name not in FIELDS:
            parser.error(f'Unknown field {name!r}. Choose from {", ".join(FIELDS)}.')
    for name in args.fields or FIELDS:
        render(name)
