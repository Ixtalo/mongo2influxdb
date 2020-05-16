#!/usr/bin/python3
# -*- coding: utf-8 -*-
# pylint: disable=line-too-long,invalid-name
"""mqtt-influxdb - Store MQTT messages to InfluxDB.

Store the MQTT messages from a mongoexport (JSON file) to InfluxDB.

Usage:
  mqtt-influxdb.py [options] <mqtt-messages-mongodbexport.json>
  mqtt-influxdb.py -h | --help
  mqtt-influxdb.py --version

Arguments:
  mqtt...json       mongoexport JSON export of mqtt.messages

Options:
  --host=HOST       InfluxDB host [default: localhost]
  --port=PORT       InfluxDB port [default: 8086]
  --sleep=N         Sleep seconds between sending batches [default: 0]
  -v --verbose      More output
  -h --help         Show this screen
  --version         Show version
"""
import logging
import sys
import json
from time import sleep
from docopt import docopt
from influxdb import InfluxDBClient     ## https://pypi.org/project/influxdb/

__author__ = "Alexander Streicher"
__email__ = "ixtalo@gmail.com"
__copyright__ = "Copyright (C) 2018 Alexander Streicher"
__license__ = "GPL"
__version__ = "1.0.1"
__date__ = "2020-05-03"
__updated__ = '2020-05-04'
__status__ = "Production"

DB_NAME = 'mqtt'  # database name

######################################################
######################################################
######################################################

DEBUG = 0
TESTRUN = 0
PROFILE = 0


def main():
    """
    Program's main entry point.
    :return: exit code
    """
    arguments = docopt(__doc__, version="mqtt-influxdb v%s" % __version__)
    # print(arguments)
    verbose = arguments['--verbose']
    input_file = arguments['<mqtt-messages-mongodbexport.json>']
    influxdb_host = arguments['--host']
    influxdb_port = int(arguments['--port'])
    sleep_time = int(arguments['--sleep'])

    ## setup logging
    logging.basicConfig(level=logging.INFO if not verbose else logging.DEBUG)
    logging.debug("CLI arguments: %s", arguments)

    ## database connection
    influx_client = InfluxDBClient(host=influxdb_host, port=influxdb_port)
    ## create database, if it does not exist yet
    influx_client.create_database(DB_NAME)

    with open(input_file) as fin:
        points = []     ## batch container
        for i, line in enumerate(fin):
            msg = json.loads(line)

            payload = msg['payload']
            if payload is None:
                continue

            payload_type = type(payload)
            payload_dbvalue = None
            payload_dbtype = None
            if payload_type in (int, float):
                payload_dbtype = 'float'
                payload_dbvalue = float(payload)
            elif payload_type in (dict, list):
                payload_dbtype = 'json'
                payload_dbvalue = json.dumps(payload)
            elif payload_type is str:
                payload_dbtype = 'str'
                payload_dbvalue = payload
            elif payload_type is bool:
                payload_dbtype = 'bool'
                payload_dbvalue = bool(payload)

            point = {
                "measurement": "message",
                "tags": {
                    "topic":  msg['topic']
                },
                "time": int(float(msg['timestamp']) * 1000 * 1000),
                "fields": {
                    "payload_%s" % payload_dbtype: payload_dbvalue
                }
            }
            logging.debug("point: %s", point)

            ## collect
            points.append(point)

            ## write as batch
            if i > 0 and i % 100000 == 0:
                logging.info("%d writing to DB...", i)
                influx_client.write_points(points, time_precision='u', database=DB_NAME)
                points = []
                if sleep_time:
                    logging.info("Waiting %d seconds...", sleep_time)
                    sleep(sleep_time)

        ## write the rest...
        logging.info("%d writing to DB...", i)
        influx_client.write_points(points, time_precision='u', database=DB_NAME)

    return 0


if __name__ == "__main__":
    if DEBUG:
        print("---------------- DEBUG MODE -----------------")
        if "--verbose" not in sys.argv:
            sys.argv.append("--verbose")
        # if "--dry-run" not in sys.argv: sys.argv.append("--dry-run")
    if TESTRUN:
        print("---------------- TEST RUN -----------------")
        import doctest
        doctest.testmod()
    if PROFILE:
        print("---------------- PROFILING -----------------")
        import cProfile
        import pstats
        profile_filename = 'profile.txt'
        cProfile.run('main()', profile_filename)
        statsfile = open("profile_stats.txt", "wb")
        p = pstats.Stats(profile_filename, stream=statsfile)
        stats = p.strip_dirs().sort_stats('cumulative')
        stats.print_stats()
        statsfile.close()
        sys.exit(0)
    sys.exit(main())

