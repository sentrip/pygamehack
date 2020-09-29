import pygamehack as gh
import logging

log = logging.getLogger('pygamehack')

from pygamehack_utils.aob import AOBFinder, extract_searchable_raw_code, aob_string_to_raw_code
from pygamehack_utils.cli import generate_aob_classes, update_offsets_in_file
from pygamehack_utils.instruction import Instruction, Operand

from brawl_structs import Game, MainMenu

from argparse import ArgumentParser


def get_args(parser_name=None):
    parser = ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')

    parsers = {}

    for name in ['gui', 'generate', 'update']:
        p = subparsers.add_parser(name)
        parsers[name] = p
        p.add_argument('process_name', nargs=1, type=str)
        p.add_argument('hackstruct_file', nargs=1, type=str)

    return parser.parse_args() if parser_name is None else parsers[parser_name].parse_args()


if __name__ == '__main__':
    print(get_args('gui'))

    # FORMAT = '%(asctime)-15s %(message)s'
    # logging.basicConfig(level=logging.DEBUG, format=FORMAT)
    # log.propagate = True

    # h = gh.Hack('')
    # log.setLevel(logging.INFO)
    # generate_offsets_class()
    # update_offsets_in_file()
    # update_offsets_file()
    # exit(0)

    # raw = b'Rj\x00Q\xff\xd0\x83\xc4\x10\xc7C\x14\x01\x00\x00\x00\xc7CH\x00\x00\x00\x00\x8bC@\x8bS\x08\x8b'
    # code, offset, size = extract_searchable_raw_code(raw, 16)
    # print(offset, size)
    # print(parse_raw_code(code))
