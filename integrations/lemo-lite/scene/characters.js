// Original reusable Canvas2D cutout rigs. Motion uses Lemo's MIT easing helpers.
import {TAU, ss, seg} from '../vendor/lemo-lib.js';
export const CHARACTERS = ['fox','rabbit','bear'];
export const EXPRESSIONS = ['happy','curious','sad','surprised'];
export const ACTIONS = ['story','idle','wave','walk','jump','talk'];
export function poseAt(t, action='idle', speed=1) {
  const q=t*speed;
  return {
    bob: action==='walk' ? Math.abs(Math.sin(q*7))*9 : Math.sin(q*2)*2,
    jump: action==='jump' ? Math.max(0,Math.sin(q*3))*85 : 0,
    arm: action==='wave' ? -2.1+Math.sin(q*8)*.4 : action==='story' ? -.2-.7*ss(seg(t,3.3,4.6)) : -.2,
    leg: action==='walk' ? Math.sin(q*7)*.35 : 0,
    blink: q%3.7>3.46 && q%3.7<3.62,
    mouth: action==='talk' ? .3+.7*Math.abs(Math.sin(q*11)) : 0,
    tail: Math.sin(q*4)*.12
  };
}
export function drawCharacter(ctx, {kind='fox', expression='happy', action='idle', speed=1, t=0, x=0, y=0, scale=1, tilt=0}) {
  const p=poseAt(t,action,speed);
  const fur=kind==='fox'?'#e98343':kind==='bear'?'#a97954':'#b5a1d5';
  const dark=kind==='fox'?'#ac542f':kind==='bear'?'#76513e':'#8b78ac';
  const cream=kind==='rabbit'?'#fff4ff':'#fff0d4';
  function ellipse(x,y,rx,ry,c){ctx.fillStyle=c;ctx.beginPath();ctx.ellipse(x,y,rx,ry,0,0,TAU);ctx.fill()}
  function path(points,c){ctx.fillStyle=c;ctx.beginPath();ctx.moveTo(...points[0]);points.slice(1).forEach(v=>ctx.lineTo(...v));ctx.closePath();ctx.fill()}
  function rect(x,y,w,h,r,c){ctx.fillStyle=c;ctx.beginPath();ctx.roundRect(x,y,w,h,r);ctx.fill()}
  ctx.save();ctx.translate(x,y);ctx.scale(scale,scale);
  if(tilt){ctx.translate(0,100);ctx.rotate(tilt);ctx.translate(0,-100)}  // pivot at the feet
  ellipse(0,102,80-p.jump*.3,12,'#214e4429');
  ctx.translate(0,p.bob-p.jump);
  if(kind==='fox'){
    ctx.save();ctx.rotate(p.tail);
    path([[35,32],[108,-2],[138,-69],[166,-45],[151,10],[100,58],[45,67]],fur);
    path([[138,-69],[166,-45],[151,10],[121,17],[128,-15]],cream);ctx.restore();
  } else ellipse(60,49,kind==='rabbit'?24:17,23,cream);
  for(const side of [-1,1]){
    ctx.save();ctx.translate(side*28,48);ctx.rotate(side*p.leg);
    rect(-15,0,30,52,14,dark);ellipse(0,51,26,13,cream);ctx.restore();
  }
  ellipse(0,16,70,78,fur);ellipse(0,22,42,58,cream);
  for(const side of [-1,1]){
    ctx.save();ctx.translate(side*51,-12);ctx.rotate(side===1?p.arm:.25-p.leg);
    rect(-13,0,27,69,14,fur);ellipse(0,64,17,16,cream);ctx.restore();
  }
  if(kind==='fox'){
    for(const s of [-1,1]){
      path([[s*72,-98],[s*81,-193],[s*8,-150]],dark);
      path([[s*59,-132],[s*68,-176],[s*27,-149]],'#eeb6a3');
    }
  }else if(kind==='rabbit'){
    for(const s of [-1,1]){ellipse(s*44,-192,25,82,fur);ellipse(s*44,-194,12,58,'#f3c8d9')}
  }else{
    for(const s of [-1,1]){ellipse(s*70,-163,34,34,dark);ellipse(s*70,-163,20,20,'#eabda0')}
  }
  ellipse(0,-92,92,83,fur);ellipse(-52,-59,40,31,cream);ellipse(52,-59,40,31,cream);
  ellipse(0,-48,39,25,cream);ellipse(0,-62,14,10,kind==='rabbit'?'#c77f97':'#343b44');
  for(const s of [-1,1]){
    if(p.blink)rect(s*37-17,-105,34,5,3,'#343b44');
    else{
      ellipse(s*37,-105,8,expression==='surprised'?18:13,'#343b44');
      ellipse(s*37-2,-109,2.5,3.5,'white');
    }
    ctx.strokeStyle=dark;ctx.lineWidth=4;ctx.lineCap='round';ctx.beginPath();
    const tilt=expression==='sad'?s*8:expression==='curious'?-s*8:0;
    ctx.moveTo(s*37-14,-128+tilt);ctx.lineTo(s*37+14,-128-tilt);ctx.stroke();
  }
  ctx.strokeStyle='#794740';ctx.lineWidth=4;ctx.beginPath();
  if(p.mouth || expression==='surprised')ellipse(0,-38,expression==='surprised'?11:15,8+p.mouth*10,'#794740');
  else {ctx.arc(0,expression==='sad'?-27:-51,16,expression==='sad'?Math.PI+.2:.2,expression==='sad'?TAU-.2:Math.PI-.2);ctx.stroke()}
  ellipse(-65,-77,12,6,'#f2a0a0');ellipse(65,-77,12,6,'#f2a0a0');
  ctx.restore();
}
