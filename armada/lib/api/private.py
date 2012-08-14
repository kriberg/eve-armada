from armada.lib.api.common import *

def get_account_characters(keyID, vCode):
    return get_list('account', 'Characters', keyID=keyID, vCode=vCode)

def get_character_sheet(keyID, vCode, characterID):
    return get_list('char', 'CharacterSheet',
            keyID=keyID, vCode=vCode, characterID=characterID)

def get_character_asset_list(keyID, vCode, characterID):
    return get_list('char', 'AssetList',
            keyID=keyID, vCode=vCode, characterID=characterID)
