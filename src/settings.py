category_id_to_alias_map = {
    'geo': 20,
    'geography': 20,
    'hist': 18,
    'history': 18,
    'lit': 15,
    'literature': 15,
    'm': 14,
    'myth': 14,
    'p': 25,
    'philo': 25,
    'r': 19,
    'religion': 19,
    'sci': 17,
    'science': 17,
    'ss': 22,
    'socialscience': 22,
    'trash': 16,
    'ce': 26,
    'currentevents': 26,
    'fa': 21,
    'finearts': 21
}

subcategory_id_to_alias_map = {
    'bio': 14,
    'biology': 14,
    'chem': 5,
    'chemistry': 5,
    'cs': 23,
    'math': 26,
    'physics': 18,
    'eurolit': 1,
    'vfa': 2,
    'vfinearts': 2,
    'amlit': 3,
    'americanlit': 3,
    'britishhist': 6,
    'afa': 8,
    'auditoryfa': 8,
    'othersci': 10,
    'americanhist': 13,
    'amhist': 13,
    'classicalhist': 16,
    'worldhist': 20,
    'britishlit': 22,
    'europeanhist': 24,
    'otherfa': 25,
    'avfa': 27,
    'audiovisualfa': 27,
    'otherhist': 28,
    'otherlit': 29,
    'classicallit': 30,
    'amreligion': 31,
    'amtrash': 32,
    'ammyth': 33,
    'amss': 34,
    'americansocialscience': 34,
    'amfa': 35,
    'americanfa': 35,
    'amscience': 36,
    'amsci': 36,
    'worldsci': 37,
    'amgeo': 38,
    'amphilo': 39,
    'amce': 40,
    'otherce': 42,
    'worldfa': 43,
    'worldgeo': 44,
    'britfa': 45,
    'indianmyth': 46,
    'chinesemyth': 47,
    'othereastasianmyth': 49,
    'japanesemyth': 48,
    'eurofa': 50,
    'eastasianreligion': 51,
    'eastasianphilo': 52,
    'videogames': 53,
    'othermyth': 54,
    'sports': 55,
    'economics': 56,
    'christianity': 57,
    'grecoromanmyth': 58,
    'othertrash': 59,
    'otherss': 60,
    'classicalphilo': 61,
    'worldlit': 12,
    'otherreligion': 62,
    'norsemyth': 63,
    'polisci': 64,
    'egyptianmyth': 65,
    'europhilo': 66,
    'music': 67,
    'islam': 68,
    'judaism': 69,
    'tv': 70,
    'psych': 71,
    'movies': 72,
    'sociology': 73,
    'otherphilo': 74,
    'linguistics': 75,
    'anthro': 76,
    'opera': 77
}

def get_categories():
    return category_id_to_alias_map

def get_subcategories():
    return subcategory_id_to_alias_map

class GlobalState:
    sessions = []
    skip_message = None

state = GlobalState()

def get_global_state():
    global state
    return state

tournament_to_alias_map = {'scop': 'scop', 'pace': 'pace', 'rmbat': 'rmbat', 'bhsat': 'bhsat', 'acf_regs': 'acf regionals', 'acf_fall': 'acf fall', 'co': 'chicago open'}
tournament_id_to_alias_map = {} # make this

def get_tournaments():
    return tournament_to_alias_map

def parse_arguments(arguments):
    difficulties = []
    categories = []
    subcategories = []
    selected_tournaments = []

    for arg in arguments:
        if arg[0].isdigit():
            # Difficulty or year
            # Check if range
            if len(arg.split('-')) > 1:
                values = arg.split('-')
                difficulties = list(range(int(values[0]), int(values[1]) + 1))
            elif 0 < int(arg) < 10:
                difficulties = [int(arg)]
            else:
                # assume year
                if selected_tournaments[-1][1] == -1:
                    selected_tournaments[-1] = (selected_tournaments[-1][0], int(arg))
        else:
            # Category, subcategory, or tournament
            if arg in subcategory_id_to_alias_map:
                subcategories.append(str(subcategory_id_to_alias_map[arg]))
            if arg in category_id_to_alias_map:
                categories.append(str(category_id_to_alias_map[arg]))
            if arg in tournament_id_to_alias_map:
                selected_tournaments.append((tournament_id_to_alias_map[arg], -1))

    return difficulties, categories, subcategories, selected_tournaments