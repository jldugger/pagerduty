#!/usr/bin/env python

import os
import shelve
import sys
import time

import ConfigParser

import pagerduty

cache_timeout = 60 * 60


def read_configurations():
    global config
    global secondary
    configfile = os.path.join(os.path.expanduser('~'), '.pagerduty.cfg')
    if not os.path.exists(configfile):
        sys.stderr.write('Move pagerduty.cfg to ~/.pagerduty.cfg to begin.\n')
        sys.exit(1)
    config = ConfigParser.RawConfigParser()
    config.read(configfile)

    secondary = config.get('Cli', 'secondary_schedule') if config.has_option('Cli', 'secondary_schedule') else False


def get_open_incidents():
    open_incidents_count = pagerduty.get_open_incidents(just_count=True)['total']
    if open_incidents_count:
        return '''
        <h3><a class="alert" href="https://riptano.pagerduty.com/incidents" target="_blank">
            Open tickets: %s
        </a></h3>
        <br/>\n''' % open_incidents_count
    return ''


def format_results(primary, secondary=False):
    if not secondary:
        dates = primary.keys()
        dates.sort()

        result = ''
        for date in dates:
            result += '<h4>Primary</h4>{0}: {1}<br/>\n'.format(primary[date]['shift_start'][-9:-1], primary[date]['agent_name']) if date in primary else ''
    else:
        dates = primary.keys() + secondary.keys()
        dates = set(dates)
        dates = sorted(dates)

        result = ''
        result += '<h4>Primary</h4>'
        for date in dates:
            result += '{0}: {1}<br/>\n'.format(primary[date]['shift_start'][-9:-1], primary[date]['agent_name']) if date in primary else ''
        result += '<br/>\n'
        result += '<h4>Secondary</h4>'
        for date in dates:
            result += '{0}: {1}<br/>\n'.format(secondary[date]['shift_start'][-9:-1], secondary[date]['agent_name']) if date in secondary else ''

    return result


def generate_page():
    global secondary

    primary = pagerduty.get_daily_schedule()
    if secondary:
        secondary = pagerduty.get_daily_schedule(secondary)

    return """Content-Type: text/html\n
    <link href="pagerduty.css" media="all" rel="stylesheet" type="text/css" />\n{0}%s
    <br/>
    <a href="full-schedule.py" target="_blank">Full Schedule</a>
    """ % format_results(primary, secondary)


def save_and_return(d):
    result = generate_page()
    d['on_call'] = {
        'result': result,
        'last_pulled': time.time()
    }
    return result


def main():
    read_configurations()
    try:
        d = shelve.open('pagerduty.db')
        if d.has_key('on_call') and (time.time() - d['on_call']['last_pulled']) < cache_timeout:
            print d['on_call']['result'].format(get_open_incidents())
        else:
            print save_and_return(d).format(get_open_incidents())
    finally:
        d.close()

if __name__ == "__main__":
    main()
