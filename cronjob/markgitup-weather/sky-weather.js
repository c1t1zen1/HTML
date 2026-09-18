/* Per-visit weather. No storage, identifiers, cookies, analytics, or GPS API. */
(function (root) {
    'use strict';
    const Astro = typeof module === 'object' && module.exports ? require('./sky-astro.js') : root.MarkgitupAstro;
    const groups = [
        [[0,1], 'clear', 'Clear sky'], [[2], 'clouds', 'Partly cloudy'], [[3], 'clouds', 'Overcast'],
        [[45,48], 'fog', 'Fog'], [[51,53,55,56,57], 'rain', 'Drizzle'],
        [[61,63,65,66,67,80,81,82], 'rain', 'Rain'],
        [[71,73,75,77,85,86], 'snow', 'Snow'], [[95,96,99], 'storm', 'Thunderstorms'],
    ];
    const codes = new Map(groups.flatMap(([values,kind,label]) => values.map(value => [value,{kind,label}])));
    const temperatureUnitSymbols = Object.freeze({celsius:'°C',fahrenheit:'°F'});
    const clamp = (x,a,b) => Math.max(a,Math.min(b,x));

    function temperatureUnitForGeoIP(data) {
        return typeof data?.country_code === 'string' && data.country_code.toUpperCase() === 'US'
            ? 'fahrenheit' : 'celsius';
    }

    function locationFrom(data) {
        function coordinate(value, limit) {
            if (!(typeof value === 'number' || (typeof value === 'string' && value.trim() !== ''))) throw new Error('Location unavailable');
            const number = Number(value);
            if (!Number.isFinite(number) || Math.abs(number)>limit) throw new Error('Location unavailable');
            return Math.round(number*10)/10;
        }
        return {latitude:coordinate(data?.latitude,90),longitude:coordinate(data?.longitude,180)};
    }

    function weatherFrom(data, now, temperatureUnit='celsius') {
        const temperatureSymbol = temperatureUnitSymbols[temperatureUnit];
        if (!temperatureSymbol) throw new Error('Unexpected weather units');
        const current = data?.current;
        const description = codes.get(current?.weather_code);
        const celsius = temperatureSymbol === '°F'
            ? (current?.temperature_2m - 32) * 5 / 9 : current?.temperature_2m;
        if (!description || !Number.isFinite(current.time) || !Number.isFinite(current.cloud_cover)
            || current.cloud_cover < 0 || current.cloud_cover > 100 || !Number.isFinite(current.temperature_2m)
            || !Number.isFinite(celsius) || celsius < -100 || celsius > 70
            || !Number.isFinite(current.precipitation) || current.precipitation < 0
            || ![0,1].includes(current.is_day)) throw new Error('Weather unavailable');
        const age = now.getTime() - current.time*1000;
        if (age > 90*60*1000 || age < -20*60*1000) throw new Error('Weather data is stale');
        if (data.current_units?.temperature_2m !== temperatureSymbol) throw new Error('Unexpected weather units');
        if (typeof data.timezone !== 'string') throw new Error('Timezone unavailable');
        new Intl.DateTimeFormat('en',{timeZone:data.timezone}).format(now);
        return {...description,code:current.weather_code,cloud:current.cloud_cover/100,
            temperature:current.temperature_2m,temperatureUnit:temperatureSymbol,precipitation:current.precipitation,
            observedAt:new Date(current.time*1000).toISOString(),timezone:data.timezone};
    }

    async function fetchJSON(url, fetchImpl, timeoutMs) {
        const controller = new AbortController();
        let timer;
        try {
            return await Promise.race([
                (async () => {
                    const response = await fetchImpl(url,{signal:controller.signal,mode:'cors',
                        credentials:'omit',cache:'no-store',referrerPolicy:'no-referrer'});
                    if (!response.ok) throw new Error('Sky service unavailable');
                    return await response.json();
                })(),
                new Promise((_,reject) => {timer=setTimeout(() => {
                    controller.abort(); reject(new Error('Sky request timed out'));
                },timeoutMs);}),
            ]);
        } finally { clearTimeout(timer); }
    }

    async function fetchSnapshot({fetchImpl=root.fetch.bind(root),now=new Date(),timeoutMs=4000}={}) {
        const geoIP = await fetchJSON('https://get.geojs.io/v1/ip/geo.json',fetchImpl,timeoutMs);
        const location = locationFrom(geoIP);
        const temperatureUnit = temperatureUnitForGeoIP(geoIP);
        const query = new URLSearchParams({...location,temperature_unit:temperatureUnit,
            current:'temperature_2m,weather_code,cloud_cover,precipitation,is_day',
            timezone:'auto',timeformat:'unixtime',forecast_days:'1'});
        const weather = weatherFrom(await fetchJSON(`https://api.open-meteo.com/v1/forecast?${query}`,fetchImpl,timeoutMs),now,temperatureUnit);
        // Coordinates and provider GeoIP payload are not returned or retained.
        return {weather,sky:Astro.skyAt(now,location.latitude,location.longitude),at:now.toISOString()};
    }

    const api = {locationFrom,weatherFrom,fetchSnapshot};
    if (typeof module === 'object' && module.exports) module.exports = api;
    else root.MarkgitupWeather = api;
})(globalThis);
