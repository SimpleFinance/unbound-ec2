from unbound_ec2 import lookup
from unboundmodule import invalidateQueryInCache, log_warn


class CacheInvalidator:
    """Lookup cache invalidator
    """

    def __init__(self, server):
        self.server = server

    def invalidate(self):
        """Invalidates lookup cache for provided server instance.
        Only CacheLookup instances will be processed.

        """
        if isinstance(self.server.lookup, lookup.CacheLookup):
            srv_lookup = self.server.lookup
            old_cache = srv_lookup.resolve()
            srv_lookup.invalidate()
            new_cache = srv_lookup.resolve()

            for key in old_cache:
                if key in new_cache and old_cache[key] == new_cache[key]:
                    pass
                elif key in self.server.cached_requests:
                    qst = self.server.cached_requests.pop(key)['qstate']
                    invalidateQueryInCache(qst, qst.qinfo)
        else:
            log_warn('Tried to invalidate direct lookup!')
