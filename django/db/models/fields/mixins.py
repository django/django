NOT_PROVIDED = object()


class FieldCacheMixin:
    """Provide an API for working with the model's fields value cache."""

    def get_cache_name(self):
        raise NotImplementedError

    def get_cached_value(self, instance, default=NOT_PROVIDED):
        cache_name = self.get_cache_name()
        try:
            return instance._state.fields_cache[cache_name]
        except KeyError:
            # An ancestor link will exist if this field is defined on a
            # multi-table inheritance parent of the instance's class.
            ancestor_link = instance._meta.get_ancestor_link(self.model)
            if ancestor_link:
                try:
                    # The value might be cached on an ancestor if the instance
                    # originated from walking down the inheritance chain.
                    ancestor = ancestor_link.get_cached_value(instance)
                except KeyError:
                    pass
                else:
                    value = self.get_cached_value(ancestor)
                    # Cache the ancestor value locally to speed up future
                    # lookups.
                    self.set_cached_value(instance, value)
                    return value
            if default is NOT_PROVIDED:
                raise
            return default

    def is_cached(self, instance):
        return self.get_cache_name() in instance._state.fields_cache

    def set_cached_value(self, instance, value):
        instance._state.fields_cache[self.get_cache_name()] = value

    def delete_cached_value(self, instance):
        del instance._state.fields_cache[self.get_cache_name()]
