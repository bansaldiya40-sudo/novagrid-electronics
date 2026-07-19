"""
NovaGrid Electronics - Retail Experience Effects
Sound cues, confetti / balloon / cracker bursts, flash messages and
popups that give the storefront a premium, dynamic retail feel.
Sounds are generated on the fly as short WAV tones (numpy) and embedded
as autoplay HTML audio so the project has zero external audio file
dependencies. All sound effects respect a global ON/OFF toggle stored
in st.session_state["sound_enabled"].
"""

import io
import base64
import wave
import struct

import numpy as np
import streamlit as st
import streamlit.components.v1 as components


def sound_enabled():
    return st.session_state.get("sound_enabled", True)


# --------------------------------------------------------------------------- #
# SOUND GENERATION (pure numpy -> WAV -> base64, no external files)
# --------------------------------------------------------------------------- #
def _generate_tone_wav(frequencies, duration=0.15, volume=0.35, sample_rate=44100):
    """Generate a short WAV tone (list of frequencies played in sequence)."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for freq in frequencies:
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            tone = np.sin(freq * t * 2 * np.pi)
            fade = np.linspace(1, 0, len(tone))
            tone = tone * fade * volume
            audio = (tone * 32767).astype(np.int16)
            wav_file.writeframes(struct.pack("<%dh" % len(audio), *audio))
    return base64.b64encode(buf.getvalue()).decode()


def _play_audio(b64_wav):
    if not sound_enabled():
        return
    html = f"""
    <audio autoplay="true" style="display:none">
        <source src="data:audio/wav;base64,{b64_wav}" type="audio/wav">
    </audio>
    """
    components.html(html, height=0, width=0)


def play_success_sound():
    _play_audio(_generate_tone_wav([660, 880, 1046]))


def play_add_to_cart_sound():
    _play_audio(_generate_tone_wav([523, 784]))


def play_notification_sound():
    _play_audio(_generate_tone_wav([440, 440]))


def play_alert_sound():
    _play_audio(_generate_tone_wav([300, 220]))


def play_order_success_sound():
    _play_audio(_generate_tone_wav([523, 659, 784, 1046], duration=0.13))


def _generate_crackle_wav(pops=6, sample_rate=44100, seed=7):
    """Synthesizes a short firecracker 'pop/crackle' burst using decaying
    noise impulses (no external audio files needed)."""
    rng = np.random.default_rng(seed)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for _ in range(pops):
            dur = rng.uniform(0.05, 0.11)
            n = max(1, int(sample_rate * dur))
            noise = rng.uniform(-1, 1, n)
            decay = np.linspace(1, 0, n) ** 2
            tone = noise * decay * 0.55
            audio = (tone * 32767).astype(np.int16)
            wav_file.writeframes(struct.pack("<%dh" % len(audio), *audio))
            gap_n = max(1, int(sample_rate * rng.uniform(0.02, 0.07)))
            silence = np.zeros(gap_n, dtype=np.int16)
            wav_file.writeframes(struct.pack("<%dh" % len(silence), *silence))
    return base64.b64encode(buf.getvalue()).decode()


def play_cracker_sound():
    _play_audio(_generate_crackle_wav())


# --------------------------------------------------------------------------- #
# VISUAL CELEBRATIONS
# --------------------------------------------------------------------------- #
def confetti_burst():
    components.html(
        """
        <script>
        (function() {
            const doc = window.parent.document;
            let old = doc.getElementById('novagrid_confetti_canvas');
            if (old) old.remove();

            const canvas = doc.createElement('canvas');
            canvas.id = 'novagrid_confetti_canvas';
            canvas.style.position = 'fixed';
            canvas.style.top = '0'; canvas.style.left = '0';
            canvas.style.width = '100%'; canvas.style.height = '100%';
            canvas.style.pointerEvents = 'none';
            canvas.style.zIndex = '999999';
            doc.body.appendChild(canvas);

            const ctx = canvas.getContext('2d');
            canvas.width = window.parent.innerWidth;
            canvas.height = window.parent.innerHeight;

            const colors = ['#7C4DFF','#FF6F91','#12B886','#D4AF6A','#C9BFEA','#9D6BFF'];
            let particles = Array.from({length: 220}, () => ({
                x: Math.random()*canvas.width, y: -20 - Math.random()*canvas.height*0.3,
                r: Math.random()*6+4, c: colors[Math.floor(Math.random()*colors.length)],
                speed: Math.random()*3+2, drift: Math.random()*2-1, rot: Math.random()*360
            }));
            let frame = 0;
            function draw() {
                ctx.clearRect(0,0,canvas.width,canvas.height);
                particles.forEach(p => {
                    p.y += p.speed; p.x += p.drift; p.rot += 5;
                    ctx.save(); ctx.translate(p.x,p.y); ctx.rotate(p.rot*Math.PI/180);
                    ctx.fillStyle = p.c; ctx.fillRect(-p.r/2,-p.r/2,p.r,p.r*1.6);
                    ctx.restore();
                });
                frame++;
                if (frame < 150) {
                    requestAnimationFrame(draw);
                } else {
                    canvas.remove();
                }
            }
            draw();
        })();
        </script>
        """,
        height=0, width=0,
    )


def balloon_rise():
    components.html(
        """
        <script>
        (function() {
            const doc = window.parent.document;
            let old = doc.getElementById('novagrid_balloon_canvas');
            if (old) old.remove();

            const canvas = doc.createElement('canvas');
            canvas.id = 'novagrid_balloon_canvas';
            canvas.style.position = 'fixed';
            canvas.style.top = '0'; canvas.style.left = '0';
            canvas.style.width = '100%'; canvas.style.height = '100%';
            canvas.style.pointerEvents = 'none';
            canvas.style.zIndex = '999998';
            doc.body.appendChild(canvas);

            const ctx = canvas.getContext('2d');
            canvas.width = window.parent.innerWidth;
            canvas.height = window.parent.innerHeight;

            const colors = ['#7C4DFF','#FF6F91','#12B886','#D4AF6A','#9D6BFF','#C9BFEA'];
            let balloons = Array.from({length: 18}, () => ({
                x: Math.random()*canvas.width,
                y: canvas.height + Math.random()*200,
                r: Math.random()*22+26,
                c: colors[Math.floor(Math.random()*colors.length)],
                speed: Math.random()*1.6+1.2,
                sway: Math.random()*2-1,
                phase: Math.random()*Math.PI*2
            }));
            let frame = 0;
            function draw() {
                ctx.clearRect(0,0,canvas.width,canvas.height);
                balloons.forEach(b => {
                    b.y -= b.speed;
                    b.x += Math.sin(frame/20 + b.phase) * b.sway;
                    ctx.beginPath();
                    ctx.ellipse(b.x, b.y, b.r*0.75, b.r, 0, 0, Math.PI*2);
                    ctx.fillStyle = b.c; ctx.globalAlpha = 0.92; ctx.fill();
                    ctx.globalAlpha = 1;
                    ctx.strokeStyle = 'rgba(0,0,0,0.25)';
                    ctx.beginPath();
                    ctx.moveTo(b.x, b.y + b.r);
                    ctx.lineTo(b.x, b.y + b.r + 40);
                    ctx.stroke();
                });
                frame++;
                if (frame < 220) {
                    requestAnimationFrame(draw);
                } else {
                    canvas.remove();
                }
            }
            draw();
        })();
        </script>
        """,
        height=0, width=0,
    )


def crackers_effect():
    components.html(
        """
        <script>
        (function() {
            const doc = window.parent.document;
            let old = doc.getElementById('novagrid_cracker_canvas');
            if (old) old.remove();

            const canvas = doc.createElement('canvas');
            canvas.id = 'novagrid_cracker_canvas';
            canvas.style.position = 'fixed';
            canvas.style.top = '0'; canvas.style.left = '0';
            canvas.style.width = '100%'; canvas.style.height = '100%';
            canvas.style.pointerEvents = 'none';
            canvas.style.zIndex = '999999';
            doc.body.appendChild(canvas);

            const ctx = canvas.getContext('2d');
            canvas.width = window.parent.innerWidth;
            canvas.height = window.parent.innerHeight;

            const colors = ['#D4AF6A','#7C4DFF','#FF6F91','#12B886','#9D6BFF','#FFD1DC'];
            function burst(cx, cy) {
                return Array.from({length: 70}, () => ({
                    x: cx, y: cy,
                    vx: (Math.random()-0.5)*9, vy: (Math.random()-0.5)*9,
                    life: 70, c: colors[Math.floor(Math.random()*colors.length)]
                }));
            }
            let allParts = [];
            for (let i=0;i<5;i++){
                allParts = allParts.concat(burst(
                    Math.random()*canvas.width, Math.random()*canvas.height*0.6+40));
            }
            function draw() {
                ctx.clearRect(0,0,canvas.width,canvas.height);
                allParts.forEach(p => {
                    p.x += p.vx; p.y += p.vy; p.vy += 0.05; p.life -= 1;
                    ctx.globalAlpha = Math.max(p.life/70,0);
                    ctx.fillStyle = p.c;
                    ctx.beginPath(); ctx.arc(p.x,p.y,3,0,Math.PI*2); ctx.fill();
                });
                ctx.globalAlpha = 1;
                allParts = allParts.filter(p => p.life > 0);
                if (allParts.length > 0) {
                    requestAnimationFrame(draw);
                } else {
                    canvas.remove();
                }
            }
            draw();
        })();
        </script>
        """,
        height=0, width=0,
    )


def checkout_celebration():
    """Full checkout celebration: confetti + balloons + crackers + sound.
    Call this WITHOUT an immediate st.rerun() afterwards — a rerun tears
    down the injected audio/animation components before they finish."""
    play_order_success_sound()
    confetti_burst()
    balloon_rise()
    crackers_effect()
    play_cracker_sound()


# --------------------------------------------------------------------------- #
# MESSAGE / POPUP HELPERS
# --------------------------------------------------------------------------- #
def flash_message(message, kind="success"):
    icon_map = {"success": "✅", "warning": "⚠️", "error": "❌", "info": "ℹ️"}
    icon = icon_map.get(kind, "ℹ️")
    color_map = {
        "success": "#12B886", "warning": "#D4AF6A", "error": "#DC2626", "info": "#7C4DFF"
    }
    color = color_map.get(kind, "#7C4DFF")
    st.markdown(
        f"""
        <div style="background:{color}18;border-left:5px solid {color};
        padding:10px 16px;border-radius:8px;margin:8px 0;font-weight:600;
        color:{color};">{icon} {message}</div>
        """,
        unsafe_allow_html=True,
    )


def congratulations_popup(message="Congratulations! Deal Activated 🎉"):
    st.balloons()
    st.success(message)


def deal_activated_popup(product_name, discount):
    st.toast(f"🔥 Deal Activated: {product_name} at {discount}% off!", icon="🔥")


def out_of_stock_popup(product_name):
    st.toast(f"❌ {product_name} just went Out of Stock!", icon="❌")


def limited_stock_warning(product_name, stock):
    st.toast(f"⚠️ Hurry! Only {stock} left of {product_name}", icon="⚠️")


def flash_sale_alert(product_name, discount):
    st.toast(f"⚡ Flash Sale: {product_name} at {discount}% off — today only!", icon="⚡")


def todays_deal_popup(product_name, discount, hours_left):
    st.toast(f"🎯 Today's Deal: {product_name} — extra {discount}% off, "
             f"ends in {hours_left}h!", icon="🎯")
