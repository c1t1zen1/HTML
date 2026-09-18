/* Color and lunar-disc rendering: deterministic, bounded, and GPU-independent. */
(function(root){
    'use strict';
    const clamp=(v,a,b)=>Math.min(b,Math.max(a,v));
    const mix=(a,b,t)=>a.map((v,i)=>Math.round(v+(b[i]-v)*clamp(t,0,1)));
    function paletteFor(snapshot,override=null){
        const {sky,weather}=snapshot;
        const alt=sky.sun.altitude,cloud=weather.cloud;
        const theme=override || (alt>=-4?'light':'dark');
        if(theme==='light'){
            const sunshine=clamp((alt+4)/30,0,1)*(1-cloud*.8);
            return {theme,background:mix([236,240,243],[252,253,254],sunshine),
                top:mix([173,189,201],[216,237,250],sunshine),
                horizon:mix([234,223,208],[255,253,247],clamp(alt/15,0,1)),
                ink:[22,38,54],muted:[60,78,94],dim:[75,94,111],
                surface:[255,255,255],surface2:[247,249,251],line:[196,209,221],
                cyan:[6,102,122],lime:[76,100,29],cloudInk:[249,252,255]};
        }
        const moonlight=sky.moon.visible?Math.pow(sky.moon.illumination,2)*clamp(sky.moon.altitude/45,0,1)*(1-cloud*.85):0;
        const twilight=clamp((alt+18)/14,0,1);
        return {theme,background:mix([2,3,5],[13,19,29],Math.max(moonlight*.8,twilight*.6)),
            top:mix(mix([3,6,12],[19,32,51],moonlight),[41,53,78],twilight),
            horizon:mix(mix([5,8,13],[27,38,54],moonlight),[71,57,66],twilight),
            ink:[237,242,249],muted:[182,194,209],dim:[153,171,192],
            surface:[12,18,27],surface2:[17,25,36],line:[44,59,78],
            cyan:[119,213,218],lime:[187,215,149],cloudInk:[95,112,132]};
    }
    function shadeMoon(size,light,texture=null,options={}){
        // In daylight the unlit hemisphere is invisible against a bright sky,
        // so its alpha follows illumination instead of painting a grey sphere.
        const daylight=!!options.daylight;
        const pixels=new Uint8ClampedArray(size*size*4);
        for(let y=0;y<size;y++) for(let x=0;x<size;x++){
            const nx=(x+.5)*2/size-1,ny=(y+.5)*2/size-1,r2=nx*nx+ny*ny;
            if(r2>=1)continue;
            const nz=Math.sqrt(1-r2),dot=nx*light.x+ny*light.y+nz*light.z;
            const exposure=dot>0?.25+.75*Math.pow(dot,.45):.014;
            let rgb=[210,213,218];
            if(texture){
                const u=clamp(Math.floor((.5+Math.atan2(nx,nz)/(2*Math.PI))*texture.width),0,texture.width-1);
                const v=clamp(Math.floor((.5+Math.asin(ny)/Math.PI)*texture.height),0,texture.height-1);
                const source=(v*texture.width+u)*4;
                rgb=[0,1,2].map(c=>Math.min(255,texture.data[source+c]*1.5));
            }
            const target=(y*size+x)*4;
            for(let c=0;c<3;c++)pixels[target+c]=rgb[c]*exposure;
            const edge=clamp((1-r2)*size/2,0,1);
            pixels[target+3]=255*edge*(daylight?clamp((dot-.12)/.18,0,1):1);
        }
        return pixels;
    }
    const api={paletteFor,shadeMoon};
    if(typeof module==='object'&&module.exports)module.exports=api;
    else root.MarkgitupPaint=api;
})(globalThis);
