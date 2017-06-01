from django.db.models import Index


__all__ = ['GistIndex']


class GistIndex(Index):
    suffix = 'gist'
    max_name_length = 31

    def create_sql(self, model, schema_editor):
        if not self.name:
            self.set_name_with_model(model)
        errors = self.check_name()
        if len(self.name) > self.max_name_length:
            errors.append('Index names cannot be longer than %s characters.' % self.max_name_length)
        if errors:
            raise ValueError(errors)
        return super().create_sql(model, schema_editor, using=' USING gist')
