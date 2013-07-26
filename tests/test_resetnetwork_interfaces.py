# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
#  Copyright (c) 2011 Openstack, LLC.
#  All Rights Reserved.
#
#     Licensed under the Apache License, Version 2.0 (the "License"); you may
#     not use this file except in compliance with the License. You may obtain
#     a copy of the License at
#
#          http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#     WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#     License for the specific language governing permissions and limitations
#     under the License.
#

"""
resetnetwork interfaces tester
"""

import re

import agent_test
import commands.redhat.network
import commands.debian.network
import commands.arch.network
import commands.gentoo.network
import commands.suse.network


class TestInterfacesUpdates(agent_test.TestCase):

    def _run_test(self, dist, infiles=None, version=None, **configs):
        interfaces = {}
        for ifname, options in configs.iteritems():
            interface = {'mac': options['hwaddr'],
                         'label': options['label']}

            ip4s = []
            for ip, netmask in options.get('ipv4', []):
                ip4s.append({'address': ip,
                             'netmask': netmask})

            interface['ip4s'] = ip4s

            interface['gateway4'] = options.get('gateway4')

            ip6s = []
            for ip, netmask in options.get('ipv6', []):
                ip6s.append({'address': ip,
                             'prefixlen': netmask})

            interface['ip6s'] = ip6s

            interface['gateway6'] = options.get('gateway6')

            if options.get('dns'):
                interface['dns'] = options['dns']

            interface['routes'] = []

            interfaces[ifname] = interface

        kwargs = {}
        if version:
            kwargs = {'version': version}

        mod = getattr(commands, dist).network
        if infiles:
            return mod.get_interface_files(infiles, interfaces, **kwargs)
        else:
            return mod.get_interface_files(interfaces, **kwargs)

    def test_redhat_ipv4(self):
        """Test setting public IPv4 for Red Hat networking"""
        interface = {
            'label': 'public',
            'hwaddr': '00:11:22:33:44:55',
            'ipv4': [('192.0.2.42', '255.255.255.0')],
            'gateway4': '192.0.2.1',
            'dns': ['192.0.2.2'],
        }
        outfiles = self._run_test('redhat', eth0=interface)
        self.assertTrue('ifcfg-eth0' in outfiles)

        generated = outfiles['ifcfg-eth0'].rstrip().split('\n')
        expected = [
            '# Automatically generated, do not edit',
            '',
            '# Label public',
            'DEVICE=eth0',
            'BOOTPROTO=static',
            'HWADDR=00:11:22:33:44:55',
            'IPADDR=192.0.2.42',
            'NETMASK=255.255.255.0',
            'DEFROUTE=yes',
            'GATEWAY=192.0.2.1',
            'DNS1=192.0.2.2',
            'ONBOOT=yes',
            'NM_CONTROLLED=no',
        ]
        self.assertSequenceEqual(generated, expected)

    def test_redhat_ipv6(self):
        """Test setting public IPv6 for Red Hat networking"""
        interface = {
            'label': 'public',
            'hwaddr': '00:11:22:33:44:55',
            'ipv6': [('2001:db8::42', 96)],
            'gateway6': '2001:db8::1',
            'dns': ['2001:db8::2'],
        }
        outfiles = self._run_test('redhat', eth0=interface)
        self.assertTrue('ifcfg-eth0' in outfiles)

        generated = outfiles['ifcfg-eth0'].rstrip().split('\n')
        expected = [
            '# Automatically generated, do not edit',
            '',
            '# Label public',
            'DEVICE=eth0',
            'BOOTPROTO=static',
            'HWADDR=00:11:22:33:44:55',
            'IPV6INIT=yes',
            'IPV6_AUTOCONF=no',
            'IPV6ADDR=2001:db8::42/96',
            'IPV6_DEFAULTGW=2001:db8::1%eth0',
            'DNS1=2001:db8::2',
            'ONBOOT=yes',
            'NM_CONTROLLED=no',
        ]
        self.assertSequenceEqual(generated, expected)

    def test_debian_ipv4(self):
        """Test setting public IPv4 for Debian networking"""
        interface = {
            'label': 'public',
            'hwaddr': '00:11:22:33:44:55',
            'ipv4': [('192.0.2.42', '255.255.255.0')],
            'gateway4': '192.0.2.1',
            'dns': ['192.0.2.2'],
        }
        outfiles = self._run_test('debian', eth0=interface)
        self.assertTrue('interfaces' in outfiles)

        generated = outfiles['interfaces'].rstrip().split('\n')
        expected = [
            '# Used by ifup(8) and ifdown(8). See the interfaces(5) '
            'manpage or',
            '# /usr/share/doc/ifupdown/examples for more information.',
            '# The loopback network interface',
            'auto lo',
            'iface lo inet loopback',
            '',
            '# Label public',
            'auto eth0',
            'iface eth0 inet static',
            '    address 192.0.2.42',
            '    netmask 255.255.255.0',
            '    gateway 192.0.2.1',
            '    dns-nameservers 192.0.2.2',
        ]
        self.assertSequenceEqual(generated, expected)

    def test_debian_ipv6(self):
        """Test setting public IPv6 for Debian networking"""
        interface = {
            'label': 'public',
            'hwaddr': '00:11:22:33:44:55',
            'ipv6': [('2001:db8::42', 96)],
            'gateway6': '2001:db8::1',
            'dns': ['2001:db8::2'],
        }
        outfiles = self._run_test('debian', eth0=interface)
        self.assertTrue('interfaces' in outfiles)

        generated = outfiles['interfaces'].rstrip().split('\n')
        expected = [
            '# Used by ifup(8) and ifdown(8). See the interfaces(5) '
            'manpage or',
            '# /usr/share/doc/ifupdown/examples for more information.',
            '# The loopback network interface',
            'auto lo',
            'iface lo inet loopback',
            '',
            '# Label public',
            'auto eth0',
            'iface eth0 inet6 static',
            '    address 2001:db8::42',
            '    netmask 96',
            '    gateway 2001:db8::1',
            '    dns-nameservers 2001:db8::2',
        ]
        self.assertSequenceEqual(generated, expected)

    def test_arch_legacy_ipv4(self):
        """Test setting public IPv4 for Arch legacy networking"""
        infiles = {
            '/etc/rc.conf': '\n'.join([
                'eth0="eth0 192.0.2.250 netmask 255.255.255.0"',
                'INTERFACES=(eth0)',
                'gateway="default gw 192.0.2.254"',
                'ROUTES=(gateway)']) + '\n'
        }
        interface = {
            'label': 'public',
            'hwaddr': '00:11:22:33:44:55',
            'ipv4': [('192.0.2.42', '255.255.255.0')],
            'gateway4': '192.0.2.1',
            'dns': ['192.0.2.2'],
        }
        outfiles = self._run_test('arch', infiles, eth0=interface,
                                  version='legacy')
        self.assertTrue('/etc/rc.conf' in outfiles)

        generated = outfiles['/etc/rc.conf'].rstrip().split('\n')
        expected = [
            'eth0="eth0 192.0.2.42 netmask 255.255.255.0"',
            'INTERFACES=(eth0)',
            'gateway="default gw 192.0.2.1"',
            'ROUTES=(gateway)',
        ]
        self.assertSequenceEqual(generated, expected)

    def test_arch_legacy_ipv6(self):
        """Test setting public IPv6 for Arch legacy networking"""
        infiles = {
            '/etc/rc.conf': '\n'.join([
                'eth0="eth0 add 2001:db8::fff0/96"',
                'INTERFACES=(eth0)',
                'gateway6="default gw 2001:db8::fffe"',
                'ROUTES=(gateway6)']) + '\n'
        }
        interface = {
            'label': 'public',
            'hwaddr': '00:11:22:33:44:55',
            'ipv6': [('2001:db8::42', 96)],
            'gateway6': '2001:db8::1',
            'dns': ['2001:db8::2'],
        }
        outfiles = self._run_test('arch', infiles, eth0=interface,
                                  version='legacy')
        self.assertTrue('/etc/rc.conf' in outfiles)

        generated = outfiles['/etc/rc.conf'].rstrip().split('\n')
        expected = [
            'eth0="eth0 add 2001:db8::42/96"',
            'INTERFACES=(eth0)',
            'gateway6="default gw 2001:db8::1"',
            'ROUTES=(gateway6)',
        ]
        self.assertSequenceEqual(generated, expected)

    def test_arch_netcfg_ipv4(self):
        """Test setting public IPv4 for Arch netcfg networking"""
        infiles = {
            '/etc/rc.conf': '\n'.join([
                'NETWORKS=()',
                'DAEMONS=(foo network bar)']) + '\n'
        }
        interface = {
            'label': 'public',
            'hwaddr': '00:11:22:33:44:55',
            'ipv4': [('192.0.2.42', '255.255.255.0')],
            'gateway4': '192.0.2.1',
            'dns': ['192.0.2.2'],
        }
        outfiles = self._run_test('arch', infiles, eth0=interface,
                                  version='netcfg')

        self.assertTrue('/etc/rc.conf' in outfiles)
        generated = outfiles['/etc/rc.conf'].rstrip().split('\n')
        expected = [
            'NETWORKS=(eth0)',
            'DAEMONS=(foo !network @net-profiles bar)',
        ]
        self.assertSequenceEqual(generated, expected)

        self.assertTrue('/etc/network.d/eth0' in outfiles)
        generated = outfiles['/etc/network.d/eth0'].rstrip().split('\n')
        expected = [
            '# Label public',
            'CONNECTION="ethernet"',
            'INTERFACE=eth0',
            'IP="static"',
            'ADDR="192.0.2.42"',
            'NETMASK="255.255.255.0"',
            'GATEWAY="192.0.2.1"',
            'DNS=(192.0.2.2)',
        ]
        self.assertSequenceEqual(generated, expected)

    def test_arch_netcfg_ipv6(self):
        """Test setting public IPv6 for Arch netcfg networking"""
        infiles = {
            '/etc/rc.conf': '\n'.join([
                'NETWORKS=()',
                'DAEMONS=(foo network bar)']) + '\n'
        }
        interface = {
            'label': 'public',
            'hwaddr': '00:11:22:33:44:55',
            'ipv6': [('2001:db8::42', 96)],
            'gateway6': '2001:db8::1',
            'dns': ['2001:db8::2'],
        }
        outfiles = self._run_test('arch', infiles, eth0=interface,
                                  version='netcfg')

        self.assertTrue('/etc/rc.conf' in outfiles)
        generated = outfiles['/etc/rc.conf'].rstrip().split('\n')
        expected = [
            'NETWORKS=(eth0)',
            'DAEMONS=(foo !network @net-profiles bar)',
        ]

        self.assertTrue('/etc/network.d/eth0' in outfiles)
        generated = outfiles['/etc/network.d/eth0'].rstrip().split('\n')
        expected = [
            '# Label public',
            'CONNECTION="ethernet"',
            'INTERFACE=eth0',
            'IP6="static"',
            'ADDR6="2001:db8::42/96"',
            'GATEWAY6="2001:db8::1"',
            'DNS=(2001:db8::2)',
        ]
        self.assertSequenceEqual(generated, expected)

    def test_gentoo_legacy_ipv4(self):
        """Test setting public IPv4 for Gentoo legacy networking"""
        interface = {
            'label': 'public',
            'hwaddr': '00:11:22:33:44:55',
            'ipv4': [('192.0.2.42', '255.255.255.0')],
            'gateway4': '192.0.2.1',
            'dns': ['192.0.2.2'],
        }
        outfiles = self._run_test('gentoo', eth0=interface, version='legacy')

        self.assertTrue('net' in outfiles)

        generated = outfiles['net'].rstrip()

        pattern = ('modules=\( "ifconfig" \)\n*' +
                   '# Label public\n*' +
                   'config_eth0=\(\s*"192.0.2.42 netmask 255.255.255.0"\s*\)\n*' +
                   'routes_eth0=\(\s*"default via 192.0.2.1"\s*\)\n*' +
                   'dns_servers_eth0=\(\s*"192.0.2.2"\s*\)').format(
                       ip=interface['ipv4'][0][0],
                       netmask=interface['ipv4'][0][1],
                       gateway=interface['gateway4'],
                       dns=interface['dns'][0]
                   )
        expected_regex = re.compile(pattern, re.MULTILINE)

        self.assertRegexpMatches(generated, expected_regex)

    def test_gentoo_legacy_ipv6(self):
        """Test setting public IPv6 for Gentoo legacy networking"""
        interface = {
            'label': 'public',
            'hwaddr': '00:11:22:33:44:55',
            'ipv6': [('2001:db8::42', 96)],
            'gateway6': '2001:db8::1',
            'dns': ['2001:db8::2'],
        }
        outfiles = self._run_test('gentoo', eth0=interface, version='legacy')

        self.assertTrue('net' in outfiles)

        generated = outfiles['net'].rstrip()
        pattern = ('modules=\( "ifconfig" \)\n*' +
                   '# Label public\n*' +
                   'config_eth0=\(\s*"{ip}/{netmask_len}"\s*\)\n*' +
                   'routes_eth0=\(\s*"default via {gateway}"\s*\)\n*' +
                   'dns_servers_eth0=\(\s*"{dns}"\s*\)').format(
                       ip=interface['ipv6'][0][0],
                       netmask_len=interface['ipv6'][0][1],
                       gateway=interface['gateway6'],
                       dns=interface['dns'][0]
                   )
        expected_regex = re.compile(pattern, re.MULTILINE)

        self.assertRegexpMatches(generated, expected_regex)

    def test_gentoo_openrc_ipv4(self):
        """Test setting public IPv4 for Gentoo OpenRC networking"""
        interface = {
            'label': 'public',
            'hwaddr': '00:11:22:33:44:55',
            'ipv4': [('192.0.2.42', '255.255.255.0')],
            'gateway4': '192.0.2.1',
            'dns': ['192.0.2.2'],
        }
        outfiles = self._run_test('gentoo', eth0=interface, version='openrc')

        self.assertTrue('net' in outfiles)

        generated = outfiles['net'].rstrip()
        pattern = ('modules="ifconfig"\n*' +
                   '# Label public\n*' +
                   'config_eth0="\s*{ip}/{netmask_len}\s*"\n*' +
                   'routes_eth0="\s*default via {gateway}\s*"\n*' +
                   'dns_servers_eth0="\s*{dns}"\s*').format(
                       ip=interface['ipv4'][0][0],
                       netmask_len=commands.network.NETMASK_TO_PREFIXLEN[
                           interface['ipv4'][0][1]
                       ],
                       gateway=interface['gateway4'],
                       dns=interface['dns'][0]
                   )
        expected_regex = re.compile(pattern, re.MULTILINE)

        self.assertRegexpMatches(generated, expected_regex)

    def test_gentoo_openrc_ipv6(self):
        """Test setting public IPv6 for Gentoo OpenRC networking"""
        interface = {
            'label': 'public',
            'hwaddr': '00:11:22:33:44:55',
            'ipv6': [('2001:db8::42', 96)],
            'gateway6': '2001:db8::1',
            'dns': ['2001:db8::2'],
        }
        outfiles = self._run_test('gentoo', eth0=interface, version='openrc')

        self.assertTrue('net' in outfiles)

        generated = outfiles['net'].rstrip()
        pattern = ('modules="ifconfig"\n*' +
                   '# Label public\n*' +
                   'config_eth0="\s*{ip}/{netmask_len}\s*"\n*' +
                   'routes_eth0="\s*default via {gateway}\s*"\n*' +
                   'dns_servers_eth0="\s*{dns}"\s*').format(
                       ip=interface['ipv6'][0][0],
                       netmask_len=interface['ipv6'][0][1],
                       gateway=interface['gateway6'],
                       dns=interface['dns'][0]
                   )
        expected_regex = re.compile(pattern, re.MULTILINE)

        self.assertRegexpMatches(generated, expected_regex)

    def test_suse_ipv4(self):
        """Test setting public IPv4 for SuSE networking"""
        interface = {
            'label': 'public',
            'hwaddr': '00:11:22:33:44:55',
            'ipv4': [('192.0.2.42', '255.255.255.0')],
            'gateway4': '192.0.2.1',
            'dns': ['192.0.2.2'],
        }
        outfiles = self._run_test('suse', eth0=interface)

        self.assertTrue('ifcfg-eth0' in outfiles)
        generated = outfiles['ifcfg-eth0'].rstrip().split('\n')
        expected = [
            "# Automatically generated, do not edit",
            "",
            "# Label public",
            "BOOTPROTO='static'",
            "IPADDR='192.0.2.42'",
            "NETMASK='255.255.255.0'",
            "STARTMODE='auto'",
            "USERCONTROL='no'",
        ]
        self.assertSequenceEqual(generated, expected)

    def test_suse_ipv6(self):
        """Test setting public IPv6 for SuSE networking"""
        interface = {
            'label': 'public',
            'hwaddr': '00:11:22:33:44:55',
            'ipv6': [('2001:db8::42', 96)],
            'gateway6': '2001:db8::1',
            'dns': ['2001:db8::2'],
        }
        outfiles = self._run_test('suse', eth0=interface)

        self.assertTrue('ifcfg-eth0' in outfiles)
        generated = outfiles['ifcfg-eth0'].rstrip().rstrip().split('\n')
        expected = [
            "# Automatically generated, do not edit",
            "",
            "# Label public",
            "BOOTPROTO='static'",
            "IPADDR='2001:db8::42'",
            "PREFIXLEN='96'",
            "STARTMODE='auto'",
            "USERCONTROL='no'",
        ]
        self.assertSequenceEqual(generated, expected)


if __name__ == "__main__":
    agent_test.main()
