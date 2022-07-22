#!/usr/bin/env python3

import argparse


def get_args():
    arg_parser = argparse.ArgumentParser("StoPro",
            description="Simple utility for productivity and will training.",
            epilog="If you find any bug or have feature suggestion you can open issue in project repository: github.com/yagarea/Stopro\n\nPublished under GPLv3 license")

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

    parser_config = command_parser.add_parser(
            "config",
            help="opens config file in editor")

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

