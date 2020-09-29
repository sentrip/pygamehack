import pygamehack as gh
from pygamehack_utils import HackStruct, Ptr
from pygamehack_utils.aob import aob_scan
from pygamehack_extensions.raw_string import const_c_str
from pygamehack_extensions.haxe_flash import HaxeVector


HackStruct.set_architecture(32)

static_addresses = [
    ('steam_root', 'SteamAir.dll', 0x000CCF08),
]

dynamic_addresses = [
    ('game', 'steam_root', [0x4C, 0x228, 0x14, 0x18C]),
    ('game_data_thing', 'steam_root', [0xC, 0x3C, 0x0]),
]


class LegendSkins(metaclass=HackStruct):
    is_unlocked: gh.uint = 0x28  # ???????
    legend_id: gh.uint = 0x30
    skin_1_name: const_c_str = [0x6C, 0x1C, 0x8]
    skin_2_name: const_c_str = [0x70, 0x1C, 0x8]


class LegendSkin(metaclass=HackStruct):
    name: const_c_str = [0x1C, 0x8]
    skins_ptr: Ptr[LegendSkins] = 0x4C


class LegendSelection(metaclass=HackStruct):
    is_locked_in: gh.uint = 0x14
    legend_id: gh.uint = 0x3C
    legend_color: gh.uint = 0x54
    legend_skins: Ptr[LegendSkins] = 0x68
    legend_skins_w: gh.uint = 0x68


class Game(metaclass=HackStruct):
    address = 'game'
    legend_selection_list: HaxeVector[LegendSelection, 8] = [0x524, 0x98]


class GameDataThing(metaclass=HackStruct):
    address = 'game_data_thing'
    skins: HaxeVector[LegendSkin, 994] = 0xB4


HackStruct.define_types()


hack = gh.Hack('Brawlhalla.exe')
hack.architecture = 32

for name, module, off in static_addresses:
    hack.add_static_address(name, module, off)

for name, depends_on, offs in dynamic_addresses:
    hack.add_dynamic_address(name, depends_on, offs)

hack.attach()

modules = hack.get_modules()

adobe_begin, adobe_size = modules['Adobe AIR.dll']

main_menu_aob = '8B 45 ?? 8B 10 8B 48 ?? B8 ?? ?? ?? ?? 89 8A '\
                '?? ?? ?? ?? 8B 4D ?? 89 0D ?? ?? ?? ?? 8B E5 ?? C3'

print(hex(aob_scan(hack, main_menu_aob, group=3, offset_size=4, begin=0x30000000, size=128 * 1024 * 1024)))


# game = Game(hack)
# game_data = GameDataThing(hack)
#
# hack.load_addresses()
# game.legend_selection_list.read_contents()
# game_data.skins.read_contents()
#
# hack.load_addresses()
# game.legend_selection_list.read_contents()
# game_data.skins.read_contents()
#
# id_to_skins = {}
# id_to_index = {}
# index_to_id = {}
# name_to_skin = {}
#
# for i, skin in enumerate(game_data.skins):
#     id_to_index[skin.skins_ptr.legend_id] = i
#     index_to_id[i] = skin.skins_ptr.legend_id
#     id_to_skins[skin.skins_ptr.legend_id] = skin.skins_ptr
#
#     try:
#         name_to_skin[skin.skins_ptr.skin_1_name] = skin
#     except UnicodeDecodeError:
#         continue
#     try:
#         name_to_skin[skin.skins_ptr.skin_2_name] = skin
#     except UnicodeDecodeError:
#         continue
#
#
# print(len(name_to_skin))
#
# garnet = name_to_skin['OrbGarnet']
# garnet_legend_id = garnet.skins_ptr.legend_id
# garnet_skin_address = garnet.variables['skins_ptr'].address.address
# nam = []
# for name in name_to_skin:
#     if 'Fists' in name or 'Orb' in name:
#         part = name.replace('Fists', '').replace('Orb', '')
#         opposite = 'Fists' if name.startswith('Orb') else 'Orb'
#         if name_to_skin.get(opposite + part, None):
#             print(name)
#
# # Unlock skin
# #garnet.skins_ptr.is_unlocked = 1
# # Write legend id
# #game.legend_selection_list[0].legend_id = garnet_legend_id
# # Write skin pointer
# #game.legend_selection_list[0].legend_skins_w = garnet_skin_address
