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

Working, but the arguments and the output formats are not yet stable.

A Smokeping probe is available.

Obviously this program is intended to be used for scripting and automated monitoring,
so this is a priority. Once it's working and has a stable output format, a wrapper for
monitoring plugins (Nagios-compatible) will also be released.

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

I recommend creating a new group `mtping` with only the privileges `api,read,test` and a new user in that
group. You can do these in Winbox from System->Users, or on the command line as follows:

```
> /user group add name=mtping policy=api,read,test comment="mtping monitoring group"
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
more intuitive, as you will be typically setting the size because you are combining it with `-f`
(do not fragment) in order to test the link MTUs.

So these commands are equivalent and all send 1500-byte IP packets with DF bit set:

| Platform | Command                       |
| -------- | -------                       |
| mtping:  | `mtping -f -s 1500 10.0.0.1`  |
| Linux:   | `ping -M do -s 1472 10.0.0.1` |
| Windows: | `ping -f -l 1472 10.0.0.1`    |

In terms of the size received shown in the output, this is again the
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
  "status": 0,
  "destination": "www.example.com",
  "router": "192.168.1.1",
  "transmitted": 3,
  "received": 3,
  "duplicate": 0,
  "errors": 0,
  "loss": 0,
  "rtt_min": 162,
  "rtt_avg": 162,
  "rtt_max": 162,
  "rtt_mdev": 0
}
```

`status` is 0 to indicate that the ping command was successfully run (irrespective of whether
any ping replies were received).

A non-zero `status` indicates an error logging into the router or executing the ping.
The status codes correspond with the Exit Status section of this document,
and the object will also contain an `error` string detailing the error encountered. There
may also be a `error_detail` string with further cryptic information.

```
$ mtping 192.168.1.48 -c 3 -o json -T green | jq
{
  "status": 5,
  "error": "input does not match any value of routing-table",
  "error_detail": "('Error \"input does not match any value of routing-table\" executing command b\\'/ping =address=192.168.1.48 =size=56 =count=3 =routing-table=green .tag=3\\'', b'input does not match any value of routing-table')"
}
```

### json-detail

Upon completion, it will output the summary as above, as well as individual ping
results. Note that you need to look at the sequence numbers to determine if there
are duplicates or missing packets - you may get a larger or smaller number of
results than expected!

Not yet implemented.

### smokeping

Simply outputs the RTT time (in ms) for each non-duplicate reply received.
If a ping times out or an error is received, nothing is output. So for example
if you issue `-c 20` and only 17 lines are returned, there is 15% packet loss.


## Exit Status

`0` indicates the program ran successfully (even if the ping itself returned no results).

`1` is an unhandled Python exception (TODO check this is the only thing it can exit)

`2` indicates an error in validating the arguments.

`3` indicates an error connecting to the router.

`4` indicates an error logging into the router.

`5` is an error from the router, which could also still be an argument error (e.g. if an invalid
routing-table is specified).

## Smokeping

A Smokeping probe is included. Copy `MtPing.pm` to your smokeping probes directory
(`/usr/share/perl5/Smokeping/probes` if you have installed from the Debian package).

Full help on the options is then available using `smokeping -man Smokeping::probes::MtPing`

Activate it by specifying the location to the `mtping` binary in your Probes section:

```
*** Probes ***

+ MtPing

binary = /usr/local/bin/mtping
```

For the probe configuration, you can optionally specify defaults in the Probes section and/or
then override them per Target.

For each Target you wish to monitor with mtping, specify the `MtPing` probe type.

Required parameters are the `ros_router`, `ros_user`, and `ros_password`, and the
`host` to ping. Optionally specify the `routingtable`, `interface`, `srcaddress`, and
`packetsize` parameters.

```
*** Targets ***

+ MyRemoteOffice

menu = MyRemoteOffice
title = MyRemoteOffice
remark = In the green VRF
probe = MtPing
host = 10.10.10.2
ros_router = 192.168.1.1
ros_user = mtping
ros_password = Password01
srcaddress = 10.10.10.1
routingtable = green
interface = ether1

```


## TODO

- Investigate RouterOS returning two error codes per packet sent when fragmentation required.
- Handle all the various error types automatically.
- Abstract output formats into classes that are called by the main loop.
- Implement json-detail output format.
- Write wrapper for monitoring-plugins style plugin, and an Icinga 2 definition.
- Flag to automatically sweep range of sizes to determine true MTU with -f.

## License

See [LICENSE.md](LICENSE.md)
