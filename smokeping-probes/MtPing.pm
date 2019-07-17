package Smokeping::probes::MtPing;

=head1 301 Moved Permanently

This is a Smokeping probe module. Please use the command

C<smokeping -man Smokeping::probes::MtPing>

to view the documentation or the command

C<smokeping -makepod Smokeping::probes::MtPing>

to generate the POD document.

=cut

use strict;
use base qw(Smokeping::probes::basefork);
use Carp;

sub pod_hash {
	return {
		name => <<DOC,
Smokeping::probes::MtPing - a mtping(1) probe for SmokePing
DOC
		overview => <<DOC,
Measures roundtrip times directly from a RouterOS router.
DOC
		description => <<DOC,
See mtping(1) and L<https://github.com/davidc/mtping> for details of the workings of the
options below.
DOC
		authors => <<DOC,
David Croft L<http://www.davidc.net/>
DOC
		see_also => <<DOC
mtping(1), L<https://github.com/davidc/mtping>
DOC
	};
}

sub new($$$)
{
    my $proto = shift;
    my $class = ref($proto) || $proto;
    my $self = $class->SUPER::new(@_);

    # no need for this if we run as a cgi
    unless ( $ENV{SERVER_SOFTWARE} ) {
	# if you have to test the program output
	# or something like that, do it here
	# and bail out if necessary
    };

    return $self;
}


# Probe-level variables

sub probevars {
	my $class = shift;
	return $class->_makevars($class->SUPER::probevars, {
		_mandatory => [ 'binary' ],
		binary => {
			_doc => "The location of your mtping binary.",
			_example => '/usr/bin/mtping',
			_sub => sub {
				my $val = shift;
				return "ERROR: mtping 'binary' does not point to an executable"
					unless -f $val and -x _;
				return undef;
			},
		},
	});
}

# Target-specific variables

sub targetvars {
	my $class = shift;
	return $class->_makevars($class->SUPER::targetvars, {
	    _mandatory => [ 'ros_router', 'ros_user', 'ros_password' ],
	    ros_router => {
		_example => 'Myrouter.foobar.com.au',
		_doc => <<DOC,
		The (mandatory) ros_router parameter specifies the RouterOS router which will
		    execute the pings.
DOC
	    },
	    ros_user => {
		_example => 'pinguser',
		_doc => <<DOC,
		The (mandatory) ros_user parameter specifies the user to login to the router as.
DOC
	    },
	    ros_password => {
		_example => 'Password01',
		_doc => <<DOC,
		The (mandatory) ros_password parameter specifies the password to login to the router with.
DOC
	    },
	    interface => {
		_example => 'ether1',
		_doc => <<DOC,
		The (optional) interface to ping from.
DOC
	    },
	    srcaddress => {
		_example => '192.168.1.1',
		_doc => <<DOC,
		The (optional) src-address to ping from.
DOC
	    },
	    routingtable => {
		_example => 'green',
		_doc => <<DOC,
		The (optional) routing-table to ping in.
DOC
	    },
	    packetsize => {
		_example => 64,
		_doc => <<DOC,
		The (optional) total packet size (including IP and ICMP headers).
DOC
	    },
	});
}

sub ProbeDesc($){
    my $self = shift;
    return "MtPing";
}


# Perform the ping on a single target

sub pingone ($){
    my $self = shift;
    my $target = shift;

    my $binary = $self->{properties}{binary};
    my $count = $self->pings($target); # the number of pings for this targets

    # ping one target

    my @params = () ;
    push @params, "-r",  $target->{vars}{ros_router};
    push @params, "-u",  $target->{vars}{ros_user};
    push @params, "-p",  $target->{vars}{ros_password};
    push @params, "-I",  $target->{vars}{interface} if $target->{vars}{interface};
    push @params, "-S",  $target->{vars}{srcaddress} if $target->{vars}{srcaddress};
    push @params, "-T",  $target->{vars}{routingtable} if $target->{vars}{routingtable};
    push @params, "-s",  int($target->{vars}{packetsize}) if $target->{vars}{packetsize};
    push @params, "-c",  $count;
    push @params, "-o", "smokeping";

    push @params, $target->{addr};

    my @cmd = (
	$binary,
	@params
	);

    my @times;

    $self->do_debug("Executing $binary " . join(" ", @params) . " 2>&1 |");
    open(P, "$binary " . join(" ", @params) . " 2>&1 |") or croak("fork: $!");
    while (<P>) {
#	$self->do_debug("Line $_");
	/^(\d+)$/ and push @times, $1;
    }
    close P;

    if ($? != 0) {
	$self->do_log("Abnormal exit code $? from mtping");
	return;
    }

    #@times = sort {$a <=> $b} @times;
    # RouterOS ping times are in milliseconds
    @times = map {sprintf "%.10e", $_ / 1000} sort {$a <=> $b} @times;

    return @times;
}

1;
