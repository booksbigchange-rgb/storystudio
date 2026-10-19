import {clamp,lerp,ss,seg,TAU,hash} from '../vendor/lemo-lib.js';
import {drawCharacter} from './characters.js';
const canvas=document.getElementById('film'), ctx=canvas.getContext('2d',{alpha:false});
const capture=new URLSearchParams(location.search).has('capture');
if(capture)document.body.classList.add('capture');
let doc, clock=0, playing=false, previous=0;
const scrub=document.getElementById('scrub'), stamp=document.getElementById('stamp');
function ellipse(x,y,rx,ry,c){ctx.fillStyle=c;ctx.beginPath();ctx.ellipse(x,y,rx,ry,0,0,TAU);ctx.fill()}
function star(x,y,r,c){ctx.fillStyle=c;ctx.beginPath();for(let i=0;i<10;i++){const a=-Math.PI/2+i*Math.PI/5,rad=i%2?r*.44:r;const p=[x+Math.cos(a)*rad,y+Math.sin(a)*rad];if(i)ctx.lineTo(...p);else ctx.moveTo(...p)}ctx.closePath();ctx.fill()}
export function sceneAt(t, scenes){
  let start=0;
  for(let i=0;i<scenes.length;i++){
    if(t<start+scenes[i].duration || i===scenes.length-1)return {scene:scenes[i],time:clamp(t-start,0,scenes[i].duration),index:i};
    start+=scenes[i].duration;
  }
}
function caption(text,W,H,portrait){
  const font=portrait?32:38, maxWidth=W*.82;
  ctx.font=`700 ${font}px system-ui,sans-serif`;
  const lines=[];let line='';
  for(const char of text){if(ctx.measureText(line+char).width>maxWidth){lines.push(line);line=char}else line+=char}if(line)lines.push(line);
  const height=lines.length*(font+6)+30, y=portrait?H*.77:H*.79;
  ctx.fillStyle='#204e48ef';ctx.beginPath();ctx.roundRect(W*.06,y,W*.88,height,20);ctx.fill();
  ctx.fillStyle='#fff9e9';ctx.textAlign='center';ctx.textBaseline='top';
  lines.forEach((line,i)=>ctx.fillText(line,W/2,y+15+i*(font+6)));ctx.textBaseline='alphabetic';
}
function motionPosition(t,duration,baseX,keys){
  if(!Array.isArray(keys)||keys.length===0)return baseX;
  const sorted=[...keys].sort((a,b)=>a.time-b.time);
  if(t<=sorted[0].time)return sorted[0].x;
  if(t>=sorted[sorted.length-1].time)return sorted[sorted.length-1].x;
  for(let i=0;i<sorted.length-1;i++){
    const a=sorted[i],b=sorted[i+1];
    if(t>=a.time&&t<=b.time){const span=b.time-a.time;if(span<=0)return b.x;return a.x+(b.x-a.x)*((t-a.time)/span)}
  }
  return baseX;
}
function picture(scene,t,W,H){
  const portrait=H>W;
  const colors={meadow:['#8cdeed','#e1f5d0','#75b896','#98cf78'],sunset:['#efb0b1','#ffe0aa','#bf91a3','#d5b18c'],night:['#293e68','#647fa2','#526b80','#749a91']}[scene.background];
  const sky=ctx.createLinearGradient(0,0,0,H);sky.addColorStop(0,colors[0]);sky.addColorStop(1,colors[1]);ctx.fillStyle=sky;ctx.fillRect(0,0,W,H);
  ellipse(W*.82,H*.16,58,58,scene.background==='night'?'#fff9db':'#fff1b7');
  for(let i=0;i<4;i++){const x=(W*(i*.28+.08)+t*(i+1)*2)%(W+100)-40,y=H*(.15+(i%2)*.11);ellipse(x,y,75,22,'#ffffff85');ellipse(x+24,y-13,40,30,'#ffffff85')}
  ellipse(W*.24,H*.85,W*.75,H*.37,colors[2]);ellipse(W*.9,H*.94,W*.8,H*.43,colors[3]);
  for(let i=0;i<22;i++){const x=hash(i+1)*W,y=H*(.7+hash(i+30)*.3);ellipse(x,y,4,7,'#fff0b7')}
  const phase=t/scene.duration*10;
  const keyedX=motionPosition(t,scene.duration,scene.x,scene.motion||[]);
  const baseX=portrait?W*(.29+keyedX*.45):W*keyedX;
  const arrival=scene.action==='story'?ss(seg(phase,.3,2.1)):1;
  const x=lerp(-150,baseX,arrival);
  const walk=scene.action==='walk'?Math.sin(t*.7*scene.speed)*(portrait?45:110):0;
  const scale=(portrait?1.05:1.0)*scene.size;
  const y=portrait?H*.64:H*.63;
  const jump=scene.action==='story' && phase>5.15 && phase<6.85?Math.sin(Math.PI*seg(phase,5.15,6.85))*80:0;
  drawCharacter(ctx,{kind:scene.character,expression:scene.expression,action:scene.action,speed:scene.speed,t,x:x+walk,y:y-jump,scale});
  const sx=portrait?W*.76:lerp(W*.82,W*.64,ss(seg(phase,2.8,5.4)));
  const sy=(portrait?H*.29:H*.33)+Math.sin(t*3)*14;
  ellipse(sx,sy,65,65,'#fff4bb42');star(sx,sy,48,'#ffe16c');star(sx,sy-2,36,'#fff3a0');
  ellipse(sx-10,sy-4,3,5,'#735f45');ellipse(sx+10,sy-4,3,5,'#735f45');
  if(scene.title && (scene.action!=='story'||phase>=7))caption(scene.title,W,H,portrait);
  // Exposed geometry is useful for automated framing checks; no random animation state.
  window.frameInfo={character:scene.character,x:x+walk,y:y-jump,scale,portrait,scene:window.activeScene};
}
function render(t){
  t=clamp(t,0,window.DUR);
  const selected=sceneAt(t,doc.scenes);window.activeScene=selected.index;
  const portrait=doc.format==='Shorts / TikTok 9:16';
  const W=portrait?720:1280,H=portrait?1280:720;
  ctx.setTransform(1,0,0,1,0,0);ctx.fillStyle='#e7eee9';ctx.fillRect(0,0,canvas.width,canvas.height);
  const scale=Math.min(canvas.width/W,canvas.height/H);
  ctx.setTransform(scale,0,0,scale,(canvas.width-W*scale)/2,(canvas.height-H*scale)/2);
  picture(selected.scene,selected.time,W,H);ctx.setTransform(1,0,0,1,0,0);
  if(!capture){scrub.value=String(t);stamp.textContent=`${t.toFixed(1)} / ${window.DUR.toFixed(1)}s`}
}
function resize(){
  canvas.width=innerWidth;canvas.height=capture?innerHeight:innerHeight-72;
  render(clock);
}
window.setProject=(value)=>{doc=structuredClone(value);window.DUR=doc.scenes.reduce((a,s)=>a+s.duration,0);scrub.max=window.DUR;clock=0;resize()};
window.render=render;
async function init(){
  const response=await fetch('/project.json');if(!response.ok)throw new Error('Project could not be loaded');
  window.setProject(await response.json());window.READY=true;
  window.addEventListener('resize',resize);
  if(!capture){
    scrub.addEventListener('input',()=>{playing=false;document.getElementById('play').textContent='Play';clock=Number(scrub.value);render(clock)});
    document.getElementById('play').addEventListener('click',()=>{playing=!playing;previous=0;document.getElementById('play').textContent=playing?'Pause':'Play'});
    function tick(ts){if(playing){if(previous)clock+=(ts-previous)/1000;if(clock>window.DUR)clock=0;render(clock)}previous=ts;requestAnimationFrame(tick)}requestAnimationFrame(tick);
  }
}
init().catch(error=>{document.getElementById('error').textContent=error.message;throw error});
