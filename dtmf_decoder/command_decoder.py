"""

A demo that executes commands based on the detected DTMF signals.

"""

import requests
import colorama
from dtmf_decoder.helpers import clear_console

colorama.init()

# Console text styles
HIGHLIGHT = '\x1b[6;30;47m'
NORMAL = '\x1b[0m'
BRIGHT_MAGENTA = '\x1b[95m'
GREEN = '\x1b[32m'
RED = '\x1b[31m'

BANNER = f'''
{HIGHLIGHT} DTMF DECODER {NORMAL}


    CODE        COMMAND         DESCRIPTION
    ----        -------         -----------

    {BRIGHT_MAGENTA}1234{NORMAL}        {GREEN}hello{NORMAL}           Prints "Hello, world!" to the console

    {BRIGHT_MAGENTA}1111{NORMAL}        {GREEN}joke{NORMAL}            Gets a random programming joke from jokeapi.dev

    {BRIGHT_MAGENTA}2222{NORMAL}        {GREEN}activity{NORMAL}        Gets a random activity to do from boredapi.com

'''


class CommandDecoder:
    def __init__(self):
        self.command = ''
        self.command_map = {
            '1234': self.hello,
            '1111': self.get_programming_joke,
            '2222': self.get_random_activity
        }

        self.show_screen()

    def make_api_call(self, api):
        r = requests.get(api)
        return r.json()

    def get_random_activity(self):
        api = 'https://www.boredapi.com/api/activity'
        resp = self.make_api_call(api)
        output = f'{BRIGHT_MAGENTA}Activity:{NORMAL} {resp["activity"]}'
        return output

    def get_programming_joke(self):
        api = 'https://v2.jokeapi.dev/joke/Programming?type=single'
        resp = self.make_api_call(api)
        output = f'{BRIGHT_MAGENTA}Joke:{NORMAL} {resp["joke"]}'
        return output

    @staticmethod
    def hello():
        return 'Hello, world!'

    def show_screen(self, command_result=None):
        clear_console()

        print(BANNER)

        if command_result:
            print(f'Executed command: {BRIGHT_MAGENTA}{command_result["command"]}{NORMAL}\n')
            print('Command output:\n')
            print(f'    {command_result["output"]}')
            print('\n')

        print(f'COMMAND ~ {BRIGHT_MAGENTA}{self.command}{NORMAL}', end='', flush=True)

    def process_command(self, prefix='*', suffix='#'):
        if not self.command.startswith(prefix):
            self.command = ''

        if self.command.endswith(suffix):
            # Strip the first character (prefix) and last character (suffix) from the command
            self.command = self.command[1:-1]

            print()

            # Execute the command
            print(f'\nExecuting command: {BRIGHT_MAGENTA}{self.command}{NORMAL}')

            try:
                command_output = self.command_map[self.command]()
            except KeyError:
                # The command was not found!
                command_output = f'{RED}[BAD COMMAND CODE] : The command you entered does not exist ("{self.command}").{NORMAL}'

            command_result = {
                'command': self.command,
                'output': command_output
            }

            # Reset the command
            self.command = ''

            return command_result
        return None

    def key(self, pressed_key):
        self.command += pressed_key

        self.show_screen()

        command_result = self.process_command()

        self.show_screen(command_result=command_result)
