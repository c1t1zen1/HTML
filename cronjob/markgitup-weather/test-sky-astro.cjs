const test = require('node:test');
const assert = require('node:assert/strict');

const at = (date, lat=51.5, lon=0) => require('./sky-astro.js').skyAt(new Date(date), lat, lon);
test('rise/set boundaries use the same event definition as the displayed arc',()=>{
    const A=require('./astronomy.js');
    const observer=new A.Observer(51.5,0,0);
    for(const [body,key] of [[A.Body.Sun,'sun'],[A.Body.Moon,'moon']]){
        const rise=A.SearchRiseSet(body,observer,1,new Date('2024-04-15T00:00:00Z'),2).date;
        const set=A.SearchRiseSet(body,observer,-1,new Date(rise.getTime()+1000),2).date;
        const beforeRise=at(new Date(rise.getTime()-1000))[key];
        const afterRise=at(new Date(rise.getTime()+1000))[key];
        const beforeSet=at(new Date(set.getTime()-1000))[key];
        const afterSet=at(new Date(set.getTime()+1000))[key];
        assert.equal(beforeRise.visible,false,`${key} before rise`);
        assert.equal(afterRise.visible,true,`${key} after rise`);
        assert.ok(afterRise.x<8.1,`${key} must emerge on left, not yesterday's arc`);
        assert.equal(beforeSet.visible,true,`${key} before set`);
        assert.ok(beforeSet.x>91.9,`${key} must reach right horizon`);
        assert.equal(afterSet.visible,false,`${key} must not select tomorrow's set while still visible`);
    }
});
test('reviewed sunset and moonset regressions cannot jump to next-day midpoint',()=>{
    assert.equal(at('2024-04-15T18:57:27.152Z').sun.visible,false);
    assert.equal(at('2024-04-16T02:59:04.754Z').moon.visible,false);
});
test('moon traverses its real rise/set interval from left to right across midnight', () => {
    const early = at('2024-04-23T22:00:00Z').moon;
    const later = at('2024-04-24T02:00:00Z').moon;
    assert.equal(early.visible, true);
    assert.equal(later.visible, true);
    assert.ok(later.x > early.x);
    // Root searches converge numerically; equality is within one second,
    // not bit-identical milliseconds when started at different instants.
    assert.ok(Math.abs(new Date(early.rise)-new Date(later.rise)) < 1000);
    assert.ok(Math.abs(new Date(early.set)-new Date(later.set)) < 1000);
    assert.ok(new Date(early.rise) < new Date('2024-04-23T22:00:00Z'));
    assert.ok(new Date(early.set) > new Date('2024-04-24T02:00:00Z'));
    assert.ok(Math.abs(later.progress - early.progress - 14400000 / (new Date(early.set)-new Date(early.rise))) < 1e-5);
});
test('sun and moon obey horizon, with finite polar fallbacks and UTC instants', () => {
    const day = at('2024-06-21T12:00:00Z');
    const night = at('2024-06-21T00:00:00Z');
    assert.equal(day.sun.visible, true);
    assert.equal(night.sun.visible, false);
    assert.equal(at('2024-04-23T12:00:00Z').moon.visible, false);
    assert.deepEqual(at('2024-04-24T02:00:00Z'), at('2024-04-23T19:00:00-07:00'));
    for (const lat of [89, -89]) {
        for (const date of ['2024-06-21T12:00:00Z', '2024-12-21T12:00:00Z']) {
            const sky = at(date,lat);
            for (const body of [sky.sun,sky.moon]) {
                assert.ok(Number.isFinite(body.x) && Number.isFinite(body.y));
                assert.ok(body.x>=8 && body.x<=92 && body.y>=12 && body.y<=88);
                if (body.rise === null || body.set === null) assert.equal(body.progress,null);
            }
        }
    }
});
test('phase names distinguish waxing and waning, light vector has correct illumination', () => {
    assert.equal(at('2024-04-12T12:00:00Z').moon.phaseName,'Waxing crescent');
    assert.equal(at('2024-04-28T12:00:00Z').moon.phaseName,'Waning gibbous');
    for (const lat of [51.5,-33.9,0]) {
        const moon=at('2024-04-15T19:13:00Z',lat).moon;
        assert.ok(Math.abs(Math.hypot(moon.light.x,moon.light.y,moon.light.z)-1)<1e-9);
        assert.ok(Math.abs(moon.light.z-(2*moon.illumination-1))<1e-9);
    }
});
test('invalid observer values fail closed rather than place a fake sky', () => {
    for (const args of [[new Date('invalid'),0,0],[new Date(),NaN,0],[new Date(),91,0],[new Date(),0,181],[new Date(),'51',0]]) {
        assert.throws(()=>require('./sky-astro.js').skyAt(...args),/observer|date/i);
    }
});

// Independent phase fixtures: US Naval Observatory phase API, April 2024.
// https://aa.usno.navy.mil/api/moon/phases/date?date=2024-04-01&nump=8
test('lunar illumination follows published new/full/quarter instants', () => {
    const {skyAt} = require('./sky-astro.js');
    const newMoon = skyAt(new Date('2024-04-08T18:21:00Z'), 51.5, 0).moon;
    const fullMoon = skyAt(new Date('2024-04-23T23:49:00Z'), 51.5, 0).moon;
    const quarter = skyAt(new Date('2024-04-15T19:13:00Z'), 51.5, 0).moon;
    assert.ok(newMoon.illumination < 0.001);
    assert.ok(fullMoon.illumination > 0.999);
    assert.ok(Math.abs(quarter.illumination - 0.5) < 0.01);
    assert.equal(newMoon.phaseName, 'New moon');
    assert.equal(fullMoon.phaseName, 'Full moon');
    assert.equal(quarter.phaseName, 'First quarter');
});
