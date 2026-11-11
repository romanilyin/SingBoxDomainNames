# Routing lists

## ChatGPT Voice IPv4

[ChatGPTVoiceIPv4.txt](ChatGPTVoiceIPv4.txt) contains one IPv4 CIDR per line,
generated from `prefixes[*].ipv4Prefix` in OpenAI's official
[ChatGPT Voice IP list](https://openai.com/chatgpt-voice.json). Use it as a remote
IPv4 subnet list in the routing section that should carry ChatGPT Voice traffic.
It is separate from the domain lists. IPv6 prefixes, if published, are validated
but are not included in this IPv4 list.

The GitHub Actions workflow refreshes this file daily at 04:25 UTC and supports
manual runs. It commits only when the generated list changes. Upstream changes
reach clients after their next remote-list refresh. Repository rules must allow
the workflow's `GITHUB_TOKEN` to push to the default branch.

To refresh manually with Python 3.12 or later:

```sh
python scripts/update_chatgpt_voice.py
python scripts/update_chatgpt_voice.py --check
```

The updater verifies TLS, limits response size and network wait time, rejects
malformed or empty data, removes duplicates, and sorts numerically. It replaces
the file atomically only after complete validation. `--check` does not write and
returns a nonzero status if the checked-in list is stale or upstream is invalid.
