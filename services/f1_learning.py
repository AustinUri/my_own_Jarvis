from __future__ import annotations

import json
from pathlib import Path

from core.user_paths import jarvis_data_dir

TOPICS = [
    ('Tyre compounds', 'How soft, medium and hard compounds trade grip for durability, and why tyre temperature matters.'),
    ('Undercut and overcut', 'How pit-stop timing can gain track position, and when an overcut beats an undercut.'),
    ('DRS and aerodynamic drag', 'Why opening the rear-wing flap increases straight-line speed and where DRS can be used.'),
    ('Qualifying formats', 'How Q1, Q2 and Q3 work, tyre preparation, traffic and track evolution.'),
    ('Parc ferme', 'What teams may and may not change after qualifying, and why setup choices become strategic commitments.'),
    ('Safety car strategy', 'How a safety car changes pit-loss time, bunches the field and creates strategic opportunities.'),
    ('Dirty air and downforce', 'Why following another car hurts cornering grip and how modern aero rules try to reduce that penalty.'),
    ('Brake bias and energy recovery', 'How drivers balance braking and how hybrid recovery affects deceleration and deployment.'),
    ('Track evolution', 'Why lap times often improve through a session as rubber builds up and conditions change.'),
    ('Race starts', 'Clutch bite point, reaction time, tyre temperature and the run to Turn 1.'),
    ('Telemetry basics', 'Speed traces, throttle, brake, steering and delta time: the basic signals engineers compare.'),
    ('Constructors vs drivers', 'How the two championships are scored and why team strategy can conflict with individual goals.'),
]


class F1LearningService:
    def __init__(self):
        self.path = jarvis_data_dir() / 'f1_learning.json'

    def _load(self):
        try:
            return json.loads(self.path.read_text(encoding='utf-8'))
        except Exception:
            return {'index': 0, 'completed': []}

    def _save(self, state):
        self.path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')


    def current_lesson(self) -> dict:
        state = self._load()
        index = int(state.get('index') or 0) % len(TOPICS)
        title, seed = TOPICS[index]
        return {'topic': title, 'seed': seed, 'lesson_number': len(state.get('completed') or []) + 1, 'instruction': 'Teach this clearly with one practical race example and end with one short question for the user.'}

    def next_lesson(self) -> dict:
        state = self._load()
        index = int(state.get('index') or 0) % len(TOPICS)
        title, seed = TOPICS[index]
        state['index'] = (index + 1) % len(TOPICS)
        completed = list(state.get('completed') or [])
        if title not in completed:
            completed.append(title)
        state['completed'] = completed[-50:]
        self._save(state)
        return {'topic': title, 'seed': seed, 'lesson_number': len(completed), 'instruction': 'Teach this clearly with one practical race example and end with one short question for the user.'}
