import pygamehack as gh
from pygamehack_utils import HackStruct, Ptr
from pygamehack_utils.pointer_scan_file_ce import PointerScanFile
from pygamehack_extensions.haxe_flash import HaxeVector

HackStruct.set_architecture(32)


def add_addresses(hack: gh.Hack):
    # static_addresses = {
    #     # 'root': ('SteamAir.dll', 0x000CCF08)
    #     'root': ('DnaManager.dll', 0x001EC1CC)
    # }
    #
    # dynamic_addresses = {
    #     # 'game': ('root', [0x20, 0x320, 0xE4, 0x0, 0x18, 0x84])
    #     'game': ('root', [0xC, 0x228, 0x14, 0x18C])
    # }
    #
    # for name, (module, offset) in static_addresses.items():
    #     hack.add_static_address(name, module, offset)
    #
    # for name, (previous, offsets) in dynamic_addresses.items():
    #     hack.add_dynamic_address(name, previous, offsets)

    PointerScanFile.load_into_hack(hack, 'MainMenuTest.PTR', 'game', skip_last_n_offsets=2, max_level=7)


"""
INPUT

QUICK_ATTACK = 640
HEAVY_ATTACK = 64
UP = 17
DOWN = 2
LEFT = 4
RIGHT = 8
DODGE = 256
THROW = 516
SPEAR = 0x00005F77
SWORD = 0x00004222
KATAR = 25411
MELEE = 14969
"""


class MainMenu(HackStruct):
    in_main_menu                  : gh.uint                                            = 0x14
    in_sub_menu                   : gh.uint                                            = 0x48
    selected_index                : gh.uint                                            = 0xF0


class SelectionUI(HackStruct):
    x                             : gh.uint                                            = 0x10
    y                             : gh.uint                                            = 0x14


class MapSelectUI(HackStruct):
    is_choosing_map               : gh.uint                                            = 0x14
    selection_ui_list             : HaxeVector[SelectionUI, 8]                         = 0x180


class LegendSelection(HackStruct):
    is_locked_in                  : gh.uint                                            = 0x14


class LegendSelectUI(HackStruct):
    is_choosing_legends           : gh.uint                                            = 0x14
    selection_ui_list             : HaxeVector[SelectionUI, 8]                         = 0x124


class PostMatchUI(HackStruct):
    is_in_post_match              : gh.uint                                            = 0x24


class Game(HackStruct):
    address = 'game'

    main_menu                     : Ptr[MainMenu]                                      = 0x344
    map_select_ui                 : Ptr[MapSelectUI]                                   = 0x350
    legend_select_ui              : Ptr[LegendSelectUI]                                = 0x298
    # post_match_ui                 : Ptr[PostMatchUI]                                   = 0x4A4
    # legend_selection_list: HaxeVector[LegendSelection, 8]                = [0x524, 0x98]
    # entity_list: HaxeVector[br.Entity, 8]            = [0x55C, 0x30]


HackStruct.define_types()


class AOB:

    class LegendSelectUI:
        is_choosing_legends            = {'offset': 11, 'offset_size': 1, 'begin': 0x00800000, 'size': 0x007FFFFF,
                                          'aob': '51 FF D0 83 C4 ?? 8B 4D ?? C7 41 ?? ?? ?? ?? ?? C7 45 ?? ?? ?? ?? '
                                                 '?? 8B 41 ?? 85 C0 74 ?? 8B'}

    class MainMenu:
        in_main_menu                   = {'offset': 11, 'offset_size': 1, 'begin': 0x00800000, 'size': 0x007FFFFF,
                                          'aob': '52 6A ?? 51 FF D0 83 C4 ?? C7 43 ?? ?? ?? ?? ?? C7 43 ?? ?? ?? ?? '
                                                 '?? 8B 43 ?? 8B 53 ?? 8B'}

        in_sub_menu                    = {'offset': 11, 'offset_size': 1, 'begin': 0x0D800000, 'size': 0x027FFFFF,
                                          'aob': 'C4 10 C7 43 ?? ?? ?? ?? ?? C7 43 ?? ?? ?? ?? ?? 8B 43 ?? 8B 53 ?? '
                                                 '8B 8A ?? ?? ?? ?? 8D 55 ?? 89'}

        selected_index                 = {'offset': 12, 'offset_size': 4, 'begin': 0x30000000, 'size': 0x0FFFFFFF,
                                          'aob': '8B 10 8B 48 ?? B8 ?? ?? ?? ?? 89 8A ?? ?? ?? ?? 8B 4D ?? 89 0D ?? '
                                                 '?? ?? ?? 8B E5 ?? C3'}

    class MapSelectUI:
        is_choosing_map                = {'offset': 11, 'offset_size': 1, 'begin': 0x0D800000, 'size': 0x027FFFFF,
                                          'aob': '52 6A ?? 51 FF D0 83 C4 ?? C7 43 ?? ?? ?? ?? ?? C7 43 ?? ?? ?? ?? '
                                                 '?? 8B 43 ?? 8B 53 ?? 8B'}

