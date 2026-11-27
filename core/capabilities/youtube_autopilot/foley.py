"""Original synthesized sound effects for the storyboard rig."""
from array import array
from functools import lru_cache
from math import ceil, cos, exp, pi, sin, sqrt, tau
import sys
import wave

from .stage import drop_times


def action_cues(scene, edit, fps):
    seconds = edit['speech_seconds']
    action = scene['action']
    if action == 'drop':
        _, first, second = drop_times(seconds)
        tone = {'acorn': 'wood', 'pebble': 'stone', 'apple': 'ground'}[scene['prop']]
        events = [(first, tone, 1.), (second, tone, .56)]
    elif action == 'hop':
        events = [(.73*seconds, 'ground', .8)]
    elif action == 'discover':
        events = [(.39*seconds, 'glimmer', .68)]
    elif action == 'cheer':
        events = [(.35*seconds, 'glimmer', .68)]
    elif action in ('follow', 'search'):
        events = [(.27*seconds, 'wings', .65)]
    else:
        events = []
    cues = []
    for time, sound, gain in events:
        frame = ceil(time*fps)
        # A cue belongs to the physical beat and cannot enter the next scene or its quiet hold.
        if frame/fps + _DURATION[sound] > seconds:
            continue
        on_right = sound in ('glimmer', 'wings') or action == 'drop'
        if scene.get('direction') == 'left':
            on_right = not on_right
        cues.append(dict(frame=frame, sound=sound, gain=gain, right=on_right))
    return cues


_DURATION = {'wood': .137, 'stone': .116, 'ground': .14, 'glimmer': .31, 'wings': .24}


@lru_cache(maxsize=32)
def _sound(name, rate):
    length = _DURATION[name]
    out = array('h')
    for i in range(round(length*rate)):
        t = i/rate
        if name == 'wings':
            flutter = (.5 + .5*cos(tau*26*t))**2
            wavelet = sin(pi*t/length)**1.8*flutter*(sin(tau*(250*t+95*t*t))+.18*sin(tau*575*t))
        elif name == 'glimmer':
            wavelet = exp(-10*t)*(sin(tau*928*t)+.35*sin(tau*1390*t))
            if t > .073:
                wavelet += .54*exp(-13*(t-.073))*sin(tau*1165*(t-.073))
        else:
            frequency = {'ground': 119, 'wood': 415, 'stone': 650}[name]
            wavelet = exp(-38*t)*sin(tau*(frequency*t+1.1*(1-exp(-33*t))))
            wavelet += .48*exp(-72*t)*sin(tau*frequency*2.43*t)
        window = min(1., t/.003, (length-t)/.014)
        out.append(round(5000*wavelet*window))
    return out


def _read_pcm(data):
    pcm = array('h', data)
    if sys.byteorder != 'little':
        pcm.byteswap()
    return pcm


def mix_soundtrack(narration, destination, scenes, timeline, fps):
    with wave.open(str(narration), 'rb') as source:
        if (source.getnchannels(), source.getsampwidth()) != (1, 2):
            raise ValueError('Foley requires a mono 16-bit narration master')
        rate = source.getframerate()
        dry = _read_pcm(source.readframes(source.getnframes()))
    stereo = array('h', [0])*(len(dry)*2)
    stereo[::2] = dry
    stereo[1::2] = dry
    for scene, edit in zip(scenes, timeline, strict=True):
        edit['foley'] = action_cues(scene, edit, fps)
        for event in edit['foley']:
            start = round((edit['start_frame']+event['frame'])*rate/fps)
            l_gain, r_gain = (.20, .90) if event['right'] else (.90, .20)
            for i, sample in enumerate(_sound(event['sound'], rate), start):
                left = stereo[i*2] + round(sample*event['gain']*l_gain)
                right = stereo[i*2+1] + round(sample*event['gain']*r_gain)
                stereo[i*2] = max(-32768, min(32767, left))
                stereo[i*2+1] = max(-32768, min(32767, right))
    if sys.byteorder != 'little':
        stereo.byteswap()
    with wave.open(str(destination), 'wb') as out:
        out.setparams((2, 2, rate, 0, 'NONE', 'not compressed'))
        out.writeframes(stereo.tobytes())


def audit_foley(pcm, scenes, timeline, fps, rate=8000):
    """Check each scheduled sound in the decoded stereo difference; centered narration cancels."""
    stereo = _read_pcm(pcm)
    scores = []
    for index, (scene, edit) in enumerate(zip(scenes, timeline, strict=True), 1):
        expected = action_cues(scene, edit, fps)
        if edit.get('foley') != expected:
            raise ValueError(f'Scene {index}: sound cues do not match the staged action')
        for event in expected:
            start = round((edit['start_frame'] + event['frame'])*rate/fps)
            source = _sound(event['sound'], rate)
            # Ignore a few samples of AAC pre-echo and resampler delay at the onset.
            sign = 1 if event['right'] else -1
            best = 0.
            for shift in range(-4, 5):
                first = start + shift
                if first < 0 or first+len(source) > len(stereo)//2:
                    continue
                heard = [(stereo[(first+i)*2+1]-stereo[(first+i)*2])*sign for i in range(len(source))]
                power = sqrt(sum(x*x for x in source)*sum(y*y for y in heard))
                # Both shape and level matter. Tiny encoder artifacts aren't audible cues.
                if power and max(heard) > 150*event['gain']:
                    best = max(best, sum(x*y for x,y in zip(source,heard))/power)
            if best < .55:
                raise ValueError(f"Scene {index}: missing or mistimed {event['sound']} sound at frame {event['frame']}")
            scores.append({'scene':index, 'sound':event['sound'], 'frame':event['frame'], 'correlation':round(best,3)})
    return scores
