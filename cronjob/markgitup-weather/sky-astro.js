/* Astronomical quantities use Astronomy Engine 2.1.19 (MIT). No network. */
(function (root) {
    'use strict';
    const A = typeof module === 'object' && module.exports ? require('./astronomy.js') : root.Astronomy;
    const rad = Math.PI / 180;
    const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

    function phaseName(angle) {
        if (angle < 1 || angle > 359) return 'New moon';
        if (Math.abs(angle - 90) < 1) return 'First quarter';
        if (Math.abs(angle - 180) < 1) return 'Full moon';
        if (Math.abs(angle - 270) < 1) return 'Last quarter';
        if (angle < 90) return 'Waxing crescent';
        if (angle < 180) return 'Waxing gibbous';
        if (angle < 270) return 'Waning gibbous';
        return 'Waning crescent';
    }

    function position(body, date, observer) {
        const eq = A.Equator(body, date, observer, true, true);
        const horizon = A.Horizon(date, observer, eq.ra, eq.dec, 'normal');
        // Match SearchRiseSet's upper-limb criterion exactly, rather than
        // applying a second, different refraction model to the center.
        // Radii and 34-arcminute lift match the pinned Engine 2.1.19 source.
        const geometric = A.Horizon(date, observer, eq.ra, eq.dec);
        const radiusKm = body === A.Body.Sun ? 695700 : 1738.1;
        const limbRadius = Math.asin(radiusKm / (A.KM_PER_AU * eq.dist)) / rad;
        const lift = (34 / 60) * A.Atmosphere(observer.height).density;
        const visible = geometric.altitude + limbRadius + lift >= 0;
        const rise = visible ? A.SearchRiseSet(body, observer, 1, date, -2) : null;
        const set = visible ? A.SearchRiseSet(body, observer, -1, date, 2) : null;
        const start = rise ? rise.date.getTime() : NaN;
        const end = set ? set.date.getTime() : NaN;
        const progress = Number.isFinite(start) && end > start
            ? clamp((date.getTime() - start) / (end - start), 0, 1) : null;
        const hourAngle = (A.SiderealTime(date) * 15 + observer.longitude - eq.ra * 15) * rad;
        return {
            altitude: horizon.altitude, azimuth: horizon.azimuth, visible,
            // Circumpolar bodies have no invented rise/set; use their hour angle.
            x: progress === null ? 50 + 42 * Math.sin(hourAngle) : 8 + 84 * progress,
            y: 88 - 76 * clamp(horizon.altitude, 0, 90) / 90,
            progress, rise: rise ? rise.date.toISOString() : null,
            set: set ? set.date.toISOString() : null,
        };
    }

    function skyAt(date, latitude, longitude) {
        if (!(date instanceof Date) || !Number.isFinite(date.getTime())) throw new Error('Invalid date');
        if (!Number.isFinite(latitude) || !Number.isFinite(longitude) || Math.abs(latitude) > 90 || Math.abs(longitude) > 180) {
            throw new Error('Invalid observer');
        }
        const observer = new A.Observer(latitude, longitude, 0);
        const sun = position(A.Body.Sun, date, observer);
        const moon = position(A.Body.Moon, date, observer);
        moon.phaseAngle = A.MoonPhase(date);
        moon.phaseName = phaseName(moon.phaseAngle);
        moon.illumination = A.Illumination(A.Body.Moon, date).phase_fraction;
        // Project the Sun into the Moon's local sky tangent plane. x points
        // screen-right, y screen-down; z points from lunar surface to viewer.
        const sa = sun.altitude * rad, ma = moon.altitude * rad;
        const delta = (sun.azimuth - moon.azimuth) * rad;
        const right = Math.cos(sa) * Math.sin(delta);
        const up = Math.sin(sa) * Math.cos(ma) - Math.cos(sa) * Math.sin(ma) * Math.cos(delta);
        const length = Math.hypot(right, up);
        const z = 2 * moon.illumination - 1;
        const transverse = Math.sqrt(Math.max(0, 1 - z * z));
        moon.light = {x: length ? transverse * right / length : transverse,
            y: length ? -transverse * up / length : 0, z};
        moon.tilt = Math.atan2(right, up) / rad;
        return {sun, moon};
    }

    const api = {skyAt};
    if (typeof module === 'object' && module.exports) module.exports = api;
    else root.MarkgitupAstro = api;
})(globalThis);
