"""
Boss respawn data - 208 bosses extracted from CEA script
All boss defeat flags for respawn functionality
Duplicate bosses have location appended to name
"""

# Complete boss data: boss_name -> {flags: [flag_ids], category: region}
BOSSES = {
    # Abyssal Woods (2 bosses)
    "Jori, Elder Inquisitor": {
        "flags": [2052430800, 2052432801, 9161, 510610, 61161, 1161, 76862],
        "category": "Abyssal Woods",
    },
    "Midra, Lord of Frenzied Flame": {
        "flags": [
            28000800,
            28000801,
            9156,
            510560,
            61156,
            72800,
            1156,
            28009211,
            28009212,
        ],
        "category": "Abyssal Woods",
    },
    # Academy of Raya Lucaria (2 bosses)
    "Red Wolf of Radagon": {
        "flags": [14000850, 14000851, 9117, 61117, 60440, 71401, 1117],
        "category": "Academy of Raya Lucaria",
    },
    "Rennala, Queen of the Full Moon": {
        "flags": [
            14000800,
            14000801,
            14000804,
            9118,
            197,
            61118,
            1118,
            71400,
            14008556,
            14009202,
            14009205,
            3371,
            3468,
            3469,
        ],
        "category": "Academy of Raya Lucaria",
    },
    # Altus Plateau (20 bosses)
    "Ancient Dragon Lansseax": {
        "flags": [1037510800, 1037510810, 1041520820, 530300],
        "category": "Altus Plateau",
    },
    "Ancient Hero of Zamor (Altus Plateau)": {
        "flags": [30080800, 9208, 520080, 61208, 1208],
        "category": "Altus Plateau",
    },
    "Black Knife Assassin (Sage's Cave)": {
        "flags": [31190800, 9242, 520420, 61242, 1242],
        "category": "Altus Plateau",
    },
    "Black Knife Assassin (Sainted Hero's Grave)": {
        "flags": [1040520800, 530350],
        "category": "Altus Plateau",
    },
    "Crystalian Duo (Altus Plateau)": {
        "flags": [32050800, 32050801, 9265, 520650, 61265, 1265, 32058590],
        "category": "Altus Plateau",
    },
    "Demi-Human Queen Gilika": {"flags": [1038510800], "category": "Altus Plateau"},
    "Elemer of the Briar": {
        "flags": [1039540800, 9182, 510820, 61182, 1182, 76322],
        "category": "Altus Plateau",
    },
    "Erdtree Burial Watchdog (Altus Plateau)": {
        "flags": [30070800, 9212, 520120, 61212, 1212],
        "category": "Altus Plateau",
    },
    "Fallingstar Beast (Altus Plateau)": {
        "flags": [1041500800, 530310],
        "category": "Altus Plateau",
    },
    "Godefroy the Grafted": {
        "flags": [1039500800, 1039507100],
        "category": "Altus Plateau",
    },
    "Godskin Apostle (Altus Plateau)": {
        "flags": [1042550800, 530325, 76313],
        "category": "Altus Plateau",
    },
    "Necromancer Garris": {
        "flags": [31190850, 9249, 520490, 61249, 1249],
        "category": "Altus Plateau",
    },
    "Night's Cavalry (Altus Plateau)": {
        "flags": [1039510800, 1039517200, 65868],
        "category": "Altus Plateau",
    },
    "Omenkiller & Miranda the Blighted Bloom": {
        "flags": [31180800, 9241, 520410, 61241, 1241],
        "category": "Altus Plateau",
    },
    "Perfumer Tricia & Misbegotten Warrior": {
        "flags": [30120800, 9211, 520110, 61211, 1211],
        "category": "Altus Plateau",
    },
    "Sanguine Noble": {"flags": [1040530800], "category": "Altus Plateau"},
    "Stonedigger Troll (Altus Plateau)": {
        "flags": [32040800, 9263, 520630, 61263, 1263],
        "category": "Altus Plateau",
    },
    "Tibia Mariner (Altus Plateau)": {
        "flags": [1038520800, 530385],
        "category": "Altus Plateau",
    },
    "Tree Sentinel Duo": {"flags": [1041510800, 530335], "category": "Altus Plateau"},
    "Wormface": {"flags": [1041530800, 65000, 65060], "category": "Altus Plateau"},
    # Ancient Ruins of Rauh (2 bosses)
    "Divine Beast Dancing Lion (Ancient Ruins of Rauh)": {
        "flags": [2046460800, 530940],
        "category": "Ancient Ruins of Rauh",
    },
    "Romina, Saint of the Bud": {
        "flags": [2044450800, 9160, 510600, 61160, 1160, 76945, 20010196, 330],
        "category": "Ancient Ruins of Rauh",
    },
    # Bellum Highway (3 bosses)
    "Black Knife Assassin (Bellum Highway)": {
        "flags": [30050850, 9221, 520210, 61221, 1221],
        "category": "Bellum Highway",
    },
    "Cemetery Shade (Bellum Highway)": {
        "flags": [30050800, 9205, 520050, 61205, 1205],
        "category": "Bellum Highway",
    },
    "Night's Cavalry (Bellum Highway)": {
        "flags": [1036480800, 1036487400, 65835],
        "category": "Bellum Highway",
    },
    # Caelid (13 bosses)
    "Cemetery Shade (Caelid)": {
        "flags": [30150800, 9215, 520150, 61215, 1215],
        "category": "Caelid",
    },
    "Commander O'Niel": {"flags": [1049380800, 530405, 76412], "category": "Caelid"},
    "Death Rite Bird (Caelid)": {
        "flags": [1049370850, 1049377110],
        "category": "Caelid",
    },
    "Decaying Ekzykes": {"flags": [1048370800, 530400], "category": "Caelid"},
    "Erdtree Burial Watchdog (Caelid)": {
        "flags": [30140800, 9214, 520140, 61214, 1214],
        "category": "Caelid",
    },
    "Fallingstar Beast (Caelid)": {
        "flags": [32080800, 32080801, 9267, 520670, 61267, 1267, 32088590],
        "category": "Caelid",
    },
    "Frenzied Duelist": {
        "flags": [31210800, 31210801, 9243, 520430, 61243, 1243],
        "category": "Caelid",
    },
    "Mad Pumpkin Head Duo": {"flags": [1048400800], "category": "Caelid"},
    "Magma Wyrm (Caelid)": {
        "flags": [32070800, 32070801, 9266, 520660, 61266, 1266, 32078540],
        "category": "Caelid",
    },
    "Night's Cavalry (Caelid)": {
        "flags": [1049370800, 1049377100, 65874],
        "category": "Caelid",
    },
    "Nox Swordstress & Nox Priest": {
        "flags": [1049390800, 1049397800, 76415],
        "category": "Caelid",
    },
    "Putrid Avatar (Caelid)": {
        "flags": [1047400800, 65100, 65280],
        "category": "Caelid",
    },
    "Putrid Crystallian Trio": {
        "flags": [31110800, 9246, 520460, 61246, 1246],
        "category": "Caelid",
    },
    # Capital Outskirts (7 bosses)
    "Bell Bearing Hunter (Capital Outskirts)": {
        "flags": [1043530800, 1043537400],
        "category": "Capital Outskirts",
    },
    "Crucible Knight & Crucible Knight Ordovis": {
        "flags": [30100800, 9210, 520100, 61210, 1210],
        "category": "Capital Outskirts",
    },
    "Deathbird (Capital Outskirts)": {
        "flags": [1044530800, 1044537300],
        "category": "Capital Outskirts",
    },
    "Draconic Tree Sentinel": {
        "flags": [1045520800, 530315],
        "category": "Capital Outskirts",
    },
    "Fell Twins": {
        "flags": [34140850, 34140851, 34140865, 9174, 510740, 10740, 1174],
        "category": "Capital Outskirts",
    },
    "Grave Warden Duelist (Capital Outskirts)": {
        "flags": [30130800, 9213, 520130, 61213, 1213],
        "category": "Capital Outskirts",
    },
    "Onyx Lord (Capital Outskirts)": {
        "flags": [34120800, 34120801, 9264, 520640, 61264, 1264, 73432, 73430],
        "category": "Capital Outskirts",
    },
    # Cerulean Coast (4 bosses)
    "Dancer of Ranah": {"flags": [2046380800, 530810], "category": "Cerulean Coast"},
    "Demi-Human Queen Marigga": {
        "flags": [2046400800, 530845],
        "category": "Cerulean Coast",
    },
    "Ghostflame Dragon (Cerulean Coast)": {
        "flags": [2048380850, 2048380870, 530840],
        "category": "Cerulean Coast",
    },
    "Putrescent Knight": {
        "flags": [
            22000800,
            22000802,
            9148,
            510480,
            61148,
            1148,
            72200,
            22009208,
            22009222,
        ],
        "category": "Cerulean Coast",
    },
    # Charo's Hidden Grave (2 bosses)
    "Death Rite Bird (Charo's Hidden Grave)": {
        "flags": [2047390800, 530855, 65931],
        "category": "Charo's Hidden Grave",
    },
    "Lamenter": {
        "flags": [41020800, 41020801, 9277, 520770, 61277, 1277],
        "category": "Charo's Hidden Grave",
    },
    # Consecrated Snowfield (8 bosses)
    "Astel, Stars of Darkness": {
        "flags": [32110800, 32110801, 9268, 520680, 61268, 1268, 32110590],
        "category": "Consecrated Snowfield",
    },
    "Death Rite Bird (Consecrated Snowfield)": {
        "flags": [1048570800, 1048577700],
        "category": "Consecrated Snowfield",
    },
    "Great Wyrm Theodorix": {
        "flags": [1050560800, 530550],
        "category": "Consecrated Snowfield",
    },
    "Misbegotten Crusader": {
        "flags": [31120800, 9247, 520470, 61247, 1247],
        "category": "Consecrated Snowfield",
    },
    "Night's Cavalry (Consecrated Snowfield)": {
        "flags": [1248550800, 1048557700, 1048557710],
        "category": "Consecrated Snowfield",
    },
    "Putrid Avatar (Consecrated Snowfield)": {
        "flags": [1050570850, 65130, 65170],
        "category": "Consecrated Snowfield",
    },
    "Putrid Grave Warden Duelist": {
        "flags": [30190800, 9219, 520190, 61219, 1219],
        "category": "Consecrated Snowfield",
    },
    "Stray Mimic Tear": {
        "flags": [30200800, 9220, 520200, 61220, 1220],
        "category": "Consecrated Snowfield",
    },
    # Crumbling Farum Azula (3 bosses)
    "Dragonlord Placidusax": {
        "flags": [13000830, 9115, 510150, 61115, 1115, 71301],
        "category": "Crumbling Farum Azula",
    },
    "Godskin Duo": {
        "flags": [13000850, 13000851, 9114, 510140, 61114, 1114, 65847, 71302],
        "category": "Crumbling Farum Azula",
    },
    "Maliketh, the Black Blade": {
        "flags": [13000800, 13000801, 9116, 510160, 61116, 1116, 71300, 13009205],
        "category": "Crumbling Farum Azula",
    },
    # Enir-Ilim (1 bosses)
    "Promised Consort Radahn": {
        "flags": [20010800, 20010801, 9143, 510430, 61143, 1143, 72010, 128, 20017981],
        "category": "Enir-Ilim",
    },
    # Flame Peak (2 bosses)
    "Ancient Hero of Zamor (Flame Peak)": {
        "flags": [30170800, 9217, 520170, 61217, 1217],
        "category": "Flame Peak",
    },
    "Fire Giant": {
        "flags": [1252520800, 1252520801, 9131, 510310, 61131, 1131, 76509, 76510],
        "category": "Flame Peak",
    },
    # Forbidden Lands (2 bosses)
    "Black Blade Kindred (Forbidden Lands)": {
        "flags": [1049520800, 530505],
        "category": "Forbidden Lands",
    },
    "Night's Cavalry (Forbidden Lands)": {
        "flags": [1048510800, 1048517700, 65870],
        "category": "Forbidden Lands",
    },
    # Gravesite Plain (9 bosses)
    "Ancient Dragon-Man": {
        "flags": [43010800, 9281, 520810, 61281, 1281, 43018540],
        "category": "Gravesite Plain",
    },
    "Chief Bloodfiend": {
        "flags": [43000800, 9280, 520800, 61280, 1280],
        "category": "Gravesite Plain",
    },
    "Death Knight (Gravesite Plain)": {
        "flags": [40000800, 9270, 520700, 61270, 1270],
        "category": "Gravesite Plain",
    },
    "Demi-Human Swordmaster Onze": {
        "flags": [41000800, 9275, 520750, 61275, 1275],
        "category": "Gravesite Plain",
    },
    "Divine Beast Dancing Lion (Gravesite Plain)": {
        "flags": [
            20000800,
            20000801,
            20000544,
            9140,
            510400,
            20007810,
            61140,
            1140,
            72000,
        ],
        "category": "Gravesite Plain",
    },
    "Ghostflame Dragon (Gravesite Plain)": {
        "flags": [2045440800, 2045440820, 530860, 530861],
        "category": "Gravesite Plain",
    },
    "Knight of the Solitary Gaol": {
        "flags": [2046410800, 530820],
        "category": "Gravesite Plain",
    },
    "Red Bear": {"flags": [2046450800, 530900], "category": "Gravesite Plain"},
    "Rellana, Twin Moon Knight": {
        "flags": [2048440800, 9190, 510900, 61190, 1190, 76823],
        "category": "Gravesite Plain",
    },
    # Greyoll's Dragonbarrow (10 bosses)
    "Battlemage Hugues": {
        "flags": [1049390850, 1049397850],
        "category": "Greyoll's Dragonbarrow",
    },
    "Beastman of Farum Azula (Greyoll's Dragonbarrow)": {
        "flags": [31100800, 31100801, 9244, 520440, 61244, 1244],
        "category": "Greyoll's Dragonbarrow",
    },
    "Bell Bearing Hunter (Greyoll's Dragonbarrow)": {
        "flags": [1048410800, 1048417800],
        "category": "Greyoll's Dragonbarrow",
    },
    "Black Blade Kindred (Greyoll's Dragonbarrow)": {
        "flags": [1051430800, 530425],
        "category": "Greyoll's Dragonbarrow",
    },
    "Cleanrot Knight (Greyoll's Dragonbarrow)": {
        "flags": [31200800, 9245, 520450, 61245, 1245],
        "category": "Greyoll's Dragonbarrow",
    },
    "Elder Dragon Greyoll": {
        "flags": [1050400800, 1050400599, 1050407800],
        "category": "Greyoll's Dragonbarrow",
    },
    "Flying Dragon Greyll": {
        "flags": [1052410800, 530420],
        "category": "Greyoll's Dragonbarrow",
    },
    "Godskin Apostle (Greyoll's Dragonbarrow)": {
        "flags": [34130800, 9173, 510730, 61173, 1173],
        "category": "Greyoll's Dragonbarrow",
    },
    "Night's Cavalry (Greyoll's Dragonbarrow)": {
        "flags": [1052410850, 1052417100, 65819],
        "category": "Greyoll's Dragonbarrow",
    },
    "Putrid Avatar (Greyoll's Dragonbarrow)": {
        "flags": [1051400800, 65110, 65260],
        "category": "Greyoll's Dragonbarrow",
    },
    # Jagged Peak (4 bosses)
    "Ancient Dragon Senessax": {
        "flags": [2054390850, 530805],
        "category": "Jagged Peak",
    },
    "Bayle, the Dread": {
        "flags": [2054390800, 2054390801, 9163, 510630, 61163, 1163, 76853],
        "category": "Jagged Peak",
    },
    "Jagged Peak Drake": {"flags": [2049410800, 530850], "category": "Jagged Peak"},
    "Jagged Peak Drake Duo": {
        "flags": [2052400800, 530800, 2048429205, 4267, 4268, 2052409206, 2052409207],
        "category": "Jagged Peak",
    },
    # Leyndell, Capital of Ash (3 bosses)
    "Elden Beast": {
        "flags": [
            19000800,
            19000801,
            19000804,
            19001100,
            9123,
            510230,
            61123,
            1123,
            71900,
            9400,
            9401,
            9402,
            9403,
            9404,
            9405,
            9406,
            9407,
            120,
        ],
        "category": "Leyndell, Capital of Ash",
    },
    "Hoarah Loux, Warrior": {
        "flags": [11050800, 11050801, 9107, 510070, 61107, 1107, 71120],
        "category": "Leyndell, Capital of Ash",
    },
    "Sir Gideon Ofnir, the All-Knowing": {
        "flags": [11050850, 11050851, 9106, 510060, 61106, 1106, 71121],
        "category": "Leyndell, Capital of Ash",
    },
    # Leyndell, Royal Capital (4 bosses)
    "Esgar, Priest of Blood": {
        "flags": [35000850, 9222, 520220, 61222, 1222],
        "category": "Leyndell, Royal Capital",
    },
    "Godfrey, First Elden Lord": {
        "flags": [11000850, 11000851, 9105, 60520, 61105, 1105, 71101],
        "category": "Leyndell, Royal Capital",
    },
    "Mohg, the Omen": {
        "flags": [35000800, 35000801, 9125, 510250, 61125, 1125, 35000820, 73500],
        "category": "Leyndell, Royal Capital",
    },
    "Morgott, the Omen King": {
        "flags": [
            11000800,
            11000801,
            9104,
            510040,
            61104,
            1104,
            11009405,
            11009406,
            11000500,
            11000501,
            9000,
            71100,
            400001,
        ],
        "category": "Leyndell, Royal Capital",
    },
    # Limgrave (14 bosses)
    "Beastman of Farum Azula (Limgrave)": {
        "flags": [31030800, 9233, 520330, 61233, 1233],
        "category": "Limgrave",
    },
    "Bloodhound Knight Darriwil": {
        "flags": [1044350800, 530130],
        "category": "Limgrave",
    },
    "Demi-Human Chiefs": {
        "flags": [31150800, 31150815, 9234, 520340, 60140, 61234, 1234],
        "category": "Limgrave",
    },
    "Erdtree Burial Watchdog (Limgrave)": {
        "flags": [30020800, 9202, 520020, 61202, 1202],
        "category": "Limgrave",
    },
    "Flying Dragon Agheel": {
        "flags": [1043360800, 1043360340, 530110],
        "category": "Limgrave",
    },
    "Grave Warden Duelist (Limgrave)": {
        "flags": [30040800, 9204, 520040, 61204, 1204],
        "category": "Limgrave",
    },
    "Guardian Golem": {
        "flags": [31170800, 9235, 520350, 61235, 1235],
        "category": "Limgrave",
    },
    "Mad Pumpkin Head": {"flags": [1044360800, 76120], "category": "Limgrave"},
    "Night's Cavalry (Limgrave)": {
        "flags": [1043370800, 1043377400, 65813],
        "category": "Limgrave",
    },
    "Soldier of Godrick": {"flags": [18000850], "category": "Limgrave"},
    "Stonedigger Troll (Limgrave)": {
        "flags": [32010800, 32010801, 32018590, 9261, 520610, 61261, 1261],
        "category": "Limgrave",
    },
    "Tibia Mariner (Limgrave)": {"flags": [1045390800, 530170], "category": "Limgrave"},
    "Tree Sentinel": {"flags": [1042360800, 530100], "category": "Limgrave"},
    "Ulcerated Tree Spirit (Limgrave)": {
        "flags": [18000800, 9128, 510280, 61128, 1128],
        "category": "Limgrave",
    },
    # Liurnia of the Lakes (21 bosses)
    "Adan, Thief of Fire": {
        "flags": [1038410800, 530245],
        "category": "Liurnia of the Lakes",
    },
    "Bell Bearing Hunter (Liurnia of the Lakes)": {
        "flags": [1037460800, 1037467400],
        "category": "Liurnia of the Lakes",
    },
    "Bloodhound Knight": {
        "flags": [31050800, 31050801, 9237, 520370, 61237, 1237],
        "category": "Liurnia of the Lakes",
    },
    "Bols, Carian Knight": {
        "flags": [1033450800, 530250],
        "category": "Liurnia of the Lakes",
    },
    "Cleanrot Knight (Liurnia of the Lakes)": {
        "flags": [31040800, 9236, 520360, 61236, 1236],
        "category": "Liurnia of the Lakes",
    },
    "Crystalian": {
        "flags": [32020800, 9262, 520620, 61262, 1262],
        "category": "Liurnia of the Lakes",
    },
    "Crystalian Duo (Liurnia of the Lakes)": {
        "flags": [31060800, 9238, 520380, 61238, 1238],
        "category": "Liurnia of the Lakes",
    },
    "Death Rite Bird (Liurnia of the Lakes)": {
        "flags": [1036450800, 1036457400],
        "category": "Liurnia of the Lakes",
    },
    "Deathbird (Liurnia of the Lakes)": {
        "flags": [1037420800, 1037427400],
        "category": "Liurnia of the Lakes",
    },
    "Erdtree Avatar (NE)": {
        "flags": [1038480800, 65290, 65300, 65310],
        "category": "Liurnia of the Lakes",
    },
    "Erdtree Avatar (SW)": {
        "flags": [1033430800, 65040, 65160],
        "category": "Liurnia of the Lakes",
    },
    "Erdtree Burial Watchdog (Liurnia of the Lakes)": {
        "flags": [30060800, 9207, 520070, 61207, 1207],
        "category": "Liurnia of the Lakes",
    },
    "Glintstone Dragon Smarag": {
        "flags": [1034450800, 530210],
        "category": "Liurnia of the Lakes",
    },
    "Magma Wyrm Makar": {
        "flags": [39200800, 39200801, 9126, 510260, 61126, 73900, 1126],
        "category": "Liurnia of the Lakes",
    },
    "Night's Cavalry (Liurnia of the Lakes)": {
        "flags": [1039430800, 1039437400, 65882],
        "category": "Liurnia of the Lakes",
    },
    "Omenkiller": {"flags": [1035420800, 530225], "category": "Liurnia of the Lakes"},
    "Onyx Lord (Liurnia of the Lakes)": {
        "flags": [1036500800, 530255],
        "category": "Liurnia of the Lakes",
    },
    "Royal Knight Loretta": {
        "flags": [1035500800, 1035500801, 9181, 510810, 61181, 65852, 76232, 1181],
        "category": "Liurnia of the Lakes",
    },
    "Royal Revenant": {"flags": [1034480800], "category": "Liurnia of the Lakes"},
    "Spirit-Caller Snail (Liurnia of the Lakes)": {
        "flags": [30030800, 9206, 520060, 61206, 1206],
        "category": "Liurnia of the Lakes",
    },
    "Tibia Mariner (Liurnia of the Lakes)": {
        "flags": [1039440800, 530240],
        "category": "Liurnia of the Lakes",
    },
    # Miquella's Haligtree (2 bosses)
    "Lorretta, Knight of the Haligtree": {
        "flags": [15000850, 15000851, 9119, 510190, 61119, 1119, 71505],
        "category": "Miquella's Haligtree",
    },
    "Malenia, Blade of Miquella": {
        "flags": [15000800, 15000801, 9120, 510200, 61120, 1120, 71500],
        "category": "Miquella's Haligtree",
    },
    # Moonlight Altar (2 bosses)
    "Alecto, Black Knife Ringleader": {
        "flags": [1033420800, 530265],
        "category": "Moonlight Altar",
    },
    "Glintstone Dragon Adula": {
        "flags": [1034420800, 1034420800, 530260],
        "category": "Moonlight Altar",
    },
    # Mountaintops of the Giants (7 bosses)
    "Borealis the Freezing Fog": {
        "flags": [1254560800, 530510],
        "category": "Mountaintops of the Giants",
    },
    "Commander Niall": {
        "flags": [1051570800, 1051570801, 9184, 510840, 61184, 1184, 76524],
        "category": "Mountaintops of the Giants",
    },
    "Death Rite Bird (Mountaintops of the Giants)": {
        "flags": [1050570800, 530530],
        "category": "Mountaintops of the Giants",
    },
    "Erdtree Avatar (Mountaintops of the Giants)": {
        "flags": [1052560800, 65050, 65070],
        "category": "Mountaintops of the Giants",
    },
    "Roundtable Knight Vyke": {
        "flags": [1053560800, 530515],
        "category": "Mountaintops of the Giants",
    },
    "Spirit-Caller Snail (Mountaintops of the Giants)": {
        "flags": [31220800, 9248, 520480, 61248, 1248],
        "category": "Mountaintops of the Giants",
    },
    "Ulcerated Tree Spirit (Mountaintops of the Giants)": {
        "flags": [30180800, 30180801, 9218, 520180, 61218, 1218],
        "category": "Mountaintops of the Giants",
    },
    # Mt. Gelmir (7 bosses)
    "Demi-Human Queen Maggie": {"flags": [1037530800, 60450], "category": "Mt. Gelmir"},
    "Demi-Human Queen Margot": {
        "flags": [1037530800, 9240, 520400, 61240, 1240],
        "category": "Mt. Gelmir",
    },
    "Full-Grown Fallingstar Beast": {
        "flags": [1036540800, 530375],
        "category": "Mt. Gelmir",
    },
    "Kindred of Rot Duo": {
        "flags": [31070800, 31070801, 9239, 520390, 61239, 1239],
        "category": "Mt. Gelmir",
    },
    "Magma Wyrm (Mt. Gelmir)": {
        "flags": [1035530800, 530390],
        "category": "Mt. Gelmir",
    },
    "Red Wolf of the Champion": {
        "flags": [30090800, 9209, 520090, 61209, 1209],
        "category": "Mt. Gelmir",
    },
    "Ulcerated Tree Spirit (Mt. Gelmir)": {
        "flags": [1037540810, 65180, 65250],
        "category": "Mt. Gelmir",
    },
    # Rauh Base (2 bosses)
    "Death Knight (Rauh Base)": {
        "flags": [40010800, 9271, 520710, 61271, 1271],
        "category": "Rauh Base",
    },
    "Rugalea the Great Red Bear": {
        "flags": [2044470800, 530905],
        "category": "Rauh Base",
    },
    # Redmane Castle (3 bosses)
    "Crucible Knight & Misbegotten Warrior": {
        "flags": [1051360800, 9183, 510830, 61183, 1183, 76419],
        "category": "Redmane Castle",
    },
    "Putrid Tree Spirit": {
        "flags": [30160800, 9216, 510260, 61216, 1216],
        "category": "Redmane Castle",
    },
    "Starscourge Radahn": {
        "flags": [
            1252380800,
            1252380801,
            9130,
            510300,
            61130,
            1130,
            3613,
            3668,
            76422,
            310,
            73016,
            910,
            9414,
            9415,
            9416,
            9417,
        ],
        "category": "Redmane Castle",
    },
    # Scadu Altus (9 bosses)
    "Black Knight Edreed": {
        "flags": [2049430850, 530965, 65911],
        "category": "Scadu Altus",
    },
    "Black Knight Garrew": {"flags": [2047450800, 530955], "category": "Scadu Altus"},
    "Count Ymir, Mother of Fingers": {
        "flags": [2051450800, 400664],
        "category": "Scadu Altus",
    },
    "Curseblade Labirith": {
        "flags": [41010800, 9276, 520760, 61276, 1276],
        "category": "Scadu Altus",
    },
    "Dryleaf Dane": {
        "flags": [2049440800, 2049449211, 400730],
        "category": "Scadu Altus",
    },
    "Ghostflame Dragon (Scadu Altus)": {
        "flags": [2049430800, 530945],
        "category": "Scadu Altus",
    },
    "Metyr, Mother of Fingers": {
        "flags": [25000800, 25000801, 9155, 510550, 61155, 1155, 72500],
        "category": "Scadu Altus",
    },
    "Rakshasa": {"flags": [2051440800, 530830], "category": "Scadu Altus"},
    "Ralva the Great Red Bear": {
        "flags": [2049450800, 530930],
        "category": "Scadu Altus",
    },
    # Scaduview (4 bosses)
    "Commander Gaius": {
        "flags": [2049480800, 2049480801, 9164, 510640, 61164, 1164, 76930],
        "category": "Scaduview",
    },
    "Fallingstar Beast (Scaduview)": {
        "flags": [2052480800, 530960],
        "category": "Scaduview",
    },
    "Tree Sentinel (Ambush)": {"flags": [2050470800, 530935], "category": "Scaduview"},
    "Tree Sentinel (Exposed)": {"flags": [2050480860, 530950], "category": "Scaduview"},
    # Shadow Keep (3 bosses)
    "Golden Hippopotamus": {
        "flags": [21000850, 21000851, 9144, 510440, 61144, 1144, 72101],
        "category": "Shadow Keep",
    },
    "Messmer the Impaler": {
        "flags": [
            21010800,
            21010801,
            9146,
            510460,
            61146,
            1146,
            21018542,
            72110,
            4368,
            2048459225,
        ],
        "category": "Shadow Keep",
    },
    "Scadutree Avatar": {
        "flags": [2050480800, 2050480801, 9162, 510620, 61162, 1162, 76960],
        "category": "Shadow Keep",
    },
    # Stormhill (5 bosses)
    "Bell Bearing Hunter (Stormhill)": {
        "flags": [1042380850, 1042387410],
        "category": "Stormhill",
    },
    "Black Knife Assassin (Stormhill)": {
        "flags": [30110800, 9203, 520030, 61203, 1203],
        "category": "Stormhill",
    },
    "Crucible Knight": {"flags": [1042370800, 530120], "category": "Stormhill"},
    "Deathbird (Stormhill)": {
        "flags": [1042380800, 1042387400],
        "category": "Stormhill",
    },
    "Margit, the Fell Omen": {
        "flags": [10000850, 10000851, 9100, 61100, 60510, 71001, 1100],
        "category": "Stormhill",
    },
    # Stormveil Castle (2 bosses)
    "Godrick the Grafted": {
        "flags": [10000800, 10000801, 9101, 510010, 61101, 3269, 10008540, 71000, 1101],
        "category": "Stormveil Castle",
    },
    "Grafted Scion": {
        "flags": [10010800, 10010801, 101, 9103, 510030, 61103, 1103],
        "category": "Stormveil Castle",
    },
    # Underground (12 bosses)
    "Ancestor Spirit": {
        "flags": [
            12080800,
            9132,
            510320,
            61132,
            1132,
            12020600,
            12020601,
            12020602,
            12020603,
            12020604,
            12020605,
            12020606,
            12020607,
            12020609,
        ],
        "category": "Underground",
    },
    "Astel, Naturalborn of the Void": {
        "flags": [12040800, 9108, 510080, 61108, 1108, 71240],
        "category": "Underground",
    },
    "Crucible Knight Siluria": {
        "flags": [12030390, 12037950],
        "category": "Underground",
    },
    "Dragonkin Soldier (Lake of Rot)": {
        "flags": [12010850, 530600],
        "category": "Underground",
    },
    "Dragonkin Soldier (Siofra River)": {
        "flags": [12020830, 530620],
        "category": "Underground",
    },
    "Dragonkin Soldier of Nokstella": {
        "flags": [12010800, 12010801, 9109, 510090, 61109, 1109, 71210],
        "category": "Underground",
    },
    "Fia's Champions": {
        "flags": [
            12030800,
            12030801,
            9135,
            510350,
            61135,
            1135,
            71230,
            4128,
            4129,
            4130,
            4131,
            4132,
            4066,
        ],
        "category": "Underground",
    },
    "Lichdragon Fortissax": {
        "flags": [
            12030850,
            12030852,
            9111,
            510110,
            61111,
            1111,
            4130,
            4131,
            4132,
            4066,
            4120,
            4123,
        ],
        "category": "Underground",
    },
    "Mimic Tear": {
        "flags": [12020850, 12020851, 9134, 510340, 91134, 1134, 71221],
        "category": "Underground",
    },
    "Mohg, Lord of Blood": {
        "flags": [12050800, 12050801, 9112, 510120, 61112, 1112, 71250, 12059261],
        "category": "Underground",
    },
    "Regal Ancestor Spirit": {
        "flags": [
            12090800,
            9133,
            510330,
            91133,
            1133,
            12020620,
            12020621,
            12020622,
            12020623,
            12020624,
            12020625,
            12020629,
        ],
        "category": "Underground",
    },
    "Valiant Gargoyles": {
        "flags": [12020800, 12020801, 9110, 510100, 61110, 1110, 71220, 65840],
        "category": "Underground",
    },
    # Volcano Manor (3 bosses)
    "Abductor Virgins": {
        "flags": [16000860, 9129, 510290, 61129, 1219],
        "category": "Volcano Manor",
    },
    "Godskin Noble": {
        "flags": [
            16000850,
            16000851,
            9121,
            510210,
            61121,
            1121,
            71601,
            16000520,
            16001520,
        ],
        "category": "Volcano Manor",
    },
    "Rykard, Lord of Blasphemy": {
        "flags": [
            16000800,
            16000801,
            9122,
            510220,
            61122,
            1122,
            71600,
            3109,
            3110,
            3111,
            16009265,
            16009264,
            16009268,
        ],
        "category": "Volcano Manor",
    },
    # Weeping Peninsula (10 bosses)
    "Ancient Hero of Zamor (Weeping Peninsula)": {
        "flags": [1042330800, 1042337100],
        "category": "Weeping Peninsula",
    },
    "Cemetery Shade (Weeping Peninsula)": {
        "flags": [30000800, 9200, 520000, 61200, 1200],
        "category": "Weeping Peninsula",
    },
    "Deathbird (Weeping Peninsula)": {
        "flags": [1044320800, 1044327400],
        "category": "Weeping Peninsula",
    },
    "Erdtree Avatar (Weeping Peninsula)": {
        "flags": [1043330800, 65080, 65090],
        "category": "Weeping Peninsula",
    },
    "Erdtree Burial Watchdog (Weeping Peninsula)": {
        "flags": [30010800, 9201, 520010, 61201, 1201],
        "category": "Weeping Peninsula",
    },
    "Leonine Misbegotten": {
        "flags": [1043300800, 9180, 510800, 61180, 76161, 1180],
        "category": "Weeping Peninsula",
    },
    "Miranda the Blighted Bloom": {
        "flags": [31020800, 9230, 520300, 61230, 1230],
        "category": "Weeping Peninsula",
    },
    "Night's Cavalry (Weeping Peninsula)": {
        "flags": [1044320850, 1044327410, 65888],
        "category": "Weeping Peninsula",
    },
    "Runebear": {
        "flags": [31010800, 31010801, 9231, 520310, 61231, 1231],
        "category": "Weeping Peninsula",
    },
    "Scaly Misbegotten": {
        "flags": [32000800, 32000801, 32000590, 9260, 520600, 61260, 1260],
        "category": "Weeping Peninsula",
    },
}

# All unique categories
BOSS_CATEGORIES = [
    "Abyssal Woods",
    "Academy of Raya Lucaria",
    "Altus Plateau",
    "Ancient Ruins of Rauh",
    "Bellum Highway",
    "Caelid",
    "Capital Outskirts",
    "Cerulean Coast",
    "Charo's Hidden Grave",
    "Consecrated Snowfield",
    "Crumbling Farum Azula",
    "Enir-Ilim",
    "Flame Peak",
    "Forbidden Lands",
    "Gravesite Plain",
    "Greyoll's Dragonbarrow",
    "Jagged Peak",
    "Leyndell, Capital of Ash",
    "Leyndell, Royal Capital",
    "Limgrave",
    "Liurnia of the Lakes",
    "Miquella's Haligtree",
    "Moonlight Altar",
    "Mountaintops of the Giants",
    "Mt. Gelmir",
    "Rauh Base",
    "Redmane Castle",
    "Scadu Altus",
    "Scaduview",
    "Shadow Keep",
    "Stormhill",
    "Stormveil Castle",
    "Underground",
    "Volcano Manor",
    "Weeping Peninsula",
]


def get_bosses_by_category(category: str) -> list:
    """Get all bosses in a category"""
    return [name for name, data in BOSSES.items() if data["category"] == category]


def get_boss_flags(boss_name: str) -> list:
    """Get flag IDs for a boss"""
    return BOSSES.get(boss_name, {}).get("flags", [])
