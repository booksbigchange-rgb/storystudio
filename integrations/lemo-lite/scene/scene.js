import {clamp,lerp,seg,ss,eo,TAU,hash} from '../vendor/lemo-lib.js';

// Original StoryStudio test animation. Deterministic Lemo-style render(t).
// No cloud model, API key, or paid asset required.
const canvas=document.getElementById('film');
const ctx=canvas.getContext('2d',{alpha:false});
const DUR=10;
let playing=false, clock=0, prev=0;
const capture=new URLSearchParams(location.search).has('capture');
if(capture) document.body.classList.add('capture');
const scrub=document.getElementById('scrub');
const stamp=document.getElementById('stamp');
function ellipse(x,y,rx,ry,c){ctx.fillStyle=c;ctx.beginPath();ctx.ellipse(x,y,rx,ry,0,0,TAU);ctx.fill()}
function path(coords,color){ctx.fillStyle=color;ctx.beginPath();ctx.moveTo(...coords[0]);coords.slice(1).forEach(p=>ctx.lineTo(...p));ctx.closePath();ctx.fill()}
function roundRect(x,y,w,h,r,col){ctx.fillStyle=col;ctx.beginPath();ctx.roundRect(x,y,w,h,r);ctx.fill()}
function star(x,y,r,n=5,color='#fff9a8'){
  ctx.save();ctx.translate(x,y);ctx.fillStyle=color;ctx.beginPath();
  for(let i=0;i<n*2;i++){
    const a=-Math.PI/2+i*Math.PI/n,rad=i%2===0?r:r*.44;
    const px=Math.cos(a)*rad,py=Math.sin(a)*rad;
    if(i===0)ctx.moveTo(px,py);else ctx.lineTo(px,py);
  }ctx.closePath();ctx.fill();ctx.restore();
}
function cloud(x,y,s){ctx.save();ctx.translate(x,y);ctx.scale(s,s);ellipse(-37,4,52,21,'#ffffffbc');ellipse(0,-10,49,34,'#ffffffda');ellipse(40,5,44,23,'#fffffff0');ctx.restore()}
function bush(x,y,s,color){ctx.save();ctx.translate(x,y);ctx.scale(s,s);ellipse(-22,0,46,27,color);ellipse(15,-8,48,34,color);ellipse(60,1,40,28,color);ctx.restore()}
function fox(t){
  const arrival=ss(seg(t,.3,2.1));
  const x=lerp(-180,475,arrival)+(t>3.4?32*ss(seg(t,3.5,4.8)):0);
  const jump=t>=5.15&&t<=6.85 ? Math.sin(Math.PI*seg(t,5.15,6.85))*118 : 0;
  const bob=Math.sin(t*7)*5*(1-seg(t,2.1,2.6));
  ctx.save();ctx.translate(x,535-jump+bob);
  ellipse(0,95,104-jump*.22,15-jump*.08,'#294c4580');
  ctx.save();ctx.rotate(Math.sin(t*4)*.12-.1);
  path([[42,31],[115,4],[139,-55],[167,-40],[151,10],[104,53],[55,67]],'#e9763d');
  path([[139,-55],[167,-40],[151,10],[123,19],[129,-10]],'#fff4de');
  ctx.restore();
  roundRect(-43,49,33,54,15,'#99542d');roundRect(17,49,33,54,15,'#99542d');
  ellipse(-26,101,28,14,'#fff3d8');ellipse(32,101,28,14,'#fff3d8');
  ellipse(0,18,75,85,'#ed8544');ellipse(-1,22,45,65,'#ffeacb');
  ctx.save();ctx.translate(50,-8);ctx.rotate(-.24-.54*ss(seg(t,3.3,4.6))+.06*Math.sin(t*6));
  roundRect(-5,-4,29,76,14,'#ed8544');ellipse(9,67,19,18,'#fff0d6');ctx.restore();
  ctx.save();ctx.translate(-52,-6);ctx.rotate(.24);roundRect(-25,0,29,70,14,'#ed8544');ellipse(-12,63,17,15,'#fff0d6');ctx.restore();
  path([[-74,-101],[-82,-199],[-7,-152]],'#b95f36');path([[74,-101],[88,-199],[5,-152]],'#b95f36');
  path([[-63,-137],[-69,-182],[-26,-150]],'#f3b9a4');path([[63,-137],[76,-183],[29,-151]],'#f3b9a4');
  ellipse(0,-97,99,90,'#ed8544');ellipse(-64,-64,45,35,'#fff1d6');ellipse(64,-64,45,35,'#fff1d6');
  ellipse(0,-54,43,26,'#fff1d6');ellipse(0,-65,17,12,'#363a41');
  const blink=Math.abs(t-2.45)<.10||Math.abs(t-7.55)<.10;
  if(blink){roundRect(-62,-110,43,6,3,'#453a3b');roundRect(21,-110,43,6,3,'#453a3b')}
  else{ellipse(-40,-108,9,14,'#34383b');ellipse(41,-108,9,14,'#34383b');ellipse(-43,-112,3,4,'white');ellipse(38,-112,3,4,'white')}
  ctx.strokeStyle='#8b433d';ctx.lineWidth=5;ctx.lineCap='round';ctx.beginPath();ctx.arc(0,-54,17,.1,Math.PI-.1);ctx.stroke();
  ellipse(-70,-84,13,7,'#f59b86');ellipse(70,-84,13,7,'#f59b86');
  ctx.restore();
}
function picture(t){
  const W=canvas.width,H=canvas.height;
  ctx.setTransform(W/1280,0,0,H/720,0,0);
  let sky=ctx.createLinearGradient(0,0,0,720);
  sky.addColorStop(0,'#81d9eb');sky.addColorStop(.65,'#d8f7d9');sky.addColorStop(1,'#fff0ad');
  ctx.fillStyle=sky;ctx.fillRect(0,0,1280,720);
  ellipse(1108,134,77,77,'#fff6b5');ellipse(1108,134,96,96,'#fffac64a');
  cloud(205+t*3,133,1);cloud(935-t*2,213,.7);cloud(660+t*1.2,74,.57);
  path([[0,464],[160,311],[333,475],[533,351],[748,475],[981,345],[1280,473],[1280,720],[0,720]],'#77baa4');
  path([[0,496],[212,421],[463,499],[709,411],[986,503],[1213,419],[1280,459],[1280,720],[0,720]],'#5aa887');
  ellipse(640,725,1080,254,'#8ac878');ellipse(1077,728,530,208,'#a0d781');
  bush(70,583,2.1,'#469765');bush(1178,560,1.7,'#4c9e68');
  for(let i=0;i<18;i++){
    const px=75+i*69+(hash(i+3)-.5)*48, py=620+hash(i*1.23)*98;
    ellipse(px,py,4,8,'#ffe5a6');ellipse(px-7,py+2,4,8,'#fff2bc');
    ellipse(px+6,py+2,4,8,'#ffeab0');ellipse(px,py,4,4,'#ffb95b');
  }
  fox(t);
  const approach=ss(seg(t,2.8,5.4));
  const x=lerp(1044,690,approach)+Math.sin(t*2.8)*35;
  const y=lerp(244,253,approach)-Math.sin(t*3.8)*20;
  ctx.save();ctx.translate(x,y);
  const flash=.2+.15*Math.sin(t*5);
  ellipse(0,0,73,73,'rgba(255,248,156,'+flash+')');
  ctx.rotate(Math.sin(t*1.8)*.16);star(0,0,56,5,'#ffe26f');star(0,-2,44,5,'#fff49d');
  ellipse(-12,-4,4,6,'#7b5e3e');ellipse(14,-4,4,6,'#7b5e3e');
  ctx.strokeStyle='#7b5e3e';ctx.lineWidth=3;ctx.beginPath();ctx.arc(1,4,12,.2,Math.PI-.2);ctx.stroke();
  ctx.restore();
  for(let i=0;i<8;i++){const a=i*TAU/8+t*.35;const radius=82+8*Math.sin(t*4+i);star(x+radius*Math.cos(a),y+radius*.7*Math.sin(a),4+hash(i)*3,4,'#fff7c1')}
  if(t>=7){
    const reveal=ss(seg(t,7,8.5));
    ctx.fillStyle='rgba(38,82,72,'+(.93*reveal)+')';
    ctx.beginPath();ctx.roundRect(755,550,405,89,25);ctx.fill();
    ctx.fillStyle='rgba(255,250,220,'+reveal+')';ctx.font='700 43px system-ui,sans-serif';
    ctx.textAlign='center';ctx.fillText('A little magic!',957,608);
  }
  ctx.setTransform(1,0,0,1,0,0);
}
function render(t){picture(clamp(t,0,DUR));if(!capture){scrub.value=String(clamp(t,0,DUR));stamp.textContent=clamp(t,0,DUR).toFixed(1)+'s'}}
function resize(){canvas.width=innerWidth;canvas.height=innerHeight;render(clock)}
window.DUR=DUR;window.render=render;window.READY=true;
window.addEventListener('resize',resize);
resize();
if(!capture){
  scrub.addEventListener('input',()=>{playing=false;document.getElementById('play').textContent='Play';clock=Number(scrub.value);render(clock)});
  document.getElementById('play').addEventListener('click',()=>{playing=!playing;prev=0;document.getElementById('play').textContent=playing?'Pause':'Play'});
  function tick(ts){if(playing){if(prev)clock+=(ts-prev)/1000;if(clock>DUR)clock=0;render(clock)}prev=ts;requestAnimationFrame(tick)}
  requestAnimationFrame(tick);
}
