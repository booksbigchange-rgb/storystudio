// StoryStudio original lightweight film-direction helpers.
// Inspired by code-driven filmmaking workflows, not copied Lemo demo footage.
import {clamp,ss,TAU,hash} from '../vendor/lemo-lib.js';
export const CAMERAS=['still','push-in','pull-back','pan-left','pan-right'];
export function cameraAt(scene,t,W,H){
  const name=scene.camera||'still';
  const u=ss(clamp(t/Math.max(scene.duration,.001),0,1));
  if(name==='still')return {zoom:1,x:0,y:0,progress:u};
  const travel=Math.min(W*.035,44);
  // Zoom overscan hides exposed borders on small screens and 9:16 exports.
  if(name==='push-in')return {zoom:1+u*.14,x:-travel*u*.24,y:-H*.008*u,progress:u};
  if(name==='pull-back')return {zoom:1.14-u*.14,x:travel*u*.24,y:H*.008*u,progress:u};
  if(name==='pan-left')return {zoom:1.10,x:travel*(1-2*u),y:-H*.008*u,progress:u};
  if(name==='pan-right')return {zoom:1.10,x:travel*(2*u-1),y:H*.008*u,progress:u};
  return {zoom:1,x:0,y:0,progress:u};
}
export function applyCamera(ctx,pose,W,H){
  ctx.translate(W/2,H/2);
  ctx.scale(pose.zoom,pose.zoom);
  ctx.translate(-W/2+pose.x,-H/2+pose.y);
}
export function drawAtmosphere(ctx,scene,t,W,H){
  if(!scene.camera || scene.camera==='still')return;
  // Gentle, deterministic foreground particles. No images, shaders or GPU work.
  // The seed changes between scenes but never between repeated renders at t.
  const night=scene.background==='night';
  for(let i=0;i<22;i++){
    const seed=i*6.7+(night?41:7);
    const x=((hash(seed+2)*W+t*(7+hash(seed)*17))%(W+40))-20;
    const y=((hash(seed+19)*H-t*(5+hash(seed+11)*9))%(H+40)+H+40)%(H+40)-20;
    const r=1.5+hash(seed+3)*3.5;
    ctx.globalAlpha=.25+.24*(.5+.5*Math.sin(t*1.7+i));
    ctx.fillStyle=night?'#fef2a6':'#fff8cc';
    ctx.beginPath();ctx.arc(x,y,r,0,TAU);ctx.fill();
  }
  ctx.globalAlpha=1;
}
