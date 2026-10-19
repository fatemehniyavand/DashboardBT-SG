"""Presentation-only Ocean Edition. Research artifacts and V1 defaults stay intact."""
from __future__ import annotations
import base64
import colorsys
from pathlib import Path
import re
import streamlit as st

ASSETS=Path(__file__).with_name('assets')
CYAN='#2DBBEA'
VIOLET='#BB80F5'
PALETTE=[CYAN,VIOLET,'#8488EF','#8AE1FF','#D6ABFF','#FF93BE']

def logo_svg():
    name='tick_wave_logo_animated.svg' if st.session_state.get('_tick_wave_surge') else 'tick_wave_logo.svg'
    return (ASSETS/name).read_text()

def logo_uri():
    return 'data:image/svg+xml;base64,'+base64.b64encode(logo_svg().encode()).decode()

def _palette(match):
    value=match.group()[1:]
    rgb=tuple(int(value[i:i+2],16)/255 for i in (0,2,4))
    hue,sat,light=colorsys.rgb_to_hsv(*rgb)
    if 70/360 <= hue <= 180/360 and sat>.13:
        hue=195/360
    elif 25/360 <= hue <70/360 and sat>.13:
        hue=274/360
    elif max(rgb)<.28 and sat>.15:
        hue=228/360;sat=min(sat,.42)
    out=colorsys.hsv_to_rgb(hue,sat,light)
    return '#'+''.join(f'{round(v*255):02x}' for v in out)+value[6:]

def ocean_markup(markup,mode='wall'):
    # Transform presentation colors before artifact JSON is interpolated.
    markup=re.sub(r'#[0-9a-fA-F]{8}\b|#[0-9a-fA-F]{6}\b',_palette,markup)
    markup=markup.replace('● GREEN: recorded activation / revealed state','● CYAN: recorded activation / revealed state').replace('Gold = actual selected host','Violet = actual selected host').replace('Gold = selected host','Violet = selected host').replace('Selected compute sites stay gold.','Selected compute sites stay violet.').replace('Gold = selected host · blue = unused compute site','Violet = selected host · slate = unused site')
    markup=markup.replace('<div class="logo"><span>∿</span> tick wave</div>',f'<div class="logo ocean-brand"><img src="{logo_uri()}" alt="tick wave logo"><span>tick <b>wave</b><small>OCEAN EDITION · V2</small></span></div>')
    markup=markup.replace('<div class="brand"><span class="wave">∿</span>tick wave</div>',f'<div class="brand"><img src="{logo_uri()}" alt="tick wave" style="width:150px;height:45px;object-fit:contain"></div>')
    if mode=='wall':
        for old,new in {
            'The living behavior tree':'The ripple · Behavior tree',
            'Trace → service graph':'The current · Service graph',
            'Edge–cloud placement & routing':'The tide · Edge–cloud routing',
            'Deployment decision studio':'The harbor · Deployment studio',
            'Kafka → knowledge graph':'The stream · Kafka → Neo4j',
        }.items():
            markup=markup.replace(old,new)
    css=(Path(__file__).with_name('ocean_wall.css')).read_text()
    markup=markup.replace('</head>',f'<style>{css}</style></head>')
    if st.session_state.get('_tick_wave_surge'):
        surge_css=Path(__file__).with_name('surge_wall.css').read_text()
        markup=markup.replace('</head>',f'<style>{surge_css}</style></head>')
        if mode=='wall':
            js=Path(__file__).with_name('surge_wall.js').read_text()
            markup=markup.replace('</body>',f'<script>{js}</script></body>')
    return markup

def apply_ocean_shell():
    css=(Path(__file__).with_name('ocean_shell.css')).read_text()
    st.markdown(f'<style>{css}</style>',unsafe_allow_html=True)
    if st.session_state.get('_tick_wave_surge'):
        st.markdown('<style>'+Path(__file__).with_name('surge_shell.css').read_text()+'</style>',unsafe_allow_html=True)

def ocean_sidebar():
    st.markdown(f'<div class="ocean-side-logo"><img src="{logo_uri()}" alt="tick wave logo"><div>tick <span>wave</span></div><small>OCEAN EDITION / 02</small></div>',unsafe_allow_html=True)

def ocean_header():
    if st.session_state.get('_tick_wave_surge'):
        sea='data:image/svg+xml;base64,'+base64.b64encode((ASSETS/'ocean_swell.svg').read_bytes()).decode()
        st.markdown(f'''<section class="ocean-hero surge-hero"><div class="ocean-copy"><div class="ocean-kicker">TICK WAVE / THE LIVING OCEAN · SURF EDITION</div><h1>Make a ripple.<br>Move an ocean.</h1><p>A request becomes a current. Watch its energy flow through every decision, service and deployment.</p><span class="ocean-tag">CYAN CURRENTS</span><span class="ocean-tag violet">VIOLET TIDES</span></div><div class="ocean-logo-stage"><img src="{logo_uri()}" alt="Animated tick wave logo — pulsing nodes and flowing branches"><span>ONE SIGNAL. AN OCEAN OF POSSIBILITIES.</span></div><div class="surge-ocean" aria-hidden="true"><img src="{sea}" alt=""><img src="{sea}" alt=""><img src="{sea}" alt=""></div><div class="surge-water-label">RIPPLE → CURRENT → TIDE → HARBOR</div></section>''',unsafe_allow_html=True)
        return
    st.markdown(f'''<section class="ocean-hero"><div class="ocean-copy"><div class="ocean-kicker">TICK WAVE / OCEAN EDITION</div><h1>Every decision<br>starts a new wave.</h1><p>One request is a ripple. Follow its current through behavior, services and the edge–cloud ocean.</p><span class="ocean-tag">RESEARCH IN MOTION</span><span class="ocean-tag violet">SIX CONNECTED CURRENTS</span></div><div class="ocean-logo-stage"><img src="{logo_uri()}" alt="tick wave logo supplied as reference"><span>FROM A SINGLE SIGNAL TO A CONNECTED SYSTEM</span></div><div class="ocean-surface"><i></i><i></i><i></i></div></section>''',unsafe_allow_html=True)
