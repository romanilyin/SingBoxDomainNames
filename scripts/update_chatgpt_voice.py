#!/usr/bin/env python3
"""Generate ChatGPTVoiceIPv4.txt from OpenAI's published Voice prefixes."""

import argparse
import http.client
import ipaddress
import json
import os
from pathlib import Path
import ssl
import sys
import tempfile
import urllib.error
import urllib.request


SOURCE_URL = "https://openai.com/chatgpt-voice.json"
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "ChatGPTVoiceIPv4.txt"
MAX_SOURCE_BYTES = 1024 * 1024
TIMEOUT_SECONDS = 30


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Require the published HTTPS endpoint, without following redirects."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_source():
    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=ssl.create_default_context()),
        NoRedirect(),
    )
    request = urllib.request.Request(
        SOURCE_URL,
        headers={"User-Agent": "SingBoxDomainNames-ChatGPTVoiceUpdater/1.0"},
    )
    with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
        payload = response.read(MAX_SOURCE_BYTES + 1)
    if len(payload) > MAX_SOURCE_BYTES:
        raise ValueError("source exceeds the 1 MiB size limit")
    return payload


def render_list(payload):
    document = json.loads(payload)
    if not isinstance(document, dict):
        raise ValueError("source must be a JSON object")
    prefixes = document.get("prefixes")
    if not isinstance(prefixes, list) or not prefixes:
        raise ValueError("source prefixes must be a nonempty array")

    networks = set()
    for index, entry in enumerate(prefixes):
        if not isinstance(entry, dict):
            raise ValueError(f"prefixes[{index}] must be an object")
        if "ipv4Prefix" not in entry and "ipv6Prefix" not in entry:
            raise ValueError(f"prefixes[{index}] has no IP prefix")
        for key, network_type in (
            ("ipv4Prefix", ipaddress.IPv4Network),
            ("ipv6Prefix", ipaddress.IPv6Network),
        ):
            if key not in entry:
                continue
            prefix = entry[key]
            if not isinstance(prefix, str):
                raise ValueError(f"prefixes[{index}].{key} must be a string")
            network = network_type(prefix, strict=True)
            if str(network) != prefix:
                raise ValueError(f"prefixes[{index}].{key} is not canonical CIDR")
            if key == "ipv4Prefix":
                networks.add(network)

    if not networks:
        raise ValueError("source contains no IPv4 prefixes")
    ordered = sorted(networks, key=lambda item: (int(item.network_address), item.prefixlen))
    return ("\n".join(str(network) for network in ordered) + "\n").encode("ascii")


def write_atomic(output, content):
    """Replace the output only after the complete new file has been written."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=output.parent, prefix=f".{output.name}.", suffix=".tmp", delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true", help="check freshness without writing")
    args = parser.parse_args(argv)
    try:
        content = render_list(fetch_source())
        existing = args.output.read_bytes() if args.output.exists() else None
        if existing == content:
            print(f"Up to date: {args.output} ({len(content.splitlines())} IPv4 prefixes)")
            return 0
        if args.check:
            print(f"Out of date: {args.output}", file=sys.stderr)
            return 1
        write_atomic(args.output, content)
        print(f"Updated: {args.output} ({len(content.splitlines())} IPv4 prefixes)")
        return 0
    except (OSError, ValueError, urllib.error.URLError, http.client.HTTPException) as error:
        print(f"ChatGPT Voice update failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
