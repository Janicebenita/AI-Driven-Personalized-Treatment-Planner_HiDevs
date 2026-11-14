"""Make a silent, labelled walkthrough from actual synthetic pipeline outputs, not a UI recording."""
import json
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rag.pipeline import create_report
from rag.retrieval import KnowledgeBase

OUT = ROOT / 'docs/demo'
WORK = ROOT / '.careweave/demo-frames'
OUT.mkdir(parents=True, exist_ok=True)
WORK.mkdir(parents=True, exist_ok=True)
cases = json.loads((ROOT / 'data/synthetic-cases.json').read_text(encoding='utf-8'))
kb = KnowledgeBase(allow_fallback=False)
maya = create_report(cases['renal'], kb)
renal = create_report({**cases['renal'], 'egfr': 24}, kb)
urgent = create_report({**cases['renal'], 'acute': True}, kb)
reports = {'maya': maya, 'renal_counterfactual': renal, 'urgent': urgent}
(OUT / 'synthetic-reports.json').write_text(json.dumps(reports, indent=2) + '\n', encoding='utf-8')

def font(size, bold=False):
    windows = Path('C:/Windows/Fonts') / ('segoeuib.ttf' if bold else 'segoeui.ttf')
    if windows.exists():
        return ImageFont.truetype(str(windows), size)
    return ImageFont.truetype('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf', size)

INK, MUTED, GREEN, BG = '#183c39', '#526b63', '#226f5b', '#f5f7f3'
slides = [
    ('Evidence into care', 'A transparent, clinician-review treatment planning prototype', [
        ('The challenge', 'Connect diagnosis, medical history, verified genetics and lifestyle to a reviewable plan.'),
        ('The approach', 'Independent safety checks + local MiniLM / Chroma retrieval + optional Groq / Llama synthesis.'),
        ('What this video shows', 'Actual synthetic-case pipeline outputs rendered as a walkthrough. This is not a screen recording or live AI generation.')], 12),
    ('01  Meet the synthetic patient', 'Maya: adult type 2 diabetes with confirmed CKD', [
        ('Clinical context', f"Age {maya['profile']['age']} | HbA1c {maya['profile']['hba1c']}% | eGFR {maya['profile']['egfr']} | BMI {maya['profile']['bmi']}"),
        ('Medicines and verified phenotype', maya['profile']['medications'] + ' | SLCO1B1: poor function'),
        ('Daily life and priorities', maya['profile']['lifestyle'] + '. Goal: ' + maya['profile']['goal'] + '. Budget: limited.')], 12),
    ('02  A personalized discussion', 'The plan explains which patient factors shaped the options', [
        (maya['options'][0]['title'], maya['options'][0]['detail']),
        ('Why it fits', maya['options'][0]['why'] + ' Evidence: ' + maya['options'][0]['source']),
        ('Practical fit', 'The report also retains lifestyle goals and affordability as explicit discussion items.')], 14),
    ('03  Make risk visible', 'The safety layer runs independently of the language model', [
        (risk['title'], risk['detail'] + ' [' + risk['source'] + ']') for risk in maya['risks']], 14),
    ('04  Change one factor', 'Counterfactual: eGFR 42 -> 24, with other inputs held constant', [
        ('Changed treatment pathway', renal['options'][0]['title'] + '. ' + renal['options'][0]['why']),
        ('New prompt-review signal', next(r['detail'] for r in renal['risks'] if r['title'].startswith('Metformin needs'))),
        ('Human oversight', 'The prototype does not calculate doses or instruct the patient to change medication independently.')], 14),
    ('05  Inspect the evidence', 'Actual local MiniLM embeddings and Chroma cosine retrieval', [
        (m['source_id'] + ' | cosine ' + str(round(m['cosine_similarity'], 3)), m['title'] + '. ' + m['section'])
        for m in maya['retrieval']['matches'][:3]] + [
        ('Interpretation', 'Similarity measures retrieval relevance, not clinical confidence. Rule-linked evidence is retained regardless of rank.')], 14),
    ('06  Plan the follow-up', 'Monitoring remains tied to explicit evidence sources', [
        (m['when'], m['task'] + ' [' + m['source'] + ']') for m in maya['monitoring'][:3]], 14),
    ('07  Know when to stop', 'Counterfactual: acute symptoms flag enabled', [
        ('Independent gate result', f"Status: {urgent['status']} | Routine options: {len(urgent['options'])} | Routine monitoring items: {len(urgent['monitoring'])}"),
        ('Escalation', urgent['risks'][0]['detail']),
        ('Provider boundary', 'Withheld cases do not call embeddings or the generative provider. The LLM cannot override this gate.')], 12),
    ('08  Be explicit about gaps', 'A useful report makes uncertainty and limits inspectable', [
        ('Missing information', '; '.join(maya['missing'][:3])),
        ('Clinical boundary', 'Educational research prototype. Not clinically validated. Adult type 2 diabetes only; allergy and interaction checks are incomplete.'),
        ('Live generation', 'Groq/Llama is integrated but requires a server-side key. This demo uses semantic retrieval only; no live provider result is claimed.')], 14),
    ('CareWeave: ready for review', 'Reproducible code, public synthetic cases, inspectable evidence', [
        ('Software verification', '25 JavaScript + 16 Python checks passed. Linux container build, HTTP startup, Node safety core and actual MiniLM/Chroma retrieval passed.'),
        ('Retrieval smoke benchmark', 'Expected source found in the top three for 5 of 5 developer-authored queries. This is not a held-out or clinical accuracy evaluation.'),
        ('Run the complete interface', 'Install the repository requirements and run: streamlit run streamlit_app.py. Cloud deployment remains disabled at the participant\'s request.')], 14),
]

def wrapped(draw, text, xy, width, size=26, color=INK, bold=False):
    face = font(size, bold)
    x, y = xy
    words, line, lines = text.split(), '', []
    for word in words:
        candidate = (line + ' ' + word).strip()
        if draw.textlength(candidate, font=face) > width and line:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    for line in lines:
        draw.text((x, y), line, fill=color, font=face)
        y += int(size * 1.35)
    return y

playlist = []
captions = ['WEBVTT', '']
elapsed = 0
for index, (title, subtitle, cards, duration) in enumerate(slides):
    image = Image.new('RGB', (1280, 720), BG)
    d = ImageDraw.Draw(image)
    d.rectangle((0, 0, 15, 720), fill=GREEN)
    d.text((55, 28), 'CAREWEAVE  /  SYNTHETIC CASE WALKTHROUGH', font=font(17, True), fill=GREEN)
    d.text((55, 76), title, font=font(40, True), fill=INK)
    wrapped(d, subtitle, (55, 137), 1155, 23, MUTED)
    y = 200
    # Fit every card into a bounded area; fail rather than exporting clipped text.
    for heading, content in cards:
        d.rounded_rectangle((55, y, 1225, y + 38), radius=7, fill='#e8f1e8')
        d.text((72, y + 4), heading, font=font(23, True), fill=GREEN)
        y = wrapped(d, content, (72, y + 47), 1135, 23, MUTED) + 22
    if y > 659:
        raise RuntimeError(f'Slide {index + 1} overflows: {y}. Shorten its text.')
    d.line((55, 666, 1225, 666), fill='#d6e2d6', width=1)
    d.text((55, 683), 'Synthetic data only  |  Clinician review required  |  Silent video: pause to inspect', font=font(16), fill=MUTED)
    d.text((1140, 683), f'{index+1:02}/{len(slides):02}', font=font(16, True), fill=GREEN)
    path = WORK / f'slide-{index:02}.png'
    image.save(path)
    playlist += [f"file '{path.as_posix()}'", f'duration {duration}']
    def stamp(seconds):
        return f'{seconds//3600:02}:{seconds//60%60:02}:{seconds%60:02}.000'
    captions += [f'{stamp(elapsed)} --> {stamp(elapsed + duration)}', title, subtitle, '']
    elapsed += duration
playlist.append(f"file '{path.as_posix()}'")
(WORK / 'slides.txt').write_text('\n'.join(playlist), encoding='utf-8')
(OUT / 'captions.vtt').write_text('\n'.join(captions), encoding='utf-8')
(OUT / 'transcript.md').write_text('# CareWeave demo transcript\n\n' + '\n\n'.join(
    f"## {title}\n\n{subtitle}\n\n" + '\n\n'.join(f'**{h}:** {body}' for h, body in cards)
    for title, subtitle, cards, duration in slides) + '\n', encoding='utf-8')
ffmpeg = shutil.which('ffmpeg')
if not ffmpeg:
    raise RuntimeError('FFmpeg must be available to encode the video.')
subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(WORK / 'slides.txt'), '-t', str(elapsed),
    '-vf', 'fps=24', '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
    '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(OUT / 'careweave-demo.mp4')], check=True)
print(f'Created {elapsed}-second silent video from actual synthetic pipeline reports.')
