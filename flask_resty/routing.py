from werkzeug.routing import RequestSlash, RoutingException, Rule

# -----------------------------------------------------------------------------


class StrictRule(Rule):
    def match(self, path, method=None):
        try:
            result = super(StrictRule, self).match(path, method)
        except RequestSlash:
            return None

        return result
