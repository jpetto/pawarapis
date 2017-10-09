# -*- coding: utf-8 -*-

from flask import Flask, jsonify
from flask_cors import CORS, cross_origin

import collections
import datetime as dt
import json
import random
import requests
import os
import time
import logging

from candidates import candidates
from facts import retrieve_daily_random_fact, retrieve_random_fact

import * from helpers

env = os.environ.get('ENV')

if env == 'LOCAL':
    from storage-local import storage
else:
    from storage import storage
        
import boto3
dynamodb = boto3.resource('dynamodb')

env_suffix=''

if env:
    env_suffix = '-'+env
else:
    env_suffix = '-dev'

cache = dynamodb.Table('expenditures_cache'+env_suffix)
fact_oftheday_table = dynamodb.Table('fact_of_the_day'+env_suffix)


app = Flask(__name__)


# how long our cached items last
cacheDuration = 3600 # one hour
# assume there will never be more than 1,000,000 expenditures (but you never know, amirite?)
apiLimit = 1000000
dateFormat = '%Y-%m-%dT%H:%M:%S'


# convenience during development/testing
@app.route('/clear', methods=['GET'])
def clear():
    for c in candidates:
        cache.delete_item(
            Key={
                'id': c.get('id')
            }
        )

    return 'cache cleared'


def generate_response(rand_fact):
    cand_expenditures = get_cand_expenditures('rauner')

    # get it before rounding
    spentPerDay = calculateSpentPerDay(float(cand_expenditures['spendingDays']),
                                       float(cand_expenditures['total']))
    spentPerSecond = calculateSpentPerSecond(spentPerDay)
    secondsPerFactUnit = float(rand_fact['amount']) / spentPerSecond

    mins, secs = divmod(secondsPerFactUnit, 60)
    hours, mins = divmod(mins, 60)
    days, hours = divmod(hours, 24)

    text = "#RaunerSpends the %s in " % rand_fact['item']
    prevNum = False
    timecomponents = []
    if days:
        timecomponents.append("%d days" % days)
    if hours:
        timecomponents.append("%dhrs" % hours)
    if mins:
        timecomponents.append("%dmins" % mins)
    if secs:
        timecomponents.append("%ds" % secs)
    text += ", ".join(timecomponents)

    text += " [%s]" % rand_fact['source']

    resp = {'text': text}

    return resp


@app.route('/facts/random/oftheday', methods=['GET'])
@cross_origin()
def get_random_fact_oftheday():
    rand_fact = retrieve_daily_random_fact()
    resp = generate_response(rand_fact)
    return jsonify(resp)


@app.route('/facts/random', methods=['GET'])
@cross_origin()
def get_random_fact():
    # pick a random fact from the db
    # pick a random candidate and get their numbers
    # calculate stuff and return the text
    rand_fact = retrieve_random_fact()
    resp = generate_response(rand_fact)
    return jsonify(resp)


def get_cand_expenditures(candidate_nick):
    # find a matching committee_id
    committeeId = None

    # default to error message
    responseJSON = { 'error': 'Candidate not found' }

    for c in candidates:
        if c.get('id') == candidate_nick:
            committeeId = c.get('committeeId')
            break

    if committeeId:
        # try to pull data from cache
        response = cache.get_item(
            Key={
                'id': candidate_nick
            }
        )

        # if data found in cache, use it
        # TODO: normalize this in STORAGE.get to work w/AWS & redis
        if 'Item' in response:
            item = response['Item'];
            cachedJSON = item['json']
            responseJSON = json.loads(cachedJSON)
        # if data not found in cache:
        else:
            # make API call
            response = requests.get('https://www.illinoissunshine.org/api/expenditures/?limit={}&committee_id={}'.format(apiLimit, committeeId))

            apiData = json.loads(json.dumps(response.json()))

            total = 0.0

            for expenditure in apiData['objects'][0]['expenditures']:
                total = total + float(expenditure['amount'])

            firstExpenditure = apiData['objects'][0]['expenditures'][-1]['expended_date']
            spendingDays = calculateSpendingDays(dateFormat, firstExpenditure)
            spentPerDay = calculateSpentPerDay(spendingDays, total)

            responseJSON = {
                'total': "{0:.2f}".format(total),
                'expendituresCount': len(apiData['objects'][0]['expenditures']),
                'firstExpenditure': firstExpenditure,
                'spendingDays': spendingDays,
                'spentPerDay': "{0:.2f}".format(spentPerDay),
                'spentPerSecond': "{0:.2f}".format(calculateSpentPerSecond(spentPerDay)),
                'timestamp': dt.datetime.strftime(dt.datetime.now(), dateFormat)
            }

            # store API call results in cache
            expireTime = int(time.time())+(cacheDuration*1000);
            cache.put_item(
                Item={
                    'id': candidate_nick,
                    'ttl': expireTime,
                    'json': json.dumps(responseJSON)
                }
            )
    return responseJSON


@app.route('/candidate/<string:candidate_nick>', methods=['GET'])
@cross_origin()
def get_candidate(candidate_nick):
    # return JSON data about requested candidate *or* error message
    return jsonify(get_cand_expenditures(candidate_nick))


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
