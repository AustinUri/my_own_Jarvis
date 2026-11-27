import math
import tempfile
import unittest
import wave
from array import array
from pathlib import Path
from random import Random

from core.capabilities.youtube_autopilot import creative_factory, foley
from core.capabilities.youtube_autopilot.stage import drop_times, sample_pose
from core.capabilities.youtube_autopilot.visual_contract import audit_storyboard


class ContactAndFoleyTests(unittest.TestCase):
    def test_prop_leaves_hand_continuously_then_hits_ground_twice(self):
        scene = {'action':'drop', 'prop':'acorn', 'shot':'close', 'cast_version':2}
        duration = 3.
        release, impact, settle = drop_times(duration)
        pose = lambda t: sample_pose(scene, t/duration, duration)
        self.assertTrue(pose(release-.0001).attached)
        self.assertFalse(pose(release+.0001).attached)
        self.assertLess(math.dist(pose(release-.0001).prop, pose(release+.0001).prop), .02)
        self.assertGreater(pose(impact).prop[1]-pose(release).prop[1], 55.)
        self.assertLess(pose((settle+impact)/2).prop[1], pose(impact).prop[1]-9.)
        self.assertAlmostEqual(pose(impact).prop[1],pose(settle).prop[1])
        self.assertEqual(pose(settle+.01).prop, pose(duration).prop)

    def test_drops_require_a_supported_inanimate_prop(self):
        story = creative_factory.offline_story(None, [], Random(6))
        self.assertTrue(audit_storyboard(story)['ok'])
        contact = next(s for s in story['scenes'] if s['action'] == 'drop')
        contact['prop'] = 'snail'
        self.assertIn('drop is unavailable', ' '.join(audit_storyboard(story)['issues']))
        options = creative_factory._episode_format('snail')['json_schema']['schema']['properties']
        self.assertNotIn('drop', options['scenes']['items']['properties']['action']['enum'])

    def test_new_firefly_performance_changes_the_reaction_in_the_same_shot(self):
        scene = {'action':'discover', 'prop':'acorn', 'shot':'close'}
        old = sample_pose(scene, .40, 3.)
        new = sample_pose(dict(scene, cast_version=2), .40, 3.)
        self.assertLess(new.firefly[1],old.firefly[1]-35)
        self.assertEqual(old.prop, new.prop)

    def test_mixed_stereo_preserves_master_and_checks_both_contact_sounds(self):
        rate, fps, seconds = 8000, 20, 3.
        scene = {'prop':'acorn','action':'drop','direction':'left'}
        timeline = [{'start_frame':0,'frame_count':65,'speech_seconds':seconds}]
        with tempfile.TemporaryDirectory() as directory:
            dry = Path(directory)/'piper.wav'
            mix = Path(directory)/'mix.wav'
            clean = array('h', (round(2800*math.sin(2*math.pi*230*i/rate))
                                for i in range(round(65*rate/fps))))
            with wave.open(str(dry),'wb') as w:
                w.setparams((1,2,rate,0,'NONE','not compressed'))
                w.writeframes(clean.tobytes())
            original = dry.read_bytes()
            foley.mix_soundtrack(dry,mix,[scene],timeline,fps)
            self.assertEqual(original,dry.read_bytes())
            with wave.open(str(mix),'rb') as w:
                self.assertEqual((2,len(clean)),(w.getnchannels(),w.getnframes()))
                pcm = w.readframes(w.getnframes())
        events = timeline[0]['foley']
        self.assertEqual([math.ceil(t*fps) for t in drop_times(seconds)[1:]], [e['frame'] for e in events])
        self.assertTrue(all(not e['right'] for e in events))
        checks = foley.audit_foley(pcm,[scene],timeline,fps)
        self.assertTrue(all(c['correlation']>.99 for c in checks))
        samples = array('h',pcm)
        # Silencing only the second bounce must fail even with a complete spoken track.
        samples[2*round(events[1]['frame']*rate/fps):] = array('h',
            (v for v in clean[round(events[1]['frame']*rate/fps):] for _ in range(2)))
        with self.assertRaisesRegex(ValueError,'missing or mistimed wood'):
            foley.audit_foley(samples.tobytes(),[scene],timeline,fps)
        events.pop()
        with self.assertRaisesRegex(ValueError,'do not match'):
            foley.audit_foley(pcm,[scene],timeline,fps)


if __name__ == '__main__':
    unittest.main()
