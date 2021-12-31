import os


def getCommand(name: str, command: str):
    try:
        if len(os.environ[name]) == 0:
            raise KeyError
        return os.environ[name]
    except KeyError:
        return command


class _BotCommands:
    def __init__(self):
        self.StartCommand = getCommand('START_BOT', 'start')
        self.RestartCommand = getCommand('RESTART_BOT', 'restart')
        self.HelpCommand = getCommand('HELP_BOT', 'help')
        self.LogCommand = getCommand('LOG_BOT', 'logs')
        self.CloneCommand = getCommand('CLONE_BOT', 'clone')
        self.DeleteCommand = getCommand('DELETE_BOT', 'del')
        self.UpdateCommand = getCommand('UPDATE_BOT', 'update')


BotCommands = _BotCommands()
