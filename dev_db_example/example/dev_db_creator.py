from dev_db.creator import DevDBCreator

from .models import Extra


class ExampleDevDBCreator(DevDBCreator):
    def get_excluded_models(self):
        return super().get_excluded_models() + ["extra"]

    def add_extra_data(self, data):
        data.append(Extra.objects.first())
        return data
