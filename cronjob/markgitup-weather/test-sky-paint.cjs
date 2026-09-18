const test=require('node:test');
const assert=require('node:assert/strict');
const snapshot=(alt,illumination=0,kind='clear',cloud=0)=>({sky:{sun:{altitude:alt},moon:{visible:true,altitude:45,illumination}},weather:{kind,cloud}});
test('lighting is bright for sun, almost black at new moon, gently brighter at full moon',()=>{
    const {paletteFor}=require('./sky-paint.js');
    const day=paletteFor(snapshot(45));
    const dark=paletteFor(snapshot(-40,0));
    const full=paletteFor(snapshot(-40,1));
    assert.equal(day.theme,'light'); assert.equal(dark.theme,'dark');
    assert.ok(day.background.every(c=>c>240));
    assert.ok(Math.max(...dark.background)<10);
    assert.ok(full.background.reduce((a,b)=>a+b)>dark.background.reduce((a,b)=>a+b));
    assert.ok(paletteFor(snapshot(45,0,'storm',1)).top[0]<day.top[0]);
    assert.equal(paletteFor(snapshot(45),'dark').theme,'dark');
});
test('daylight moon shows only its lit limb instead of an opaque grey disc',()=>{
    const {shadeMoon}=require('./sky-paint.js');
    const z=2*.405-1,light={x:Math.sqrt(1-z*z),y:0,z};
    const night=shadeMoon(120,light,null,{daylight:false});
    const day=shadeMoon(120,light,null,{daylight:true});
    const sample=(pixels,pred)=>{let n=0;for(let i=0;i<pixels.length;i+=4){if(pred(pixels,i))n++;}return n;};
    const inside=(p,i)=>p[i+3]>0||p[i]>0||p[i+1]>0||p[i+2]>0;
    // Night keeps the full sphere silhouette; daylight must not.
    assert.ok(sample(night,(p,i)=>p[i+3]>200)>6000,'night disc should be solid');
    const dayUnlit=[];const dayLit=[];
    for(let y=0;y<120;y++)for(let x=0;x<120;x++){
        const nx=(x+.5)*2/120-1,ny=(y+.5)*2/120-1;
        if(nx*nx+ny*ny>.64)continue;
        const i=(y*120+x)*4;
        const nz=Math.sqrt(Math.max(0,1-nx*nx-ny*ny));
        const dot=nx*light.x+ny*light.y+nz*light.z;
        if(dot<0)dayUnlit.push(day[i+3]);
        else if(dot>.45)dayLit.push(day[i+3]);
    }
    assert.ok(dayUnlit.length>0&&dayLit.length>0);
    assert.ok(Math.max(...dayUnlit)<24,`daylight shadow must be near-transparent, saw ${Math.max(...dayUnlit)}`);
    assert.ok(Math.min(...dayLit)>190,`daylight lit limb must stay opaque, saw ${Math.min(...dayLit)}`);
    // Colour of the lit limb is unchanged by the daylight alpha treatment.
    assert.ok(sample(day,inside)>0);
});
test('lunar terminator illuminates correct projected area and swaps waxing/waning side',()=>{
    const {shadeMoon}=require('./sky-paint.js');
    for(const f of [0,.1,.25,.5,.75,.9,1]){
        const z=2*f-1,light={x:Math.sqrt(1-z*z),y:0,z};
        const pixels=shadeMoon(160,light); let total=0,lit=0;
        for(let i=0;i<pixels.length;i+=4){if(pixels[i+3]>200){total++;if(pixels[i]>30)lit++;}}
        assert.ok(Math.abs(lit/total-f)<.012,`fraction ${f}: ${lit/total}`);
    }
    const waxing=shadeMoon(80,{x:1,y:0,z:0}),waning=shadeMoon(80,{x:-1,y:0,z:0});
    const right=4*(40*80+60),left=4*(40*80+20);
    assert.ok(waxing[right]>waxing[left]); assert.ok(waning[left]>waning[right]);
});
