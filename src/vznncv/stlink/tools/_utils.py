import re


def format_command(args):
    """
    Format external command with arguments for logging.

    :param args: list with command and arguments
    :return: command string
    """
    return " ".join("'{}'".format(command_elem) if re.search(r'\s', command_elem) else command_elem
                    for command_elem in args)
