# mtping

`mtping` logs into a remote RouterOS router and performs a ping from there.

This is useful for monitoring or pinging to things that only the router has access to
(such a particular VRF), from a specific router IP/interface (e.g. to test an IPSec tunnel),
or simply to eliminate the latency between the monitoring host and the router, and measure
the true RTT between the router and the target (e.g. to monitor a circuit by ping to its
next hop).

As such you may use it in a similar way and for similar purposes as you might use
CISCO-RTTMON-MIB on a Cisco device.

As with any use of ping or traceroute, the usual disclaimer applies that routers typically
treat ICMP destined to their control plane differently and at a lower priority than
traffic on the forwarding plane. For mtping there is the additional disclaimer that the
ping is being originated on the router in question, so this applies for the source too,
and may in particular be unrepresentative on lower-end Routerboards or switches with
low-powered CPUs.

## Current status

It's not finished. Don't use it.

Once it's working and has a stable output format, a wrapper for monitoring plugins
(Nagios-compatible) and a plugin for Smokeping will also be released.

## WARNING

The format of the arguments and of the output is not yet stable.

Obviously this program is intended to be used for scripting and automated monitoring,
so this is a priority.

## Installation

For now:

```
# pip3 install -r requirements.txt

# cp mtping /usr/local/bin/
or
# ln -s `pwd`/mtping /usr/local/bin/mtping
```

## Arguments

For now, arguments are documented in `mtping -h`

Wherever possible, flags have been chosen to be compatible with `ping` from
Linux [iputils](http://www.skbuff.net/iputils/) or, failing that, Windows ping.

## API Login

This tool uses the RouterOS API to login to the router to perform the ping. For this to work,
you need the API enabled on the router, you need a user account with appropriate permissions to
login, and you need to pass this information to mtping.

### Enabling API on the router

This is done in Winbox from IP->Services. Find the "api" line and enable it, ideally
also locking it down to specific subnets.

From the command-line, `/ip service enable api` and then
`/ip service set api address=192.168.0.0/16` to lock it down.

Note that using this API involves transmitting the username and password in plaintext.
It is alternatively possible to use API-SSL, however note that you will need to create
a certificate on the router before this can be used.

Apart from enabling the API and setting allowed subnets there, you may also need to adjust
your firewall rules to allow TCP port 8728 (or 8729 for API-SSL) on the `input` chain from
your management subnet.

### User account

You need a user created, and this user must have the `api` and `test` privileges. It does not need
to be a privileged user, although Mikrotik currently require it to also have `read` privilege.

I recommend creating a new group `mtping` with only the privilege `api` and a new user in that
group. You can do these in Winbox from System->Users, or on the command line as follows:

```
> /user group add name=mtping policy=api comment="mtping monitoring group"
> /user add name=mtping password=Password01 group=mtping comment="mtping monitoring user"
```

### Passing credentials to mtping

You can pass the credentials either by environment variables or as arguments on the command-line.
Arguments take precedence, if specified.

The environment variables and command-line arguments are:

| Argument       | Environment  | Purpose |
| --------       | -----------  | ------- |
| -r, --router   | ROS_ROUTER   | The router to login into and ping from |
| -u, --user     | ROS_USER     | The user name to login to the API with |
| -p, --password | ROS_PASSWORD | The user name to login to the API with |

Command-line arguments may be seen by other users on the system and may be logged, so
environment variables are preferable.

An easy way to do this is to create a file, e.g. `~/.mtping` with the following contents:

```
export ROS_ROUTER=192.168.1.1
export ROS_USER=mtping
export ROS_PASSWORD=Password01
```

Then you can simply source this file into your current shell:

```
$ . ~/.mtping
$ mtping 127.0.0.1     # pings from the default ROS_ROUTER
$ mtping -r 192.168.5.1 127.0.0.1     # pings from 192.168.5.1 but with same credentials
```

## Packet size

One key difference from ping on other platforms is the `-s` size parameter.

On other platforms, you specify the number of data bytes to send in the echo request. Adding
20 bytes for IPv4 header and 8 bytes for ICMP header gives the total size of the IP packet
transmitted.

On Mikrotik however, you simply specify the total size of the packet to transmit, and
it automatically figures out how many data bytes to stuff it with. Personally I find this
more intuitive, as typically you will be doing this because you are combining it with `-f`
(do not fragment) in order to test the link MTUs.

So these commands are equivalent and all send 1500-byte IP packets with DF bit set:

| mtping:  | `mtping -f -s 1500 10.0.0.1` |
| Linux:   | `ping -M do -s 1472 10.0.0.1` |
| Windows: | `ping -f -l 1472 10.0.0.1` |

In terms of the size received shown in the output, the size shown is again the
total packet size. Confusingly on other systems, it is the neither the data bytes size you
specified nor the total packet size, it is the ICMP packet size including ICMP header.

## Resolution

Mikrotik RTT times are only reported to a resolution of 1ms.

This tool therefore only shows min/avg/max/mdev as integers as well.

## Python

This was developed for Python 3. It may or may not work with Python 2. Pull requests
for Python 2 compatibility will only be accepted if they do not convolute the code.

## Output formats

The output format can be selected with the `-o` argument. The default is 'human'.

If an output other than 'human' is selected, the tool assumes it is being run
non-interactively and will require the specification of a count (`-c`) otherwise it
would run forever with no output.

### human

The default output format is 'human', which aims for an experience compatible with
the familiar Linux [iputils](http://www.skbuff.net/iputils/) ping. Timings are however
all shown as integer milliseconds.

As with that tool, `-q` will suppress most output (including individual ping responses)
and only show the header and summary lines.

The 'human' output format is subject to change and should not be used for scripting.
Other output formats exist for consumption by other programs.

### json

Upon completion, it will output a JSON representation of the summary, suitable for loading
into another program:

```
$ mtping www.example.com -c 3 -o json | jq
{
  "destination": "www.example.com",
  "router": "192.168.1.1",
  "transmitted": 3,
  "received": 3,
  "duplicate": 0,
  "loss": 0,
  "rtt_min": 162,
  "rtt_avg": 162,
  "rtt_max": 162,
  "rtt_mdev": 0
}
```

### json-detail

Upon completion, it will output the summary as above, as well as individual ping
results. Note that you need to look at the sequence numbers to determine if there
are duplicates or missing packets - you may get a larger or smaller number of
results than expected!

TODO

## Arguments

Arguments are documented within the tool itself, use `mtping -h`.

## License

See [LICENSE.md](LICENSE.md)
