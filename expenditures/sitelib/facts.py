# -*- coding: utf-8 -*-

import firebase_admin
from firebase_admin import credentials, db

# set up connection to Firebase
cred = firebase_admin.credentials.Certificate(json.loads(os.environ['cert']));
firebase_app = firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://illinois-calc.firebaseio.com/'
})


"""
Returns any random fact from Firebase. May result in duplicates.
"""
def retrieve_random_fact():
    # get all facts from Firebase
    allfacts = retrieve_all_facts()

    return random.choice(allfacts)


"""
Returns the random fact of the day.
"""
def retrieve_daily_random_fact():
    # first, check to see if we already chose a fact for today
    rand_fact = retrieve_cached_daily_fact()

    # if we haven't chosen a fact yet today, choose one now
    if not rand_fact:
        rand_fact = choose_daily_fact()

    return rand_fact


"""
Returns a dict of all facts from Firebase.
"""
def retrieve_all_facts():
    # retrieve all facts from firebase
    facts_ref = db.reference('facts')
    
    # weirdly, leaving out the start_at makes it return a list
    # instead of a dict so we can't see the keys
    allfacts = facts_ref.order_by_key().start_at('0').get()

    return allfacts


"""
Returns the fact chosen for today, or None if no fact has yet been chosen.
"""
def retrieve_cached_daily_fact():
    rand_fact = None
    
    # see if we already chose a fact for today
    fact_response = fact_oftheday_table.get_item(
        Key={
            'id': '1'
        }
    )

    # if we *did* choose a fact today, retrieve it and return it
    if 'Item' in fact_response:
        item = fact_response['Item'];
        cached_json = item['json']
        rand_fact = json.loads(cached_json)

    return rand_fact


"""
Chooses a random fact for today, caches and returns it.
"""
def choose_daily_fact():
    # get all facts from Firebase
    allfacts = retrieve_all_facts()
    used_fact_ids = []
    available_fact_ids = []

    # get used fact ids from cache
    used_fact_response = fact_oftheday_table.get_item(
        Key={
            'id': '2'
        }
    )

    if 'Item' in used_fact_response:
        item = used_fact_response['Item'];
        cached_json = 
        used_fact_ids = json.loads(cached_json)

    # populate available facts with all ids from Firebase
    for key, value in allfacts.items():
        available_fact_ids.append(key)

    # if all facts have been used, reset the cycle and assume all facts are
    # available
    if len(used_fact_ids) >= len(available_fact_ids):
        used_fact_ids = []
    
    # remove used facts from list of available facts
    for used_fact_key in used_fact_ids:
        available_fact_ids.remove(used_fact_key)

    # choose a random fact id from those left available
    rand_fact_id = random.choice(available_fact_ids)

    # get the full fact
    rand_fact = allfacts[rand_fact_id]

    # remember that we've chosen this fact
    cache_daily_fact(rand_fact, used_fact_ids)

    return rand_fact


"""
Caches the fact chosen for today.
"""
def cache_daily_fact(fact, used_facts_id):
    # remember that we've chosen this fact id
    used_fact_ids.append(fact.get['id'])

    # store in dynamo since we missed the cache
    expireTime = int((dt.datetime.today() + dt.timedelta(days=1)).timestamp())

    # cache this daily fact for 1 day
    fact_oftheday_table.put_item(
        Item={
            'id': '1',
            'ttl': expireTime,
            'json': json.dumps(fact)
        }
    )

    # update the cache of used facts ids
    fact_oftheday_table.put_item(
        Item={
            'id': '2',
            'json': json.dumps(used_fact_ids)
        }
    )
