"""Original illustrations for the career atlas. Run with Pillow and NumPy installed.

Working from a field notebook, measure first and ink second. In the landscape,
parallel cuts describe folds in rock. On the specimen pages the same cuts turn
wood, glass and brass. Paper left between marks is part of every object.

Broad masses should read across a desk. Up close, a viewer can find the smaller
observations: a clip under tension, a bevel on a gear, the ticks on an instrument.

The paper stocks change with the discipline. Light always enters from the upper
left, so even plates taken out of order still belong to the same notebook.
"""
from pathlib import Path
import math
import random
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1] / 'assets'
S = 3
TAU = math.tau

def rgb(s):
    if isinstance(s, tuple): return s
    return tuple(bytes.fromhex(s.strip('#')))

def mix(a,b,t):
    return tuple(round(u+(v-u)*t) for u,v in zip(rgb(a),rgb(b)))

def grain(im,seed):
    rng=np.random.default_rng(seed)
    a=np.asarray(im.convert('RGB'),dtype=np.float32)
    h,w=a.shape[:2]
    slow=Image.fromarray(rng.integers(80,170,(max(3,h//18),max(3,w//18)),dtype=np.uint8)).resize((w,h),Image.Resampling.BICUBIC)
    n=rng.normal(0,1.38,(h,w))+(np.asarray(slow,dtype=float)-125)*.038
    return Image.fromarray(np.uint8(np.clip(a+n[:,:,None],0,255)))

def cubic(p,a,b,q,n=20):
    pts=[]
    for i in range(1,n+1):
        t=i/n; u=1-t
        pts.append(tuple(u**3*p[j]+3*u*u*t*a[j]+3*u*t*t*b[j]+t**3*q[j] for j in range(2)))
    return pts

def path(start,*segments):
    pts=[start]
    for seg in segments:
        if len(seg)==2: pts.append(seg)
        else: pts.extend(cubic(pts[-1],seg[:2],seg[2:4],seg[4:]))
    return pts

def oval(x,y,rx,ry,a=0,b=360):
    count=max(6,round(abs(b-a)/3))
    return [(x+rx*math.cos(math.radians(t)),y+ry*math.sin(math.radians(t))) for t in np.linspace(a,b,count+1)]

class Pen:
    def __init__(self,im,tr=(1,0,0,1,0,0),scale=S):
        self.im=im; self.d=ImageDraw.Draw(im); self.tr=tr; self.s=scale
    def xy(self,p):
        x,y=p; a,b,c,d,e,f=self.tr
        return (round((a*x+c*y+e)*self.s), round((b*x+d*y+f)*self.s))
    def at(self,x,y,angle=0,sx=1,sy=None,skew=0):
        sy=sx if sy is None else sy; ca=math.cos(math.radians(angle)); sa=math.sin(math.radians(angle)); a,b,c,d,e,f=self.tr
        A=ca*sx; B=sa*sx; C=(skew*ca-sa)*sy; D=(skew*sa+ca)*sy
        return Pen(self.im,(a*A+c*B,b*A+d*B,a*C+c*D,b*C+d*D,a*x+c*y+e,b*x+d*y+f),self.s)
    def line(self,pts,col,w=1):
        if len(pts)>1:self.d.line([self.xy(p) for p in pts],fill=rgb(col),width=max(1,round(w*self.s)),joint='curve')
    def shape(self,pts,fill,edge=None,w=1):
        if fill is not None:self.d.polygon([self.xy(p) for p in pts],fill=rgb(fill))
        if edge is not None:self.line([*pts,pts[0]],edge,w)
    def box(self,x,y,w,h,fill,edge=None,lw=1): self.shape([(x,y),(x+w,y),(x+w,y+h),(x,y+h)],fill,edge,lw)
    def el(self,x,y,rx,ry,fill,edge=None,w=1): self.shape(oval(x,y,rx,ry),fill,edge,w)
    def hatch(self,points,col,gap=4,slope=-.7,w=.55):
        # Intersect engraved strokes with the specimen's outline in local space.
        poly=points+[points[0]]; vals=[y-slope*x for x,y in points]
        for k in np.arange(min(vals)+gap*.43,max(vals),gap):
            xs=[]
            for (x1,y1),(x2,y2) in zip(poly,poly[1:]):
                v1=y1-slope*x1; v2=y2-slope*x2
                if min(v1,v2)<=k<max(v1,v2): xs.append(x1+(x2-x1)*(k-v1)/(v2-v1))
            xs.sort()
            for a,b in zip(xs[::2],xs[1::2]):
                if b-a>.8:self.line([(a,k+slope*a),(b,k+slope*b)],col,w)
    def dash(self,pts,col,w=1,on=4,off=3):
        phase=0
        for (x,y),(X,Y) in zip(pts,pts[1:]):
            dx=X-x;dy=Y-y;L=math.hypot(dx,dy)
            if not L:continue
            u=0
            while u<L-1e-6:
                draw=phase<on; run=min((on if draw else on+off)-phase,L-u)
                if draw:self.line([(x+dx*u/L,y+dy*u/L),(x+dx*(u+run)/L,y+dy*(u+run)/L)],col,w)
                u+=run; phase=(phase+run)%(on+off)
                if abs(phase-on)<1e-7:phase=on
                if abs(phase-on-off)<1e-7:phase=0

def sky_noise(x,z,k,seed):
    # Smooth, reproducible lattice noise with no sampled external textures.
    X=x/k;Z=z/k; i=np.floor(X);j=np.floor(Z);u=X-i;v=Z-j
    u=u*u*(3-2*u);v=v*v*(3-2*v)
    def val(a,b):
        t=np.sin(a*127.1+b*311.7+seed*19.71)*43758.5453
        return (t-np.floor(t))*2-1
    return (1-v)*((1-u)*val(i,j)+u*val(i+1,j))+v*((1-u)*val(i,j+1)+u*val(i+1,j+1))

def stream(d): return 666+45*np.sin((d-80)/47)+50*np.sin(d/105)-.51*np.maximum(d-240,0)

def mountain_grid(x,d):
    n=sky_noise
    X=x+19*n(x,d,54,11)+7*n(x,d,21,12); D=d+12*n(x,d,62,33)
    peaks=[(20,-120,73,.79,.63),(201,-118,104,.73,.62),(333,-104,137,.83,.71),(420,-155,91,.7,.76),(512,-105,128,.92,.68),(625,-140,102,.8,.71),(861,-128,117,.88,.71),(970,-90,101,1,.71),(1127,-146,106,.71,.54),
           (251,60,71,.59,.56),(372,35,114,.72,.75),(480,43,153,.97,.87),(537,67,167,1.06,.79),(604,42,140,.94,.75),(701,55,208,1.04,.93),(748,78,216,1.24,1.02),(784,62,186,1.14,.91),(851,80,131,.8,.84),(940,68,154,1.03,.74),(1093,58,138,.74,.82)]
    h=np.zeros(np.broadcast_shapes(X.shape,D.shape))
    for idx,(px,pd,height,sx,sd) in enumerate(peaks):
        if pd < 0: height *= .63
        dx=(X-px)*sx; dz=(D-pd)*sd;r=np.hypot(dx,dz);ang=np.arctan2(dz,dx)
        ribs=1+.14*np.sin(5*ang+idx*2+.009*r)+.085*np.sin(9*ang-idx+.007*r)
        h=np.maximum(h,height-r*ribs)
    noise=n(x,d,27,9)*6+n(x,d,13,21)*3+n(x,d,6,25)*1.7+n(x,d,3,7)*.65
    h=np.maximum(h+noise*np.clip(h/38,0,1),0)
    bank=stream(d); dist=np.abs(x-bank); dw=np.maximum(4,4+(d-210)*.052)
    roll=14+16*n(x,d,86,26)+6*n(x,d,28,19)+2*n(x,d,13,22)
    foothills=roll+74*np.exp(-((x-1020)/220)**2-((d-390)/146)**2)+49*np.exp(-((x-314)/196)**2-((d-395)/135)**2)+59*np.exp(-((x-1090)/198)**2-((d-665)/180)**2)
    foothills=np.maximum(2,foothills)*np.clip((dist-dw)/59,0,1)**.73
    return np.maximum(h,foothills),dw

def pine(p,x,y,h,ink,pale,seed):
    r=random.Random(seed);wid=h*r.uniform(.15,.23);lean=r.uniform(-.035,.035)*h
    p.line([(x,y),(x+lean,y-h)],ink,max(.34,h*.025)); levels=max(4,min(14,round(h*.46)))
    for i in range(levels):
        t=(i+.7)/(levels+1); yy=y-h+h*.91*t;xx=x+lean*(1-t);width=wid*t**.73
        for side in [-1,1]:
            w=width*r.uniform(.77,1.13); end=yy+h*r.uniform(.035,.095); tip=xx+w*side
            p.shape([(xx,yy-h*.085),(xx+side*w*.53,yy+h*.01),(tip,end),(xx+side*w*.74,end-h*.012),(xx+side*w*.49,end+h*.025),(xx,yy+h*.025)],(pale if side==-1 else ink))
            if h>17 and r.random()<.7:p.line([(xx,yy),(xx+side*w*.73,end)],mix(ink,pale,.56),.42)

def compass(p,x,y):
    q=p.at(x,y); ink='486454'; muted='859681'; ivory='edf0dc';gold='aa864b'
    for r,w in [(32,.55),(28,.65),(21,.48)]:q.el(0,0,r,r,None,muted,w)
    for i in range(64):
        t=i*TAU/64;rr=24 if i%8==0 else (26 if i%4==0 else 29.5)
        q.line([(rr*math.cos(t),rr*math.sin(t)),(31*math.cos(t),31*math.sin(t))],muted,.6)
    for i in range(8):
        t=i*TAU/8-math.pi/2; r=(42 if i==0 else 37) if i%2==0 else 22; w=5 if i%2==0 else 2.7
        X,Y=r*math.cos(t),r*math.sin(t);lx,ly=-math.sin(t)*w,math.cos(t)*w
        q.shape([(0,0),(lx,ly),(X,Y)],gold if i%2 else ink,ink,.58);q.shape([(0,0),(-lx,-ly),(X,Y)],ivory,ink,.58)
    q.el(0,0,3.3,3.3,gold,ink,.75);q.el(0,0,1,1,ivory)
    q.line([(-3,-47),(-3,-54),(3,-47),(3,-54)],ink,.88)

def terrain():
    W,H=1100,520; ss=2; rng=np.random.default_rng(97)
    xs=np.arange(W*ss)/ss; depths=np.arange(-215,830,1.0)
    x=xs[None,:];d=depths[:,None];z,_=mountain_grid(x,d); projected=240+.46*d-z
    ys=np.arange(H*ss)/ss; depthmap=np.empty((len(ys),len(xs)),dtype=np.float32)
    # Invert the visible profile of every surveyed column, retaining the front slope.
    for j in range(len(xs)):
        v=projected[::-1,j];lowest=np.minimum.accumulate(v)
        keep=np.r_[True,lowest[1:]<lowest[:-1]]; V=v[keep][::-1];D=depths[::-1][keep][::-1]
        depthmap[:,j]=np.interp(ys,V,D,left=-999)
    y=ys[:,None];valid=depthmap>-900;D=np.where(valid,depthmap,-215); indices=np.clip(np.rint(D-depths[0]).astype(int),0,len(depths)-1);cols=np.arange(len(xs))[None,:]
    hd,hx=np.gradient(z,1,1/ss);gx=hx[indices,cols];gd=hd[indices,cols];elev=240+.46*D-y
    n=lambda k,seed:sky_noise(x,D,k,seed)
    rock=np.clip((elev-27)/56,0,1); face=np.clip(.44+gx*.36-gd*.25+n(10,83)*.042,0,1)
    dist=np.clip((D+180)/360,.2,1); soil=np.clip((D-120)/165,0,1)
    def comb(phase,thickness):return np.clip((thickness-np.abs((phase+.5)%1-.5))/.11,0,1)
    phase=(x*.78+D*.18+elev*.27+4.7*n(23,31)+1.4*n(8,32))/3.4
    fine=comb(phase,.06+face*.22)*np.clip((face-.15)*1.9,0,1)
    cross=comb((x*.29-D*.22+elev*.95+2.3*n(14,12))/4.9,.14)*np.clip((face-.53)*3,0,1)
    ledges=comb((elev+3.7*n(23,3)+D*.055)/6.7,.11)*(.2+.8*face)
    relief=np.clip((gx*.48-gd*.19+.11),0,1)
    ink=(.038+face*.20+relief*.19+fine*.55+cross*.22+ledges*.13)*dist
    meadow=(.045+face*.12+comb((elev*.5+D*.19+3.7*n(35,11))/3.3,.115)*.27+comb((elev*.48+D*.2+x*.24)/3.8,.14)*.14*face)*dist
    ink=ink*rock+meadow*(1-rock)
    # Thin skyline and interlocking spurs, with atmospheric perspective.
    jump=np.maximum(0,np.roll(depthmap,-1,axis=0)-np.roll(depthmap,1,axis=0));ink+=np.clip((jump-6)/23,0,.48)*dist
    water=(np.abs(x-stream(D))<np.maximum(4,4+(D-210)*.052))&(D>188)&(elev<2.8)
    ripple=comb((y+1.3*n(27,71))/2.7,.15)*np.clip(n(25,8)+.32,0,1)
    ink=np.where(water,.052+ripple*.29,ink); ink=np.where(valid,ink,0)
    paper=np.array(rgb('eaf0e6'));green=np.array(rgb('365c4d')); strength=np.clip(ink,0,1)
    # The lower-field print has a cream second ink laid beneath the green cuts.
    base=paper+(np.array(rgb('f6eed8'))-paper)*(.29*valid+.12*water)[:,:,None]
    a=base+(green-base)*strength[:,:,None]
    im=Image.fromarray(np.uint8(np.clip(a,0,255)));p=Pen(im,scale=ss)
    treegroups=[(187,312,79,41,180),(347,325,66,39,290),(455,310,72,28,320),(575,281,40,29,130),(856,268,86,22,240),(990,338,105,55,790),(785,392,56,33,200),(538,468,60,46,225),(1065,529,115,70,720),(360,630,70,42,155),(896,684,75,48,290)]
    trees=[]
    for cx,cd,wx,wd,count in treegroups:
        for _ in range(count):
            tx=rng.normal(cx,wx);td=rng.normal(cd,wd)
            if tx<1 or tx>=W-1 or td<140 or td>810:continue
            j=round(tx*ss);k=round(td-depths[0]);yp=projected[k,j];ty=round(yp*ss)
            if ty<0 or ty>=H*ss or depthmap[ty,j]>td+5 or abs(tx-stream(td))<max(5,4+(td-210)*.052)+5 or z[k,j]>105:continue
            h=(4+(td-170)*.041)*rng.uniform(.57,1.3);trees.append((td,tx,yp,h,int(rng.integers(999999))))
    for td,tx,ty,h,seed in sorted(trees):
        density=min(.87,.35+(td-150)*.00093+(seed%6)*.018);c=mix('d5dfcb','305447',density)
        pine(p,tx,ty,h,c,mix(c,'e8ecd7',.23),seed)
    # Track a traversable line across the meadow rather than over the main summit.
    trail=path((565,523),(591,499,685,499,681,477),(675,458,617,465,638,446),(661,426,759,444,755,422),(753,410,707,416,724,401),(742,386,799,392,803,373),(810,357,767,361,771,347),(774,336,818,330,831,316))
    p.line(trail,'ede9d4',3.7);p.dash(trail,'ac783a',2.05,6,4)
    for tx,ty in [trail[39],trail[82],trail[120],trail[-1]]:
        p.el(tx,ty,4.3,4.3,'f1edd9','886637',1.05);p.el(tx,ty,1.8,1.8,'b18345')
    # A closer stand at the edge sets the scale of the mountains behind it.
    for tx,ty,h in [(1060,519,25),(1073,526,41),(1096,508,39),(1046,528,29),(1084,531,59),(1101,526,55),(1015,524,23)]:
        pine(p,tx,ty,h,'395b4c','68816a',int(tx))
    # Narrow bands of etched cirrus, left open at the ends.
    for cx,cy,span in [(489,60,48),(584,29,36),(872,41,56)]:
        for j in range(5):
            rr=random.Random(cx+j);w=span*(1-abs(j-2)*.19);yy=cy+2.1*j
            p.line(path((cx-w*.8+rr.uniform(-4,4),yy),(cx-w*.3,yy+.4,cx-w*.14,yy-2.7,cx+w*.1,yy-1.7),(cx+w*.5,yy-.5,cx+w*.51,yy+1.6,cx+w*.87+rr.uniform(-8,8),yy+.45)),mix('eaf0e6','718879',.23-.022*abs(j-2)),.48)
    compass(p,1018,84)
    # Leave the western area quiet for the facing text column.
    arr=np.asarray(im,dtype=float);t=np.clip((xs-73)/340,0,1);t=.20+.80*(t*t*(3-2*t));arr=paper+(arr-paper)*t[None,:,None]
    im=Image.fromarray(np.uint8(arr)).resize((W,H),Image.Resampling.LANCZOS);grain(im,810).save(ROOT/'terrain.webp',quality=95,method=6)

# Each job uses a different stock and one warm spot ink. All coordinates below
# refer to a single 650 x 220 printing plate, prior to supersampling.
STOCKS=[('e1e9dc','344f46','78907a','bf9959'),('f0dfd0','614b43','b9866f','af744c'),('dee7e8','3e5662','849ba2','b69761'),('e3e7dd','3e514c','859184','b69759'),('eee5d8','594e43','aa9070','b48951'),('dfe9df','36564f','83a393','b38f60'),('ece0d8','624e47','b99077','b88b55'),('e5e6dd','4b5450','96a093','b59562')]

def backing(i):
    bg,ink,mid,gold=STOCKS[i]; im=Image.new('RGB',(650*S,220*S),rgb(bg));p=Pen(im); r=random.Random(i+33)
    guide=mix(bg,ink,.22); ghost=mix(bg,ink,.10); faint=mix(bg,ink,.065)
    # Broken survey lines stay subordinate at card size.
    if i in (0,1,3,7):
        g=p.at(337,114,[-6,3,0,-12,0,0,0,0][i]);
        for x in range(-255,256,14):
            ext=72-38*abs(x)/255+r.uniform(-9,8);g.line([(x,-ext),(x,ext)],faint,.42)
        for y in range(-70,72,14):
            ext=248-abs(y)*.77;g.line([(-ext,y),(ext,y)],faint,.42)
    else:
        for x,y,rad in [(253,112,70),(375,111,78)]:
            for rr in [rad,rad+4,rad+26]:p.line(oval(x,y,rr,rr,169+11*i,352+13*i),ghost,.54)
        p.dash([(110,112),(544,112)],ghost,.55,8,4)
    for x,y in [(84+r.randrange(30),52+r.randrange(16)),(530+r.randrange(32),144+r.randrange(17))]:
        p.line([(x-8,y),(x+8,y)],guide,.65);p.line([(x,y-8),(x,y+8)],guide,.65);p.el(x,y,2.5,2.5,None,guide,.5)
    # A dry engraved grounding shadow, hand-broken at its tapered ends.
    for j in range(96):
        t=r.uniform(-1,1); y=167+19*(1-t*t)+r.uniform(-5,5);x=328+t*143
        p.line([(x,y),(x+r.uniform(2,12)*(1-.4*abs(t)),y+r.uniform(-1,0))],mix(bg,ink,r.uniform(.09,.22)),.5)
    return p

def rim(p,x,y,rx,ry,colors):
    for rad,col,edge in colors:p.el(x,y,rx*rad,ry*rad,col,edge,.8)

def pencil(p,x,y,angle,length,ink,gold):
    q=p.at(x,y,angle); q.shape([(0,0),(16,-4.4),(length-5,-4.4),(length,-2.5),(length,3.5),(16,5.2)],'e7cc97',ink,1.24)
    q.shape([(16,2),(length,1.7),(length,3.5),(16,5.2)],mix(ink,gold,.5));q.shape([(17,-4.1),(length-5,-4.1),(length-5,-.7),(15,-1)],gold)
    q.line([(16,-1),(length-4,-.6)],'f4dfb2',.85);q.shape([(0,0),(4.8,-1.35),(5.8,1.7)],ink)
    q.box(length-11,-4.2,5.8,8.2,'d6c499',ink,.7)
    for i in [1,2.6,4]:q.line([(length-11+i,-3.3),(length-11+i,3.2)],ink,.45)

def report(p):
    bg,ink,mid,gold=STOCKS[0];cream='f4efda'; rule='b4bc9f'; q=p.at(188,57,-7,1,1, -.10)
    board=[(-5,-8),(202,-8),(206,-4),(206,129),(202,134),(-5,134),(-8,131),(-8,-4)]
    q.shape([(x+2,y+3) for x,y in board],mid,ink,1.0);q.shape(board,'c0b68e',ink,1.45)
    for o in [3,1,0]:q.box(o,2+o,198,125,cream,ink,.65)
    q.line([(12,19),(185,19)],ink,.8);q.box(12,9,33,2.8,ink);q.box(49,10,17,1.3,mid)
    for j in range(6):q.line([(19,32+10*j),(130,32+10*j)],rule,.55)
    for j in range(9):q.line([(19+14*j,29),(19+14*j,84)],mix(rule,cream,.35),.43)
    vals=[12,21,17,30,27,38,35,49];points=[]
    for j,v in enumerate(vals):
        bx=22+j*13.5; bar=[(bx,83),(bx,83-v),(bx+7.3,83-v),(bx+7.3,83)]
        q.shape(bar,mid if j<6 else gold,ink,.63);q.hatch(bar,mix(ink,mid,.4),3,-.7,.4);points.append((bx+3,75-v))
    q.line(points,ink,1.25)
    for pt in points:q.el(*pt,1.7,1.7,cream,ink,.75)
    q.line([(17,28),(17,84),(133,84)],ink,1.05)
    for j in range(4):
        q.line([(13,95+6*j),(114+(j%3)*8,95+6*j)],rule,.7)
        q.line([(14,97+6*j),(29+7*(j%3),97+6*j)],mid,.52)
    q.el(164,79,18,18,mid,ink,.75);q.shape([(164,79)]+oval(164,79,18,18,201,304),gold,ink,.7);q.shape([(164,79)]+oval(164,79,18,18,305,359),cream,ink,.7)
    for j in range(3):q.line([(146,104+j*4),(179-j*3,104+j*4)],mid,.8)
    # Spring-loaded brass clamp and its folded lip.
    q.shape([(67,-6),(78,-9),(81,-14),(110,-14),(114,-9),(125,-6),(124,3),(67,3)],gold,ink,1.3)
    q.box(67,1,57,4,'e5d3a6',ink,.75);q.el(96,-13,10,5.5,'d1bd8f',ink,1);q.el(96,-13,4.8,2.4,bg,ink,.6)
    for j in range(12):q.line([(70+j*4.6,-4),(71+j*4.6,-.5)],ink,.47)
    # A reading glass catches and enlarges its own section of graph paper.
    q=p.at(399,91);h=q.at(19,25,40)
    h.shape(path((0,-3),(12,-4),(18,-5),(56,-7,76,-8,80,-3),(85,2,79,6,73,6),(47,7,25,5,17,4),(0,3)),mix(ink,mid,.38),ink,1.4)
    for j in [0,2,4]:h.line(path((19,-3+j),(38,-6+j,65,-6+j,76,-4+j)),mix(mid,cream,.28),.65)
    h.box(6,-4.5,13,9,'c5b080',ink,.9)
    for j in range(3):h.line([(9+3*j,-4),(9+3*j,4)],ink,.6)
    rim(q,0,0,39,38,[(1,mix(mid,ink,.45),ink),(.946,'d2c49b',ink),(.894,'e3e9d9',ink)])
    radius=33
    for n in range(-24,25,8):
        d=(radius**2-n*n)**.5;q.line([(-d,n),(d,n)],rule,.65);q.line([(n,-d),(n,d)],rule,.65)
    q.line([(-30,12),(-19,9),(-11,12),(0,-4),(12,0),(24,-16)],ink,2)
    for pt in [(-19,9),(-11,12),(0,-4),(12,0),(24,-16)]:q.el(*pt,2.4,2.4,gold,ink,.85)
    q.line(oval(0,0,30,29,204,272),'ffffeb',2.4);q.line(oval(0,0,36.5,36,7,102),cream,.95)

def interface(p):
    bg,ink,mid,gold=STOCKS[1]; cream='f8efd9';shadow='bb9c87';q=p.at(188,62,-8,1,1,-.08)
    q.shape([(-7,-5),(204,-4),(208,122),(-5,128)],mid,ink,1.3)
    for j in [4,2,0]:
        q.shape(path((-4,j),(27,-3+j,70,-4+j,98,4+j),(127,-1+j,167,-4+j,201,-2+j),(202,117+j),(161,115+j,125,120+j,99,123+j),(66,114+j,28,117+j,-4,120+j)),cream,ink,.8)
    for i in range(1,6):q.line(path((92+i,4),(93+i,41,93+i,82,94+i,119)),mix(cream,shadow,i/9),.65)
    for i in range(9):
        yy=12+i*12;q.el(94,yy,1.3,1.8,ink);q.el(104,yy-.4,1.3,1.8,ink)
        q.line(path((94,yy),(93,yy-6,104,yy-6,104,yy)),ink,1.2)
    # Browser diagram and a paper mobile prototype on facing pages.
    q.box(8,12,72,64,'f1e4ca',ink,1.05);q.line([(8,21),(80,21)],ink,.8)
    for i in range(3):q.el(13+i*4,16,1,1,mid)
    q.box(13,27,61,24,'ddc1a8',ink,.7);q.line([(14,50),(32,35),(42,43),(50,36),(74,50)],ink,.85);q.el(61,33,2.7,2.7,cream)
    for i in range(3):q.box(13+21*i,57,16,5,'b98d76',ink,.5);q.line([(13+21*i,66),(25+21*i,66)],ink,.7)
    for j in range(3):q.line([(11,87+j*5),(59-j*5,87+j*5)],mid,.72)
    q.dash(path((72,88),(82,86,86,75,82,69)),ink,.75,2.4,2.4)
    q.box(119,15,45,84,'eddcc4',ink,1.3);q.box(122,19,39,73,cream,ink,.65);q.el(141,95,1.4,1.4,mid)
    q.box(125,23,33,18,'cba68c',ink,.55);q.line([(126,39),(138,29),(144,34),(156,25)],ink,.82)
    for j in range(3):
        q.box(125,47+j*12,7,7,None,ink,.62);q.line([(136,49+j*12),(157-j*2,49+j*12)],ink,.87);q.line([(136,52+j*12),(146+j*2,52+j*12)],mid,.6)
    q.box(128,83,25,4,mid,ink,.45);q.line([(169,34),(181,29),(190,29)],ink,.65)
    # Engraver's triangle, cut from honey-tinted celluloid.
    t=p.at(388,170,-12);tri=[(0,0),(96,0),(96,-65)];t.shape(tri,'e2bd8a',ink,1.15);t.shape([(27,-8),(85,-8),(85,-47)],bg,ink,1)
    for a in range(4,94,3):t.line([(a,-1),(a,-(5.5 if a%3==1 and a%2==0 else 3.5))],ink,.55)
    t.line([(92,-61),(92,-5)],cream,.75)
    pencil(p,336,157,-39,155,ink,'ab7051')

def bone(p,outline,shade,folds,ink,mid):
    p.shape(outline,'f2ecd5',ink,1.4);p.shape(shade,'c5c9b9');p.hatch(shade,mix(mid,ink,.30),3.7,-.65,.52);p.line(outline+[outline[0]],ink,1.28)
    for line in folds:p.line(line,mix(ink,mid,.33),.83)

def rehab(p):
    bg,ink,mid,gold=STOCKS[2];q=p.at(288,117)
    # Lateral knee with patella, the tibial tuberosity and separate fibula.
    # The model is bent so its two long bones make the flexion angle clear.
    femur=path((-100,-75),(-88,-78,-84,-76,-77,-69),(-52,-50,-39,-36,-21,-30),(-10,-27,0,-26,8,-19),(18,-15,20,-2,15,5),(12,12,3,15,-6,10),(-15,14,-24,9,-26,1),(-28,-9,-21,-11,-32,-22),(-51,-40,-73,-51,-98,-64),(-105,-66,-105,-70,-100,-75))
    shaded=path((-97,-65),(-75,-55,-45,-31,-30,-21),(-13,-7,-19,1,-14,6),(-9,12,-3,6,1,6),(7,10,12,7,16,2),(14,13,7,15,-7,10),(-17,16,-27,8,-26,0),(-27,-12,-29,-16,-34,-23),(-57,-42,-83,-55,-97,-65))
    bone(q,femur,shaded,[path((-88,-68),(-66,-59,-36,-31,-21,-25)),path((-23,-21),(-8,-14,-10,-8,-10,-3)),path((-12,2),(-11,-12,5,-14,12,-7)),path((-5,6),(2,10,16,3,12,-4))],ink,mid)
    tibia=path((-16,16),(-6,10,6,14,16,12),(26,9,29,17,26,22),(23,29,14,33,20,43),(29,59,41,72,52,82),(55,86,50,91,43,89),(24,76,12,57,0,45),(-7,36,-9,33,-15,32),(-22,30,-24,19,-16,16))
    shaded=path((-17,19),(-11,23,-6,21,3,23),(1,35,17,53,26,66),(32,77,44,82,47,87),(43,90,35,83,29,78),(13,63,3,44,-9,36),(-19,32,-22,25,-17,19))
    bone(q,tibia,shaded,[path((-16,18),(-4,22,13,15,22,16)),path((4,25),(11,25,11,35,15,40)),path((9,39),(18,50,31,73,45,81)),path((18,25),(22,23,23,19,23,17))],ink,mid)
    fibula=path((-19,35),(-23,31,-28,35,-25,40),(-23,43,-18,43,-16,47),(-2,62,15,80,33,94),(37,96,40,94,37,90),(15,69,-4,53,-15,39),(-15,35,-16,33,-19,35))
    q.shape(fibula,'d9decc',ink,1);q.line(path((-19,40),(-2,62,20,83,33,92)),mid,.8)
    pat=path((23,-12),(28,-16,34,-10,32,-4),(31,1,28,8,24,8),(20,5,19,-4,23,-12));q.shape(pat,'e8dfbf',ink,1);q.hatch(pat,mid,3,-.9,.5)
    # Tendon strokes, cancellous bone marks and the articular surface.
    q.line(path((13,-19),(24,-17,29,-13,31,-9)),mid,.9);q.line(path((29,5),(30,12,26,20,23,27)),mid,1.05)
    for j in range(8):
        q.line(path((-19+j*1.1,-4),(-22+j*1.2,0,-20+j*1.4,4,-17+j*1.3,6)),mid,.47)
    q.dash(oval(1,2,77,64,211,332),mid,.85,4,3);q.shape([(69,-29),(72,-24),(65,-26)],mid)
    # Separate open brass goniometer with an engraved semicircular degree scale.
    t=p.at(386,126);arm=t.at(0,0,-47)
    arm.box(-6,-5,113,10,'d4d1b8',ink,1.1);arm.line([(8,1),(104,1)],mid,.8)
    for k in range(15,104,4):arm.line([(k,-4),(k,-1 if k%8 else 1)],ink,.56)
    disk=oval(0,0,34,34,180,360)+[(34,7),(-34,7)];t.shape(disk,'d6c59b',ink,1.15)
    for rr in [20,26,31]:t.line(oval(0,0,rr,rr,181,359),ink,.65)
    for j in range(37):
        th=math.pi+j*math.pi/36;r=24 if j%3==0 else 27;t.line([(r*math.cos(th),r*math.sin(th)),(31*math.cos(th),31*math.sin(th))],ink,.68)
    arm=t.at(0,0,21);arm.box(-6,-4.5,123,9,'ddd3af',ink,1.05)
    for k in range(12,116,3):arm.line([(k,-3.8),(k,-1 if k%9 else 1)],ink,.57)
    t.el(0,0,6,6,'b9a676',ink,.9);t.el(0,0,2.9,2.9,'e9e1c6',ink,.7);t.line([(-1.7,1.5),(1.7,-1.5)],ink,.8)

def plate(i, illustrator):
    p=backing(i)
    illustrator(p)
    image=p.im.resize((650,220),Image.Resampling.LANCZOS)
    grain(image,520+i).save(ROOT/f'role-{i}.webp',quality=95,method=6)

def gear(q,rx,ry,n,ink,metal,stock):
    def toothring():
        ring=[]
        for i in range(n):
            for dt,r in [(0,.88),(.18,.89),(.27,1),(.59,1),(.69,.89),(.83,.88)]:
                t=TAU*(i+dt)/n; ring.append((r*rx*math.cos(t),r*ry*math.sin(t)))
        return ring
    ring=toothring(); side=mix(ink,metal,.32);q.shape([(x+4,y+7) for x,y in ring],side,ink,1.16)
    for x,y in ring[2::6]:q.line([(x,y),(x+4,y+7)],ink,.65)
    q.shape(ring,metal,ink,1.25);q.el(0,0,rx*.75,ry*.75,mix(metal,ink,.15),ink,.68);q.el(0,0,rx*.69,ry*.69,metal,ink,.7)
    for i in range(5):
        a=TAU*i/5+.05; xx=rx*.48*math.cos(a);yy=ry*.48*math.sin(a)
        q.el(xx,yy,rx*.125,ry*.125,side,ink,.8);q.el(xx+1,yy+1.6,rx*.097,ry*.087,stock,ink,.45)
    for a in range(0,360,4):
        t=math.radians(a);q.line([(rx*.77*math.cos(t),ry*.77*math.sin(t)),(rx*.82*math.cos(t),ry*.82*math.sin(t))],mix(ink,metal,.36),.55)
    rim(q,0,0,rx*.27,ry*.27,[(1,side,ink),(.86,metal,ink),(.5,ink,ink),(.38,stock,None)])

def engineering(p):
    bg,ink,mid,gold=STOCKS[3]
    gear(p.at(355,89,-13),72,57,22,ink,'a4b3a0',bg)
    gear(p.at(426,135,3),43,35,15,ink,'c4b389',bg)
    # Vernier caliper, with fixed jaw, moving jaw, depth rod and thumb roller.
    q=p.at(166,134,-20);steel='d7d8c3';light='ecebd6'
    q.shape([(2,-15),(14,-15),(18,-9),(241,-9),(241,2),(17,2),(16,36),(9,51),(4,53),(3,9),(-2,1)],steel,ink,1.45)
    q.shape([(5,-12),(8,-23),(14,-34),(16,-32),(14,-10)],mid,ink,1.05)
    q.line([(20,-6),(237,-6)],'f3f2de',1);q.line([(22,.1),(240,.1)],mid,.8)
    for i in range(18,239,3):q.line([(i,-8.2),(i,-5 if i%15 else -2.2)],ink,.62)
    q.shape([(47,-11),(46,-32),(50,-34),(59,-15),(63,-10),(95,-10),(99,-7),(99,10),(54,10),(55,38),(50,51),(44,54),(44,4)],'b9c5b3',ink,1.2)
    q.box(49,-7,45,13,steel,ink,.8)
    for i in range(52,94,3):q.line([(i,-4),(i,0 if i%2 else 2)],ink,.55)
    q.line([(6,7),(7,48)],'f1efdb',1.35);q.line([(46,9),(46,47)],ink,.75)
    q.shape([(72,9),(90,9),(89,16),(85,20),(77,20),(72,16)],mid,ink,.9)
    for i in range(74,91,2):q.line([(i,12),(i-1,17)],ink,.54)
    q.box(239,-6,19,3.5,mid,ink,.6)

def supply_chain(p):
    bg,ink,mid,gold=STOCKS[4]
    cream='f5ecd6'
    board=p.at(292,48,-5)
    outline=[(-4,3),(0,-2),(176,-2),(180,2),(180,131),(176,135),(0,135),(-4,131)]
    board.shape(outline,'ac9475',ink,1.35)
    board.box(2,4,172,125,'ded4b9',ink,.7)
    board.box(4,2,169,124,cream,ink,.8)
    clip=path((57,7),(57,3,63,2,67,2),(69,-2,68,-8,76,-10),(86,-13,94,-8,93,-2),(93,1),(105,1,107,3,107,7),(107,10),(57,10))
    board.shape(clip,'c5ae81',ink,1)
    board.el(81,-5,4.4,2.2,cream,ink,.65)
    board.line([(60,7),(105,7)],cream,.8)

    # Material, assembly and dispatch windows share the same calendar grid.
    grid=mix(mid,cream,.28)
    for col in range(9):
        x=45+14*col
        board.line([(x,24),(x,84)],grid,.57)
        board.line([(x+2,23),(x+6,23)],mid,.78)
    for row in range(5):
        y=29+13*row
        board.line([(15,y),(161,y)],grid,.58)
    stagger=[(49,34,33),(70,47,47),(107,60,27),(124,73,27)]
    for index,(x,y,width) in enumerate(stagger):
        board.line([(17,y+1),(31+(index%2)*5,y+1)],ink,.8)
        board.line([(17,y+3.5),(25,y+3.5)],mid,.55)
        board.box(x,y-1,width,5.5,gold if index in (0,3) else 'abaf96',ink,.71)
        if index<3:
            next_x=stagger[index+1][0]
            board.line([(x+width-2,y+4.5),(x+width-2,y+7.5),(next_x+3,y+7.5),(next_x+3,y+11.5)],mid,.75)
    # Warehouse, carton and delivery lorry form a wordless dispatch key.
    for start,end in [(43,76),(95,124)]:
        board.dash([(start,105),(end,105)],mid,.85,3,2)
        board.line([(end-3,103),(end,105),(end-3,107)],ink,.78)
    board.shape([(20,101),(30,94),(41,101),(40,113),(20,113)],'d6c5a3',ink,.85)
    board.box(25,103,10,10,cream,ink,.65)
    for y in [105,108,111]:board.line([(26,y),(34,y)],mid,.52)
    board.shape([(78,99),(85,95),(94,99),(94,109),(87,114),(78,110)],'decbab',ink,.8)
    board.line([(78,99),(87,103),(94,99)],ink,.7)
    board.line([(87,103),(87,114)],ink,.7)
    board.box(128,98,17,10,'d8c7a0',ink,.9)
    board.shape([(145,101),(151,101),(156,106),(156,110),(145,110)],mid,ink,.85)
    board.line([(129,110),(155,110)],ink,1.2)
    for x in (133,150):board.el(x,111,2.5,2.5,ink);board.el(x,111,1,1,cream)

    # A shallow pallet lifts the slatted packing cases clear of the page.
    pallet=p.at(160,168,-2)
    pallet.shape([(0,0),(110,7),(145,-8),(34,-14)],'d7c3a0',ink,.95)
    for x,y in [(8,6),(84,11),(121,3)]:pallet.box(x,y,12,6,'aa9376',ink,.8)
    pallet.shape([(0,0),(111,7),(111,13),(0,6)],'b7a080',ink,1)
    pallet.shape([(111,7),(145,-8),(145,-2),(111,13)],'a58c71',ink,.9)

    def crate(x,y,scale,seed,brace):
        case=p.at(x,y,-2,scale)
        face=[(0,0),(89,8),(89,58),(0,49)]
        side=[(89,8),(119,-6),(119,43),(89,58)]
        lid=[(0,0),(31,-13),(119,-6),(89,8)]
        case.shape(face,'d8bf98',ink,1.25)
        case.shape(side,'b69c7c',ink,1.1)
        case.shape(lid,'e5d3b1',ink,1.1)
        for h in [15,31]:
            case.line([(1,h),(88,h+8),(118,h-6)],ink,.75)
            case.line([(1,h+1.5),(88,h+9.5)],cream,.65)
        for off in [8,17,25]:case.line([(off,-off*.41),(off+87,8-off*.44)],mid,.64)
        rng=random.Random(seed)
        for _ in range(23):
            xx=rng.uniform(3,70);yy=rng.uniform(4,44)+xx*.10;w=rng.uniform(4,15)
            case.line(path((xx,yy),(xx+w*.25,yy-.5,xx+w*.7,yy+.4,xx+w,yy+w*.1)),mid,.48)
        for offset in (0,78):
            yy=offset*.1
            case.shape([(offset,yy),(offset+9,yy+.9),(offset+9,yy+49.2),(offset,yy+48.5)],'c5aa83',ink,.8)
            for h in (3.5,45):case.el(offset+4.5,yy+h,.8,.8,ink)
        case.shape([(111,-2),(118,-5),(118,42),(111,45)],'bea482',ink,.72)
        if brace:
            case.shape([(9,38),(77,9),(77,18),(9,47)],'e4ceaa',ink,.88)
            case.line([(13,42),(74,16)],mid,.6)
        else:
            case.shape([(37,14),(61,16),(61,37),(37,35)],cream,ink,.8)
            for xx in (44,53):
                case.line([(xx,29),(xx,20)],ink,1.15)
                case.line([(xx-2.4,23),(xx,20),(xx+2.4,23)],ink,.95)
            case.line([(41,31),(57,32.5)],ink,.76)
    crate(167,123,1.05,48,True)
    crate(183,80,.78,52,False)


def social_work(p):
    bg,ink,mid,gold=STOCKS[5]
    cream='f0edd9'
    # The resource map is an accordion fold with a continuous street network.
    atlas=p.at(259,56,-4)
    seams=[(0,5),(42,-2),(85,6),(129,-2)]
    for panel,tint in enumerate(['e5e7d2','d4decb','e9e9d5']):
        (x,y),(end,h)=seams[panel:panel+2]
        atlas.shape([(x,y),(end,h),(end,h+69),(x,y+69)],tint,mid,.85)
    streets=[[(2,47),(28,32),(47,35),(78,20),(102,25),(127,13)],
             [(5,13),(26,26),(39,50),(65,67)],[(32,6),(47,20),(77,35),(97,47),(123,54)],
             [(67,6),(62,25),(68,41),(59,57)],[(16,64),(37,51),(58,57),(85,43),(104,39),(125,43)],
             [(97,7),(91,23),(98,32),(105,46),(102,62)]]
    for street in streets:
        atlas.line(street,'acbfad',3.2)
        atlas.line(street,'f5f2dd',1.95)
    for x,y in seams[1:3]:atlas.dash([(x,y+1),(x,y+68)],mid,.65,2,2)
    for x,y in [(27,34),(67,44),(106,19)]:
        pin=path((x,y),(x-2,y-3,x-5,y-6,x-5,y-9),(x-5,y-15,x+5,y-15,x+5,y-9),(x+5,y-6,x+2,y-3,x,y))
        atlas.shape(pin,gold,ink,.8)
        atlas.el(x,y-9,1.6,1.6,cream)

    def chair(x,y,facing,fabric):
        frame='bba587'
        c=p.at(x,y,0,.93*facing,.93)
        legs=[[(47,62),(52,60),(51,114),(47,116)],[(74,81),(79,83),(84,120),(80,122)],
              [(17,76),(23,76),(12,131),(7,132)],[(49,91),(56,91),(61,141),(57,143)]]
        for leg in legs:c.shape(leg,frame,ink,1.05)
        c.line([(16,104),(55,116)],ink,1.3)
        c.line([(55,116),(80,102)],ink,1.1)
        # The bentwood rails wrap around the upholstered back and seat.
        rear=path((0,18),(-1,10,3,6,9,5),(34,-2),(41,-4,43,-1,45,6),(53,54),(52,62,48,66,41,70),(22,77),(16,80,12,77,11,71),(0,18))
        c.shape(rear,frame,ink,1.3)
        pad=path((4,17),(3,12,6,10,11,9),(34,2),(39,0,40,2,41,7),(49,51),(50,57,47,61,42,63),(21,70),(17,72,15,69,14,64),(4,17))
        c.shape(pad,fabric,ink,.92)
        c.hatch(pad,mix(fabric,cream,.37),5.5,-.38,.49)
        c.line(path((8,16),(8,12,10,12,14,11),(34,5)),cream,.72)
        c.line(path((18,64),(20,69,24,66,29,65),(44,59)),mix(ink,fabric,.45),.7)
        for pt in [(16,32),(36,26)]:c.el(*pt,1,1,mix(fabric,ink,.35))
        c.shape([(13,71),(46,59),(81,78),(79,88),(50,101),(15,83)],frame,ink,1.15)
        seat=path((13,69),(13,66,17,64,22,63),(42,56),(45,55,49,55,52,57),(78,72),(85,76,84,81,80,84),(53,96),(49,97,46,96,42,94),(18,82),(14,80,13,77,13,74))
        c.shape(seat,fabric,ink,1.07)
        c.line(path((15,72),(17,75,37,85,47,88),(50,90,52,90,56,88),(77,79),(80,78,81,77,81,75)),mix(fabric,cream,.75),.84)
        c.line(path((17,77),(28,82,42,91,49,93),(54,93,71,84,79,81)),mix(fabric,ink,.38),.72)
        for xx,yy in [(17,81),(52,98)]:c.el(xx,yy,1,1,ink)
    chair(174,52,1,'a8beaa')
    chair(478,60,-1,'c7bb96')

def camera(p):
    bg,ink,mid,gold=STOCKS[6];cream='efdfbf'; q=p.at(188,58,-4)
    # Rear standard, folded leather bellows, brass front standard and lens hood.
    q.shape([(0,15),(22,2),(42,6),(42,113),(21,127),(0,122)],'9c7966',ink,1.45)
    q.shape([(5,18),(20,10),(20,117),(5,120)],'c0a087',ink,.75)
    for i in range(5):q.line([(5+2.6*i,20),(5+2.6*i,116)],mix(ink,mid,.7),.47)
    q.shape([(24,9),(143,38),(143,103),(24,120)],'b38a76',ink,1.35)
    for i in range(12):
        u=i/12;v=(i+1)/12; xx=28+u*116;X=28+v*116; t=11+u*28; T=11+v*28; b=118-u*16;B=118-v*16;midX=(xx+X)/2
        q.shape([(xx,t),(midX,t+5),(midX,b-4),(xx,b)],'846c60',ink,.75)
        q.shape([(midX,t+5),(X,T),(X,B),(midX,b-4)],'c49c85',ink,.65)
        q.line([(xx+1,t+1),(xx+1,b-1)],'e0bea2',.66)
    q.shape([(24,9),(55,2),(162,34),(143,39)],'d1ae94',ink,1)
    for i in range(12):
        u=i/12;xx=28+u*112;yy=10+u*28;q.line([(xx,yy),(xx+20,yy-5)],ink,.85)
    q.shape([(2,124),(23,130),(187,124),(204,112),(183,107),(40,116)],'b59b77',ink,1.2)
    q.shape([(23,130),(187,124),(187,128),(23,135)],'96846d',ink,.8)
    q.shape([(139,33),(158,26),(185,31),(185,108),(157,116),(139,110)],'bd9f7e',ink,1.4)
    q.shape([(143,36),(158,32),(158,110),(143,106)],'91705d',ink,.8)
    q.shape([(160,32),(184,34),(184,106),(160,112)],'d3b698',ink,.95)
    q.el(182,71,16,28,'c5ab81',ink,1.16);q.shape([(181,44),(207,50),(208,94),(181,99)],'b49773',ink,1.1)
    for i in range(5):q.line(path((184+i*4,44+i),(194+i*4,55,196+i*4,80,185+i*4,98-i)),ink,.74)
    q.el(209,71,14,23,'8c7765',ink,1.2);q.el(211,71,11.4,19,'564d47',ink,1.0);q.el(212,71,7,14,'829087',ink,.85);q.line(oval(212,71,5,10,223,290),cream,1.5)
    q.el(174,116,6,5,'b49b76',ink,1.0);q.el(174,116,2,2,cream,ink,.65)
    # A roll of perforated film makes the plate readable even at thumb size.
    t=p.at(425,110,13);t.box(0,0,29,47,'a48671',ink,1.15);t.el(14.5,47,14.5,4.8,'967963',ink,1.0);t.box(0,3,29,42,'b69a76');t.box(1,12,27,20,cream,ink,.65);t.el(14.5,0,14.5,4.6,'d2bfa1',ink,1);t.el(14.5,-1,5.5,2.2,ink);t.box(11,-5,7,5,ink)
    strip=path((25,18),(41,19,39,36,55,34),(60,34,62,32,66,30),(66,48),(49,58,36,45,32,40),(28,37,24,38,24,37));t.shape(strip,'a98c75',ink,.85)
    for j in range(7):
        x=29+5*j; y=20+14*math.sin(j/6*math.pi*.65);t.box(x,y,2,1.7,cream);t.box(x,y+13,2,1.7,cream)

def architecture(p):
    bg,ink,mid,gold=STOCKS[7];cream='f4efdd';q=p.at(166,62,-5,1,1,-.06)
    q.box(1,3,208,119,mid,ink,.9);q.box(0,0,208,119,cream,ink,1)
    # A measured elevation showing an arcade and its dressed-stone voussoirs.
    q.line([(10,100),(196,100)],ink,1);q.box(15,90,173,7,'c1c4b0',ink,.8);q.box(21,33,163,57,'d6d5bf',ink,.9)
    for j in range(7):
        y=37+j*8;q.line([(22,y),(184,y)],mid,.5)
        for k in range(10):
            x=24+k*18+9*(j%2)
            if x<183:q.line([(x,y),(x,y+5.7)],mid,.4)
    for x in [50,102,154]:
        q.shape([(x-15,90),(x-15,63)]+oval(x,63,15,18,180,360)+[(x+15,90)],cream,ink,.9)
        q.line(oval(x,63,21.3,24,180,360),ink,.9)
        for aa in range(180,361,15):
            th=math.radians(aa);q.line([(x+15*math.cos(th),63+18*math.sin(th)),(x+21.3*math.cos(th),63+24*math.sin(th))],ink,.6)
        q.box(x-23,62,10,3,cream,ink,.7);q.box(x+13,62,10,3,cream,ink,.7)
    q.box(17,29,171,4,'b9beac',ink,.78);q.box(15,25,174,4,'e2dfc7',ink,.78);q.box(22,21,160,4,'d2d0b7',ink,.8)
    q.dash([(11,107),(191,107)],mid,.6,6,2)
    for x in [21,77,128,184]:q.line([(x,102),(x,111)],mid,.65)
    # Hinged drawing dividers with replaceable steel points.
    t=p.at(420,41,9)
    for pts,fill in [([(-6,9),(-1,9),(-16,89),(-27,130),(-31,130),(-26,97)],'bba579'), ([(3,9),(9,7),(36,98),(42,134),(38,133),(26,99)],'c6b58e')]:
        t.shape(pts,fill,ink,1.25);t.hatch(pts,mix(ink,gold,.65),4,-1,.5)
    t.shape([(-27,113),(-22,114),(-34,150),(-34,146)],mid,ink,.85);t.shape([(35,119),(40,117),(47,152),(43,147)],mid,ink,.85)
    t.box(-2,-19,6,20,'c4b691',ink,1);t.box(-3,-16,8,8,'a79572',ink,.75)
    for j in range(3):t.line([(-3,-15+j*2),(5,-15+j*2)],ink,.55)
    t.el(1,6,11,11,'c0af85',ink,1.15);t.el(1,6,6.5,6.5,'e5ddc1',ink,.85);t.line([(-2,9),(4,3)],ink,1)
    t.line([(-14,71),(29,71)],ink,2);t.line([(-14,70),(29,70)],cream,.6);t.box(4,66,8,10,'b5a47f',ink,.75)
    for j in range(3):t.line([(5+2*j,67),(5+2*j,75)],ink,.5)

if __name__=='__main__':
    ROOT.mkdir(exist_ok=True)
    if len(sys.argv)==1 or 'terrain' in sys.argv: terrain()
    for i,fn in enumerate([report,interface,rehab,engineering,supply_chain,social_work,camera,architecture]):
        if len(sys.argv)==1 or str(i) in sys.argv:plate(i,fn)
