import datetime
import os
import re
import sys
from subprocess import call
from tempfile import NamedTemporaryFile
from time import sleep

from gtts import gTTS
from pynput import mouse, keyboard


class SirBugMeLot:
    buglevels = {
        'Low': 5 * 60,
        'Med': 2 * 60,
        'High': 30,
    }

    def __init__(self):
        self.first_press = self.last_press = self.last_pause = self.last_bug = self.last_log = self.now()
        self.base_path = os.path.abspath(os.path.dirname(sys.argv[0]))
        self.logfile = open(os.path.join(self.base_path, 'bugme.log'), "w")
        self.config = self.read_config()
        self.workspan = 0
        self.playing = False
        self.buglvl = False
        self.bugsound = ''

    def write_log(self, msg):
        self.logfile.write(msg + "\n")
        self.logfile.flush()

    @staticmethod
    def now():
        return datetime.datetime.utcnow().timestamp()

    # noinspection PyUnusedLocal
    def mouse_count(self, x, y):
        self.process_press()

    # noinspection PyUnusedLocal
    def key_count(self, key):
        self.process_press()

    def process_press(self):
        self.last_pause = self.last_press
        self.last_press = self.now()
        self.check_bugme()

    def check_bugme(self):
        self.workspan = self.last_press - self.first_press
        if self.playing:
            return
        # Check if pause was done
        paused_seconds = round(self.last_press - self.last_pause)
        if paused_seconds > self.config['pausetime']:
            self.reset_timers()
            self.playing = True
            paused_minutes = str(round(paused_seconds / 60))
            if paused_seconds < self.config['pausetime'] * 3:
                # This counts as a real pause (and not as a long time away) announce time
                if self.config['use_tts']:
                    if self.config['txt_pause'] != '':
                        name = self.config['txt_name']
                        pause_msg = self.config['txt_pause'].format(minutes=paused_minutes, name=name)
                        self.speak(pause_msg)
                else:
                    self.play_mp3(self.config['sound_pause'])
            self.write_log('Pause of {} minutes registered, resetting timer'.format(paused_minutes))
            self.playing = False
            return
        if self.workspan > self.config['worktime_max'] and self.set_buglevel():
            if self.workspan > self.config['worktime_max'] * 3:
                # Happens when machine hibernates, so we need to start over
                self.reset_timers()
                return
            # buglevel changed, bug him
            self.bug_him()
        # Check if bugging is necessary
        seconds_since_bug = self.now() - self.last_bug
        if self.workspan > self.config['worktime_max'] and seconds_since_bug > self.buglvl:
            self.bug_him()
        elif self.last_press - self.last_pause > 60 or self.now() - self.last_log > 300:
            if self.workspan < 120:
                return
            self.write_log('Working for {} minutes'.format(round(self.workspan / 60, 2)))
            self.last_log = self.now()

    def reset_timers(self):
        self.first_press = self.last_pause = self.last_bug = self.now()

    def speak(self, msg):
        tts = gTTS(text=msg, lang='en')
        f = NamedTemporaryFile()
        tts.write_to_fp(f)
        f.flush()
        self.play_mp3(f.name)
        f.close()

    @staticmethod
    def play_mp3(file_path: str):
        if file_path is None or not os.path.isfile(file_path):
            return
        fnull = open(os.devnull, 'w')
        call(["ffplay", "-autoexit", "-nodisp", str(file_path)], stdout=fnull, stderr=fnull, close_fds=True)

    def bug_him(self):
        if self.playing:
            return
        self.playing = True
        if self.config['use_tts']:
            work_minutes = str(round(self.workspan / 60))
            name = self.config['txt_name']
            if self.buglvl == self.buglevels['Low']:
                bug_msg = self.config['txt_lvl1'].format(minutes=work_minutes, name=name)
                self.speak(bug_msg)
            elif self.buglvl == self.buglevels['Med']:
                bug_msg = self.config['txt_lvl2'].format(minutes=work_minutes, name=name)
                self.speak(bug_msg)
            else:
                bug_msg = self.config['txt_lvl3'].format(minutes=work_minutes, name=name)
                self.speak(bug_msg)
                self.play_mp3(self.bugsound)
        else:
            self.play_mp3(self.bugsound)
        self.last_bug = self.now()
        self.write_log('Bugging after {} minutes'.format(round(self.workspan / 60, 2)))
        self.playing = False

    def set_buglevel(self):
        # Adjust bug level according to uninterrupted working time
        if self.workspan >= self.config['worktime_max'] + 20 * 60:
            if self.buglvl != self.buglevels['High']:
                self.buglvl = self.buglevels['High']
                self.bugsound = self.config['sound_lvl3']
                self.write_log('Setting buglevel to High at workspan {} minutes'.format(round(self.workspan / 60)))
                return True
        elif self.workspan >= self.config['worktime_max'] + 10 * 60:
            if self.buglvl != self.buglevels['Med']:
                self.buglvl = self.buglevels['Med']
                self.bugsound = self.config['sound_lvl2']
                self.write_log('Setting buglevel to Med at workspan {} minutes'.format(round(self.workspan / 60)))
                return True
        elif self.workspan >= self.config['worktime_max']:
            if self.buglvl != self.buglevels['Low']:
                self.buglvl = self.buglevels['Low']
                self.bugsound = self.config['sound_lvl1']
                self.write_log('Setting buglevel to Low at workspan {} minutes'.format(round(self.workspan / 60)))
                return True
        return False

    def read_config(self):
        defaults = self.parse_env(os.path.join(self.base_path, '.env.dist'))
        usr_config = self.parse_env(os.path.join(self.base_path, '.env'))
        # Verify config
        for dk, dv in defaults.items():
            if dk not in usr_config:
                usr_config[dk] = dv
        self.write_log('Config read: ' + usr_config.__str__())
        return usr_config

    def parse_env(self, env_path):
        result = {}
        if os.path.isfile(env_path):
            envre = re.compile(r'''^([^\s=]+)=(?:[\s"']*)(.+?)(?:[\s"']*)$''')
            with open(env_path) as env_file:
                for line in env_file:
                    match = envre.match(line)
                    if match is not None:
                        key = str(match.group(1))
                        result[key] = self.get_env_value(key, match.group(2))
        return result

    def get_env_value(self, key, value):
        default_sound_path = os.path.join(self.base_path, 'bugme.mp3')
        if not os.path.isfile(default_sound_path):
            raise FileNotFoundError(default_sound_path)
        if key == 'use_tts':
            value = bool(value)
        if key in ('worktime_max', 'pausetime'):
            value = int(value)
            if key == 'worktime_max':
                value = value * 60 if value > 0 else 45 * 60
            if key == 'pausetime':
                value = value * 60 if value > 0 else 5 * 60
        if key in ('sound_lvl1', 'sound_lvl2', 'sound_lvl3', 'sound_pause'):
            file_name = str(value)
            if re.match('.*mp3$', file_name):
                sound_file_path = os.path.join(self.base_path, file_name)
            else:
                sound_file_path = default_sound_path
            if os.path.isfile(sound_file_path):
                value = sound_file_path
            else:
                value = default_sound_path
        if key in ('txt_name', 'txt_lvl1', 'txt_lvl2', 'txt_lvl3', 'txt_pause'):
            value = str(value)
        return value


try:
    sbml = SirBugMeLot()
    mlistener = mouse.Listener(on_move=sbml.mouse_count)
    mlistener.start()
    klistener = keyboard.Listener(on_press=sbml.key_count)
    klistener.start()
    while True:
        sleep(5)
except FileNotFoundError as e:
    sys.stdout.write('Missing file: ' + str(e.args[0]))
