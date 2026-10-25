import subprocess

import pytest

from psp_buddy import launch

V4 = """
Active Connections

  Proto  Local Address          Foreign Address        State           PID
  TCP    0.0.0.0:135            0.0.0.0:0              LISTENING       1180
  TCP    127.0.0.1:45463        0.0.0.0:0              LISTENING       4242
  TCP    127.0.0.1:454630       0.0.0.0:0              LISTENING       9
  TCP    127.0.0.1:50001        127.0.0.1:45463        ESTABLISHED     77
"""
V6 = """
Active Connections

  Proto  Local Address          Foreign Address        State           PID
  TCP    [::]:135               [::]:0                 LISTENING       1180
  TCP    [::]:45463             [::]:0                 LISTENING       4242
"""


def fake_run(outputs, calls):
    def run(args, **kwargs):
        calls.append(args)
        out = outputs[args[-1]]
        if isinstance(out, Exception):
            raise out
        assert kwargs.get('timeout') and kwargs.get('check') is True
        return subprocess.CompletedProcess(args, 0, stdout=out, stderr='')
    return run


def listeners(monkeypatch, outputs, port=45463):
    calls = []
    monkeypatch.setattr(launch.subprocess, 'run', fake_run(outputs, calls))
    return launch.WindowsInspector().listeners(port), calls


def test_listeners_come_from_netstat_for_ipv4_and_ipv6(monkeypatch):
    found, calls = listeners(monkeypatch, {'TCP': V4, 'TCPv6': V6})
    assert found == (('127.0.0.1', 4242), ('::', 4242))
    assert [c[:4] for c in calls] == [['netstat', '-ano', '-p', 'TCP'],
                                      ['netstat', '-ano', '-p', 'TCPv6']]


def test_no_listener_on_the_port_is_an_empty_answer(monkeypatch):
    found, _ = listeners(monkeypatch, {'TCP': V4, 'TCPv6': V6}, port=45999)
    assert found == ()


def test_output_without_any_listening_row_fails_closed(monkeypatch):
    # e.g. a localized state name: never read that as "no listener".
    localized = V4.replace('LISTENING', 'ABHOEREN')
    with pytest.raises(ValueError):
        listeners(monkeypatch, {'TCP': localized, 'TCPv6': V6})


@pytest.mark.parametrize('row', [
    '  TCP    127.0.0.1:45463        0.0.0.0:0              LISTENING\n',
    '  TCP    127.0.0.1:45463        0.0.0.0:0              LISTENING       pid\n',
    '  TCP    127.0.0.1-45463        0.0.0.0:0              LISTENING       1\n',
])
def test_a_malformed_tcp_row_fails_closed(monkeypatch, row):
    with pytest.raises(ValueError):
        listeners(monkeypatch, {'TCP': V4 + row, 'TCPv6': V6})


@pytest.mark.parametrize('error', [
    subprocess.TimeoutExpired('netstat', 15), subprocess.CalledProcessError(1, 'netstat'),
    OSError('missing')])
def test_a_failed_netstat_fails_closed(monkeypatch, error):
    with pytest.raises(ValueError):
        listeners(monkeypatch, {'TCP': V4, 'TCPv6': error})
