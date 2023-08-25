#!/usr/bin/env python3

import argparse


def get_args():
    arg_parser = argparse.ArgumentParser("StoPro",
            description="Simple utility for productivity and will training.",
            epilog="If you find any bug or have feature suggestion you can open issue in project repository: github.com/yagarea/Stopro\r\rPublished under GPLv3 license")

    arg_parser.add_argument("-d", "--debug",
            action="store_true",
            dest="debug",
            help="Print debug information")

    command_parser = arg_parser.add_subparsers(title="commands", dest="command", required=True)

    parser_start = command_parser.add_parser(
            "start",
            help="start self control session")

    parser_start.add_argument(
            "-s", "--silent",
            dest="silent_mode",
            required=False,
            action="store_true",
            help="silent mode")

    parser_start.add_argument(
            "-l", "--lock",
            dest="locked_for",
            required=False,
            default="",
            help="lock session for specified time. (30m, 4h, 1d)")

    parser_stop = command_parser.add_parser(
            "stop",
            help="stop self control session")

    parser_stop.add_argument(
            "-s", "--silent",
            dest="silent_mode",
            required=False,
            action="store_true",
            help="silent mode")

    parser_status = command_parser.add_parser(
            "status",
            help="print info about current session")

    parser_lock = command_parser.add_parser(
            "lock",
            help="lock ongoing session for specified time")

    parser_lock.add_argument(
            "locked_for",
            action="store",
            type=str,
            help="lock session for specified time. (30m, 4h, 1d)")

    parser_config = command_parser.add_parser(
            "config",
            help="opens configuration file in editor")

    parser_stats = command_parser.add_parser(
            "stats",
            help="print statistics about usage and time saving")

    parser_clear_history = command_parser.add_parser(
            "clear-history",
            help="remove all logs and usage history")

    parser_verion = command_parser.add_parser(
            "version",
            help="print version of StoPro")

    arg_parser.add_argument(
            "-s", "--silent",
            dest="silent_mode",
            required=False,
            action="store_true",
            help="silent mode")

    arg_parser.add_argument(
            "-c", "--config",
            dest="config_path",
            default="/etc/stopro/conf.yml",
            required=False,

            help="sets custom config file path")

    return arg_parser.parse_args()

