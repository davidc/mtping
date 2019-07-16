#!/usr/bin/python3

import sys
#sys.path.insert(0, '/home/david/mtping/RouterOS-api')

import routeros_api
from routeros_api import exceptions
import os
import argparse
from pprint import pprint
import math


default_router = os.environ['ROS_ROUTER'] if 'ROS_ROUTER' in os.environ else None
default_user = os.environ['ROS_USER'] if 'ROS_USER' in os.environ else None
default_password = os.environ['ROS_PASSWORD'] if 'ROS_PASSWORD' in os.environ else None

parser = argparse.ArgumentParser(description='Perform a ping from a remote router.',
                                 epilog='Note that Mikrotik only ping in a resolution of 1 ms. Drawing any inference from the fractional part of any average value returned may therefore be invalid.')

parser.add_argument('destination', nargs=1,
                    help='the host to ping to')

parser.add_argument('-r', '--router', nargs=1,
                    default=[default_router],
                    required=default_router is None,
                    help='the router to ping from. Optional if environment variable ROS_ROUTER is set.')

parser.add_argument('-u', '--user', nargs=1,
                    default=[default_user],
                    required=default_user is None,
                    help='the user to login to the API. Optional if environment variable ROS_USER is set. The user can be read-only, but it does need the "api" privilege.')

parser.add_argument('-p', '--password', nargs=1,
                    default=[default_password],
                    required=default_password is None,
                    help='the password to login to the API. Optional if environment variable ROS_PASSWORD is set. It is generally a bad idea to set the password '
                                 'on the command line, as arguments are visible to all users '
                                 'and may be logged. Better to use the ROS_PASSWORD '
                                 'environment variable.')

parser.add_argument('-T', '--table', nargs=1,
                    help='the routing-table to ping in')

parser.add_argument('-S', '--src-address', nargs=1,
                    help='the src-address for the echo request')

parser.add_argument('-I', '--interface', nargs=1,
                    help='Interface to ping from')

parser.add_argument('-f', '--do-not-fragment',
                    default=False,
                    action='store_const', const=True,
                    help='Set the do not fragment bit. Equivalent of Linux ping "-M do".')

parser.add_argument('-a', '--arp-ping',
                    default=False,
                    action='store_const', const=True,
                    help='Performs an ARP ping. The <address> is therefore a MAC address.')

parser.add_argument('-q', '--quiet',
                    default=False,
                    action='store_const', const=True,
                    help='Do not print progress reports.')

parser.add_argument('-d', '--debug',
                    default=False,
                    action='store_const', const=True,
                    help='Pring debugging information.')

parser.add_argument('-c', '--count', nargs=1,
#                    default=[3],
                    type=int,
                    help='the number of ICMP echo requests to send. 0..4294967295. Unspecified or 0 means ping forever.')

parser.add_argument('-s', '--size', nargs=1,
                    type=int,
                    help='The total size of the echo request packets - for Mikrotik, this includes IP and ICMP headers. Can therefore be up to the full MTU of your link. For IPv4, the IP header is 20 bytes and ICMP echo request header is 8 bytes, for a total of 28 bytes. A Linux ping of -s 1472 is equivalent to mtping of -s 1500 will therefore both send a 1500 byte IP packet. (28-65535)')

parser.add_argument('-Q', '--dscp', nargs=1,
                    type=int,
                    help='the DSCP value to use (0-63)')

parser.add_argument('-t', '--ttl', nargs=1,
                    type=int,
                    help='the TTL value to use (0-255)')

parser.add_argument('-o', '--output', nargs=1,
                    default=['human'],
                    help='The output format desired. Valid values: human (default), json')


args = parser.parse_args()
router = args.router[0]
destination = args.destination[0]
quiet = args.quiet
debug = args.debug

#pprint(args)

#sys.exit(0)

connection = routeros_api.RouterOsApiPool(router, username=args.user[0], password=args.password[0], debug=debug)
api = connection.get_api()



api_root = api.get_binary_resource('/');

params = {
    'address': str(destination),
    }

if (args.count is not None):
    params['count'] = str(args.count[0])

if (args.size is None):
    params['size'] = 56
else:
    params['size'] = str(args.size[0])

print("PING {dest} (via {router}) {size} bytes total packet size." \
      .format(dest=destination, router=router, size=params['size']))

    

## TODO set api timeout to timeout expected for the number of pings

pkts_transmitted = 0
pkts_received = 0
pkts_duplicate = 0

rtt_min = None
rtt_max = None
rtt_sum = 0
rtt_sum2 = 0 # sum of square
rtt_num = 0

seen_seq = [] # track sequences already seen to detect duplicates

try:
    ping_responses = api_root.call_async('ping', params)
    for ping_response in ping_responses:
        if debug:
            pprint(ping_response)

        if 'status' in ping_response:
            status = ping_response['status'].decode()
        else:
            status = 'ok'

        if status == 'timeout':
            response_host = ping_response['host'].decode()
            print("timeout waiting for response from {host}" \
                  .format(host=response_host));
            pkts_transmitted += 1
            
        elif status == 'ok':
            response_time = int(ping_response['time'].decode().replace('ms', ''))
            response_seq = int(ping_response['seq'].decode())

            if response_seq in seen_seq:
                is_dup = True
            else:
                seen_seq.append(response_seq)
                is_dup = False

            if not quiet:
                response_host = ping_response['host'].decode()
                response_ttl = int(ping_response['ttl'].decode())
                response_size = int(ping_response['size'].decode())
                print("{size} bytes from {host}: icmp_seq={seq} ttl={ttl} time={time} ms" \
                      .format(size=response_size, host=response_host, seq=response_seq, ttl=response_ttl, time=response_time), end='')
                if is_dup:
                    print(" (DUP!)", end='')

                print()
                
            if is_dup:
                pkts_duplicate += 1
            else:
                pkts_transmitted += 1
                pkts_received += 1
                
            rtt_sum += response_time
            rtt_sum2 += response_time * response_time
            rtt_num += 1

            if rtt_min is None or response_time < rtt_min:
                rtt_min = response_time
            if rtt_max is None or response_time > rtt_max:
                rtt_max = response_time
        else:
            print("Unknown status {status}".format(status=status))
            
except KeyboardInterrupt:
    # Do nothing, continue to print summary
    pass
except routeros_api.exceptions.RouterOsApiCommunicationError as e:
    print(e.original_message.decode(), file=sys.stderr)
    print(str(e), file=sys.stderr)
    sys.exit(1)


print("")
print("--- %s ping statistics (via %s) ---" % (destination, router))
print("{tx} packets transmitted, {rx} received" \
      .format(tx=pkts_transmitted, rx=pkts_received), end='')
if pkts_duplicate > 0:
    print(", +{dup} duplicates" \
      .format(dup=pkts_duplicate), end='')

if pkts_transmitted > 0:
    #loss = 100.0 * (1 - (pkts_received / pkts_transmitted))
    loss = ((pkts_transmitted - pkts_received) * 100.0) / pkts_transmitted;

    print(", {loss}% packet loss" \
          .format(loss=loss), end='') # TODO this shouldn't have a .0 on the end

print("")

if rtt_num > 0:
    rtt_avg = int(rtt_sum / rtt_num)

    # This slightly clumsy computation order is important to avoid
    # integer rounding errors for small ping times.
    tmvar = (rtt_sum2 - ((rtt_sum * rtt_sum) / rtt_num)) / rtt_num
    rtt_mdev = int(math.sqrt(tmvar))
    
    print("rtt min/avg/max/mdev = {min}/{avg}/{max}/{mdev} ms" \
          .format(min=rtt_min, avg=rtt_avg, max=rtt_max, mdev=rtt_mdev))



#output format reference: https://github.com/iputils/iputils/blob/master/ping_common.c
