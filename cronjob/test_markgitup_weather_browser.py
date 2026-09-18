#!/usr/bin/env python3
"""Weather hero integration tests: synthetic API fixtures, real Chromium."""
import json
import time
import unittest

try:
    from .test_markgitup_index_browser import BrowserHarness
except ImportError:
    from test_markgitup_index_browser import BrowserHarness


def weather_setup(instant='2024-06-21T12:00:00Z', code=0, cloud=0, latitude='51.5', longitude='0', country_code='GB', temperature=18, temperature_unit='°C', failure=False):
    return f"""
window.RealDate = Date;
window.Date = class extends RealDate {{
    constructor(...args) {{ super(...(args.length ? args : [{json.dumps(instant)}])); }}
    static now() {{ return new RealDate({json.dumps(instant)}).getTime(); }}
}};
window.skyRequests=[];
Object.defineProperty(window,'localStorage',{{get(){{throw new Error('Storage forbidden')}}}});
Object.defineProperty(window,'sessionStorage',{{get(){{throw new Error('Storage forbidden')}}}});
navigator.geolocation.getCurrentPosition=()=>{{throw new Error('GPS forbidden')}};
window.fetch=async(url,options)=>{{
    skyRequests.push({{url,credentials:options.credentials,cache:options.cache,referrerPolicy:options.referrerPolicy}});
    if ({str(failure).lower()}) throw new Error('Provider offline');
    return {{ok:true,json:async()=>url.includes('geojs')
        ? {{latitude:{json.dumps(latitude)},longitude:{json.dumps(longitude)},country_code:{json.dumps(country_code)},ip:'203.0.113.1',city:'NOT FOR DISPLAY'}}
        : {{timezone:'Europe/London',current_units:{{temperature_2m:{json.dumps(temperature_unit)}}},current:{{time:Date.now()/1000-300,
            temperature_2m:{json.dumps(temperature)},weather_code:{code},cloud_cover:{cloud},precipitation:0,is_day:1}}}}}};
}};
"""


class WeatherBrowserTests(BrowserHarness):
    def wait_sky(self, state='ready'):
        deadline=time.monotonic()+10
        while self.evaluate('document.body.dataset.skyState') != state:
            if time.monotonic()>deadline:
                self.fail(f'Sky never reached {state}')
            time.sleep(.05)
        self.settle()
        self.assertEqual([], self.evaluate('testErrors'))

    def test_sunny_hero_sets_light_theme_without_storage_or_permission(self):
        self.load(setup=weather_setup())
        self.assertEqual('ready', self.evaluate('document.body.dataset.skyState'), 'weather hero is missing')
        self.assertEqual('light',self.evaluate('document.body.dataset.theme'))
        self.assertFalse(self.evaluate("document.querySelector('#sky-sun').hidden"))
        self.assertTrue(self.evaluate("document.querySelector('.hero').contains(document.querySelector('#sky-scene'))"))
        self.assertEqual(2,self.evaluate('skyRequests.length'))
        self.assertIn('Clear sky',self.evaluate("document.querySelector('#weather-label').textContent"))
        self.assertFalse(self.evaluate("document.body.innerText.includes('NOT FOR DISPLAY')"))
        self.assertLess(self.metrics()['count'],30)

    def test_us_ip_region_displays_fahrenheit_temperature(self):
        self.load(setup=weather_setup(
            latitude='37.8', longitude='-122.4', country_code='US', temperature=54,
            temperature_unit='°F',
        ))
        self.wait_sky()
        self.assertEqual(
            'fahrenheit',
            self.evaluate("new URL(skyRequests[1].url).searchParams.get('temperature_unit')"),
        )
        self.assertIn('54°F',self.evaluate("document.querySelector('#weather-label').textContent"))
        self.assertFalse(self.evaluate("document.body.innerText.includes('US')"))

    def test_night_moon_has_texture_correct_phase_and_real_hourly_travel(self):
        self.load(setup=weather_setup(instant='2024-04-23T22:00:00Z'))
        self.wait_sky()
        self.assertEqual('dark',self.evaluate('document.body.dataset.theme'))
        self.assertFalse(self.evaluate("document.querySelector('#sky-moon').hidden"))
        self.assertTrue(self.evaluate("document.querySelector('#sky-sun').hidden"))
        self.assertRegex(self.evaluate("document.querySelector('#weather-detail').textContent"),r'(?:99\.\d|100\.0)% illuminated')
        first=self.evaluate("parseFloat(document.querySelector('#sky-moon').style.left)")
        self.assertTrue(self.evaluate("(() => {const c=document.querySelector('#sky-moon');const p=c.getContext('2d').getImageData(0,0,160,160).data;return p.some(v=>v>150)})()"))
        self.load(setup=weather_setup(instant='2024-04-24T02:00:00Z'))
        self.wait_sky()
        self.assertGreater(self.evaluate("parseFloat(document.querySelector('#sky-moon').style.left)"),first)

    def test_daytime_moon_is_not_an_opaque_grey_disc(self):
        # Gibbous daytime moon: visible but only its lit limb, never a solid grey ball.
        self.load(setup=weather_setup(instant='2024-04-01T00:00:00Z', latitude='-33.9', longitude='151.2'))
        self.wait_sky()
        self.assertEqual('light', self.evaluate('document.body.dataset.theme'))
        self.assertFalse(self.evaluate("document.querySelector('#sky-moon').hidden"))
        self.assertLess(float(self.evaluate("getComputedStyle(document.querySelector('#sky-moon')).opacity")), .4)
        shadow = self.evaluate("""(() => {
            const c=document.querySelector('#sky-moon');
            const d=c.getContext('2d').getImageData(0,0,c.width,c.height).data;
            let opaque=0, inside=0;
            for(let y=0;y<c.height;y++)for(let x=0;x<c.width;x++){
                const nx=(x+.5)*2/c.width-1, ny=(y+.5)*2/c.height-1;
                if(nx*nx+ny*ny>=.81) continue;
                inside++; if(d[(y*c.width+x)*4+3]>200) opaque++;
            }
            return opaque/inside;})()""")
        self.assertLess(shadow, .95, 'daytime moon must not be a fully opaque disc')
        self.assertGreater(shadow, .02, 'daytime moon must still show its lit limb')

    def test_thin_daytime_crescent_is_omitted_rather_than_faked(self):
        self.load(setup=weather_setup(instant='2024-04-10T13:00:00Z'))
        self.wait_sky()
        self.assertEqual('light', self.evaluate('document.body.dataset.theme'))
        self.assertTrue(self.evaluate("document.querySelector('#sky-moon').hidden"))

    def test_new_moon_night_is_dark_without_a_fabricated_visible_moon(self):
        self.load(setup=weather_setup(instant='2024-04-08T23:30:00Z'))
        self.wait_sky()
        self.assertEqual('dark',self.evaluate('document.body.dataset.theme'))
        self.assertTrue(self.evaluate("document.querySelector('#sky-moon').hidden"))
        background=self.evaluate("getComputedStyle(document.body).getPropertyValue('--bg')")
        self.assertEqual('rgb(2,3,5)',background.strip())

    def test_weather_effects_are_inside_hero_and_reduced_motion_stops_them(self):
        for code,kind in [(3,'clouds'),(45,'fog'),(63,'rain'),(73,'snow'),(95,'storm')]:
            with self.subTest(kind=kind):
                self.load(setup=weather_setup(code=code,cloud=90))
                self.wait_sky()
                self.assertEqual(kind,self.evaluate('document.body.dataset.weather'))
                self.assertTrue(self.evaluate("[...document.querySelectorAll('.sky-particles,.sky-clouds,.sky-orbit')].every(n=>!!n.closest('.hero'))"))
                if kind in ['rain','snow','storm']:
                    self.assertEqual(28,self.evaluate("document.querySelectorAll('.sky-particles i').length"))
                    self.cdp('Emulation.setEmulatedMedia',features=[dict(name='prefers-reduced-motion',value='reduce')])
                    self.assertEqual('none',self.evaluate("getComputedStyle(document.querySelector('.sky-particles i')).animationName"))
                    self.cdp('Emulation.setEmulatedMedia',features=[])
                    self.evaluate('window.scrollTo(0,document.body.scrollHeight)')
                    self.settle()
                    self.assertEqual('true',self.evaluate("document.querySelector('#sky-scene').dataset.paused"))

    def test_provider_failure_keeps_cards_theme_control_and_search_working(self):
        self.load(setup=weather_setup(failure=True))
        self.wait_sky('unavailable')
        self.assertTrue(self.evaluate("document.querySelector('#sky-scene').hidden"))
        self.assertIn('unavailable',self.evaluate("document.querySelector('#weather-label').textContent"))
        self.assertEqual(1,self.evaluate('skyRequests.length'))
        self.search('archive-marker-0001')
        self.assertEqual(['html/article-0001.html'],self.metrics()['links'])
        self.evaluate("document.querySelector('#theme').click()")
        self.assertEqual('light',self.evaluate('document.body.dataset.theme'))

    def test_bfcache_return_refreshes_without_reusing_a_manual_theme(self):
        self.load(setup=weather_setup())
        self.wait_sky()
        self.evaluate("document.querySelector('#theme').click()")
        self.assertEqual('dark',self.evaluate('document.body.dataset.theme'))
        self.evaluate("window.dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true}))")
        self.wait_sky()
        self.assertEqual(4,self.evaluate('skyRequests.length'))
        self.assertEqual('light',self.evaluate('document.body.dataset.theme'))
        self.assertTrue(self.evaluate("skyRequests.every(r=>r.credentials==='omit'&&r.cache==='no-store'&&r.referrerPolicy==='no-referrer')"))

    def test_mobile_sky_does_not_overflow_or_expand_card_window(self):
        self.load(width=390,height=844,setup=weather_setup(code=73,cloud=90))
        self.wait_sky()
        self.assertLessEqual(self.evaluate('document.documentElement.scrollWidth'),390)
        self.assertLess(self.metrics()['count'],10)
        self.assertGreater(self.evaluate("document.querySelector('#theme').getBoundingClientRect().height"),43)


if __name__=='__main__':
    unittest.main()
