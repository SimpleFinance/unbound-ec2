# unbound-ec2

<img src="https://travis-ci.org/SimpleFinance/unbound-ec2.png?branch=master" />

This module uses the [Unbound](http://unbound.net) DNS resolver to answer simple DNS queries using EC2 API calls. For example, the following query would match an EC2 instance with a `Name` tag of `foo.example.com`:

```
$ dig -p 5003 @127.0.0.1 foo.dev.example.com
[1380410835] unbound[25204:0] info: unbound_ec2: handling forward query for foo.dev.example.com.

; <<>> DiG 9.8.1-P1 <<>> -p 5003 @127.0.0.1 foo.dev.example.com
; (1 server found)
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 5696
;; flags: qr aa rd ra; QUERY: 1, ANSWER: 2, AUTHORITY: 0, ADDITIONAL: 0

;; QUESTION SECTION:
;foo.dev.example.com.	IN	A

;; ANSWER SECTION:
foo.dev.example.com. 300 IN	A	10.0.0.2
foo.dev.example.com. 300 IN	A	10.0.0.1

;; Query time: 81 msec
;; SERVER: 127.0.0.1#5003(127.0.0.1)
;; WHEN: Sat Sep 28 23:27:16 2013
;; MSG SIZE  rcvd: 77
```

## Installation

On Ubuntu, install the `unbound`, `python-unbound`, and `python-boto` system packages. Then, install `unbound_ec2`:

```
wget -qO- https://raw.github.com/whilp/unbound-ec2/master/unbound_ec2.py | sudo tee /path/to/unbound_ec2.py > /dev/null
```

The following settings must be added to your Unbound configuration:

```
server:
    chroot: ""
    module-config: "validator python iterator"

python:
    python-script: "/path/to/unbound_ec2.py"
```

You'll also probably want to set some configuration specific to `unbound_ec2`; on Ubuntu:

```
cat <<EOF | sudo tee -a /etc/default/unbound > /dev/null
export ZONE=yourdomain.instead.of.example.com
export TTL=60
export EC2_ENDPOINT=ec2.us-west-2.amazonaws.com
EOF
```

You can also define `AWS_ACCESS_KEY` and `AWS_SECRET_ACCESS_KEY` entries in the environment directory. When `unbound_ec2` is run on an EC2 instance, though, it will automatically use an IAM instance profile if one is available.

## Considerations

`unbound_ec2` queries the EC2 API to answer requests about names inside the specified `ZONE`. All other requests are handled normally by Unbound's caching resolver. For requests for names within the specified `ZONE`, `unbound_ec2` calls [`DescribeInstances`](http://docs.aws.amazon.com/AWSEC2/latest/APIReference/ApiReference-query-DescribeInstances.html) and filters the results by instance state and tag name. Only instances in the `running` state with a `Name` tag matching the DNS request will be returned by the API query. When more than one instance matches the `DescribeInstances` query, `unbound_ec2` will return multiple A records in a round-robin. The query results are cached by Unbound, and a TTL (default: five minutes) is defined to encourage well-behaved clients to cache the information themselves.

Public addresses, IPv6, and reverse DNS lookups (PTR) are not yet supported.

## Testing

This repository includes a test configuration. Run it as follows:

```
unbound -c unbound_ec2.conf
```

### On Mac

Edit the `unbound` formula:

```
brew edit unbound
```

And drop in the following:

```ruby
require 'formula'

class Unbound < Formula
  homepage 'http://www.unbound.net'
  url 'http://www.unbound.net/downloads/unbound-1.4.21.tar.gz'
  sha1 '3ef4ea626e5284368d48ab618fe2207d43f2cee1'

  depends_on 'ldns'
  depends_on 'swig'

  def install
    # gost requires OpenSSL >= 1.0.0, and support built into ldns
    system "./configure", "--prefix=#{prefix}",
                          "--disable-gost",
                          "--with-pythonmodule"
    system "make install"
  end
end
```

Then install as normal:

```
brew install unbound
```

## License

```
Copyright (c) 2013 Will Maier <wcmaier@m.aier.us>

Permission to use, copy, modify, and distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
```
