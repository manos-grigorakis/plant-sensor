import logging
import socket

log = logging.getLogger('dns')

class DnsServer:
    DNS_PORT = 53
    HEADER_SIZE = 12

    def __init__(self, ip) -> None:
        # '192.168.4.1' -> b'\xc0\xa8\x04\x01'
        self.ip_bytes = bytes(int(part) for part in ip.split('.'))
        self.socket = None

    def start(self) -> socket.socket:
        """Create a UDP socket

        :return: The socket object
        """
        # Create a UDP over IPv4 socket for DNS
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('', self.DNS_PORT))
        log.info('DNS server started on port %s', self.DNS_PORT)
        return self.socket

    def handle(self) -> None:
        """Read one query and send back the answer, call only when socket is readable"""
        try:
            query, client = self.socket.recvfrom(256)

            # Ignore anything too short to be a DNS query
            if len(query) <= self.HEADER_SIZE:
                log.debug('Ignored short DNS packet from %s', client[0])
                return

            log.debug('DNS query from %s', client[0])
            self.socket.sendto(self._build_response(query), client)
        except (OSError, ValueError) as error:
            log.warning('DNS query failed: %s', error)

    def _build_response(self, query) -> bytes:
        """Builds a DNS answer that points the queried name to our IP address

        :param query: The raw DNS query bytes
        :return: The raw DNS response bytes
        """
        # The question starts after the 12byte header, the name ends at the first zero byte
        name_end = query.index(b'\x00', self.HEADER_SIZE) + 1

        # Question = name + 2 byte type + 2 byte class
        question = query[self.HEADER_SIZE:name_end + 4]
        is_a_record = query[name_end:name_end + 2] == b'\x00\x01'

        # Header = same ID as the query + flags (response, no error) + 1 question + answer count
        # + 0 authority records + 0 additional records
        answer_count = b'\x00\x01' if is_a_record else b'\x00\x00'
        header = query[:2] + b'\x81\x80' + b'\x00\x01' + answer_count + b'\x00\x00\x00\x00'

        # Only IPv4 (A) questions get an IP
        if not is_a_record:
            return header + question

        # Answer = pointer to the name, type A, class IN, TTL 60s, 4 bytes of data, then the IP
        answer = b'\xc0\x0c\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04' + self.ip_bytes
        return header + question + answer