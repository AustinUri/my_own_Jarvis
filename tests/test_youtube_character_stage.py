import unittest

from PIL import Image, ImageChops

from core.capabilities.youtube_autopilot.stage import draw_stage, sample_pose
from core.capabilities.youtube_autopilot.visual_contract import ACTIONS, PROPS, SHOTS


def scene(action='watch', prop='apple', shot='medium'):
    return {'action': action, 'prop': prop, 'shot': shot}


class CharacterStageTests(unittest.TestCase):
    def test_every_declared_prop_contributes_visible_pixels_in_each_framing(self):
        for prop in PROPS:
            for shot in SHOTS:
                with self.subTest(prop=prop, shot=shot):
                    plan = scene(prop=prop, shot=shot)
                    image = Image.new('RGB',(240,420),'#a5b79a')
                    without = image.copy()
                    draw_stage(image, plan, .65, 4)
                    draw_stage(without, plan, .65, 4, include_prop=False)
                    difference = ImageChops.difference(image, without).convert('L')
                    ink = difference.point(lambda value: 255 if value > 12 else 0)
                    box = ink.getbbox()
                    self.assertIsNotNone(box)
                    self.assertGreater(ink.histogram()[-1], 45)
                    self.assertGreater(box[0], 0)
                    self.assertLess(box[2], image.width)
                    self.assertLess(box[3], .85*image.height)

    def test_carry_reaches_lifts_and_transports_the_same_object(self):
        plan = scene('carry')
        start, grasp, lifted, end = [sample_pose(plan, t, 4) for t in (0.,.34,.60,.99)]
        self.assertFalse(start.attached)
        for before, after in zip(start.prop, grasp.prop):
            self.assertAlmostEqual(before, after)
        for pose in (grasp, lifted, end):
            self.assertTrue(pose.attached)
            self.assertAlmostEqual(pose.prop[0]-pose.hand[0], 10*pose.size)
            self.assertAlmostEqual(pose.prop[1]-pose.hand[1], 6*pose.size)
        self.assertLess(lifted.prop[1], grasp.prop[1]-40)
        self.assertGreater(end.prop[0], lifted.prop[0]+50)

    def test_locomotion_and_reactions_follow_the_action(self):
        pose = lambda action, progress: sample_pose(scene(action), progress, 4)
        self.assertLess(pose('enter',0).feet[0], pose('enter',1).feet[0]-80)
        self.assertLess(pose('hop',.5).feet[1], pose('hop',1).feet[1]-25)
        self.assertLess(pose('search',.1).turn, 0)
        self.assertGreater(pose('search',.9).turn, 0)
        self.assertEqual(pose('discover',.45).expression,'amazed')
        self.assertTrue(pose('watch',.0).closed)
        self.assertFalse(pose('watch',.25).closed)
        apple = pose('follow',.8)
        snail = sample_pose(scene('follow', 'snail'),.8,4)
        self.assertGreater(apple.roll, 3.)
        self.assertEqual(snail.roll, 0.)
        self.assertGreater(apple.prop[0], snail.prop[0]+40)

    def test_every_action_moves_the_cast_with_the_object_hidden(self):
        for action in ACTIONS:
            with self.subTest(action=action):
                plan = scene(action)
                start = Image.new('RGB',(240,420))
                end = start.copy()
                draw_stage(start, plan, .12, 4, include_prop=False)
                draw_stage(end, plan, .53, 4, include_prop=False)
                diff = ImageChops.difference(start,end).convert('L')
                self.assertGreater(sum(diff.histogram()[20:]), 100)


if __name__ == '__main__':
    unittest.main()
