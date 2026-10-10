from pathlib import Path
import xml.etree.ElementTree as E
ROOT=Path(__file__).resolve().parents[1]
project=ROOT/'projects'/'starter-test';project.mkdir(exist_ok=True)
(project/'frames').mkdir(exist_ok=True)
canvas=E.Element('canvas',version='0.2',width='640',height='360',xres='2834.645752',yres='2834.645752',**{'view-box':'-4 2.25 4 -2.25','antialias':'1','fps':'24','begin-time':'0f','end-time':'10s','bgcolor':'0.91 0.88 0.80 1'})
E.SubElement(canvas,'name').text='StoryStudio — movement and blinking test'
def value(parent,kind,data):
 if kind=='vector':
  node=E.SubElement(parent,kind)
  for key,val in zip(['x','y'],data):E.SubElement(node,key).text=str(val)
 elif kind=='color':
  node=E.SubElement(parent,kind)
  for key,val in zip('rgba',data):E.SubElement(node,key).text=str(val)
 else:E.SubElement(parent,kind,value=str(data).lower())
def param(layer,name,kind,data):value(E.SubElement(layer,'param',name=name),kind,data)
def animated(layer,name,kind,points):
 node=E.SubElement(E.SubElement(layer,'param',name=name),'animated',type=kind)
 for time,data in points:
  point=E.SubElement(node,'waypoint',time=f'{time}s',before='linear',after='linear');value(point,kind,data)
def circle(name,radius,pos,color,blink=False):
 l=E.SubElement(canvas,'layer',type='circle',active='true',version='0.2',desc=name)
 param(l,'blend_method','integer',0);param(l,'color','color',color);param(l,'radius','real',radius)
 param(l,'feather','real',0)
 x,y=pos
 animated(l,'origin','vector',[(0,(x-.6,y)),(5,(x+.6,y)),(10,(x-.6,y))])
 if blink:animated(l,'amount','real',[(0,1),(2.9,1),(3,0),(3.15,1),(6.9,1),(7,0),(7.15,1),(10,1)])
 else:param(l,'amount','real',1)
coal=(.025,.021,.018,1);cream=(.88,.82,.68,1);gold=(.56,.35,.09,1)
circle('Left pupil',.075,(-.21,.69),coal,True)
circle('Right pupil',.075,(.21,.69),coal,True)
circle('Left eye',.14,(-.21,.7),cream,True)
circle('Right eye',.14,(.21,.7),cream,True)
circle('Head',.62,(0,.62),gold)
circle('Body',.83,(0,-.74),coal)
l=E.SubElement(canvas,'layer',type='SolidColor',active='true',version='0.1',desc='Cream background')
param(l,'color','color',(.83,.78,.66,1));param(l,'amount','real',1);param(l,'blend_method','integer',0)
layers=list(canvas.findall('layer'))
for layer in layers:canvas.remove(layer)
for layer in reversed(layers):canvas.append(layer)
E.indent(canvas)
E.ElementTree(canvas).write(project/'starter.sif',encoding='utf-8',xml_declaration=True)
print(project/'starter.sif')
