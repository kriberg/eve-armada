from armada.lib.api.common import *

def get_alliance_list():
    return get_list('eve', 'AllianceList')

def get_corporation_sheet(corporationID):
    return get_list('corp', 'CorporationSheet',
            corporationID=corporationID)

def get_character_sheet(characterID):
    return get_list('eve', 'CharacterInfo',
            characterID=characterID)

def get_names_to_ids(names):
    result = get_list_uncached('eve', 'CharacterID', names=names)
    name_map = {}
    for row in result.characters:
        name_map[row.name] = row.characterID
    return name_map

def get_conquerable_station_list():
    return get_list('eve', 'ConquerableStationList')


if __name__ == '__main__':
    l = get_alliance_list()
