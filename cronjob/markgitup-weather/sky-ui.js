/* All data is per-document memory; a fresh visit performs a fresh lookup. */
(function () {
    'use strict';
    const scene=document.querySelector('#sky-scene');
    if(!scene)return;
    const label=document.querySelector('#weather-label');
    const detail=document.querySelector('#weather-detail');
    const themeButton=document.querySelector('#theme');
    const fallback={sky:{sun:{altitude:-30},moon:{visible:false,altitude:0,illumination:0}},weather:{kind:'unknown',cloud:0}};
    let snapshot=null,themeChoice=null,generation=0;
    const rgb=v=>`rgb(${v.join(',')})`;

    function setPalette(){
        const palette=MarkgitupPaint.paletteFor(snapshot||fallback,themeChoice);
        document.body.dataset.theme=palette.theme;
        document.documentElement.style.colorScheme=palette.theme;
        const variables={bg:palette.background,'sky-top':palette.top,'sky-horizon':palette.horizon,
            ink:palette.ink,muted:palette.muted,dim:palette.dim,surface:palette.surface,
            surface2:palette.surface2,line:palette.line,cyan:palette.cyan,lime:palette.lime,'cloud-ink':palette.cloudInk};
        for(const [name,value] of Object.entries(variables))document.body.style.setProperty(`--${name}`,rgb(value));
        document.body.style.setProperty('--rain-ink',palette.theme==='light'?'#6e8292':'#9cafc4');
        document.body.style.setProperty('--snow-ink',palette.theme==='light'?'#fff':'#d9e4f3');
        const meta=document.querySelector('meta[name="theme-color"]');
        if(meta)meta.content=rgb(palette.background);
        themeButton.textContent=palette.theme==='light'?'☾':'☼';
        themeButton.setAttribute('aria-label',`Switch to ${palette.theme==='light'?'dark':'light'} theme for this visit`);
        themeButton.title='Theme override lasts only this visit. Reload restores the local sky.';
    }

    function place(node,body){
        node.hidden=!body.visible;
        node.style.left=`${body.x.toFixed(3)}%`;
        node.style.top=`${body.y.toFixed(3)}%`;
    }

    async function drawMoon(moon,run,daylight){
        const canvas=document.querySelector('#sky-moon');
        let texture=null;
        try {
            const image=new Image();
            image.src=__MOON_TEXTURE__;
            await image.decode();
            const source=document.createElement('canvas');source.width=image.width;source.height=image.height;
            const context=source.getContext('2d',{willReadFrequently:true});
            if(context){context.drawImage(image,0,0);texture=context.getImageData(0,0,image.width,image.height);}
        } catch { /* Smooth, correctly phased disc remains if texture decoding fails. */ }
        if(run!==generation)return;
        const context=canvas.getContext('2d');
        if(!context){canvas.hidden=true;return;}
        const pixels=MarkgitupPaint.shadeMoon(canvas.width,moon.light,texture,{daylight});
        context.clearRect(0,0,canvas.width,canvas.height);
        context.putImageData(new ImageData(pixels,canvas.width,canvas.height),0,0);
    }

    function particles(){
        const host=scene.querySelector('.sky-particles');
        if(host.childElementCount)return;
        const fragment=document.createDocumentFragment();
        for(let i=0;i<28;i++){
            const drop=document.createElement('i');
            drop.style.setProperty('--drop-left',`${(i*37+9)%100}%`);
            drop.style.setProperty('--drop-top',`${(i*23)%85}%`);
            drop.style.setProperty('--drop-delay',`${-(i%13)*.71}s`);
            drop.style.setProperty('--drop-opacity',String(.25+(i%5)*.12));
            fragment.append(drop);
        }
        host.append(fragment);
    }

    async function refresh(){
        const run=++generation;
        snapshot=null;themeChoice=null;scene.hidden=true;
        document.body.dataset.skyState='loading';
        label.textContent='Finding your local sky…';
        detail.textContent='Approximate region · no GPS permission';
        setPalette();
        try{
            const next=await MarkgitupWeather.fetchSnapshot();
            if(run!==generation)return;
            snapshot=next;
            const {sky,weather}=snapshot;
            document.body.dataset.weather=weather.kind;
            setPalette();
            place(document.querySelector('#sky-sun'),sky.sun);
            const moon=document.querySelector('#sky-moon');
            place(moon,sky.moon);
            const daylight=sky.sun.altitude>-2;
            // A daytime crescent must be faint: only the lit limb reads against a bright sky.
            moon.hidden=!sky.moon.visible||sky.moon.illumination<.005||(daylight&&sky.moon.illumination<.18);
            const clouds=weather.kind==='fog'?Math.max(.75,weather.cloud):weather.cloud;
            scene.style.setProperty('--cloud-opacity',String(clouds*.78));
            scene.style.setProperty('--veil-opacity',String(.05+clouds*.2));
            scene.style.setProperty('--star-opacity',String(sky.sun.altitude<-6?(1-clouds)*.45:0));
            document.querySelector('#sky-sun').style.opacity=String(1-clouds*.9);
            moon.style.opacity=String((daylight?.34:1)*(1-clouds*.88));
            if(['rain','snow','storm'].includes(weather.kind))particles();
            const clock=new Intl.DateTimeFormat(undefined,{hour:'2-digit',minute:'2-digit',timeZone:weather.timezone}).format(new Date(snapshot.at));
            label.textContent=`${weather.label} · ${Math.round(weather.temperature)}${weather.temperatureUnit} · ${clock} local`;
            detail.textContent=`${sky.moon.phaseName} · ${(sky.moon.illumination*100).toFixed(1)}% illuminated${sky.moon.visible?'':' · below horizon'}`;
            detail.title='Calculated for your approximate IP region at this visit. Reload later to see the sky advance.';
            scene.hidden=false;
            if(!moon.hidden)await drawMoon(sky.moon,run,daylight);
            if(run===generation)document.body.dataset.skyState='ready';
        }catch{
            if(run!==generation)return;
            snapshot=null;scene.hidden=true;document.body.dataset.skyState='unavailable';
            delete document.body.dataset.weather;
            label.textContent='Local sky unavailable';
            detail.textContent='News is ready. Weather retries on your next visit.';
            setPalette();
        }
    }

    themeButton.addEventListener('click',()=>{themeChoice=document.body.dataset.theme==='light'?'dark':'light';setPalette();});
    if('IntersectionObserver' in window){
        new IntersectionObserver(entries=>{
            scene.dataset.paused=String(!entries[0].isIntersecting);
        }).observe(document.querySelector('.hero'));
    }
    window.addEventListener('pageshow',event=>{if(event.persisted)void refresh();});
    // Cards get their first animation frame before optional network work begins.
    requestAnimationFrame(()=>{void refresh();});
})();
