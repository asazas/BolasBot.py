import yaml     # pip install pyyaml

import pyz3r    # pip install pyz3r

async def crea_seed_con_settings(my_settings):
    seed = await pyz3r.alttpr(settings=my_settings['settings'])
    return seed

if __name__ == "__main__":
    with open("rando-settings/tournament.yaml") as settings_file:
        settings = yaml.load(settings_file, Loader=yaml.FullLoader)
        print(settings)