#!/usr/bin/python3

import sys
sys.path.insert(0, '/home/david/mtping/RouterOS-api')

import routeros_api
from routeros_api import exceptions
import os
import argparse
from pprint import pprint


default_router = os.environ['ROS_ROUTER'] if 'ROS_ROUTER' in os.environ else None
default_user = os.environ['ROS_USER'] if 'ROS_USER' in os.environ else None
default_password = os.environ['ROS_PASSWORD'] if 'ROS_PASSWORD' in os.environ else None

parser = argparse.ArgumentParser(description='Perform a ping from a remote router.',
                                 epilog='Note that Mikrotik only ping in a resolution of 1 ms. Drawing any inference from the fractional part of any average value returned may therefore be invalid.')

parser.add_argument('destination', nargs=1,
                    help='the host to ping to')

parser.add_argument('-r', '--router', nargs=1,
                    default=default_router,
                    required=default_router is None,
                    help='the router to ping from. Optional if environment variable ROS_ROUTER is set.')

parser.add_argument('-u', '--user', nargs=1,
                    default=default_user,
                    required=default_user is None,
                    help='the user to login to the API. Optional if environment variable ROS_USER is set. The user can be read-only, but it does need the "api" privilege.')

parser.add_argument('-p', '--password', nargs=1,
                    default=default_password,
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
                    default=[3],
                    type=int,
                    help='the number of ICMP echo requests to send. 0..4294967295. 0 would ping forever, so is only allowed if not quiet')

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

if not quiet:
    print("connected to %s" % router)

api_root = api.get_binary_resource('/');

params = {
    'address': str(destination),
    'count': str(args.count[0]),
    }

if (args.size is not None):
    params['size'] = str(args.size[0])


## TODO set api timeout to timeout expected for the number of pings
## TODO can we alter RouterOS-api to stream results as they come in interactive mode rather than batching them up

try:
    ping_result = api_root.call('ping', params)
except routeros_api.exceptions.RouterOsApiCommunicationError as e:
    print(e.original_message.decode(), file=sys.stderr)
    print(str(e), file=sys.stderr)
    sys.exit(1)

pprint(ping_result)

pkts_transmitted = 0
pkts_received = 0

rtt_min = None
rtt_max = None
rtt_total = 0
rtt_num = 0

rtt_mdev = 0 # TODO



loss = 99.3333333

print("--- %s ping statistics (via %s) ---\n" % (destination, router))
print("%d packets transmitted, %d received, %g%% packet loss, time ????0ms\n" % (pkts_transmitted, pkts_received, loss))

if pkts_received > 0 or True:
    rtt_avg = rtt_total / 1#rtt_num
    print("rtt min/avg/max/mdev = {min:0.3f}ms\n".format(min=rtt_min, avg=rtt_avg, max=rtt_max, mdev=rtt_mdev))



#https://github.com/iputils/iputils/blob/master/ping_common.c
# printf(_("%ld received"), nreceived);
# if (nrepeats)
# printf(_(", +%ld duplicates"), nrepeats);
# if (nchecksum)
# printf(_(", +%ld corrupted"), nchecksum);
# if (nerrors)
# printf(_(", +%ld errors"), nerrors);

# if (ntransmitted) {
# #ifdef USE_IDN
#     setlocale(LC_ALL, "C");
# #endif
#     printf(_(", %g%% packet loss"),
#                   (float)((((long long)(ntransmitted - nreceived)) * 100.0) / ntransmitted));
#     printf(_(", time %ldms"), 1000 * tv.tv_sec + (tv.tv_usec + 500) / 1000);
#     }



