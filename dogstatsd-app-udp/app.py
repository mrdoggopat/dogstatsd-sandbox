from datadog import initialize, statsd
import time

options = {
    'statsd_host':'127.0.0.1',
    'statsd_port':8125
}

initialize(**options)

while(1):
  statsd.increment('containerspod.isthebest', tags=["environment:lowkey"])
  statsd.decrement('failedatdoing.ecsfargatelogging', tags=["environment:sad"])
  time.sleep(10)