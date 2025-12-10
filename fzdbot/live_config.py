import os

EVENT_IDS_GGP7=os.getenv("EVENT_IDS_GGP7").split()
print(EVENT_IDS_GGP7)

USER_IDS_CLASSIC=os.getenv("USER_IDS_CLASSIC")
USER_IDS_ALLIN=os.getenv("USER_IDS_ALLIN")    
USER_ID_PACHINKO=os.getenv("USER_ID_PACHINKO")
USER_ID_ROULETTE=os.getenv("USER_ID_ROULETTE")

THREAD_IDS_CLASSIC=os.getenv("THREAD_IDS_CLASSIC")
THREAD_IDS_ALLIN=os.getenv("THREAD_IDS_ALLIN") 
THREAD_ID_PACHINKO=os.getenv("THREAD_ID_PACHINKO")
THREAD_ID_ROULETTE=os.getenv("THREAD_ID_ROULETTE")

DIVISIONS_CLASSIC="novice master expert standard"
DIVISIONS_ALLIN="master expert"

DIVISION_DICT = [
    {"id": EVENT_IDS_GGP7[0], "thread_ids": THREAD_IDS_CLASSIC, "user_ids": USER_IDS_CLASSIC, "divisions": DIVISIONS_CLASSIC},
    {"id": EVENT_IDS_GGP7[1], "thread_ids": THREAD_ID_PACHINKO, "user_ids": USER_ID_PACHINKO, "divisions": "na"},
    {"id": EVENT_IDS_GGP7[2], "thread_ids": THREAD_ID_ROULETTE, "user_ids": USER_ID_ROULETTE, "divisions": "na"},
    {"id": EVENT_IDS_GGP7[3], "thread_ids": THREAD_IDS_ALLIN,   "user_ids": USER_IDS_ALLIN,   "divisions": DIVISIONS_ALLIN}
]

