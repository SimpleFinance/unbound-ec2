from collections import defaultdict
import itertools
import copy


class DirectLookup:
    """Looks up all names that correspond to provided filter.
    Every resolve call will result EC2 describe instances query.
    """

    def __init__(self, ec2, zone, _filter, tag_name_include_domain=False):
        self.ec2 = ec2
        self.domain = zone.strip('.')
        self.filter = copy.deepcopy(_filter)
        if tag_name_include_domain:
            self.filter['tag:Name'] = '*%s' % self.domain

    def resolve(self):
        result = defaultdict(list)
        reservations = self.ec2.get_all_reservations(filters=self.filter)
        for instance in itertools.chain(*(i.instances for i in reservations)):
            for name, addresses in self._lookup(instance).items():
                result[name].extend(addresses)
        return result

    def lookup(self, name):
        return self.resolve()[name.rstrip('.')]

    def _lookup(self, instance):
        result = defaultdict(list)

        # We can support multiple names by comma-separating them.
        if 'Name' in instance.tags:
            names = instance.tags['Name'].split(',')
            for name in names:
                lookup_name = name if self.domain in name else '%s.%s' % (name, self.domain)
                result[lookup_name].append(instance)

        # We want instance-id to be a cname to the instance
        id_lookup_name = "%s.%s" % (instance.id, self.domain)
        result[id_lookup_name].append(instance)

        return result


class CacheLookup(DirectLookup):
    """Looks up all names that correspond to provided filter and cache the results.
    First resolve call will result EC2 describe instances query. All consecutive requests
    will hit the existing cache.
    """

    def __init__(self, ec2, zone, filter, tag_name_include_domain=False):
        DirectLookup.__init__(self, ec2, zone, filter, tag_name_include_domain)
        self.cache = defaultdict(list)

    def invalidate(self, lookup_name=None):
        if lookup_name:
            self.cache.pop(lookup_name)
        else:
            self.cache.clear()

    def resolve(self):
        if len(self.cache) < 1:
            self.cache = DirectLookup.resolve(self)
        return self.cache
