"""WARC/WET readers (provided by the course; see NOTICE).
"""
from warcio.archiveiterator import ArchiveIterator
from typing import Optional, Iterator, Tuple




def read_warc_file(fname: str, num_to_read: Optional[int] = None) -> Iterator[Tuple[str, bytes]]:
    """Parses a warc file.
    Args:
        fname (str): File name of the WARC file.
        num_to_read (int, optional): Number of records to read. Useful for debugging. If None, reads all records.

    Returns:
        An iterator yielding (URL, HTML content) tuples.
    """
    count = 0
    with open(fname, 'rb') as stream:
        for record in ArchiveIterator(stream):
            if (record.rec_type == 'response') and (record.http_headers.get_header('Content-Type') == 'text/html'):
                url = record.rec_headers.get_header('WARC-Target-URI')
                html = record.content_stream().read()
                count += 1
                yield (url,  bytes(html))
            if num_to_read and count == num_to_read:
                break


def read_wet_file(fname, num_to_read=None):
    """Parses a warc file.
    Args:
        fname (str): File name of the WARC file.
        num_to_read (int, optional): Number of records to read. Useful for debugging. If None, reads all records.

    Returns:
        An iterator yielding (URL, text) tuples.
    """

    count = 0
    with open(fname, 'rb') as stream:
        for record in ArchiveIterator(stream):
            if (record.rec_type == 'conversion') and (record.rec_headers.get_header('Content-Type') == 'text/plain'):
                url = record.rec_headers.get_header('WARC-Target-URI')
                text = record.content_stream().read()
                yield (url,  text)
                count += 1
            if num_to_read and count == num_to_read:
                break
