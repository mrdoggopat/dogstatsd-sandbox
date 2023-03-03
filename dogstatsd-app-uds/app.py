from datadog import initialize, statsd
import time

options = {
    "statsd_socket_path": "/var/run/datadog/dsd.socket",
}

initialize(**options)

while(1):
  statsd.increment('dogstatsd.kickedmybutt', tags=["environment:lowkey"])
  statsd.decrement('ineedtoget.fourtyticketsolves', tags=["environment:sad"])
  time.sleep(10)