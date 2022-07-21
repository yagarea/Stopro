#!/usr/bin/env python3

import argparse


def get_args():
    arg_parser = argparse.ArgumentParser("StoPro",
            description="Simple utility for productivity and will training.",
            epilog="hope it helps")

    command_parser = arg_parser.add_subparsers(title="commands", dest="command", required=True)

    parser_start = command_parser.add_parser(
            "start", 
            help="start self control session")
    parser_stop = command_parser.add_parser(
            "stop",
            help="stop self control session")
    parser_status = command_parser.add_parser(
            "status",
            help="print info about current session")

    return arg_parser.parse_args()

