#!/usr/bin/python3

import sys
#sys.path.insert(0, '/home/david/mtping/RouterOS-api')

import routeros_api
from routeros_api import exceptions
import os
import argparse
from pprint import pprint
import math
import json


default_router = os.environ['ROS_ROUTER'] if 'ROS_ROUTER' in os.environ else None
default_user = os.environ['ROS_USER'] if 'ROS_USER' in os.environ else None
default_password = os.environ['ROS_PASSWORD'] if 'ROS_PASSWORD' in os.environ else None

parser = argparse.ArgumentParser(description='Perform a ping from a remote router.',
                                 epilog='Note that Mikrotik only measures RTT with a resolution of 1 ms.')

parser.add_argument('destination', nargs=1,
                    help='the host to ping to (IP address, MAC or DNS name). If a DNS name is used, it '
                    'will be resolved by the router itself.')

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
                    help='Performs an ARP ping.')

parser.add_argument('-c', '--count', nargs=1,
                    type=int,
                    help='the number of ICMP echo requests to send. 0..4294967295. Unspecified or 0 means ping forever.')

parser.add_argument('-s', '--size', nargs=1,
                    type=int,
                    default=[56],
                    help='The total size of the echo request packets - for Mikrotik, this includes IP and ICMP headers. Can therefore be up to the full MTU of your link. For IPv4, the IP header is 20 bytes and ICMP echo request header is 8 bytes, for a total of 28 bytes. A Linux ping of -s 1472 is equivalent to mtping of -s 1500 will therefore both send a 1500 byte IP packet. (28-65535)')

parser.add_argument('-Q', '--dscp', nargs=1,
                    type=int,
                    help='the DSCP value to use (0-63)')

parser.add_argument('-t', '--ttl', nargs=1,
                    type=int,
                    help='the TTL value to use (1-255)')

parser.add_argument('-q', '--quiet',
                    default=False,
                    action='store_const', const=True,
                    help='Do not print progress reports.')

parser.add_argument('-d', '--debug',
                    default=False,
                    action='store_const', const=True,
                    help='Print routeros-api and other debugging information.')

parser.add_argument('-o', '--output', nargs=1,
                    default=['human'],
                    help='The output format desired. Valid values: human (default), json.')

# Validate arguments

args = parser.parse_args()

destination = args.destination[0]
router = args.router[0]
user = args.user[0]
password=args.password[0]

routing_table = None if args.table is None else args.table[0]
src_address = None if args.src_address is None else args.src_address[0]
interface = None if args.interface is None else args.interface[0]
do_not_fragment = args.do_not_fragment
arp_ping = args.arp_ping

count = None if args.count is None else args.count[0]
if count is not None and count < 0:
    print("Invalid count %d" % (count), file=sys.stderr)
    sys.exit(1)
        
packet_size = args.size[0]
if packet_size < 28 or packet_size > 65535:
    print("Invalid size %d" % (packet_size), file=sys.stderr)
    sys.exit(1)

dscp = None if args.dscp is None else args.dscp[0]
if dscp is not None and (dscp < 0 or dscp > 63):
    print("Invalid DSCP %d" % (dscp), file=sys.stderr)
    sys.exit(1)

ttl = None if args.ttl is None else args.ttl[0]
if ttl is not None and (ttl < 1 or ttl > 255):
    print("Invalid TTL %d" % (ttl), file=sys.stderr)
    sys.exit(1)
    
quiet = args.quiet
debug = args.debug

VALID_OUTPUT = ['human', 'json']
output = args.output[0]
if output not in VALID_OUTPUT:
    # TODO probably can have a callback in argparse to validate this?
    print("Invalid output format %s" % (output), file=sys.stderr)
    sys.exit(1)

# Check any parameters that need to be consistent with each other

if output != 'human' and count is None:
    # TODO error_die (so it gets formatted for this output format)
    print("Script output selected but count not specified (-c)", file=sys.stderr)
    sys.exit(1)


# Establish connection to router. Error will be throw here if unable to connect or login fails

connection = routeros_api.RouterOsApiPool(router, username=user, password=password, debug=debug)
api = connection.get_api()


api_root = api.get_binary_resource('/');


# Prepare the args to pass to the API
params = {
    'address': str(destination),
    'size': str(packet_size),
    }

if (count is not None):
    params['count'] = str(count)

if src_address:
    params['src-address'] = str(src_address)

if interface:
    params['interface'] = str(interface)

if routing_table:
    params['routing-table'] = str(routing_table)

if do_not_fragment:
    params['do-not-fragment'] = str(1)

if arp_ping:
    params['arp-ping'] = 'yes'

if dscp is not None:
    params['dscp'] = str(dscp)

if ttl is not None:
    params['ttl'] = str(ttl)


# Print header
    
if output == 'human':
    print("PING {dest} () from {router}: {size} bytes packets." \
          .format(dest=destination, router=router, size=packet_size))
    if src_address and not quiet:
        print("... from source address {src}" \
              .format(src=src_address))
    if routing_table and not quiet:
        print("... in routing table {table}" \
              .format(table=routing_table))


## TODO set api timeout to timeout expected for the number of pings

pkts_transmitted = 0
pkts_received = 0
pkts_duplicate = 0
pkts_error = 0

rtt_min = None
rtt_max = None
rtt_sum = 0
rtt_sum2 = 0 # sum of square
rtt_num = 0

seen_seq = [] # track sequences already seen to detect duplicates

try:
    if debug:
        print("Calling API /ping with params:")
        pprint(params)
    
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

        elif status == 'TTL exceeded':
            if output == 'human' and not quiet:
                response_host = ping_response['host'].decode()
                response_seq = int(ping_response['seq'].decode())
                print("From {host} icmp_seq={seq} Time to live exceeded" \
                      .format(host=response_host, seq=response_seq))
            pkts_transmitted += 1
            pkts_error += 1
            
        elif status == 'ok':
            response_time = int(ping_response['time'].decode().replace('ms', ''))
            response_seq = int(ping_response['seq'].decode())

            if response_seq in seen_seq:
                is_dup = True
            else:
                seen_seq.append(response_seq)
                is_dup = False

            if output == 'human' and not quiet:
                response_host = ping_response['host'].decode()

                if 'size' in ping_response:
                    response_size = int(ping_response['size'].decode())
                    print("{size} bytes" \
                      .format(size=response_size), end='')
                else:
                    print("response", end='')
                    
                print(" from {host}: icmp_seq={seq}" \
                      .format(host=response_host, seq=response_seq), end='')

                if 'ttl' in ping_response:
                    response_ttl = int(ping_response['ttl'].decode())
                    print(" ttl={ttl}" \
                          .format(ttl=response_ttl), end='')

                print(" time={time} ms" \
                      .format(time=response_time), end='')
                
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
            print("Unknown status {status}".format(status=status), file=sys.stderr)
            
except KeyboardInterrupt:
    # Do nothing, continue to print summary
    pass
except routeros_api.exceptions.RouterOsApiCommunicationError as e:
    # TODO pass to error_die()
    print(e.original_message.decode(), file=sys.stderr)
    if debug:
        print(str(e), file=sys.stderr)
    sys.exit(1)


# Calculate stats


# loss is only valid if at least one packet was transmitted
if pkts_transmitted > 0:
    #loss = 100.0 * (1 - (pkts_received / pkts_transmitted))
    loss = ((pkts_transmitted - pkts_received) * 100.0) / pkts_transmitted;

# rtt_avg and rtt_mdev are only valid if at least one reply was received
if rtt_num > 0:
    rtt_avg = int(rtt_sum / rtt_num)

    # This slightly clumsy computation order is important to avoid
    # integer rounding errors for small ping times.
    tmvar = (rtt_sum2 - ((rtt_sum * rtt_sum) / rtt_num)) / rtt_num
    rtt_mdev = int(math.sqrt(tmvar))


# Output stats

if output == 'human':
    #output format reference: https://github.com/iputils/iputils/blob/master/ping_common.c
    print("")
    print("--- %s ping statistics (via %s) ---" % (destination, router))
    print("{tx} packets transmitted, {rx} received" \
          .format(tx=pkts_transmitted, rx=pkts_received), end='')
    if pkts_duplicate > 0:
        print(", +{dup} duplicates" \
              .format(dup=pkts_duplicate), end='')

    if pkts_error > 0:
        print(", +{err} errors" \
              .format(err=pkts_error), end='')

    if pkts_transmitted > 0:
        print(", {loss}% packet loss" \
              .format(loss=loss), end='') # TODO this shouldn't have a .0 on the end

    print("")

    if rtt_num > 0:
        print("rtt min/avg/max/mdev = {min}/{avg}/{max}/{mdev} ms" \
              .format(min=rtt_min, avg=rtt_avg, max=rtt_max, mdev=rtt_mdev))

elif output == 'json':
    result = { 'destination': destination,
               'router': router,
               'transmitted': pkts_transmitted,
               'received': pkts_received,
               'duplicate': pkts_duplicate,
               'errors': pkts_error
               }

    if pkts_transmitted > 0:
        result.update( { 'loss': loss,
                         } );
    if rtt_num > 0:
        result.update( { 'rtt_min': rtt_min,
                         'rtt_avg': rtt_avg,
                         'rtt_max': rtt_max,
                         'rtt_mdev': rtt_mdev,
                         } );

    print(json.dumps(result))

