import struct
MAPS = {
    "00001":"Bakisi Isles",
    "00010":"Hoven Gorge",
    "00011":"Outpost x12",
    "00100":"Korgon Outpost",
    "00101":"Metropolis",
    "00110":"Blackwater City",
    "00111":"Command Center",
    "01001":'Aquatos Sewers',
    "01000": "Blackwater Dox",
    "01010":"Marcadia Palace",
}


def try_parse_value(func, num):
    try:
        return func(num)
    except:
        return func(num+2**32)

def mapParser(num):

    def internal_parser(num):
        '''Accepts generic_field_3 INTEGER number (which is 4 a byte long hex string)'''
        num = int(num) if type(num) != 'int' else num
        num = struct.pack('<I', num).hex()
        num=num[0:2]
        num = int(num,16)
        num = format(num, "#010b")[2:]
        game_map = num[:5]
        game_map = MAPS[game_map]
        return game_map

    try:
        val = try_parse_value(internal_parser, num)
    except:
        val = 'Unknown map!' 

    return val


TIME = {
    '000':'No Time Limit',
    '001':"5 Minutes",
    '010':"10 Minutes",
    '011':"15 Minutes",
    "100":"20 Minutes",
    "101":"25 Minutes",
    "110":"30 Minutes",
    "111":"35 Minutes",
}

def timeParser(num):
    def internal_parser(num):

        '''Accepts generic_field_3 INTEGER number (which is 4 a byte long hex string)'''
        num = int(num) if type(num) != 'int' else num
        num = struct.pack('<I', num).hex()
        num=num[0:2]
        num = int(num,16)
        num = format(num, "#010b")[2:]
        game_time = num[5:]
        game_time = TIME[game_time]
        return game_time

    try:
        val = try_parse_value(internal_parser, num)
    except:
        val = 'Unknown Time!' 

    return val

MODE={ #3,4
    '00':"Siege",
    '01':"CTF",
    '10':"Deathmatch"
}
SUBMODES = {
    # '1':"no_teams", #13
    # "1":"base_attrition" #20
    'isTeams':13, #1 = yes, means u can swap teams only 0 in DM
    "isAttrition":20, #1 = yes #consitutes also as chaos ctf
}


def gamerulesParser(num):
    def internal_parser(num):
        '''Accepts generic_field_3 INTEGER number (which is 4 a byte long hex string)
        returns game MODE andd game SUBMODE/ type'''
        num = int(num) if type(num) != 'int' else num
        num = struct.pack('<I', num).hex()
        num=num[2:] #cut off the front 2 bytes
        num = int(num,16)
        num = format(num, "#026b")[2:]
        game_mode = MODE[num[3:5]] if num[3:5] in MODE else "Unknown Game Mode"
        isTeams = True if num[SUBMODES['isTeams']] == '1' else False
        isAttrition = True if num[SUBMODES['isAttrition']]== '1' else False

        if game_mode == MODE['00']:
            game_type = "Attrition" if isAttrition else "Normal"
        elif game_mode == MODE['01']:
            game_type = "Chaos" if isAttrition else "Normal"
        elif game_mode == MODE['10']:
            game_type = "Teams" if isTeams else "FFA"
        else:
            game_type = "Game Type Not Found"
        return game_mode, game_type
    try:
        game_mode, game_type = try_parse_value(internal_parser, num)
    except:
        game_mode, game_type = 'Unkown Game Mode', 'Unknown Game Type'

    return game_mode, game_type

import struct
OTHER_RULES = {
    'base_defenses' : 19,
    "spawn_charge_boots":18,
    'spawn_weapons':17,
    'unlimited_ammo':16,
    "player_names":9,
    "vehicles":1,
}

def advancedRulesParser(num):
    '''Accepts generic_field_3 INTEGER number (which is 4 a byte long hex string)
    returns game MODE andd game SUBMODE/ type'''
    advanced_rules = {}
    num = int(num) if type(num) != 'int' else num
    num = struct.pack('<I', num).hex()
    num=num[2:] #cut off the front 2 bytes
    num = int(num,16)
    num = format(num, "#026b")[2:]
    advanced_rules['baseDefenses'] = True if num[OTHER_RULES['base_defenses']] == '1' else False
    advanced_rules['spawn_charge_boots'] = True if num[OTHER_RULES['spawn_charge_boots']] == '1' else False
    advanced_rules['spawn_weapons'] = True if num[OTHER_RULES['spawn_weapons']] == '1' else False
    advanced_rules["player_names"] = True if num[OTHER_RULES["player_names"]] == '1' else False
    advanced_rules['vehicles'] = True if num[OTHER_RULES['vehicles']] == '0' else False
    return advanced_rules


weapons = {
    0:"Lava Gun",
    1:"Morph O' Ray",
    2:"Mines",
    3:"Gravity Bomb",
    4:"Rockets",
    5:"Blitz",
    6:"N60",
    7:"Flux"
}

def weaponParserNew(num:int):
    try:
        num = format(num, "#010b")[-8:]
        res = []
        for i in range(len(num)-1, -1, -1):
            if num[i] == "0":
                res.append(weapons[i])
        return 'Weapons: ' + ', '.join(res)
    except:
        return 'Unknown weapons!'