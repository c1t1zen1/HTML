const test = require('node:test');
const assert = require('node:assert/strict');
const now = new Date('2024-04-23T23:49:00Z');
const forecast = (code=0, cloud=0) => ({timezone:'Europe/London', current_units:{temperature_2m:'°C'}, current:{time:now.getTime()/1000-300,temperature_2m:12,weather_code:code,cloud_cover:cloud,precipitation:0,is_day:0}});

test('WMO precipitation and obscuration codes map without pretending unknown weather is clear',()=>{
    const W=require('./sky-weather.js');
    for(const [code,kind] of [[0,'clear'],[2,'clouds'],[3,'clouds'],[45,'fog'],[48,'fog'],[55,'rain'],[67,'rain'],[82,'rain'],[71,'snow'],[77,'snow'],[86,'snow'],[95,'storm'],[99,'storm']]){
        assert.equal(W.weatherFrom(forecast(code,80),now).kind,kind);
    }
    for(const code of [999,null,'0'])assert.throws(()=>W.weatherFrom(forecast(code),now));
});
test('missing, stale, future, and malformed weather fails closed',()=>{
    const W=require('./sky-weather.js');
    for(const [key,value] of [['time',null],['time',now.getTime()/1000-7200],['time',now.getTime()/1000+7200],['cloud_cover',101],['temperature_2m',null],['precipitation',-1],['is_day',2]]){
        const bad=forecast();bad.current[key]=value;assert.throws(()=>W.weatherFrom(bad,now));
    }
    const bad=forecast();bad.timezone='not/a-zone';assert.throws(()=>W.weatherFrom(bad,now));
    assert.throws(()=>W.weatherFrom({},now));
});
test('coordinates accept zero but reject absent/out-of-range data before forecast',async()=>{
    const W=require('./sky-weather.js');
    assert.deepEqual(W.locationFrom({latitude:'0',longitude:0}),{latitude:0,longitude:0});
    for(const v of ['',null,undefined,true,91,'bogus'])assert.throws(()=>W.locationFrom({latitude:v,longitude:0}));
    let calls=0;await assert.rejects(W.fetchSnapshot({now,fetchImpl:async()=>{calls++;return {ok:true,json:async()=>({latitude:null,longitude:0})}}}));
    assert.equal(calls,1);
});
test('network denial and hanging JSON have bounded failure and abort',async()=>{
    const W=require('./sky-weather.js');let signal;
    await assert.rejects(W.fetchSnapshot({now,timeoutMs:20,fetchImpl:async(_,options)=>{signal=options.signal;return {ok:true,json:()=>new Promise(()=>{})}}}),/timed out/);
    assert.equal(signal.aborted,true);
    await assert.rejects(W.fetchSnapshot({now,fetchImpl:async()=>({ok:false})}),/unavailable/);
});
test('each visit performs fresh lookups rather than reusing visitor data',async()=>{
    const W=require('./sky-weather.js');let calls=0;
    const fetchImpl=async()=>{calls++;return {ok:true,json:async()=>calls%2?{latitude:0,longitude:0}:forecast()}};
    await W.fetchSnapshot({now,fetchImpl});await W.fetchSnapshot({now,fetchImpl});assert.equal(calls,4);
});

test('visitor snapshot uses coarse coordinates, private fetch options, no returned identifiers', async () => {
    const W = require('./sky-weather.js');
    const calls=[];
    const fetchImpl=async (url,options) => {
        calls.push({url,options});
        return {ok:true,json:async()=> calls.length===1 ? {latitude:'51.5123',longitude:'-0.1256',ip:'203.0.113.1',city:'DO NOT STORE'} : forecast()};
    };
    const result=await W.fetchSnapshot({fetchImpl,now});
    assert.equal(calls.length,2);
    assert.equal(calls[0].url,'https://get.geojs.io/v1/ip/geo.json');
    const url=new URL(calls[1].url);
    assert.equal(url.hostname,'api.open-meteo.com');
    assert.equal(url.searchParams.get('latitude'),'51.5');
    assert.equal(url.searchParams.get('longitude'),'-0.1');
    for (const {options} of calls) {
        assert.equal(options.credentials,'omit'); assert.equal(options.cache,'no-store');
        assert.equal(options.referrerPolicy,'no-referrer'); assert.equal(options.mode,'cors');
    }
    assert.equal(result.weather.kind,'clear');
    assert.ok(result.sky.moon.illumination>.999);
    assert.ok(!JSON.stringify(result).includes('203.0.113.1'));
    assert.ok(!JSON.stringify(result).includes('DO NOT STORE'));
    assert.equal('latitude' in result,false);
});
